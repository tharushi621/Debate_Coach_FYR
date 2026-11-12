"""Runs ui/streamlit_app.py end to end against a stand-in `streamlit` module and a fake API client.
It checks the flow and the blinding behaviour; it does NOT replace opening the real page once (see README)."""
import runpy
import sys
import types
from unittest.mock import MagicMock

import pytest

from ui import client as api_client


class Halt(Exception):
    pass


class SS(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


def make_st(buttons=(), chat=None, texts=None):
    st = MagicMock()
    st.session_state = SS()
    st.button.side_effect = lambda label, *a, **k: any(b in label for b in buttons)
    st.chat_input.return_value = chat
    st.text_input.return_value = (texts or {}).get("code", "P01")
    st.selectbox.return_value = "Social media should be banned for children under 16."
    st.columns.side_effect = lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
    st.slider.return_value = 3
    st.text_area.return_value = ""
    st.stop.side_effect = Halt
    st.rerun.side_effect = Halt
    comp = types.SimpleNamespace(html=MagicMock())
    st.components = types.SimpleNamespace(v1=comp)  # `import streamlit.components.v1 as c` resolves by attribute
    return st, comp


class FakeClient:
    display = "full"

    def topics(self):
        return ["Social media should be banned for children under 16."]

    def create_user(self, name):
        return 1

    def create_session(self, uid, topic, side, mode):
        FakeClient.side_seen = side
        return {"session_id": 7, "mode": mode}

    def turn(self, sid, arg):
        full = FakeClient.display == "full"
        r = {"display": FakeClient.display, "ai_opponent_response": "Counter point.", "feedback": "fb", "validation_flags": [],
             "scores": {"overall_quality": 4.2, "dimensions": {"evidence_quality": {"score": 4}, "claim_clarity": {"score": 4}}},
             "diagnosis": {"lowest_weakness": "weak_rebuttal", "diagnosis_reason": "why"}, "intervention": {"type": "counter"},
             "analysis": {"main_claim": "c"}, "progress": {"score_change": None}}
        return r if full else {**r, "scores": r["scores"]}

    def history(self, sid):
        return []

    def feedback(self, p):
        return {}


def run(monkeypatch, st, comp):
    mods = {"streamlit": st, "streamlit.components": types.SimpleNamespace(v1=comp), "streamlit.components.v1": comp}
    for k, v in mods.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.setattr(api_client, "Client", lambda *a, **k: FakeClient())
    try:
        runpy.run_path("ui/streamlit_app.py", run_name="__main__")
    except Halt:
        pass


def test_full_flow_lobby_toss_stage_turn(monkeypatch):
    st, comp = make_st(buttons=("Enter the arena",))
    run(monkeypatch, st, comp)
    assert st.session_state["phase"] == "toss" and st.session_state["user_id"] == 1

    st.button.side_effect = lambda label, *a, **k: "Flip the coin" in label
    run(monkeypatch, st, comp)
    toss = st.session_state["toss"]
    st.button.side_effect = lambda *a, **k: False
    run(monkeypatch, st, comp)  # the rerun that follows st.rerun(): coin is drawn landing on the stored face
    assert toss["face"] in ("heads", "tails")
    assert any(f'RESULT = "{toss["face"]}"' in c.args[0] for c in comp.html.call_args_list)

    st.button.side_effect = lambda label, *a, **k: "Take the stage" in label
    run(monkeypatch, st, comp)
    assert st.session_state["phase"] == "stage" and st.session_state["side"] == toss["side"] == FakeClient.side_seen

    st.chat_input.return_value = "Social media harms attention because studies link it to lower focus, therefore limits are justified."
    st.button.side_effect = lambda *a, **k: False
    run(monkeypatch, st, comp)
    g = st.session_state["game"]
    assert g["turns"] == 1 and g["xp"] > 30 and st.session_state["report"]["full"]


def test_blind_arm_stage_shows_only_participation(monkeypatch):
    FakeClient.display = "reply_only"
    try:
        from app import game
        st, comp = make_st(chat="x" * 40)
        st.session_state.update(phase="stage", user_id=1, topic="T", side="opponent", session_id=7, log=[], game=game.new_state(), report=None)
        run(monkeypatch, st, comp)
        assert st.session_state["game"]["xp"] == game.PARTICIPATION_XP
        assert not st.bar_chart.called and not st.metric.called  # no scores leaked in a control arm
    finally:
        FakeClient.display = "full"


def test_backend_down_is_friendly(monkeypatch):
    class Down(FakeClient):
        def topics(self):
            raise api_client.ApiError("Cannot reach the backend")

    st, comp = make_st()
    monkeypatch.setattr(api_client, "Client", lambda *a, **k: Down())
    for k, v in {"streamlit": st, "streamlit.components": types.SimpleNamespace(v1=comp), "streamlit.components.v1": comp}.items():
        monkeypatch.setitem(sys.modules, k, v)
    with pytest.raises(Halt):
        runpy.run_path("ui/streamlit_app.py", run_name="__main__")
    st.error.assert_called_once()
