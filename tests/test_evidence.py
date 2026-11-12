import pandas as pd
import pytest

from app.db import Database
from app.llm import HeuristicLLM
from app.pipeline import process_turn
from app.taxonomy import WEAKNESSES
from analysis.report import build as build_report, claim_wording
from eval import agreement, diagnostic_eval
from eval.make_label_sheets import build as build_sheets

TOPIC = "Social media should be banned for children under 16."


@pytest.fixture
def lab(tmp_path):
    d = str(tmp_path / "lab")
    build_sheets(out_dir=d)
    return d


def _fill(d, flip=3):
    key = pd.read_csv(f"{d}/key.csv").set_index("item_id")
    for name, flips in (("A", 0), ("B", flip)):
        sh = pd.read_csv(f"{d}/labeller_{name}.csv")
        sh["weakness_label"] = key.intended_weakness.reindex(sh.item_id).values
        for i in range(flips):  # labeller B disagrees on a few items
            sh.loc[i, "weakness_label"] = "unclear_claim" if sh.loc[i, "weakness_label"] != "unclear_claim" else "missing_warrant"
        sh.to_csv(f"{d}/labeller_{name}.csv", index=False)


def test_wilson_interval_matches_reference_values():
    lo, hi = diagnostic_eval.wilson(24, 30)
    assert abs(lo - 0.627) < 0.005 and abs(hi - 0.905) < 0.005


def test_sheets_are_blind_balanced_and_deterministic(lab, tmp_path):
    A, B = pd.read_csv(f"{lab}/labeller_A.csv"), pd.read_csv(f"{lab}/labeller_B.csv")
    assert len(A) == 45 and "intended_weakness" not in A.columns and "split" not in A.columns
    assert set(A.item_id) == set(B.item_id) and list(A.item_id) != list(B.item_id)
    key = pd.read_csv(f"{lab}/key.csv")
    dev = key[key.split == "dev"]
    assert len(dev) == 10 and dev.intended_weakness.nunique() == len(WEAKNESSES)
    assert key.intended_weakness.value_counts().eq(5).all()
    d2 = str(tmp_path / "lab2")
    build_sheets(out_dir=d2)
    assert open(f"{lab}/key.csv").read() == open(f"{d2}/key.csv").read()


def test_agreement_resolution_and_reference(lab):
    _fill(lab, flip=3)
    stats, dis = agreement.compute(f"{lab}/labeller_A.csv", f"{lab}/labeller_B.csv", f"{lab}/key.csv", lab)
    assert stats["n"] == 45 and 0 < stats["kappa"] < 1 and len(dis) >= 2
    with pytest.raises(ValueError):
        agreement.finalise(lab)  # final_label still empty
    res = pd.read_csv(f"{lab}/resolve.csv")
    res["final_label"] = res.label_A
    res.to_csv(f"{lab}/resolve.csv", index=False)
    ref = agreement.finalise(lab)
    assert len(ref) == 45 and int((~ref.agreed_without_discussion).sum()) == len(dis)
    assert set(ref.reference_weakness) <= set(WEAKNESSES)


def test_invalid_labels_are_rejected(lab):
    with pytest.raises(ValueError):
        agreement.compute(f"{lab}/labeller_A.csv", f"{lab}/labeller_B.csv", f"{lab}/key.csv", lab)  # sheets are still blank


def test_eval_respects_split_and_logs_every_test_run(lab, tmp_path):
    _fill(lab)
    agreement.compute(f"{lab}/labeller_A.csv", f"{lab}/labeller_B.csv", f"{lab}/key.csv", lab)
    res = pd.read_csv(f"{lab}/resolve.csv")
    res["final_label"] = res.label_A
    res.to_csv(f"{lab}/resolve.csv", index=False)
    agreement.finalise(lab)
    out = str(tmp_path / "res")
    ref = f"{lab}/reference_labels.csv"
    dev, _ = diagnostic_eval.run("heuristic", "dev", ref, out)
    assert dev["system"]["n"] == 10 and "test_split_runs_so_far" not in dev
    t1, df = diagnostic_eval.run("heuristic", "test", ref, out)
    t2, _ = diagnostic_eval.run("heuristic", "test", ref, out)
    assert t1["system"]["n"] == 35 and t1["test_split_runs_so_far"] == 1 and t2["test_split_runs_so_far"] == 2
    assert t1["human_reference_labels"] is True and "human_labeller_kappa" in t1
    assert len(t1["prompt_hash"]) == 12 and "majority_class" in t1["baselines"]
    assert set(df.diagnosis_source) <= {"llm", "rule_fallback"}


