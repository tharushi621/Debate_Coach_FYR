"""The six reasoning agents as plain, testable functions.

Design decision (viva-relevant): the LLM is used where language understanding is
needed (Toulmin extraction, scoring, response wording). The *decision logic* that
links diagnosis -> intervention is deterministic code, so the closed loop is
auditable and reproducible instead of depending on a stochastic model.
"""
import re

from .llm import _ABS
from .taxonomy import (DEFAULT_SCORE, DIMENSION_TO_WEAKNESS, DIMENSIONS, INTERVENTION_INSTRUCTION, INTERVENTION_MAP,
                       PRIORITY, SCORE_MAX, SCORE_MIN, WEAKNESSES, WEAKNESS_TO_COMPONENT, WEAKNESS_TO_DIMENSION)

# ---------------------------------------------------------------- prompts
DIAG_PROMPT = """You are a weakness diagnostician for student debate arguments.
Motion: {topic}. Student side: {side}.
Dimension scores (1-5) with explanations: {scores}
Student argument: {argument}
Pick the single most consequential weakness from: {weaknesses}. It should normally be the lowest-scoring dimension.
Return ONLY JSON: {{"lowest_weakness":str,"affected_component":str,"diagnosis_reason":str,"recommended_intervention":str}}"""

ANALYSE_PROMPT = """You are an argument analyst using Toulmin's model.
Motion: {topic}
Student side: {side}
Earlier turns: {history}
Student argument: {argument}
Return ONLY JSON: {{"main_claim":str,"grounds":[str],"warrant":str|null,"backing":str|null,"qualifier":str|null,"rebuttal":str|null,"missing_components":[str],"stance_matches_side":bool}}
Extract only what the student actually wrote. Use null when a component is absent."""

SCORE_PROMPT = """Score this debate argument 1-5 on each dimension using the rubric.
Rubric (1 / 3 / 5): claim_clarity (unclear / broad / specific+debatable); evidence_quality (none / some relevant / strong specific);
warrant_strength (missing / partial / clearly justified); relevance (off-topic / partial / directly on motion);
rebuttal_readiness (none / some / strong); logical_validity (major fallacy / minor weakness / coherent); qualification (overgeneralised / some / well qualified).
Motion: {topic}. Side: {side}. Toulmin analysis: {analysis}. Argument: {argument}
Return ONLY JSON with each dimension as {{"score":int,"explanation":str}}."""

OPPONENT_PROMPT = """You are a respectful debate opponent who is also a tutor. Motion: {topic}. The student argues as {side}; you argue the other side.
Student's latest argument: {argument}
Diagnosed weakness: {weakness} ({reason}). Intervention: {instruction}
Rules: stay on the motion; target ONLY the diagnosed weakness; 2-4 sentences; Socratic, challenging but not discouraging;
do NOT mention scores or the rubric; do NOT write or suggest the student's argument for them.
Return ONLY JSON: {{"ai_opponent_response":str}}"""

# Deterministic fallback wording (also the guardrail fallback if the LLM breaks the rules).
FALLBACK = {
    "claim_clarification_question": "I'm not sure exactly what position you are defending. Can you state in one precise sentence what you want this motion to mean in practice, and what someone on the other side would disagree with?",
    "evidence_demanding_challenge": "You say \"{claim}\" - but what specific evidence supports that? Name an example, a study or a source, and tell me why it should convince someone who disagrees.",
    "relevance_checking_question": "The evidence you gave is interesting, but how does it bear on the motion \"{topic}\"? What exactly does it show about the question we are debating?",
    "warrant_challenge_question": "You've offered a reason, but why does it follow that \"{claim}\"? What connects your evidence to your conclusion, and would that link hold for a sceptic?",
    "topic_refocusing_prompt": "Let's return to the motion: \"{topic}\". As {side}, how does your point directly address that question?",
    "counterargument_presentation": "Consider this objection: the other side would argue that the costs of your position outweigh its benefits, and that there are less drastic alternatives. How do you respond?",
    "socratic_reasoning_question": "If that reasoning were applied consistently, where would it lead - and would you accept the other cases it would also justify? Does the conclusion truly follow from your premise?",
    "counterexample_presentation": "Your claim sounds universal. Can you think of a situation where it clearly fails? I can: a case where the opposite outcome occurs. Does your claim survive that case?",
    "qualification_challenge": "Does your claim hold in every case? Under what conditions would it not apply, and how would that change your conclusion?",
}


