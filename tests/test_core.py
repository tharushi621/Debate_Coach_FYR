import pytest
from app import agents
from app.db import Database
from app.llm import HeuristicLLM, extract_json
from app.pipeline import process_turn
from app.taxonomy import DIMENSIONS, INTERVENTION_MAP, WEAKNESSES
from app.validation import ValidationError, validate

TOPIC = "Social media should be banned for children under 16."


@pytest.fixture
def env():
    db = Database(":memory:")
    uid = db.create_user("p01")
    return db, HeuristicLLM(), db.create_session(uid, TOPIC, "proponent")


def test_every_weakness_has_intervention():
    assert set(INTERVENTION_MAP) == set(WEAKNESSES)


def test_validation_rejects_empty_short_duplicate():
    for bad in ["", "   ", "too short"]:
        with pytest.raises(ValidationError):
            validate(bad, TOPIC, [])
    ok = "Social media harms teenagers because it disrupts sleep."
    with pytest.raises(ValidationError):
        validate(ok, TOPIC, [ok])


def test_score_clamping_and_overall():
    class Bad:
        def json(self, *a, **k):
            return {d: {"score": 9, "explanation": ""} for d in DIMENSIONS[:-1]} | {"qualification": {"score": "x"}}
    s = agents.score(Bad(), TOPIC, "proponent", {}, "arg")
    assert all(1 <= v["score"] <= 5 for v in s["dimensions"].values())
    assert s["dimensions"]["qualification"]["score"] == 3
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
        d = {"lowest_weakness": w}
        assert agents.strategise(d)["type"] == INTERVENTION_MAP[w]


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


def test_full_turn_and_progress(env):
    db, llm, sid = env
    r1 = process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
    assert r1["diagnosis"]["lowest_weakness"] in WEAKNESSES
    assert r1["intervention"]["type"] == INTERVENTION_MAP[r1["diagnosis"]["lowest_weakness"]]
    assert r1["progress"]["score_change"] is None
    r2 = process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy social media use linked to depression. Therefore children under 16 need protection. However some argue bans are unenforceable, though age checks exist.")
    assert r2["progress"]["score_change"] > 0
    assert r2["progress"]["targeted_improved"] is True
    assert len(db.history(sid)) == 2


def test_generic_control_mode_is_untargeted(env):
    db, llm, _ = env
    sid = db.create_session(1, TOPIC, "opponent", mode="generic")
    r = process_turn(db, llm, sid, "Banning social media would restrict free expression and push teens to worse places.")
    assert r["intervention"]["type"] == "generic_counter"


def test_api_flow_and_persistence():
    pytest.importorskip('fastapi')
    pytest.importorskip('httpx')
    from fastapi.testclient import TestClient
    from app.api import build_app
    db = Database(":memory:")
    c = TestClient(build_app(db=db, llm=HeuristicLLM()))
    uid = c.post("/users", json={"name": "p02"}).json()["user_id"]
    sid = c.post("/sessions", json={"user_id": uid, "topic": TOPIC, "student_side": "proponent"}).json()["session_id"]
    assert c.post("/debate/turn", json={"session_id": sid, "argument": ""}).status_code == 400
    ok = c.post("/debate/turn", json={"session_id": sid, "argument": "Social media should be banned for children because it is harmful."})
    assert ok.status_code == 200 and "ai_opponent_response" in ok.json()
    assert c.get(f"/sessions/{sid}/next-turn").json()["next_turn"] == 2
    assert c.post("/debate/turn", json={"session_id": 999, "argument": "x" * 40}).status_code == 404
    assert len(c.get("/topics").json()) == 5


def test_three_arms_share_measurement_but_differ_in_reply():
    db, llm = Database(":memory:"), HeuristicLLM()
    arg = "Social media should be banned for children because it is harmful."
    out = {}
    for mode in ("adaptive", "single", "generic"):
        sid = db.create_session(1, TOPIC, "proponent", mode)
        out[mode] = process_turn(db, llm, sid, arg)
    # identical measurement in every arm
    assert len({o["scores"]["overall_quality"] for o in out.values()}) == 1
    assert len({o["diagnosis"]["lowest_weakness"] for o in out.values()}) == 1
    # only the adaptive arm shows diagnostics and targets the weakness
    assert out["adaptive"]["display"] == "full" and out["generic"]["display"] == "reply_only"
    assert out["adaptive"]["intervention"]["type"] != out["generic"]["intervention"]["type"]
    assert out["adaptive"]["ai_opponent_response"] != out["generic"]["ai_opponent_response"]


def test_study_statistics():
    import numpy as np
    from analysis.study import cohens_d, perm_test
    a, b = [1.0, 0.9, 1.1, 0.8, 1.2, 1.0], [0.1, 0.0, 0.2, -0.1, 0.1, 0.0]
    diff, p = perm_test(a, b, n=3000)
    assert diff > 0.8 and p < 0.01 and cohens_d(a, b) > 3
    _, p0 = perm_test(list(np.zeros(6)) + [0.1], list(np.zeros(6)) + [0.1], n=500)
    assert p0 > 0.5


