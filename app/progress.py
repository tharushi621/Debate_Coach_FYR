"""Learner progression: levels, XP, streaks, badges, quests, stats, recommendations.

Blinding rule (study integrity): quality based XP and badges are granted only when the learner is in a
study arm that shows the full report (display == "full"). Participation XP is the same for all arms.

BUG FIX: WEAKNESS_DIM used to be a hand written copy that mapped irrelevant_evidence to relevance and
overgeneralisation to logical_validity. It now comes from app/taxonomy.py, the single source of truth,
so the Skills radar, the recommendations and the training badge agree with the thesis (Table 3.11).
"""
import datetime as dt

from .taxonomy import WEAKNESS_TO_DIMENSION as WEAKNESS_DIM  # noqa: F401  (re-exported for the UI)

DIMS = ["claim_clarity", "evidence_quality", "warrant_strength", "logical_validity",
        "rebuttal_readiness", "relevance", "qualification"]
DIM_LABEL = {"claim_clarity": "Claim clarity", "evidence_quality": "Evidence", "warrant_strength": "Warrant",
             "logical_validity": "Logic", "rebuttal_readiness": "Rebuttal", "relevance": "Relevance",
             "qualification": "Qualification"}
SKILLS = {  # three headline skills shown on the profile
    "Argumentation": ["claim_clarity", "evidence_quality", "warrant_strength"],
    "Critical thinking": ["logical_validity", "relevance", "qualification"],
    "Rebuttal": ["rebuttal_readiness"],
}
WEAKNESS_LABEL = {"unclear_claim": "Unclear claim", "insufficient_evidence": "Not enough evidence",
                  "irrelevant_evidence": "Evidence off topic", "missing_warrant": "Missing warrant",
                  "poor_relevance": "Drifting off the point", "weak_rebuttal": "Weak rebuttal",
                  "logical_fallacy": "Logical slip", "overgeneralisation": "Overgeneralising",
                  "missing_qualification": "No qualifier"}
INTERVENTION_LABEL = {"claim_clarification_question": "Claim clarification question",
                      "evidence_demanding_challenge": "Evidence demanding challenge",
                      "relevance_checking_question": "Relevance checking question",
                      "warrant_challenge_question": "Warrant challenge question",
                      "topic_refocusing_prompt": "Topic refocusing prompt",
                      "counterargument_presentation": "Counterargument presentation",
                      "socratic_reasoning_question": "Socratic reasoning question",
                      "counterexample_presentation": "Counterexample presentation",
                      "qualification_challenge": "Qualification challenge",
                      "single_prompt": "Single prompt baseline", "generic_counter": "Generic counterargument"}
# weakness -> training family shown in stage 06
TRAIN_KIND = {"unclear_claim": "clarity", "insufficient_evidence": "evidence", "irrelevant_evidence": "evidence",
              "missing_warrant": "logic", "poor_relevance": "clarity", "weak_rebuttal": "rebuttal",
              "logical_fallacy": "logic", "overgeneralisation": "logic", "missing_qualification": "logic"}
LEVELS = [(0, "Curious Mind"), (150, "Argument Apprentice"), (400, "Claim Crafter"),
          (800, "Evidence Hunter"), (1400, "Rebuttal Ranger"), (2200, "Master Debater")]
BADGES = {
    "first_words": ("🎤", "First Words", "Finish your first debate"),
    "evidence_hunter": ("🔎", "Evidence Hunter", "Score 4 or more on Evidence in a debate"),
    "tight_logic": ("🧩", "Tight Logic", "Score 4 or more on Logic in a debate"),
    "rebuttal_ready": ("🛡️", "Rebuttal Ready", "Score 4 or more on Rebuttal in a debate"),
    "weakness_slayer": ("⚔️", "Weakness Slayer", "Pass a training exercise on your weakest skill"),
    "comeback": ("📈", "Comeback", "Improve your overall score against the last debate"),
    "on_fire": ("🔥", "On Fire", "Practise on three days in a row"),
    "explorer": ("🧭", "Explorer", "Debate in 3 different categories"),
    "level_up": ("🚀", "Level Up", "Reach Claim Crafter"),
}
PARTICIPATION_XP, TRAIN_PASS_XP, TRAIN_TRY_XP = 40, 25, 8


def level_info(xp: int):
    idx = max(i for i, (t, _) in enumerate(LEVELS) if xp >= t)
    lo = LEVELS[idx][0]
    hi = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
    pct = 1.0 if hi is None else (xp - lo) / (hi - lo)
    return {"level": idx + 1, "name": LEVELS[idx][1], "xp": xp, "floor": lo, "next": hi,
            "to_next": None if hi is None else hi - xp, "pct": round(pct, 3),
            "next_name": LEVELS[idx + 1][1] if hi is not None else None}


def _today(today=None):
    return today or dt.date.today()


def touch_streak(state: dict, today=None) -> dict:
    t = _today(today)
    last = dt.date.fromisoformat(state["last_day"]) if state.get("last_day") else None
    if last == t:
        return state
    state["streak"] = state.get("streak", 0) + 1 if last and (t - last).days == 1 else 1
    state["best_streak"] = max(state.get("best_streak", 0), state["streak"])
    state["last_day"] = t.isoformat()
    return state


def skill_scores(scores: dict) -> dict:
    out = {}
    for name, dims in SKILLS.items():
        vals = [scores[d] for d in dims if d in scores]
        out[name] = round(sum(vals) / len(vals), 2) if vals else None
    return out


def band(v: float) -> str:
    """Label used on score cards (scale 1 to 5)."""
    return "Strong" if v >= 4 else "Proficient" if v >= 3.2 else "Developing" if v >= 2.5 else "Needs improvement"


