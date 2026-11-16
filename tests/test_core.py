import pytest

from app import agents, llm as llm_module, pipeline
from app.db import Database
from app.llm import extract_json
from app.pipeline import process_turn
from app.taxonomy import DIMENSIONS, INTERVENTION_MAP, WEAKNESSES
from app.validation import ValidationError, preprocess, validate

TOPIC = "Social media should be banned for children under 16."
ARG1 = "Social media should be banned for children because it is harmful."
ARG2 = "A 2019 study of 12000 teenagers found heavy social media use linked to depression. Therefore children under 16 need protection."


@pytest.fixture
def env():
    db = Database(":memory:")
    uid = db.create_user("p01")
    return db, db.create_session(uid, TOPIC, "proponent")


def improving(scripted, turn):
    """Scripted model for two turns: evidence is the weakness on turn 1 and is fixed on turn 2."""
    return scripted([turn({"evidence_quality": 1}), turn({"evidence_quality": 4})])


# ---------------------------------------------------------------- no model needed
def test_every_weakness_has_intervention():
    assert set(INTERVENTION_MAP) == set(WEAKNESSES)


def test_validation_rejects_empty_short_duplicate():
    for bad in ["", "   ", "too short"]:
        with pytest.raises(ValidationError):
            validate(bad, TOPIC, [])
    ok = "Social media harms teenagers because it disrupts sleep."
    with pytest.raises(ValidationError):
        validate(ok, TOPIC, [ok])


def test_preprocess_keeps_meaning_of_curly_quotes_and_dashes():
    assert preprocess("don’t  stop — “ok”") == 'don\'t stop - "ok"'


def test_score_clamping_overall_and_default_is_flagged():
    class Bad:
        def json(self, *a, **k):
            return {d: {"score": 9, "explanation": ""} for d in DIMENSIONS[:-1]} | {"qualification": {"score": "x"}}
    s = agents.score(Bad(), TOPIC, "proponent", {}, "arg")
    assert all(1 <= v["score"] <= 5 for v in s["dimensions"].values())
    assert s["dimensions"]["qualification"]["score"] == 3
    assert s["dimensions"]["qualification"]["explanation"].startswith("[no valid LLM score")
    assert s["overall_quality"] == round((5 * 6 + 3) / 7, 2)


def test_thesis_example_overall_is_2_86():
    vals = dict(zip(DIMENSIONS, [4, 1, 2, 5, 2, 3, 3]))
    assert round(sum(vals.values()) / 7, 2) == 2.86


def test_tie_break_prefers_more_consequential():
    dims = {d: {"score": 3, "explanation": ""} for d in DIMENSIONS}
    dims["rebuttal_readiness"]["score"] = dims["evidence_quality"]["score"] = 1
    assert agents.lowest_dimension(dims) == "evidence_quality"


def test_diagnosis_drives_intervention():
    for w in WEAKNESSES:
        assert agents.strategise({"lowest_weakness": w})["type"] == INTERVENTION_MAP[w]


def test_json_extraction_tolerates_prose():
    assert extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}


def test_guardrail_replaces_leaky_or_toothless_reply():
    class Leaky:
        def json(self, *a, **k):
            return {"ai_opponent_response": "You scored 2/5 on evidence."}
    diag = {"lowest_weakness": "insufficient_evidence", "diagnosis_reason": "x"}
    iv = agents.strategise(diag)
    text, fb = agents.oppose(Leaky(), TOPIC, "proponent", "arg", {"main_claim": "c"}, diag, iv)
    assert fb and "2/5" not in text


def test_no_mock_model_or_control_arms_left_in_app():
    assert not hasattr(llm_module, "HeuristicLLM")
    assert not hasattr(agents, "single_prompt_baseline") and not hasattr(agents, "SINGLE_PROMPT")
    assert not hasattr(pipeline, "GENERIC_REPLY")


def test_unknown_llm_backend_is_an_error_not_a_silent_mock(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "heuristic")
    with pytest.raises(RuntimeError):
        llm_module.make_llm()


# ---------------------------------------------------------------- LLM diagnosis proposal (thesis 6.2.4)
def _scores(**over):
    dims = {d: {"score": 3, "explanation": ""} for d in DIMENSIONS}
    for k, v in over.items():
        dims[k]["score"] = v
    return {"dimensions": dims, "overall_quality": 3.0}


class _Diag:
    def __init__(self, out):
        self.out = out

    def json(self, *a, **k):
        if isinstance(self.out, Exception):
            raise self.out
        return self.out


