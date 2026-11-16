"""Comparison arms for the evaluation. They stand for what an existing, un-targeted AI debate tool does.

  single_prompt_diagnose  ONE LLM call that names the main weakness (no Toulmin analysis, no rubric, no agents).
                          It is given the same label set and the same definitions the human labellers saw, so it is a fair rival.
  generic_opponent        a debate opponent that answers the student with no diagnosis (typical chatbot debate partner).
  single_call_opponent    ONE call that diagnoses AND replies (tests whether decomposing the work into agents matters).

All three use the same LLM backend as the system, so any difference comes from the design, not the model.
"""
from app.agents import fmt_convo, guard_reply
from app.taxonomy import INTERVENTION_INSTRUCTION, INTERVENTION_MAP, WEAKNESSES

DEFINITIONS = """unclear_claim: the position is vague or it is not clear what is argued.
insufficient_evidence: reasons are given but no specific evidence, example or source.
irrelevant_evidence: evidence is given but has nothing to do with the claim or the motion.
missing_warrant: evidence is given but the link from the evidence to the claim is not explained.
poor_relevance: the argument does not address the debate motion.
weak_rebuttal: otherwise supported but ignores opposing views.
logical_fallacy: the reasoning is invalid.
overgeneralisation: absolute claims (all, never, always) that are hard to defend.
missing_qualification: a developed claim with no limits or conditions."""

SINGLE_DIAG = """You are an expert debate coach. Motion: {topic}. The student argues {side}.
Student argument: {argument}
Choose the single most consequential weakness of this argument from this list:
{definitions}
Return ONLY JSON: {{"lowest_weakness": one label from the list}}"""

GENERIC_OPP = """You are a debate opponent. Motion: {topic}. The student argues {side}; you argue the other side.
Debate so far:
{history}
Student's latest argument: {argument}
Reply to the student in 2 or 3 short sentences, challenging their argument.
Return ONLY JSON: {{"ai_opponent_response": str}}"""

SINGLE_CALL = """You are a respectful debate opponent who is also a tutor. Motion: {topic}. The student argues {side}; you argue the other side.
Debate so far:
{history}
Student's latest argument: {argument}
First decide the single most consequential weakness of the argument from this list:
{definitions}
Then reply in 2 or 3 short sentences, Socratic and challenging but not discouraging, aimed ONLY at that weakness.
Do NOT mention scores or a rubric and do NOT write or suggest the student's argument for them.
Return ONLY JSON: {{"lowest_weakness": str, "ai_opponent_response": str}}"""


def single_prompt_diagnose(llm, topic, side, argument):
    out = llm.json("diagnose", SINGLE_DIAG.format(topic=topic, side=side, argument=argument, definitions=DEFINITIONS), {}) or {}
    w = str(out.get("lowest_weakness", "")).strip().lower()
    return w if w in WEAKNESSES else "invalid"


def generic_opponent(llm, topic, side, argument, convo=None):
    out = llm.json("oppose", GENERIC_OPP.format(topic=topic, side=side, argument=argument, history=fmt_convo(convo)), {}) or {}
    return str(out.get("ai_opponent_response", "")).strip()


def single_call_opponent(llm, topic, side, argument, convo=None):
    out = llm.json("oppose", SINGLE_CALL.format(topic=topic, side=side, argument=argument, history=fmt_convo(convo),
                                                definitions=DEFINITIONS), {}) or {}
    w = str(out.get("lowest_weakness", "")).strip().lower()
    return (w if w in WEAKNESSES else "invalid"), str(out.get("ai_opponent_response", "")).strip()
