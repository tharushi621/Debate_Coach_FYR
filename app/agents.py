"""The six agents' logic as plain functions (thesis 5.4 and 6.2). crew_flow.py wraps the same logic in CrewAI agents;
ORCHESTRATOR=python runs these functions directly. No mock data: every call needs a real LLM backend."""
import os
import re

from .llm import _ABS #_ABS variable is a regex used to identify absolute lang.
from .taxonomy import (DEFAULT_SCORE, DIMENSION_TO_WEAKNESS, DIMENSIONS, INTERVENTION_INSTRUCTION,
                       INTERVENTION_MAP, PRIORITY, SCORE_MAX, SCORE_MIN, WEAKNESSES,
                       WEAKNESS_TO_COMPONENT, WEAKNESS_TO_DIMENSION)

#Prompts
ANALYSE_PROMPT = """You are an argument analyst using Toulmin's model.
Motion: {topic}
Student side: {side}
Earlier turns: {history}
Student argument: {argument}
Return ONLY JSON:
{{"main_claim":str,"grounds":[str],"warrant":str|null,"backing":str|null,"qualifier":str|null,"rebuttal":str|null,"missing_components":[str],"stance_matches_side":bool}}
Extract only what the student actually wrote, each part in under 12 words. Use null when a component is absent."""

SCORE_PROMPT = """Score this debate argument 1 to 5 on each dimension using the rubric.
Rubric (1 / 3 / 5): claim_clarity (unclear / broad / specific and debatable); evidence_quality (none / some relevant / strong specific); warrant_strength (missing / partial / clearly justified); relevance (off topic / partial / directly on motion); rebuttal_readiness (none / some / strong); logical_validity (major fallacy / minor weakness / coherent); qualification (overgeneralised / some / well qualified).
Motion: {topic}. Side: {side}. Toulmin analysis: {analysis}. Argument: {argument}
Return ONLY JSON with the seven dimensions, each as {{"score":int,"explanation":str}}. Each explanation must be under 8 words."""

DIAG_PROMPT = """You are a weakness diagnostician for student debate arguments.
Motion: {topic}. Student side: {side}.
Dimension scores (1 to 5) with explanations: {scores}
Student argument: {argument}
Pick the single most consequential weakness from: {weaknesses}. It should normally be the lowest scoring dimension.
Return ONLY JSON:
{{"lowest_weakness":str,"affected_component":str,"diagnosis_reason":str,"recommended_intervention":str}}
Keep diagnosis_reason under 12 words."""


OPPONENT_PROMPT = """You are a respectful debate opponent who is also a tutor. Motion: {topic}. The student argues as {side}; you argue the other side.
Debate so far (oldest first):
{history}
Student's latest argument: {argument}
Diagnosed weakness: {weakness} ({reason}). Intervention: {instruction}
Rules: stay on the motion;
target ONLY the diagnosed weakness; 2 or 3 short sentences; Socratic, challenging but not discouraging; do NOT mention scores or the rubric; do NOT write or suggest the student's argument for them.
Return ONLY JSON: {{"ai_opponent_response":str}}"""

# Used by the CrewAI path. the previous agent's output reaches the next agent through the task context.
FROM_CONTEXT = "(given by the previous agent in the context below)" # A helper string for CrewAI implementation

# guardrail fallback if the LLM breaks the rules. This dictionary contain predefined responses.
# This is called as a Fallback mechanism.
FALLBACK = {
    "claim_clarification_question": "I'm not sure exactly what position you are defending. Can you state in one precise sentence what you want this motion to mean in practice, and what someone on the other side would disagree with?",
    "evidence_demanding_challenge": "You say \"{claim}\", but what specific evidence supports that? Name an example, a study or a source, and tell me why it should convince someone who disagrees.",
    "relevance_checking_question": "The evidence you gave is interesting, but how does it bear on the motion \"{topic}\"? What exactly does it show about the question we are debating?",
    "warrant_challenge_question": "You've offered a reason, but why does it follow that \"{claim}\"? What connects your evidence to your conclusion, and would that link hold for a sceptic?",
    "topic_refocusing_prompt": "Let's return to the motion: \"{topic}\". As {side}, how does your point directly address that question?",
    "counterargument_presentation": "Consider this objection: the other side would argue that the costs of your position outweigh its benefits, and that there are less drastic alternatives. How do you respond?",
    "socratic_reasoning_question": "If that reasoning were applied consistently, where would it lead, and would you accept the other cases it would also justify? Does the conclusion truly follow from your premise?",
    "counterexample_presentation": "Your claim sounds universal. Can you think of a situation where it clearly fails? I can: a case where the opposite outcome occurs. Does your claim survive that case?",
    "qualification_challenge": "Does your claim hold in every case? Under what conditions would it not apply, and how would that change your conclusion?",
}

