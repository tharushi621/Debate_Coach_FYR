"""Shared test helpers.

ScriptedLLM is a TEST DOUBLE: it returns exactly the JSON a test scripts, so the pipeline logic (validation, diagnosis,
intervention, guardrails, progress, persistence) can be checked without a running model. It lives in tests/ only;
app/ never imports it, and nothing here produces data for the thesis, the pilot or the evaluation.
"""
import pytest

from app.taxonomy import DIMENSIONS


class ScriptedLLM:
    """json(task, ...) returns the scripted answer for the current turn.

    `turns` is a list of dicts with the keys "analyse", "score", "diagnose", "oppose".
    The turn index advances on every "analyse" call; the last scripted turn repeats when the script runs out."""
    name = "scripted"
    model = "scripted"

    def __init__(self, turns):
        self.turns, self.i, self.calls = list(turns), -1, []

    def json(self, task, prompt, payload=None, retries=0):
        if task == "analyse":
            self.i += 1
        self.calls.append((task, prompt))
        turn = self.turns[max(0, min(self.i, len(self.turns) - 1))]
        return dict(turn.get(task, {}))


def make_turn(scores=None, reply="Why does that follow from your evidence?", grounds=("a study",), diagnose=None):
    """One scripted turn. `scores` overrides single dimension scores (all others are 3)."""
    dims = {d: {"score": 3, "explanation": "scripted"} for d in DIMENSIONS}
    for name, value in (scores or {}).items():
        dims[name]["score"] = value
    return {"analyse": {"main_claim": "the claim", "grounds": list(grounds), "warrant": None},
            "score": dims, "diagnose": diagnose or {}, "oppose": {"ai_opponent_response": reply}}


@pytest.fixture(autouse=True)
def _plain_runner(monkeypatch):
    """Tests use the plain Python runner so they never need CrewAI or a model server."""
    monkeypatch.setenv("ORCHESTRATOR", "python")


@pytest.fixture
def scripted():
    return ScriptedLLM


@pytest.fixture
def turn():
    return make_turn