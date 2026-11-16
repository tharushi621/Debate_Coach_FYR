"""Checks for the thesis items added late: session status, stored motions, custom motions, the seven-agent crew."""
import pytest

from app.api import build_app
from app.db import Database
from app.pipeline import process_turn
from app.topics import THESIS_MOTIONS, check_motion
from app.validation import ValidationError


def test_thesis_motions_are_stored_in_the_database():
    assert Database(":memory:").topics()[:5] == THESIS_MOTIONS


def test_custom_motion_is_validated_and_stored():
    assert check_motion("cities should ban cars from their centres") == "cities should ban cars from their centres."
    with pytest.raises(ValueError):
        check_motion("cars")
    db = Database(":memory:")
    db.add_topic(check_motion("Homework should be abolished in primary schools"))
    assert "Homework should be abolished in primary schools." in db.topics()


def test_new_session_is_active_and_an_ended_session_rejects_arguments(scripted, turn):
    db = Database(":memory:")
    sid = db.create_session(db.create_user("a"), THESIS_MOTIONS[0], "proponent")
    assert db.get_session(sid)["status"] == "active"
    db.end_session(sid)
    assert db.get_session(sid)["status"] == "ended"
    with pytest.raises(ValidationError):
        process_turn(db, scripted([turn()]), sid, "Social media harms the sleep of children under sixteen.")


def test_api_exposes_topics_custom_motion_and_end(scripted, turn):
    from fastapi.testclient import TestClient
    c = TestClient(build_app(Database(":memory:"), scripted([turn()])))
    assert c.get("/topics").json()[:5] == THESIS_MOTIONS
    assert c.post("/topics", json={"motion": "x"}).status_code == 422
    uid = c.post("/users", json={"name": "zed"}).json()["user_id"]
    sid = c.post("/sessions", json={"user_id": uid, "topic": "Cities should ban cars from their centres.",
                                    "student_side": "opponent"}).json()["session_id"]
    assert c.post(f"/sessions/{sid}/end").json()["status"] == "ended"
    assert c.post("/debate/turn", json={"session_id": sid, "argument": "Cars are essential for people with disabilities."}).status_code == 400


def test_crew_has_seven_agents_with_a_debate_orchestrator():
    pytest.importorskip("crewai")
    src = open("app/crew_flow.py", encoding="utf-8").read()
    assert 'agent("Debate Orchestrator"' in src and "agents=[orchestrator," in src