REASONS = {
    "unclear_claim": "The position is vague or not clearly debatable.",
    "insufficient_evidence": "The claim is not supported by specific evidence, examples or sources.",
    "irrelevant_evidence": "Evidence is offered, but it does not clearly support the claim or the motion.",
    "missing_warrant": "The link between the evidence and the claim is not explained.",
    "poor_relevance": "The argument does not directly address the debate motion.",
    "weak_rebuttal": "Opposing views or counter conditions are not considered.",
    "logical_fallacy": "The reasoning contains an invalid or fallacious inference.",
    "overgeneralisation": "The claim is stated in absolute terms that are hard to defend.",
    "missing_qualification": "The claim is not limited to the cases where it plausibly holds.",
}


# normalisation - bcz LLMs can return incomplete or inconsistent JSON.
def _as_dict(raw):
    """A model sometimes wraps its answer in a list: take the first dict inside it, else an empty dict."""
    if isinstance(raw, list):
        raw = next((x for x in raw if isinstance(x, dict)), {})
    return dict(raw) if isinstance(raw, dict) else {}


def _scores_as_dict(raw):
    """Accept the shapes models really return for the seven scores: {dim: {...}}, {"scores"/"dimensions": {...}},
    a list of {"dimension": name, "score": n} items, or a plain list of seven items in rubric order."""
    if isinstance(raw, dict):
        for wrap in ("scores", "dimensions"):
            if isinstance(raw.get(wrap), (dict, list)) and not any(d in raw for d in DIMENSIONS):
                return _scores_as_dict(raw[wrap])
        return raw
    if isinstance(raw, list):
        out = {}
        named = [x for x in raw if isinstance(x, dict) and (x.get("dimension") or x.get("name"))]
        for x in named:
            out[str(x.get("dimension") or x.get("name")).strip().lower().replace(" ", "_")] = x
        if out:
            return out
        if len(raw) == len(DIMENSIONS):
            return dict(zip(DIMENSIONS, raw))
    return {}


def normalise_analysis(out, topic, argument): #Raw output from Arg Analyzer.
    out = _as_dict(out)
    out.setdefault("main_claim", argument)
    out["grounds"] = out.get("grounds") or []
    if isinstance(out["grounds"], str):
        out["grounds"] = [out["grounds"]]
    for k in ("warrant", "backing", "qualifier", "rebuttal"):
        out.setdefault(k, None)
    out["missing_components"] = [k for k in ("grounds", "warrant", "backing", "qualifier", "rebuttal") #Because the system does not blindly trust the LLM's original missing_components list. It recalculates it from the actual extracted fields.
                                 if not out.get(k)]
    out.setdefault("stance_matches_side", None)   # feeds the side consistency check (Table 3.9)
    return out


def normalise_scores(raw):
    """Clamp every dimension to 1..5; a missing score becomes 3; overall = mean / 7."""
    raw = _scores_as_dict(raw)
    dims = {}
    for d in DIMENSIONS:
        item = raw.get(d) or {} #Get the score for current dimension.If missing use an empty dictionary.
        if not isinstance(item, dict):
            item = {"score": item}
        missing = "score" not in item
        try:
            s = int(round(float(item.get("score", DEFAULT_SCORE))))
        except (TypeError, ValueError):
            s, missing = DEFAULT_SCORE, True
        expl = str(item.get("explanation", ""))
        if missing:
            expl = "[no valid LLM score, default 3 applied] " + expl
        dims[d] = {"score": max(SCORE_MIN, min(SCORE_MAX, s)), "explanation": expl}
    overall = round(sum(v["score"] for v in dims.values()) / len(DIMENSIONS), 2)
    return {"dimensions": dims, "overall_quality": overall}


