"""One results file, every number from stored data:  python -m analysis.report [db_path] [--out results_summary.md]
Builds provenance, the latest test-split diagnostic run, pilot tables and (if several arms exist) the comparison, then runs
consistency checks (the same participant count everywhere) and adds hedged wording that matches what the data can support."""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

from analysis.pilot import change_stats, per_participant, ratings
from analysis.study import compare, per_session, session_table
from app.db import Database


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
    files = sorted(glob.glob(f"{res_dir}/*_test_*.json"))
    return json.load(open(files[-1])) if files else None


def build(db, out="results_summary.md", res_dir="eval/results"):
    L = ["# Results summary (generated; do not edit numbers by hand)\n"]
    meta = latest_test_meta(res_dir)
    L.append("## Provenance\n")
    if meta:
        runs = meta.get("test_split_runs_so_far", "unknown")
        L.append(f"- Diagnostic run: backend `{meta['backend']}`, model `{meta['model']}`, date {meta['date']}, prompt fingerprint `{meta['prompt_hash']}`")
        L.append(f"- Test split evaluated {runs} time(s); human reference labels: {meta['human_reference_labels']}")
    else:
        L.append("- No test-split diagnostic run found yet.")
    L.append("\n## Diagnostic agreement (test split)\n")
    if meta:
        s = meta["system"]
        L.append(f"Accuracy {s['correct']}/{s['n']} = {s['accuracy']:.1%} (95% Wilson interval {s['ci95'][0]:.1%} to {s['ci95'][1]:.1%}), kappa {s['kappa']:.2f}.")
        for name, b in meta["baselines"].items():
            L.append(f"- Baseline {name}: accuracy {b['accuracy']:.1%}")
        if "human_labeller_kappa" in meta:
            L.append(f"- Human labellers' own agreement: kappa {meta['human_labeller_kappa']:.2f}")
        if not meta["human_reference_labels"]:
            L.append("\n**WARNING: reference labels are not human labels; do not report these figures.**")
    pp = per_participant(db, "adaptive")
    L.append("\n## Pilot: turn-level change\n")
    L.append(md(pp))
    warn = []
    if len(pp):
        st = change_stats(pp)
        L.append(f"\n{claim_wording(st)}\n")
    L.append("\n## Pilot: participant ratings\n")
    rt = ratings(db)
    L.append(md(rt))
    ps = per_session(session_table(db))
    if len(ps) and ps["mode"].nunique() > 1:
        L.append("\n## Arm comparison (system scorer; confirm with blind human ratings)\n")
        L += [f"- {line}" for line in compare(ps, "change")]
    n_users = db.one("SELECT COUNT(DISTINCT user_id) n FROM debate_sessions")["n"]
    n_rated = db.one("SELECT COUNT(DISTINCT user_id) n FROM feedback")["n"]
    if len(pp) and n_rated and n_rated != len(pp):
        warn.append(f"{len(pp)} participants have 2+ turns but {n_rated} submitted ratings: state the same n everywhere or explain the difference.")
    if n_users != len(pp) and len(pp):
        warn.append(f"{n_users} participants created sessions but {len(pp)} appear in the turn-level table: report who was excluded and why.")
    L.append("\n## Consistency checks\n")
    L += [f"- WARNING: {w}" for w in warn] or ["- Participant counts agree across tables."]
    open(out, "w").write("\n".join(L) + "\n")
    return "\n".join(L)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "results_summary.md"
    if out in args:
        args.remove(out)
    print(build(Database(args[0] if args else "debate.db"), out))