# ---------------------------------------------------------------- agents
def analyse(llm, topic, side, history, argument):
    out = llm.json("analyse", ANALYSE_PROMPT.format(topic=topic, side=side, history=history[-3:], argument=argument),
                   {"argument": argument, "topic": topic})
    out.setdefault("main_claim", argument)
    out["grounds"] = out.get("grounds") or []
    for k in ("warrant", "backing", "qualifier", "rebuttal"):
        out.setdefault(k, None)
    out["missing_components"] = [k for k in ("grounds", "warrant", "backing", "qualifier", "rebuttal") if not out.get(k)]
    out.setdefault("stance_matches_side", None)  # extra field: feeds the side-consistency check (Table 3.9)
    return out


def score(llm, topic, side, analysis, argument):
    raw = llm.json("score", SCORE_PROMPT.format(topic=topic, side=side, analysis=analysis, argument=argument),
                   {"argument": argument, "topic": topic, "analysis": analysis})
    dims = {}
    for d in DIMENSIONS:
        item = raw.get(d) or {}
        try:
            s = int(round(float(item.get("score", DEFAULT_SCORE))))
        except (TypeError, ValueError):
            s = DEFAULT_SCORE
        dims[d] = {"score": max(SCORE_MIN, min(SCORE_MAX, s)), "explanation": str(item.get("explanation", ""))}
    overall = round(sum(v["score"] for v in dims.values()) / len(DIMENSIONS), 2)
    return {"dimensions": dims, "overall_quality": overall}


def lowest_dimension(dims):
    """Lowest score; ties broken by PRIORITY (the 'most consequential' rule)."""
    return min(DIMENSIONS, key=lambda d: (dims[d]["score"], PRIORITY.index(d)))


def diagnose(scores, argument, analysis, llm=None, topic="", side=""):
    """Thesis 6.2.4: the LLM proposes the weakness; it is accepted only if valid AND among the weakest dimensions
    (within 1 point of the minimum). Otherwise the rule fallback maps the lowest-scoring dimension (Table 6.4)."""
    dims = scores["dimensions"]
    dim = lowest_dimension(dims)
    weakness = DIMENSION_TO_WEAKNESS[dim]
    # subtype resolution for the two dimensions that cover two weaknesses
    if dim == "evidence_quality" and analysis.get("grounds") and dims["relevance"]["score"] <= 2:
        weakness = "irrelevant_evidence"
    if dim == "qualification" and len(_ABS.findall(argument)) >= 1:
        weakness = "overgeneralisation"
    source, llm_reason = "rule_fallback", None
    if llm is not None:
        try:
            raw = llm.json("diagnose", DIAG_PROMPT.format(topic=topic, side=side, argument=argument, weaknesses=WEAKNESSES,
                           scores={d: (v["score"], v["explanation"]) for d, v in dims.items()}), {}) or {}
        except Exception:
            raw = {}
        cand = raw.get("lowest_weakness")
        if cand in WEAKNESSES and dims[WEAKNESS_TO_DIMENSION[cand]]["score"] <= dims[dim]["score"] + 1:
            weakness, dim, source, llm_reason = cand, WEAKNESS_TO_DIMENSION[cand], "llm", raw.get("diagnosis_reason")
    reasons = {
        "unclear_claim": "The position is vague or not clearly debatable.",
        "insufficient_evidence": "The claim is not supported by specific evidence, examples or sources.",
        "irrelevant_evidence": "Evidence is offered, but it does not clearly support the claim or the motion.",
        "missing_warrant": "The link between the evidence and the claim is not explained.",
        "poor_relevance": "The argument does not directly address the debate motion.",
        "weak_rebuttal": "Opposing views or counter-conditions are not considered.",
        "logical_fallacy": "The reasoning contains an invalid or fallacious inference.",
        "overgeneralisation": "The claim is stated in absolute terms that are hard to defend.",
        "missing_qualification": "The claim is not limited to the cases where it plausibly holds.",
    }
    return {"lowest_weakness": weakness, "affected_component": WEAKNESS_TO_COMPONENT[weakness],
            "diagnosis_reason": (llm_reason or reasons[weakness]) if source == "llm" else reasons[weakness], "source": source, "dimension": dim, "dimension_score": dims[dim]["score"],
            "recommended_intervention": INTERVENTION_MAP[weakness]}


