"""Input validation + pre-processing (thesis 3.10.4, 3.10.5)."""
import re

from .llm import _toks
from .taxonomy import MIN_ARGUMENT_CHARS


class ValidationError(ValueError):
    pass


def preprocess(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return re.sub(r"[^\w\s.,;:!?%'\"()\-/$&]", "", text)


def validate(argument: str, topic: str, previous: list[str]) -> str:
    clean = preprocess(argument)
    if not clean:
        raise ValidationError("Please enter an argument.")
    if len(clean) < MIN_ARGUMENT_CHARS:
        raise ValidationError("Your argument is too short. Please develop it in a sentence or two.")
    if not re.search(r"[A-Za-z]{3,}", clean) or len(re.findall(r"[A-Za-z]", clean)) / len(clean) < 0.5:
        raise ValidationError("Please write your argument in English sentences.")  # simple language check
    if clean.lower() in {p.lower() for p in previous}:
        raise ValidationError("You already submitted this argument. Please revise it.")
    return clean
    # Topic relevance is deliberately NOT a hard gate: off-topic input is a diagnosable
    # weakness ("poor_relevance") and should reach the diagnostician, not be rejected.


def soft_flags(clean: str, topic: str, analysis: dict | None = None) -> list[dict]:
    """Table 3.9 'topic relevance' and 'side consistency' IDENTIFY problems; they do not reject, so that
    off-topic input can still be diagnosed as poor_relevance (a weakness in the taxonomy)."""
    flags, t = [], _toks(topic)
    if t and len(_toks(clean) & t) / len(t) < 0.1:
        flags.append({"code": "low_topic_overlap", "message": "Your response does not clearly address the selected debate motion. Please provide an argument related to the topic."})
    if analysis and analysis.get("stance_matches_side") is False:
        flags.append({"code": "side_inconsistent", "message": "Your argument seems to support the other side of the motion."})
    return flags
