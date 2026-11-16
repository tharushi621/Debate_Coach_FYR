"""Runs the REAL CrewAI crew (seven agents) with a scripted model, so the orchestration is checked without Ollama."""
import json

import pytest

pytest.importorskip("crewai")

from app.db import Database
from app.pipeline import process_turn
from app.taxonomy import DIMENSIONS


class ScriptedInner:
    """Stands in for OllamaLLM: complete(messages, task) returns the scripted JSON text for that task."""
    name, model = "scripted", "scripted"

    def __init__(self):
        self.tasks = []

    def complete(self, messages, task=None):
        self.tasks.append(task)
        out = {"analyse": {"main_claim": "Ban it", "grounds": ["it is harmful"], "warrant": None},
               "score": {d: {"score": 4 if d != "evidence_quality" else 1, "explanation": "x"} for d in DIMENSIONS},
               "diagnose": {}, "oppose": {"ai_opponent_response": "What specific evidence supports that claim?"}}[task]
        return json.dumps(out)


def test_crew_runs_all_agents_in_order_and_saves_the_turn(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR", "crewai")
    db = Database(":memory:")
    sid = db.create_session(db.create_user("c"), "Social media should be banned for children under 16.", "proponent")
    inner = ScriptedInner()
    r = process_turn(db, inner, sid, "Social media should be banned for children because it is harmful.")
    assert r["orchestrator"] == "crewai"
    assert inner.tasks == ["analyse", "score", "diagnose", "oppose"]
    assert r["diagnosis"]["lowest_weakness"] == "insufficient_evidence"
    assert r["intervention"]["type"] == "evidence_demanding_challenge"
    assert {"orchestrate", "strategise", "track"} <= set(r["timings"])      # the three rule-based agents ran
    assert db.history(sid)[0]["weakness"] == "insufficient_evidence"