def test_claim_wording_matches_what_data_can_support():
    assert "no inferential" in claim_wording({"n": 4, "improved": 4, "mean_change": 1.0, "bootstrap_95ci": (0.5, 1.5)})
    assert "Preliminary evidence" in claim_wording({"n": 8, "improved": 8, "mean_change": 1.0, "bootstrap_95ci": (0.7, 1.3)})
    assert "Inconclusive" in claim_wording({"n": 8, "improved": 5, "mean_change": 0.3, "bootstrap_95ci": (-0.2, 0.9)})
    assert "fell" in claim_wording({"n": 8, "improved": 1, "mean_change": -0.5, "bootstrap_95ci": (-0.9, -0.1)})


def test_report_flags_participant_count_mismatch(tmp_path):
    db, llm = Database(":memory:"), HeuristicLLM()
    for code in ("P01", "P02"):
        uid = db.create_user(code)
        sid = db.create_session(uid, TOPIC, "proponent")
        process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
        process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy use linked to depression. Therefore children need protection.")
    with db.tx() as c:  # only one of two participants rated
        c.execute("INSERT INTO feedback(user_id,session_id,ease_of_use,clarity,ai_relevance,weakness_help,improvement_help,fairness,reuse,comment) VALUES(1,1,4,4,4,4,4,4,4,'')")
    text = build_report(db, str(tmp_path / "r.md"), str(tmp_path / "none"))
    assert "Provenance" in text and "No test-split diagnostic run" in text
    assert "WARNING" in text and "Only 2 participants" in text


def test_eval_reads_the_simple_labelling_kit_output(tmp_path):
    """eval.labelling (the simpler kit) and eval.make_label_sheets both feed the same evaluation."""
    import shutil
    from eval import labelling
    d = tmp_path / "data"
    d.mkdir()
    shutil.copy("eval/data/sample_arguments.csv", d / "sample_arguments.csv")
    labelling.make(str(d))
    a, b = pd.read_csv(d / "labeller_sheet_A.csv"), pd.read_csv(d / "labeller_sheet_B.csv")
    truth = pd.read_csv(d / "sample_arguments.csv").set_index("id")["intended_weakness"]
    a["label"], b["label"] = a["id"].map(truth), b["id"].map(truth)
    b.loc[b.index[0], "label"] = "unclear_claim" if b.loc[b.index[0], "label"] != "unclear_claim" else "weak_rebuttal"
    a.to_csv(tmp_path / "a.csv", index=False)
    b.to_csv(tmp_path / "b.csv", index=False)
    labelling.reference(str(tmp_path / "a.csv"), str(tmp_path / "b.csv"), str(d))
    with pytest.raises(ValueError):
        diagnostic_eval._from_simple_kit(str(d))  # one disagreement is still unresolved
    ref = pd.read_csv(d / "reference_labels.csv")
    ref["final_label"] = ref["final_label"].fillna("").where(ref["final_label"].notna(), ref["label_A"])
    ref.to_csv(d / "reference_labels.csv", index=False)
    df = diagnostic_eval._from_simple_kit(str(d))
    assert len(df) == 45 and set(df.split) == {"dev", "test"} and set(df.reference_weakness) <= set(WEAKNESSES)


def test_report_and_study_summary_work_on_an_empty_database(tmp_path):
    db = Database(":memory:")
    text = build_report(db, str(tmp_path / "r.md"), str(tmp_path / "none"))
    assert "Provenance" in text and "no data yet" in text and "Participant counts agree" in text
