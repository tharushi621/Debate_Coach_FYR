"""Pilot tables straight from the database:  python -m analysis.pilot [db_path] [mode]
Prints the equivalents of thesis Table 7.25 (ratings), Table 7.26 (turn-level change) and the improvement statistics.

'Targeted weakness improved' (defined here so the thesis can state it once): for each pair of consecutive turns, the score on the
dimension that was diagnosed in the earlier turn must rise. All pairs rise = Yes, some = Partly, none = No."""
import sys

import numpy as np
import pandas as pd

from app.db import Database
from app.taxonomy import WEAKNESS_TO_DIMENSION

ASPECTS = [("ease_of_use", "Ease of use"), ("clarity", "Clarity of feedback"), ("ai_relevance", "Relevance of AI response"),
           ("weakness_help", "Helpfulness in identifying weakness"), ("improvement_help", "Helpfulness in improving next argument"),
           ("fairness", "Fairness of assessment"), ("reuse", "Willingness to use again")]


def per_participant(db, mode="adaptive"):
    rows = db.all("""SELECT s.session_id, u.name, t.turn_id, d.weakness, d.overall_score FROM debate_sessions s
        JOIN users u ON u.user_id=s.user_id JOIN debate_turns t ON t.session_id=s.session_id
        JOIN weakness_diagnoses d ON d.turn_id=t.turn_id WHERE s.mode=? ORDER BY s.session_id, t.turn_number""", (mode,))
    out = []
    for sid in sorted({r["session_id"] for r in rows}):
        turns = [r for r in rows if r["session_id"] == sid]
        if len(turns) < 2:
            continue
        scores = [db.turn_scores(t["turn_id"]) for t in turns]
        pairs = []
        for i in range(len(turns) - 1):
            dim = WEAKNESS_TO_DIMENSION[turns[i]["weakness"]]
            pairs.append(scores[i + 1][dim] > scores[i][dim])
        share = sum(pairs) / len(pairs)
        out.append({"Participant": turns[0]["name"], "Turns": len(turns), "Turn 1 overall": turns[0]["overall_score"],
                    "Final overall": turns[-1]["overall_score"], "Change": round(turns[-1]["overall_score"] - turns[0]["overall_score"], 2),
                    "Initial weakness": turns[0]["weakness"], "Final weakness": turns[-1]["weakness"],
                    "Targeted weakness improved": "Yes" if share == 1 else "No" if share == 0 else "Partly"})
    return pd.DataFrame(out)


def ratings(db):
    df = pd.DataFrame(db.all("SELECT * FROM feedback"))
    if df.empty:
        return df
    return pd.DataFrame([{"Evaluation aspect": label, "Mean /5": round(df[k].mean(), 2),
                          "SD": round(df[k].std(ddof=1), 2) if len(df) > 1 else float("nan"), "n": int(df[k].count())} for k, label in ASPECTS])


def change_stats(pp, seed=2026):
    ch = pp["Change"].to_numpy(float)
    rng = np.random.default_rng(seed)
    lo, hi = np.percentile([rng.choice(ch, len(ch)).mean() for _ in range(10000)], [2.5, 97.5])
    res = {"n": len(ch), "improved": int((ch > 0).sum()), "mean_change": round(float(ch.mean()), 2), "bootstrap_95ci": (round(float(lo), 2), round(float(hi), 2))}
    try:
        from scipy.stats import wilcoxon
        if len(ch) >= 6 and np.any(ch != 0):
            res["wilcoxon_signed_rank_p"] = round(float(wilcoxon(ch).pvalue), 4)
    except Exception:
        pass
    return res


if __name__ == "__main__":
    db = Database(sys.argv[1] if len(sys.argv) > 1 else "debate.db")
    mode = sys.argv[2] if len(sys.argv) > 2 else "adaptive"
    pp = per_participant(db, mode)
    print(f"== Turn-level change (Table 7.26 equivalent), mode={mode} ==")
    print(pp.to_string(index=False) if not pp.empty else "no sessions with 2+ turns yet")
    if not pp.empty:
        print("\n" + str(change_stats(pp)))
    r = ratings(db)
    print("\n== Participant ratings (Table 7.25 equivalent) ==")
    print(r.to_string(index=False) if not r.empty else "no ratings yet")
