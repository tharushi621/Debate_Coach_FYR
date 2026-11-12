"""Single source of truth for dimensions, weaknesses and interventions.

Everything the thesis tables define (Table 3.3, 3.4, 3.6/3.11) lives here so the
prompts, rules, tests and evaluation all read the same definitions.
"""

DIMENSIONS = [
    "claim_clarity",
    "evidence_quality",
    "warrant_strength",
    "relevance",
    "rebuttal_readiness",
    "logical_validity",
    "qualification",
]

# Tie-break priority when several dimensions share the lowest score
# ("most consequential" in the thesis). Earlier = more consequential.
# Rationale: an argument that is off-topic or has no clear claim cannot be
# repaired by better evidence; evidence/warrant are the core of Toulmin's
# grounds->warrant->claim chain; rebuttal/qualification refine a sound argument.
PRIORITY = [
    "relevance",
    "claim_clarity",
    "evidence_quality",
    "warrant_strength",
    "logical_validity",
    "rebuttal_readiness",
    "qualification",
]

WEAKNESSES = [
    "unclear_claim",
    "insufficient_evidence",
    "irrelevant_evidence",
    "missing_warrant",
    "poor_relevance",
    "weak_rebuttal",
    "logical_fallacy",
    "overgeneralisation",
    "missing_qualification",
]

# Default dimension -> weakness. Evidence and qualification dimensions each
# cover two weaknesses; the diagnostician resolves the subtype (see agents.py).
DIMENSION_TO_WEAKNESS = {
    "claim_clarity": "unclear_claim",
    "evidence_quality": "insufficient_evidence",
    "warrant_strength": "missing_warrant",
    "relevance": "poor_relevance",
    "rebuttal_readiness": "weak_rebuttal",
    "logical_validity": "logical_fallacy",
    "qualification": "missing_qualification",
}

WEAKNESS_TO_DIMENSION = {
    "unclear_claim": "claim_clarity",
    "insufficient_evidence": "evidence_quality",
    "irrelevant_evidence": "evidence_quality",
    "missing_warrant": "warrant_strength",
    "poor_relevance": "relevance",
    "weak_rebuttal": "rebuttal_readiness",
    "logical_fallacy": "logical_validity",
    "overgeneralisation": "qualification",
    "missing_qualification": "qualification",
}

WEAKNESS_TO_COMPONENT = {
    "unclear_claim": "claim",
    "insufficient_evidence": "grounds",
    "irrelevant_evidence": "grounds",
    "missing_warrant": "warrant",
    "poor_relevance": "claim",
    "weak_rebuttal": "rebuttal",
    "logical_fallacy": "warrant",
    "overgeneralisation": "qualifier",
    "missing_qualification": "qualifier",
}

# Table 3.11 / Appendix B
INTERVENTION_MAP = {
    "unclear_claim": "claim_clarification_question",
    "insufficient_evidence": "evidence_demanding_challenge",
    "irrelevant_evidence": "relevance_checking_question",
    "missing_warrant": "warrant_challenge_question",
    "poor_relevance": "topic_refocusing_prompt",
    "weak_rebuttal": "counterargument_presentation",
    "logical_fallacy": "socratic_reasoning_question",
    "overgeneralisation": "counterexample_presentation",
    "missing_qualification": "qualification_challenge",
}

INTERVENTION_INSTRUCTION = {
    "claim_clarification_question": "Ask the student to restate a clear, specific, debatable position.",
    "evidence_demanding_challenge": "Ask for specific evidence, examples or sources behind the claim.",
    "relevance_checking_question": "Ask how the evidence given relates to the motion.",
    "warrant_challenge_question": "Ask why the evidence they gave actually supports the claim.",
    "topic_refocusing_prompt": "Redirect the student to the debate motion and their assigned side.",
    "counterargument_presentation": "Present one strong counterargument and ask the student to respond.",
    "socratic_reasoning_question": "Ask a Socratic question that exposes the flaw in their reasoning without naming it as a fallacy outright.",
    "counterexample_presentation": "Present a concrete counterexample to their sweeping claim.",
    "qualification_challenge": "Ask whether the claim holds in all cases and under what conditions it would not.",
}

SCORE_MIN, SCORE_MAX = 1, 5
DEFAULT_SCORE = 3  # fallback when the LLM omits a score (thesis 6.2.3)
MIN_ARGUMENT_CHARS = 25
