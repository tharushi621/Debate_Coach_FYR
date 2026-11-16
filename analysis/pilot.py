"""Pilot tables straight from the database:
  python -m analysis.pilot [db_path] [--since YYYY-MM-DD] [--exclude nick1,nick2] [--min-turns N]

Prints the equivalents of thesis Table 7.25 (ratings), Table 7.26 (turn-level change) and the improvement statistics.
Only 'adaptive' sessions of real participants are used: pass --exclude with your own developer / test nicknames and
--since with the first day of the pilot so test sessions never count as participants.
Thesis 7.9 says each pilot session had 5 debate turns, so the 'Turns' column is shown: check that it is 5.

'Targeted weakness improved' (the thesis shows this column in Table 7.26 but does not define it; this is the definition the
code uses): for each pair of consecutive turns, the score on the dimension that was diagnosed in the earlier turn must rise.
All pairs rise = Yes, some = Partly, none = No. (A dimension already at 5 cannot rise, so it counts as not improved.)
'Weakness changed after turn 1' reproduces the statement in thesis 7.10 that the diagnosed weakness changed in the following turn."""
import sys

import numpy as np
import pandas as pd

from app.db import Database
from app.taxonomy import WEAKNESS_TO_DIMENSION

ASPECTS = [("ease_of_use", "Ease of use"), ("clarity", "Clarity of feedback"), ("ai_relevance", "Relevance of AI response"),
           ("weakness_help", "Helpfulness in identifying weakness"), ("improvement_help", "Helpfulness in improving next argument"),
           ("fairness", "Fairness of assessment"), ("reuse", "Willingness to use again")]


def _skip(names):
    return {str(x).strip().lower() for x in names if str(x).strip()}


def _nice(weakness):
    """insufficient_evidence -> 'Insufficient evidence' (the wording used in thesis Table 7.26)."""
    return (weakness or "").replace("_", " ").capitalize()


def per_participant(db, mode="adaptive", min_turns=2, since=None, exclude=(), anonymise=False):
    """One row per participant: the participant's longest qualifying session (earliest if tied)."""
    min_turns = max(2, int(min_turns))  # a change needs at least two turns
    q = ("SELECT s.session_id, s.created_at, u.name, t.turn_id, d.weakness, d.overall_score FROM debate_sessions s "
         "JOIN users u ON u.user_id=s.user_id JOIN debate_turns t ON t.session_id=s.session_id "
         "JOIN weakness_diagnoses d ON d.turn_id=t.turn_id WHERE s.mode=?" + (" AND s.created_at>=?" if since else "") +
         " ORDER BY s.session_id, t.turn_number")
    rows = db.all(q, (mode, since) if since else (mode,))
    skip = _skip(exclude)
    sessions = {}
    for r in rows:
        if (r["name"] or "").lower() in skip:
            continue
        sessions.setdefault(r["session_id"], []).append(r)
    best = {}
    for sid, turns in sessions.items():
        if len(turns) < min_turns:
            continue
        key = (turns[0]["name"] or "").lower()
        if key not in best or len(turns) > len(best[key][1]):
            best[key] = (sid, turns)
    out = []
    for sid, turns in sorted(best.values(), key=lambda x: x[0]):
        scores = [db.turn_scores(t["turn_id"]) for t in turns]
        pairs = []
        for i in range(len(turns) - 1):
            dim = WEAKNESS_TO_DIMENSION.get(turns[i]["weakness"])
            if dim is None or dim not in scores[i] or dim not in scores[i + 1]:
                continue  # no diagnosed dimension for this pair, so it cannot be judged
            pairs.append(scores[i + 1][dim] > scores[i][dim])
        share = sum(pairs) / len(pairs) if pairs else None
        out.append({"Participant": f"Participant {len(out) + 1}" if anonymise else turns[0]["name"], "Turns": len(turns),
                    "Turn 1 overall": turns[0]["overall_score"], "Final overall": turns[-1]["overall_score"],
                    "Change": round(turns[-1]["overall_score"] - turns[0]["overall_score"], 2),
                    "Initial weakness": _nice(turns[0]["weakness"]), "Final weakness": _nice(turns[-1]["weakness"]),
                    "Weakness changed after turn 1": "Yes" if turns[0]["weakness"] != turns[1]["weakness"] else "No",
                    "Targeted weakness improved": "n/a" if share is None else "Yes" if share == 1 else "No" if share == 0 else "Partly"})
    return pd.DataFrame(out)


def ratings(db, mode="adaptive", since=None, exclude=()):
    """Mean rating per aspect. One submission per participant (the latest), only from adaptive sessions."""
    q = ("SELECT f.*, u.name AS _name FROM feedback f JOIN debate_sessions s ON s.session_id=f.session_id "
         "JOIN users u ON u.user_id=f.user_id WHERE s.mode=?" + (" AND s.created_at>=?" if since else ""))
    df = pd.DataFrame(db.all(q, (mode, since) if since else (mode,)))
    if df.empty:
        return df
    df = df[~df["_name"].str.lower().isin(_skip(exclude))]
    if df.empty:
        return df
    df = df.sort_values("feedback_id").groupby("user_id").tail(1)
    return pd.DataFrame([{"Evaluation aspect": label, "Mean /5": round(df[k].mean(), 2),
                          "SD": round(df[k].std(ddof=1), 2) if len(df) > 1 else float("nan"), "n": int(df[k].count())} for k, label in ASPECTS])


def change_stats(pp, seed=2026):
    """Extra descriptive statistics. The thesis reports only 'X out of N improved'; do not present these as thesis results."""
    ch = pp["Change"].to_numpy(float)
    if len(ch) == 0:
        return {"n": 0, "improved": 0, "mean_change": float("nan"), "bootstrap_95ci": (float("nan"), float("nan"))}
    rng = np.random.default_rng(seed)
    lo, hi = np.percentile([rng.choice(ch, len(ch)).mean() for _ in range(10000)], [2.5, 97.5])
    res = {"n": len(ch), "improved": int((ch > 0).sum()), "mean_change": round(float(ch.mean()), 2), "bootstrap_95ci": (round(float(lo), 2), round(float(hi), 2))}
    if "Weakness changed after turn 1" in pp:
        res["weakness_changed_after_turn1"] = int((pp["Weakness changed after turn 1"] == "Yes").sum())
    if "Turns" in pp:
        res["sessions_not_5_turns"] = int((pp["Turns"] != 5).sum())  # thesis 7.9: each session had 5 debate turns
    try:
        from scipy.stats import wilcoxon
        if len(ch) >= 6 and np.any(ch != 0):
            res["wilcoxon_signed_rank_p"] = round(float(wilcoxon(ch).pvalue), 4)
    except Exception:
        pass
    return res


def _flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


if __name__ == "__main__":
    a = sys.argv[1:]
    positional = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    db = Database(positional[0] if positional else "debate.db")
    since, skip = _flag(a, "--since"), (_flag(a, "--exclude", "") or "").split(",")
    min_turns = int(_flag(a, "--min-turns", 2))
    pp = per_participant(db, "adaptive", min_turns, since, skip, anonymise=True)
    print("== Turn-level change (Table 7.26 equivalent), adaptive sessions ==")
    print(pp.to_string(index=False) if not pp.empty else "no sessions with enough turns yet")
    if not pp.empty:
        print("\n" + str(change_stats(pp)))
    r = ratings(db, "adaptive", since, skip)
    print("\n== Participant ratings (Table 7.25 equivalent) ==")
    print(r.to_string(index=False) if not r.empty else "no ratings yet")