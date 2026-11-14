"""Stage 06 — AI counterargument training. Exercises are written per weakness family.

Evaluation is deterministic and transparent (rule checks on the learner's text), so feedback is
reproducible and needs no LLM. It is practice feedback, NOT the thesis scorer; never report it as such.
"""
import re

HEDGES = ("generally", "usually", "often", "in most cases", "typically", "tends to", "mostly", "likely",
          "in many cases", "may", "might", "unless", "although", "except", "probably", "can ")
EVIDENCE_CUES = ("for example", "for instance", "according to", "study", "studies", "research", "data",
                 "survey", "percent", "%", "found that", "report", "evidence", "statistics")
LINK_CUES = ("because", "therefore", "since", "so that", "this means", "which shows", "it follows",
             "as a result", "consequently", "this is why")
REBUT_CUES = ("however", "but", "although", "even if", "while", "you claim", "your point", "yet",
              "that overlooks", "that ignores", "granted")
FALLACY_WORDS = ("everyone knows", "always", "never", "nobody", "all people", "obviously")

EXERCISES = {
    "evidence": [
        {"id": "ev1", "title": "Back it with a fact",
         "prompt": "Claim: “Cities with more bike lanes have healthier residents.”\nAdd one concrete piece of evidence (a study, a statistic, or a specific example) and say where it comes from.",
         "hint": "Try: “According to … a study found that …”"},
        {"id": "ev2", "title": "Make evidence specific",
         "prompt": "Weak: “Many students are stressed.”\nRewrite it with a specific number or named source, and tie it to why it matters.",
         "hint": "Specific beats many/some/lots."}],
    "logic": [
        {"id": "lg1", "title": "Bridge the gap",
         "prompt": "Claim: “Schools should start later.”  Evidence: “Teenagers sleep less.”\nWrite the missing link (warrant) that connects the evidence to the claim, using ‘because’ or ‘therefore’.",
         "hint": "Warrant = why the evidence supports the claim."},
        {"id": "lg2", "title": "Qualify the claim",
         "prompt": "Overclaim: “Social media always harms teenagers.”\nRewrite it so it is defensible: add a qualifier (usually, in many cases, unless…).",
         "hint": "Replace always/never with a scoped claim."}],
    "rebuttal": [
        {"id": "rb1", "title": "Answer the objection",
         "prompt": "Opponent: “Banning cars from city centres would hurt local shops.”\nWrite a rebuttal: acknowledge the point, then answer it with a reason or evidence.",
         "hint": "Pattern: “Granted…, but … because …”"},
        {"id": "rb2", "title": "Pre-empt the counter",
         "prompt": "Your claim: “Compulsory voting increases turnout.”\nWrite one likely objection and your reply to it.",
         "hint": "Name the objection, then defeat it."}],
    "clarity": [
        {"id": "cl1", "title": "One clear claim",
         "prompt": "Rewrite in one sentence a reader could agree or disagree with:\n“Technology and school and stuff is complicated.”",
         "hint": "Subject + position (should/should not)."}],
}
KIND_DIM = {"evidence": "evidence_quality", "logic": "warrant_strength", "rebuttal": "rebuttal_readiness",
            "clarity": "claim_clarity"}


def exercise_for(kind: str, attempt: int = 0):
    pool = EXERCISES[kind]
    return {**pool[attempt % len(pool)], "kind": kind}


def _words(t): return re.findall(r"[A-Za-z']+", t)


def evaluate(kind: str, text: str):
    """Returns {passed, score(0-1), checks:[(label, ok, tip)], feedback}."""
    t = (text or "").strip(); low = t.lower(); n = len(_words(t))
    has = lambda cues: any(c in low for c in cues)
    checks = [("Long enough to make a point (12+ words)", n >= 12, "Say a little more — one full sentence or two.")]
    if kind == "evidence":
        checks += [("Cites evidence", has(EVIDENCE_CUES), "Name a study, a number or a source."),
                   ("Contains a specific figure or name", bool(re.search(r"\d|[A-Z][a-z]+ [A-Z]", t)),
                    "Add a number or a proper name.")]
    elif kind == "logic":
        checks += [("Links reason to claim", has(LINK_CUES), "Use ‘because’ / ‘therefore’ to connect the dots."),
                   ("Scoped, not absolute", has(HEDGES) or not has(FALLACY_WORDS),
                    "Soften absolutes with usually/in many cases.")]
    elif kind == "rebuttal":
        checks += [("Addresses the other side", has(REBUT_CUES), "Start from their point: ‘Granted…, but…’."),
                   ("Gives a reason", has(LINK_CUES) or has(EVIDENCE_CUES), "Back your answer with ‘because…’.")]
    else:
        checks += [("Takes a position", bool(re.search(r"\b(should|must|ought|is|are|will)\b", low)),
                    "State what should or should not happen."),
                   ("Stays focused (≤ 30 words)", n <= 30, "Trim it to one sentence.")]
    ok = sum(1 for _, o, _ in checks if o)
    score = ok / len(checks)
    passed = ok == len(checks)
    miss = [tip for _, o, tip in checks if not o]
    fb = "Well done — that is clear and well supported." if passed else "Almost: " + " ".join(miss)
    return {"passed": passed, "score": round(score, 2), "checks": checks, "feedback": fb}