def lowest_dimension(dims):
    """Lowest score; ties broken by PRIORITY (the 'most consequential' rule)."""
    return min(DIMENSIONS, key=lambda d: (dims[d]["score"], PRIORITY.index(d)))


def resolve_diagnosis(scores, argument, analysis, proposal=None):
    """Thesis 6.2.4. The LLM proposal is accepted only if valid AND among the weakest dimensions
    (within 1 point of the minimum). Otherwise the rule maps the lowest scoring dimension."""
    dims = scores["dimensions"]
    dim = lowest_dimension(dims)
    weakness = DIMENSION_TO_WEAKNESS[dim]
    if dim == "evidence_quality" and analysis.get("grounds") and dims["relevance"]["score"] <= 2:
        weakness = "irrelevant_evidence"
    if dim == "qualification" and len(_ABS.findall(argument)) >= 1:
        weakness = "overgeneralisation"
    source, llm_reason = "rule_fallback", None
    cand = (proposal or {}).get("lowest_weakness")
    if cand in WEAKNESSES and dims[WEAKNESS_TO_DIMENSION[cand]]["score"] <= dims[dim]["score"] + 1:
        weakness, dim, source, llm_reason = cand, WEAKNESS_TO_DIMENSION[cand], "llm", proposal.get("diagnosis_reason")
    return {"lowest_weakness": weakness, "affected_component": WEAKNESS_TO_COMPONENT[weakness],
            "diagnosis_reason": (llm_reason or REASONS[weakness]) if source == "llm" else REASONS[weakness],
            "source": source, "dimension": dim, "dimension_score": dims[dim]["score"],
            "recommended_intervention": INTERVENTION_MAP[weakness]}


# Thesis 3.7.3 / NFR08: the opponent must not reveal rubric scores. The pattern targets real leaks only (numbers like "3/5",
# "your score", "overall score", the rubric, the dimension names). The bare word "score" is NOT flagged, because a motion such as
# "Standardised testing ..." legitimately needs "test scores" and every such reply would otherwise be replaced by a canned one.
_SCORE_LEAK = re.compile(r"\b\d(\.\d+)?\s*(/|out of)\s*5\b|\b(your|my|overall|argument|quality)\s+scores?\b"
                         r"|\byou\s+scored\b|\bscored\s+you\b|\brubric\b"
                         r"|\b(claim_clarity|evidence_quality|warrant_strength|rebuttal_readiness|logical_validity)\b", re.I)
# Thesis 3.7.3 / NFR08: the opponent must not write the student's argument for them (also stated in the prompt).
_WRITES_FOR_STUDENT = re.compile(r"\b(here is|here's)\s+(a|an|your)\s+(better|stronger|improved|revised|rewritten)\b"
                                 r"|\byou (could|might|should) (say|write|argue)\s*[:,\"“]|\btry (saying|writing)\b", re.I)


def guard_reply(text, intervention, topic, side, argument, analysis):
    """Guardrails: no score leakage and no writing the student's argument (thesis 3.7.3, NFR08). Also an implementation choice:
    the reply must challenge (contain a question unless it is a counterargument) and be short (at most 120 words)."""
    fallback = FALLBACK[intervention["type"]].format(
        claim=(analysis.get("main_claim") or argument).rstrip(".!?"), topic=topic, side=side)
    if (not isinstance(text, str) or not text.strip() or _SCORE_LEAK.search(text) or _WRITES_FOR_STUDENT.search(text)
            or ("?" not in text and intervention["type"] != "counterargument_presentation")
            or len(text.split()) > 120):
        return fallback, True
    return text.strip(), False


def fmt_convo(convo):
    """Conversation history as readable text for the opponent prompt (thesis 3.11.5).
    convo = [{"student": str, "opponent": str|None}, ...] oldest first (see Database.conversation)."""
    if not convo:
        return "(this is the first turn)"
    lines = []
    for t in convo:
        lines.append(f"Student: {t.get('student')}")
        if t.get("opponent"):
            lines.append(f"Opponent: {t['opponent']}")
    return "\n".join(lines)


# agents
# Agent 1 — Argument Analyzer
def analyse(llm, topic, side, history, argument): #llm=llm interface
    out = llm.json("analyse", ANALYSE_PROMPT.format(topic=topic, side=side, history=history[-3:],
                                                    argument=argument), {"argument": argument, "topic": topic})
    return normalise_analysis(out, topic, argument)