def test_llm_diagnosis_accepted_when_valid_and_near_lowest():
    sc = _scores(evidence_quality=1, warrant_strength=2)
    d = agents.diagnose(sc, "arg", {"grounds": []}, llm=_Diag({"lowest_weakness": "missing_warrant", "diagnosis_reason": "link unexplained"}))
    assert d["lowest_weakness"] == "missing_warrant" and d["source"] == "llm" and d["diagnosis_reason"] == "link unexplained"


def test_llm_diagnosis_rejected_falls_back_to_lowest_dimension():
    sc = _scores(evidence_quality=1)
    for bad in ({"lowest_weakness": "nonsense"}, {"lowest_weakness": "weak_rebuttal"}, RuntimeError("down")):
        d = agents.diagnose(sc, "arg", {"grounds": []}, llm=_Diag(bad))
        assert d["lowest_weakness"] == "insufficient_evidence" and d["source"] == "rule_fallback"


# ---------------------------------------------------------------- full turns with a scripted model
def test_full_turn_and_progress(env, scripted, turn):
    db, sid = env
    llm = improving(scripted, turn)
    r1 = process_turn(db, llm, sid, ARG1)
    assert r1["diagnosis"]["lowest_weakness"] == "insufficient_evidence"
    assert r1["intervention"]["type"] == INTERVENTION_MAP["insufficient_evidence"]
    assert r1["progress"]["score_change"] is None and r1["mode"] == "adaptive"
    r2 = process_turn(db, llm, sid, ARG2)
    p = r2["progress"]
    assert p["score_change"] > 0 and p["targeted_improved"] is True
    assert len(db.history(sid)) == 2


def test_progress_has_the_thesis_6_2_7_fields(env, scripted, turn):
    db, sid = env
    llm = improving(scripted, turn)
    process_turn(db, llm, sid, ARG1)
    p = process_turn(db, llm, sid, ARG2)["progress"]
    assert p["previous_score"] == 2.71 and p["current_score"] == 3.14 and p["score_change"] == 0.43
    assert p["improvement"] is True                      # score went up AND the weakness changed
    assert p["previous_weakness"] == "insufficient_evidence" and p["current_weakness"] != p["previous_weakness"]


def test_conversation_history_reaches_the_opponent(env, scripted, turn):
    db, sid = env
    llm = improving(scripted, turn)
    process_turn(db, llm, sid, ARG1)
    process_turn(db, llm, sid, ARG2)
    prompt = [p for t, p in llm.calls if t == "oppose"][-1]
    assert f"Student: {ARG1}" in prompt and "Opponent: Why does that follow" in prompt


def test_soft_flags_identify_but_do_not_reject(env, scripted, turn):
    from app.validation import soft_flags
    assert soft_flags("Football is popular and many people watch it on weekends.", TOPIC)[0]["code"] == "low_topic_overlap"
    db, sid = env
    r = process_turn(db, scripted([turn({"relevance": 1})]), sid, "Football is popular and many people watch it on weekends with friends.")
    assert r["validation_flags"] and r["diagnosis"]["lowest_weakness"] == "poor_relevance"


def test_every_table_gets_rows_for_a_turn(env, scripted, turn):
    db, sid = env
    r = process_turn(db, scripted([turn()]), sid, ARG1)
    tid = r["turn_id"]
    expected = {"argument_analyses": 1, "argument_scores": 7, "weakness_diagnoses": 1, "ai_responses": 1}
    for table, n in expected.items():
        assert db.one(f"SELECT COUNT(*) n FROM {table} WHERE turn_id=?", (tid,))["n"] == n, table
    assert db.one("SELECT COUNT(*) n FROM interventions")["n"] == 1
    assert db.one("SELECT COUNT(*) n FROM debate_turns WHERE session_id=?", (sid,))["n"] == 1
    assert set(r["analysis"]["missing_components"]) <= {"grounds", "warrant", "backing", "qualifier", "rebuttal"}


def test_data_survives_restart(tmp_path, scripted, turn):
    path = str(tmp_path / "restart.db")
    db = Database(path)
    sid = db.create_session(db.create_user("P01"), TOPIC, "proponent")
    process_turn(db, scripted([turn()]), sid, ARG1)
    again = Database(path)  # a fresh connection, as after restarting the backend
    h = again.history(sid)
    assert len(h) == 1 and h[0]["weakness"] and h[0]["response_text"]


def test_fallback_and_source_are_persisted(env, scripted, turn):
    db, sid = env
    process_turn(db, scripted([turn()]), sid, ARG1)
    assert db.one("SELECT source FROM weakness_diagnoses")["source"] == "rule_fallback"
    assert db.one("SELECT fallback_used FROM ai_responses")["fallback_used"] == 0