def outcome(prev_overall, overall) -> str:
    """Honest replacement for win or loss: the AI is not a judge, so compare you with your last self."""
    if prev_overall is None:
        return "baseline"
    d = overall - prev_overall
    return "improved" if d >= 0.15 else "dipped" if d <= -0.15 else "held"


def finish_debate(state: dict, debate: dict, history: list, full: bool, today=None):
    """Apply XP and badges for a finished debate. Returns (new_state, report). Does not mutate inputs."""
    s = {**state, "badges": list(state["badges"]), "recent_topics": list(state.get("recent_topics", []))}
    before = level_info(s["xp"])
    touch_streak(s, today)
    breakdown = [("Finished a debate", PARTICIPATION_XP)]
    scores = debate.get("scores") or {}
    prev = history[-1]["overall"] if history else None
    oc = outcome(prev, debate.get("overall") or 0) if full else "n/a"
    earned = []

    def give(key):
        if key not in s["badges"]:
            s["badges"].append(key)
            earned.append(key)

    give("first_words")
    if full:
        for dim, key in (("evidence_quality", "evidence_hunter"), ("logical_validity", "tight_logic"),
                         ("rebuttal_readiness", "rebuttal_ready")):
            if scores.get(dim, 0) >= 4:
                breakdown.append((f"Strong {DIM_LABEL[dim].lower()}", 20))
                give(key)
        if oc == "improved":
            breakdown.append(("Beat your last score", 30))
            give("comeback")
    if len({h["category"] for h in history} | {debate.get("category")}) >= 3:
        give("explorer")
    if s["streak"] >= 3:
        give("on_fire")
    s["xp"] += sum(v for _, v in breakdown)
    if level_info(s["xp"])["level"] >= 3:
        give("level_up")
    s["recent_topics"] = (s["recent_topics"] + [debate.get("topic")])[-6:]
    after = level_info(s["xp"])
    return s, {"xp_gained": sum(v for _, v in breakdown), "breakdown": breakdown, "badges": earned,
               "level": after, "level_up": after["level"] > before["level"], "outcome": oc}


def training_result(state: dict, weakest_dim: str, kind_dim: str, passed: bool, first_pass: bool):
    s = {**state, "badges": list(state["badges"])}
    gain = TRAIN_PASS_XP if passed else TRAIN_TRY_XP
    before = level_info(s["xp"])["level"]
    s["xp"] += gain
    earned = []
    if passed and kind_dim == weakest_dim and "weakness_slayer" not in s["badges"]:
        s["badges"].append("weakness_slayer")
        earned.append("weakness_slayer")
    return s, {"xp_gained": gain, "badges": earned, "level_up": level_info(s["xp"])["level"] > before}


def profile_stats(debates: list, training: list) -> dict:
    n = len(debates)
    latest = debates[-1] if debates else None
    avg = {d: None for d in DIMS}
    if debates:
        for d in DIMS:
            vals = [x["scores"][d] for x in debates if d in x["scores"]]
            avg[d] = round(sum(vals) / len(vals), 2) if vals else None
    overall = [x["overall"] for x in debates if x.get("overall") is not None]
    weak_counts = {}
    for x in debates:
        if x.get("weakness"):
            weak_counts[x["weakness"]] = weak_counts.get(x["weakness"], 0) + 1
    outcomes = {k: sum(1 for x in debates if x.get("outcome") == k) for k in ("improved", "held", "dipped")}
    return {"debates": n, "latest": latest, "avg_dims": avg,
            "overall_now": overall[-1] if overall else None, "overall_first": overall[0] if overall else None,
            "trend": overall, "weak_counts": weak_counts, "outcomes": outcomes,
            "training_attempts": len(training), "training_passed": sum(t["passed"] for t in training),
            "skills": skill_scores(latest["scores"]) if latest else {},
            "turns": sum(x.get("turns", 0) for x in debates)}


def quests(state: dict, debates: list, training: list) -> list:
    """Three small goals; (id, title, done, progress text)."""
    cats = {d["category"] for d in debates}
    items = [("debate1", "Complete a debate", len(debates) >= 1, f"{min(len(debates), 1)}/1"),
             ("train1", "Pass a training exercise", any(t["passed"] for t in training),
              f"{min(sum(t['passed'] for t in training), 1)}/1"),
             ("explore3", "Debate in 3 categories", len(cats) >= 3, f"{min(len(cats), 3)}/3")]
    return [{"id": i, "title": t, "done": d, "progress": p} for i, t, d, p in items]


def recommend(stats: dict, state: dict):
    """Next debate recommendation: target the most frequent or lowest skill, step difficulty by overall."""
    from . import topics as T
    latest = stats["latest"]
    if not latest:
        return {"category": "technology", "difficulty": "beginner", "focus": None,
                "why": "Start with a short motion to set your baseline."}
    weak = latest.get("weakness") or max(stats["weak_counts"], key=stats["weak_counts"].get, default=None)
    ov = stats["overall_now"] or 0
    order = ["beginner", "intermediate", "advanced"]
    i = order.index(latest.get("difficulty") or "beginner")
    i = min(i + 1, 2) if ov >= 3.8 else max(i - 1, 0) if ov < 2.2 else i
    seen = {d for d in (state.get("recent_topics") or [])}
    cats = [c for c in T.CATEGORIES if c != latest.get("category")]
    cat = next((c for c in cats if all(t not in seen for t in T.TOPICS[c][order[i]])), cats[0])
    why = (f"Your most frequent gap is “{WEAKNESS_LABEL.get(weak, weak)}”. " if weak else "") + \
          ("Your score is strong, so we step up the difficulty." if ov >= 3.8 else
           "Let’s consolidate at an easier level first." if ov < 2.2 else "Same level, fresh category.")
    return {"category": cat, "difficulty": order[i], "focus": weak, "why": why}