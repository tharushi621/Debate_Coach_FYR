import json

from analysis.pilot import change_stats, per_participant, ratings
from analysis.report import build as build_report
from app.db import Database
from app.pipeline import process_turn

TOPIC = "Social media should be banned for children under 16."
ARGS = ["Social media should be banned for children because it is harmful.",
        "A 2019 study of 12000 teenagers found heavy social media use linked to depression. Therefore children under 16 need protection.",
        "Critics say bans are hard to enforce, but age checks already work for gambling and alcohol sales."]


def play(db, nickname, scripted, turn, n_turns=2, mode="adaptive"):
    uid = db.get_or_create_user(nickname)[0]
    sid = db.create_session(uid, TOPIC, "proponent", mode)
    llm = scripted([turn({"evidence_quality": 1}), turn({"evidence_quality": 3}), turn({"evidence_quality": 4})])
    for arg in ARGS[:n_turns]:
        process_turn(db, llm, sid, arg)
    return uid, sid


def test_one_row_per_participant_uses_the_longest_session_and_can_be_anonymised(scripted, turn):
    db = Database(":memory:")
    play(db, "P01", scripted, turn, n_turns=2)
    play(db, "P01", scripted, turn, n_turns=3)          # same participant, second and longer session
    play(db, "P02", scripted, turn, n_turns=2)
    pp = per_participant(db, anonymise=True)
    assert list(pp["Participant"]) == ["Participant 1", "Participant 2"] and list(pp["Turns"]) == [3, 2]


def test_developer_and_non_adaptive_sessions_never_count(scripted, turn):
    db = Database(":memory:")
    play(db, "P01", scripted, turn)
    play(db, "my_dev_account", scripted, turn)
    play(db, "P03", scripted, turn, mode="generic")      # a leftover session from a removed control arm
    assert list(per_participant(db)["Participant"]) == ["P01", "my_dev_account"]
    assert list(per_participant(db, exclude=["MY_DEV_ACCOUNT"])["Participant"]) == ["P01"]


def test_weakness_change_after_turn_1_is_counted_like_thesis_7_10(scripted, turn):
    db = Database(":memory:")
    play(db, "P01", scripted, turn)
    pp = per_participant(db)
    assert pp.loc[0, "Initial weakness"] == "Insufficient evidence" and pp.loc[0, "Weakness changed after turn 1"] == "Yes"
    assert change_stats(pp)["weakness_changed_after_turn1"] == 1


def test_ratings_use_the_latest_submission_of_each_participant(scripted, turn):
    db = Database(":memory:")
    uid, sid = play(db, "P01", scripted, turn)
    for fairness in (1, 5):
        with db.tx() as c:
            c.execute("INSERT INTO feedback(user_id,session_id,ease_of_use,clarity,ai_relevance,weakness_help,improvement_help,fairness,reuse,comment) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (uid, sid, 4, 4, 4, 4, 4, fairness, 4, ""))
    r = ratings(db)
    assert r.loc[r["Evaluation aspect"] == "Fairness of assessment", "Mean /5"].iloc[0] == 5 and (r["n"] == 1).all()


def test_report_reads_a_diagnostic_run_and_cross_checks_the_thesis(tmp_path, scripted, turn):
    db = Database(":memory:")
    play(db, "P01", scripted, turn)
    res = tmp_path / "res"
    res.mkdir()
    meta = {"backend": "ollama", "model": "llama3:8b", "date": "2026-11-16", "prompt_hash": "abc123abc123", "diag_use_llm": True,
            "test_split_runs_so_far": 1, "system": {"n": 30, "correct": 24, "accuracy": 0.8, "ci95": [0.627, 0.905], "kappa": 0.77},
            "baselines": {"majority_class": {"label": "unclear_claim", "accuracy": 0.11}}, "human_labeller_kappa": 0.8,
            "llm_diagnosis_accepted": 20, "rule_fallback_used": 10}
    (res / "ollama_test_2026-11-16.json").write_text(json.dumps(meta))
    text = build_report(db, str(tmp_path / "r.md"), str(res))
    assert "Accuracy 24/30 = 80.0%" in text and "DIAG_USE_LLM=True" in text
    assert "thesis says 7, stored data gives 1" in text and "differs" in text