def test_study_summary_on_db():
    from analysis.study import per_session, session_table
    db, llm = Database(":memory:"), HeuristicLLM()
    sid = db.create_session(1, TOPIC, "proponent", "adaptive")
    process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
    process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy use linked to depression. Therefore children need protection. However some argue bans are unenforceable.")
    ps = per_session(session_table(db))
    assert len(ps) == 1 and ps.iloc[0]["change"] > 0


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


def test_soft_flags_identify_but_do_not_reject(env):
    from app.validation import soft_flags
    assert soft_flags("Football is popular and many people watch it on weekends.", TOPIC)[0]["code"] == "low_topic_overlap"
    db, llm, sid = env
    r = process_turn(db, llm, sid, "Football is popular and many people watch it on weekends with friends.")
    assert r["validation_flags"] and r["diagnosis"]["lowest_weakness"] == "poor_relevance"


def test_progress_reports_previous_and_current_weakness(env):
    db, llm, sid = env
    process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
    r2 = process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy use linked to depression. Therefore children need protection.")
    p = r2["progress"]
    assert p["previous_weakness"] and p["current_weakness"] and p["previous_overall"] is not None


def test_every_table_gets_rows_for_a_turn(env):
    db, llm, sid = env
    r = process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
    tid = r["turn_id"]
    expected = {"argument_analyses": 1, "argument_scores": 7, "weakness_diagnoses": 1, "ai_responses": 1}
    for table, n in expected.items():
        assert db.one(f"SELECT COUNT(*) n FROM {table} WHERE turn_id=?", (tid,))["n"] == n, table
    assert db.one("SELECT COUNT(*) n FROM interventions")["n"] == 1
    assert db.one("SELECT COUNT(*) n FROM debate_turns WHERE session_id=?", (sid,))["n"] == 1
    assert set(r["analysis"]["missing_components"]) <= {"grounds", "warrant", "backing", "qualifier", "rebuttal"}


def test_data_survives_restart(tmp_path):
    path = str(tmp_path / "restart.db")
    db = Database(path)
    sid = db.create_session(db.create_user("P01"), TOPIC, "proponent")
    process_turn(db, HeuristicLLM(), sid, "Social media should be banned for children because it is harmful.")
    again = Database(path)  # a fresh connection, as after restarting the backend
    h = again.history(sid)
    assert len(h) == 1 and h[0]["weakness"] and h[0]["response_text"]


def test_pilot_tables_from_database():
    from analysis.pilot import change_stats, per_participant, ratings
    db, llm = Database(":memory:"), HeuristicLLM()
    for code in ("P01", "P02"):
        uid = db.create_user(code)
        sid = db.create_session(uid, TOPIC, "proponent")
        process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
        process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy use linked to depression. Therefore children need protection. However some argue bans are unenforceable.")
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


def test_labelling_kit_end_to_end(tmp_path):
    import shutil

    import pandas as pd

    from eval import labelling
    d = tmp_path / "data"
    d.mkdir()
    shutil.copy("eval/data/sample_arguments.csv", d / "sample_arguments.csv")
    labelling.make(str(d))
    a, b = pd.read_csv(d / "labeller_sheet_A.csv"), pd.read_csv(d / "labeller_sheet_B.csv")
    assert "intended_weakness" not in a.columns and list(a["id"]) != list(b["id"])  # blind and differently ordered
    truth = pd.read_csv(d / "sample_arguments.csv").set_index("id")["intended_weakness"]
    a["label"], b["label"] = a["id"].map(truth), b["id"].map(truth)
    b.loc[b.index[0], "label"] = "unclear_claim" if b.loc[b.index[0], "label"] != "unclear_claim" else "weak_rebuttal"
    a.to_csv(tmp_path / "a.csv", index=False)
    b.to_csv(tmp_path / "b.csv", index=False)
    kappa, agree = labelling.reference(str(tmp_path / "a.csv"), str(tmp_path / "b.csv"), str(d))
    assert 0.9 < kappa < 1.0 and abs(agree - 44 / 45) < 1e-9
    ref = pd.read_csv(d / "reference_labels.csv")
    assert (ref["final_label"].isna() | (ref["final_label"] == "")).sum() == 1
    split = pd.read_csv(d / "split.csv")
    assert set(split["set"]) == {"dev", "test"} and (split["set"] == "dev").sum() == 9


def test_fallback_and_source_are_persisted(env):
    db, llm, sid = env
    process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
    assert db.one("SELECT source FROM weakness_diagnoses")["source"] == "rule_fallback"
    assert db.one("SELECT fallback_used FROM ai_responses")["fallback_used"] in (0, 1)