def score(llm, topic, side, analysis, argument):
    raw = llm.json("score", SCORE_PROMPT.format(topic=topic, side=side, analysis=analysis, argument=argument),
                   {"argument": argument, "topic": topic, "analysis": analysis})
    return normalise_scores(raw)


def diagnose(scores, argument, analysis, llm=None, topic="", side=""):
    """Set DIAG_USE_LLM=0 to skip the LLM proposal (saves one model call per turn); the rule decides."""
    if os.getenv("DIAG_USE_LLM", "1") == "0":
        llm = None
    proposal = {}
    if llm is not None:
        try:
            proposal = llm.json("diagnose", DIAG_PROMPT.format(
                topic=topic, side=side, argument=argument, weaknesses=WEAKNESSES,
                scores={d: (v["score"], v["explanation"]) for d, v in scores["dimensions"].items()}), {}) or {}
        except Exception:
            proposal = {}
    return resolve_diagnosis(scores, argument, analysis, proposal)


def strategise(diagnosis, previous_weakness=None, repeat_count=0):
    """Intervention from the weakness (thesis 6.2.5). If the same weakness persisted, escalate the scaffold."""
    itype = INTERVENTION_MAP.get(diagnosis["lowest_weakness"], "warrant_challenge_question")
    desc = INTERVENTION_INSTRUCTION[itype]
    if previous_weakness == diagnosis["lowest_weakness"] and repeat_count >= 1:
        desc += (" The student did not fix this last turn: be more concrete about what kind of answer "
                 "would satisfy you (without giving the answer).")
    return {"type": itype, "description": desc}


def oppose(llm, topic, side, argument, analysis, diagnosis, intervention, convo=None):
    prompt = OPPONENT_PROMPT.format(topic=topic, side=side, argument=argument, history=fmt_convo(convo),
                                    weakness=diagnosis["lowest_weakness"], reason=diagnosis["diagnosis_reason"],
                                    instruction=intervention["description"])
    try:
        text = (llm.json("oppose", prompt, {}) or {}).get("ai_opponent_response")
    except Exception:
        text = None
    return guard_reply(text, intervention, topic, side, argument, analysis)


def feedback(scores, diagnosis):
    dims = scores["dimensions"]
    best = max(DIMENSIONS, key=lambda d: (dims[d]["score"], -PRIORITY.index(d)))
    nice = lambda d: d.replace("_", " ")
    return (f"Strength: your {nice(best)} is your strongest area ({dims[best]['score']}/5). "
            f"Focus next on {nice(diagnosis['dimension'])}: {diagnosis['diagnosis_reason']} "
            f"Next step: address the opponent's challenge in your own words.")


def track(current_scores, current_diag, previous):
    """Progress between turns.

    Thesis 6.2.7 fields: previous_score, current_score, score_change, improvement
    (improvement = score went up AND the diagnosed weakness changed).
    Extra fields: improvement is also measured on the targeted dimension (diagnosed last turn)."""
    if not previous:
        return {"previous_score": None, "current_score": current_scores["overall_quality"],
                "score_change": None, "improvement": None,
                "targeted_dimension": None, "targeted_before": None,
                "targeted_after": None, "targeted_improved": None, "weakness_changed": None,
                "previous_overall": None}
    tdim = WEAKNESS_TO_DIMENSION.get(previous.get("weakness"))
    before = (previous.get("scores") or {}).get(tdim) if tdim else None
    after = current_scores["dimensions"][tdim]["score"] if tdim else None
    changed = previous["weakness"] != current_diag["lowest_weakness"]
    change = round(current_scores["overall_quality"] - previous["overall_score"], 2)
    return {"previous_score": previous["overall_score"], "current_score": current_scores["overall_quality"],
            "score_change": change, "improvement": bool(change > 0 and changed),
            "previous_overall": previous["overall_score"], "previous_weakness": previous["weakness"],
            "current_weakness": current_diag["lowest_weakness"],
            "targeted_dimension": tdim, "targeted_before": before, "targeted_after": after,
            "targeted_improved": None if before is None or after is None else after > before,
            "weakness_changed": changed}