def strategise(diagnosis, previous_weakness=None, repeat_count=0):
    """Intervention from the weakness. If the same weakness persisted, escalate the scaffold."""
    itype = INTERVENTION_MAP.get(diagnosis["lowest_weakness"], "warrant_challenge_question")
    desc = INTERVENTION_INSTRUCTION[itype]
    if previous_weakness == diagnosis["lowest_weakness"] and repeat_count >= 1:
        desc += " The student did not fix this last turn: be more concrete about what kind of answer would satisfy you (without giving the answer)."
    return {"type": itype, "description": desc}


_SCORE_LEAK = re.compile(r"\b\d(\.\d+)?\s*/\s*5\b|\bscore[sd]?\b|\brubric\b", re.I)


def oppose(llm, topic, side, argument, analysis, diagnosis, intervention):
    prompt = OPPONENT_PROMPT.format(topic=topic, side=side, argument=argument, weakness=diagnosis["lowest_weakness"],
                                    reason=diagnosis["diagnosis_reason"], instruction=intervention["description"])
    fallback = FALLBACK[intervention["type"]].format(claim=(analysis.get("main_claim") or argument).rstrip(".!?"), topic=topic, side=side)
    try:
        text = (llm.json("oppose", prompt, {}) or {}).get("ai_opponent_response")
    except Exception:
        text = None
    # guardrails from thesis 3.7.3 / NFR08: no score leakage, must challenge, not too long
    if not text or _SCORE_LEAK.search(text) or "?" not in text and intervention["type"] != "counterargument_presentation" or len(text.split()) > 120:
        return fallback, True
    return text.strip(), False


def feedback(scores, diagnosis):
    dims = scores["dimensions"]
    best = max(DIMENSIONS, key=lambda d: (dims[d]["score"], -PRIORITY.index(d)))
    nice = lambda d: d.replace("_", " ")
    return (f"Strength: your {nice(best)} is your strongest area ({dims[best]['score']}/5). "
            f"Focus next on {nice(diagnosis['dimension'])}: {diagnosis['diagnosis_reason']} "
            f"Next step: address the opponent's challenge in your own words.")


def track(current_scores, current_diag, previous):
    """Progress between turns. Improvement is measured on the *targeted* dimension (the one diagnosed last turn)."""
    if not previous:
        return {"score_change": None, "targeted_dimension": None, "targeted_before": None, "targeted_after": None,
                "targeted_improved": None, "weakness_changed": None, "previous_overall": None}
    tdim = WEAKNESS_TO_DIMENSION[previous["weakness"]]
    before, after = previous["scores"].get(tdim), current_scores["dimensions"][tdim]["score"]
    return {"previous_overall": previous["overall_score"], "previous_weakness": previous["weakness"], "current_weakness": current_diag["lowest_weakness"],
            "score_change": round(current_scores["overall_quality"] - previous["overall_score"], 2),
            "targeted_dimension": tdim, "targeted_before": before, "targeted_after": after,
            "targeted_improved": None if before is None else after > before,
            "weakness_changed": previous["weakness"] != current_diag["lowest_weakness"]}


SINGLE_PROMPT = """You are a debate coach and opponent in one. Motion: {topic}. The student argues as {side}.
Student argument: {argument}
Give short feedback on the argument and a reply as the opposing debater. Do not write the student's argument for them.
Return ONLY JSON: {{"feedback":str,"ai_opponent_response":str}}"""


def single_prompt_baseline(llm, topic, side, argument):
    """Baseline B2: ONE un-decomposed LLM call does feedback + opponent reply (what most chatbot studies do)."""
    try:
        out = llm.json("single", SINGLE_PROMPT.format(topic=topic, side=side, argument=argument), {}) or {}
    except Exception:
        out = {}
    return (out.get("feedback") or "Consider strengthening your argument."), (out.get("ai_opponent_response") or "I disagree. Can you elaborate?")
