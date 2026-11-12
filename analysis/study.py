"""Study tooling: python -m analysis.study <summary|export|import> [db]

summary : per-arm outcomes from the system's own scorer + permutation tests, bootstrap CIs, effect sizes.
export  : anonymised, shuffled first/last arguments for BLIND human raters (arm hidden) -> analysis/rater_sheet.csv
import  : read completed rater scores and compare arms using HUMAN ratings (the credible outcome measure).
The system's own scorer is the same instrument that drives the adaptation, so human ratings are the primary outcome.
"""
import random
import sys

import numpy as np
import pandas as pd

from app.db import Database

SEED = 2026


def session_table(db):
    rows = db.all("""SELECT s.session_id, s.user_id, s.mode, t.turn_number, t.turn_id, t.student_argument, d.overall_score
        FROM debate_sessions s JOIN debate_turns t ON t.session_id=s.session_id
        JOIN weakness_diagnoses d ON d.turn_id=t.turn_id ORDER BY s.session_id, t.turn_number""")
    return pd.DataFrame(rows)


def per_session(df):
    if df.empty:  # no turns stored yet
        return pd.DataFrame(columns=["session_id", "user_id", "mode", "turns", "first", "last", "change", "first_turn_id", "last_turn_id", "first_arg", "last_arg"])
    out = []
    for sid, g in df.groupby("session_id"):
        if len(g) < 2:
            continue
        out.append({"session_id": sid, "user_id": g.user_id.iloc[0], "mode": g["mode"].iloc[0], "turns": len(g),
                    "first": g.overall_score.iloc[0], "last": g.overall_score.iloc[-1],
                    "change": g.overall_score.iloc[-1] - g.overall_score.iloc[0],
                    "first_turn_id": int(g.turn_id.iloc[0]), "last_turn_id": int(g.turn_id.iloc[-1]),
                    "first_arg": g.student_argument.iloc[0], "last_arg": g.student_argument.iloc[-1]})
    return pd.DataFrame(out)


def perm_test(a, b, n=20000, rng=None):
    rng = rng or np.random.default_rng(SEED)
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs, pool = a.mean() - b.mean(), np.concatenate([a, b])
    cnt = 0
    for _ in range(n):
        rng.shuffle(pool)
        cnt += abs(pool[:len(a)].mean() - pool[len(a):].mean()) >= abs(obs) - 1e-12
    return obs, (cnt + 1) / (n + 1)


def boot_ci(a, b, n=10000, rng=None):
    rng = rng or np.random.default_rng(SEED)
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return np.percentile(d, [2.5, 97.5])


def cohens_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return (a.mean() - b.mean()) / sp if sp else float("nan")


def compare(ps, col, ref="adaptive"):
    res = []
    for arm in sorted(set(ps["mode"]) - {ref}):
        a, b = ps[ps["mode"] == ref][col], ps[ps["mode"] == arm][col]
        if len(a) < 3 or len(b) < 3:
            res.append(f"{ref} vs {arm}: not enough sessions (n={len(a)} vs {len(b)})")
            continue
        diff, p = perm_test(a, b)
        lo, hi = boot_ci(a, b)
        res.append(f"{ref} vs {arm}: mean diff {diff:+.2f} (95% CI {lo:+.2f}..{hi:+.2f}), d={cohens_d(a, b):.2f}, permutation p={p:.4f}, n={len(a)} vs {len(b)}")
    return res


def summary(db):
    ps = per_session(session_table(db))
    if ps.empty:
        print("No completed multi-turn sessions yet.")
        return
    print(ps.groupby("mode")[["first", "last", "change"]].agg(["mean", "std", "count"]).round(2).to_string())
    print("\nChange in overall score (system scorer):")
    print("\n".join(compare(ps, "change")))
    print("\nNOTE: adaptation and measurement share one scorer. Confirm with blind human ratings (export/import).")


def export(db, out="analysis/rater_sheet.csv"):
    ps = per_session(session_table(db))
    rows = []
    for _, r in ps.iterrows():
        for when, arg in (("first", r.first_arg), ("last", r.last_arg)):
            rows.append({"item_id": f"S{int(r.session_id)}-{when}", "argument": arg, **{k: "" for k in
                         ("claim_clarity", "evidence_quality", "warrant_strength", "relevance", "rebuttal_readiness", "logical_validity", "qualification")}})
    random.Random(SEED).shuffle(rows)  # shuffled; arm and first/last not revealed by order
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"{len(rows)} items written to {out}. Give to >=2 raters independently, who score each 1-5 using Appendix A. Do not share arm labels.")


def import_ratings(db, *files):
    ps = per_session(session_table(db))
    dims = ["claim_clarity", "evidence_quality", "warrant_strength", "relevance", "rebuttal_readiness", "logical_validity", "qualification"]
    frames = [pd.read_csv(f) for f in files]
    allr = pd.concat(frames)
    allr["overall"] = allr[dims].mean(axis=1)
    mean = allr.groupby("item_id").overall.mean()
    ps["h_first"] = ps.session_id.map(lambda s: mean.get(f"S{int(s)}-first"))
    ps["h_last"] = ps.session_id.map(lambda s: mean.get(f"S{int(s)}-last"))
    ps["h_change"] = ps.h_last - ps.h_first
    ps = ps.dropna(subset=["h_change"])
    print(ps.groupby("mode").h_change.agg(["mean", "std", "count"]).round(2).to_string())
    print("\n".join(compare(ps, "h_change")))
    if len(frames) >= 2:
        from sklearn.metrics import cohen_kappa_score
        a, b = frames[0].set_index("item_id")[dims].stack(), frames[1].set_index("item_id")[dims].stack()
        k = cohen_kappa_score(a.astype(int), b.reindex(a.index).astype(int), weights="quadratic")
        print(f"\nInter-rater agreement (quadratic weighted kappa, rater 1 vs 2): {k:.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    db = Database(sys.argv[2] if len(sys.argv) > 2 and cmd != "import" else "debate.db")
    if cmd == "summary":
        summary(db)
    elif cmd == "export":
        export(db)
    elif cmd == "import":
        import_ratings(db, *sys.argv[2:])
