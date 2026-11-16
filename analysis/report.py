"""One results file, every number from stored data:
  python -m analysis.report [db_path] [--out results_summary.md] [--since YYYY-MM-DD] [--exclude nick1,nick2]

Builds provenance, the latest test-split diagnostic run (from eval.diagnostic_eval), the pilot tables from real adaptive
sessions, a cross-check against the figures printed in the submitted thesis, and consistency checks (the same participant count
everywhere). The wording it adds matches what the data can support.
The thesis has no control group (7.12), so there is no arm comparison here."""
import glob
import json
import os
import sys

from analysis.pilot import _skip, change_stats, per_participant, ratings
from app.db import Database

# Figures printed in the submitted thesis (Sections 7.9 and 7.10), for the viva cross-check only.
THESIS = [("participants in the pilot (7.9)", 7), ("participants listed in Table 7.26", 5),
          ("participants named in the 7.10 text", 10), ("participants who improved (7.10 text)", 8),
          ("cases where the weakness changed after turn 1 (7.10 text)", 4)]
THESIS_TURNS = 5  # thesis 7.9: each pilot session had 5 debate turns


def md(df):
    if df is None or len(df) == 0:
        return "_no data yet_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def claim_wording(stats):
    n = stats["n"]
    if n < 6:
        return f"Only {n} participants: report individual results; make no inferential statement."
    lo, hi = stats["bootstrap_95ci"]
    base = f"{stats['improved']} of {n} participants improved; mean change {stats['mean_change']:+.2f} (95% bootstrap interval {lo:+.2f} to {hi:+.2f})."
    if lo > 0:
        return base + " Preliminary evidence of improvement; without a control group this cannot be attributed to the system."
    if hi < 0:
        return base + " Scores fell on average."
    return base + " Inconclusive: the interval includes zero."


def latest_test_meta(res_dir="eval/results"):
    """The most recently written test-split result file (by modification time, not by file name)."""
    files = glob.glob(f"{res_dir}/*_test_*.json")
    if not files:
        return None
    with open(max(files, key=os.path.getmtime), encoding="utf-8") as fh:
        return json.load(fh)


def _participants_with_sessions(db, since, exclude):
    """Distinct real participants with an adaptive session: same since/exclude filters as the pilot tables,
    so developer and test accounts do not trigger a false warning."""
    q = ("SELECT DISTINCT u.user_id, u.name FROM debate_sessions s JOIN users u ON u.user_id=s.user_id WHERE s.mode='adaptive'"
         + (" AND s.created_at>=?" if since else ""))
    rows = db.all(q, (since,) if since else ())
    skip = _skip(exclude)
    return len({r["user_id"] for r in rows if (r["name"] or "").lower() not in skip})


def build(db, out="results_summary.md", res_dir="eval/results", since=None, exclude=()):
    L = ["# Results summary (generated; do not edit numbers by hand)\n"]
    meta = latest_test_meta(res_dir)
    L.append("## Provenance\n")
    if meta:
        runs = meta.get("test_split_runs_so_far", "unknown")
        L.append(f"- Diagnostic run: backend `{meta.get('backend')}`, model `{meta.get('model')}`, date {meta.get('date')}, "
                 f"prompt fingerprint `{meta.get('prompt_hash')}`, DIAG_USE_LLM={meta.get('diag_use_llm')}")
        L.append(f"- Test split evaluated {runs} time(s)")
    else:
        L.append("- No test-split diagnostic run found yet.")
    L.append("\n## Diagnostic agreement (test split, two human labellers)\n")
    if meta and meta.get("system"):
        s = meta["system"]
        ci = s.get("ci95") or (float("nan"), float("nan"))
        L.append(f"Accuracy {s.get('correct')}/{s.get('n')} = {s.get('accuracy', float('nan')):.1%} "
                 f"(95% Wilson interval {ci[0]:.1%} to {ci[1]:.1%}), kappa {s.get('kappa', float('nan')):.2f}.")
        for name, b in meta.get("baselines", {}).items():
            L.append(f"- Baseline {name}: accuracy {b['accuracy']:.1%}")
        if "human_labeller_kappa" in meta:
            L.append(f"- Human labellers' own agreement: kappa {meta['human_labeller_kappa']:.2f}")
        L.append(f"- LLM diagnosis accepted {meta.get('llm_diagnosis_accepted', 'n/a')} times; rule fallback used {meta.get('rule_fallback_used', 'n/a')} times")
        L.append("- This is an additional protocol on researcher-prepared test arguments; the thesis (7.7) reports 24/30 = 80% "
                 "on its first set of 30 arguments, so the two figures are not directly comparable.")
    else:
        L.append("_no data yet_")

    pp = per_participant(db, "adaptive", 2, since, exclude, anonymise=True)
    L.append("\n## Pilot: turn-level change (adaptive sessions)\n")
    L.append(md(pp))
    st = change_stats(pp) if len(pp) else None
    if st:
        L.append(f"\n{claim_wording(st)}\n")
    L.append("\n## Pilot: participant ratings\n")
    rt = ratings(db, "adaptive", since, exclude)
    L.append(md(rt))

    L.append("\n## Cross-check against the submitted thesis (for the viva)\n")
    data = {"participants in the pilot (7.9)": len(pp), "participants listed in Table 7.26": len(pp),
            "participants named in the 7.10 text": len(pp),
            "participants who improved (7.10 text)": st["improved"] if st else 0,
            "cases where the weakness changed after turn 1 (7.10 text)": st.get("weakness_changed_after_turn1", 0) if st else 0}
    for label, thesis_value in THESIS:
        v = data[label]
        L.append(f"- NOTE: {label}: thesis says {thesis_value}, stored data gives {v}" + ("" if v == thesis_value else "  <- differs; know which figure you will defend"))

    n_users = _participants_with_sessions(db, since, exclude)
    n_rated = int(rt["n"].max()) if rt is not None and len(rt) else 0
    warn = []
    if len(pp) and n_rated and n_rated != len(pp):
        warn.append(f"{len(pp)} participants have 2+ turns but {n_rated} submitted ratings: state the same n everywhere or explain the difference.")
    if len(pp) and n_users != len(pp):
        warn.append(f"{n_users} participants created sessions but {len(pp)} appear in the turn-level table: report who was excluded and why.")
    if len(pp):
        short = int((pp["Turns"] != THESIS_TURNS).sum())
        if short:
            warn.append(f"{short} participant(s) did not complete {THESIS_TURNS} turns (thesis 7.9 says each session had {THESIS_TURNS}): "
                        "check the Turns column and state how many turns each session really had.")
    L.append("\n## Consistency checks\n")
    L += [f"- WARNING: {w}" for w in warn] or ["- Participant counts and turns agree with the thesis setup."]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return "\n".join(L)


if __name__ == "__main__":
    a = sys.argv[1:]
    flag = lambda name, default=None: a[a.index(name) + 1] if name in a else default
    positional = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    print(build(Database(positional[0] if positional else "debate.db"), flag("--out", "results_summary.md"),
                since=flag("--since"), exclude=(flag("--exclude", "") or "").split(",")))