def test_leaky_reply_is_replaced_and_recorded_as_fallback(env, scripted, turn):
    db, sid = env
    r = process_turn(db, scripted([turn(reply="You scored 2/5 here.")]), sid, ARG1)
    assert r["guardrail_fallback"] is True and "2/5" not in r["ai_opponent_response"]
    assert db.one("SELECT fallback_used FROM ai_responses")["fallback_used"] == 1


# ---------------------------------------------------------------- API (needs fastapi + httpx)
def test_api_flow_and_persistence(scripted, turn):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.api import build_app
    db = Database(":memory:")
    c = TestClient(build_app(db=db, llm=scripted([turn()])))
    uid = c.post("/users", json={"name": "p02"}).json()["user_id"]
    made = c.post("/sessions", json={"user_id": uid, "topic": TOPIC, "student_side": "proponent"})
    assert made.json()["mode"] == "adaptive"
    sid = made.json()["session_id"]
    assert c.post("/debate/turn", json={"session_id": sid, "argument": ""}).status_code == 400
    ok = c.post("/debate/turn", json={"session_id": sid, "argument": ARG1})
    assert ok.status_code == 200 and "ai_opponent_response" in ok.json()
    assert c.get(f"/sessions/{sid}/next-turn").json()["next_turn"] == 2
    assert c.post("/debate/turn", json={"session_id": 999, "argument": "x" * 40}).status_code == 404
    assert len(c.get("/topics").json()) == 5


def test_api_only_supports_the_adaptive_mode(scripted, turn):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.api import build_app
    c = TestClient(build_app(db=Database(":memory:"), llm=scripted([turn()])))
    uid = c.post("/users", json={"name": "p03"}).json()["user_id"]
    for mode in ("generic", "single", "random"):
        r = c.post("/sessions", json={"user_id": uid, "topic": TOPIC, "student_side": "proponent", "mode": mode})
        assert r.status_code == 422


# ---------------------------------------------------------------- analysis package (pilot tables; study.py was removed: no control group, thesis 7.12)
def test_pilot_tables_from_database(scripted, turn):
    from analysis.pilot import change_stats, per_participant, ratings
    db = Database(":memory:")
    for code in ("P01", "P02"):
        uid = db.create_user(code)
        sid = db.create_session(uid, TOPIC, "proponent")
        llm = improving(scripted, turn)
        process_turn(db, llm, sid, ARG1)
        process_turn(db, llm, sid, ARG2)
        with db.tx() as c:
            c.execute("INSERT INTO feedback(user_id,session_id,ease_of_use,clarity,ai_relevance,weakness_help,improvement_help,fairness,reuse,comment) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (uid, sid, 5, 4, 4, 4, 5, 3, 5, ""))
    pp = per_participant(db)
    assert list(pp["Participant"]) == ["P01", "P02"] and (pp["Change"] > 0).all()
    assert set(pp["Targeted weakness improved"]) <= {"Yes", "Partly", "No"}
    r = ratings(db)
    assert len(r) == 7 and r.loc[r["Evaluation aspect"] == "Fairness of assessment", "Mean /5"].iloc[0] == 3
    assert change_stats(pp)["improved"] == 2


def test_wilson_interval_matches_thesis_example():
    from eval.diagnostic_eval import wilson
    lo, hi = wilson(24, 30)
    assert 0.62 < lo < 0.65 and 0.89 < hi < 0.92

def test_scores_returned_as_a_list_or_wrapped_do_not_crash():
    from app import agents
    from app.taxonomy import DIMENSIONS
    as_list = [{"dimension": d, "score": 2, "explanation": "x"} for d in DIMENSIONS]
    assert all(v["score"] == 2 for v in agents.normalise_scores(as_list)["dimensions"].values())
    assert all(v["score"] == 4 for v in agents.normalise_scores([4] * 7)["dimensions"].values())
    wrapped = {"scores": {d: {"score": 5} for d in DIMENSIONS}}
    assert agents.normalise_scores(wrapped)["overall_quality"] == 5
    junk = agents.normalise_scores([{"foo": 1}])            # unusable shape: every score defaults to 3, no exception
    assert junk["overall_quality"] == 3
    assert agents.normalise_analysis([{"main_claim": "c"}], "t", "a")["main_claim"] == "c"
    assert agents.normalise_analysis(["not a dict"], "t", "a")["main_claim"] == "a"
