import pandas as pd
import pytest

from app.db import Database
from app.pipeline import process_turn
from app.taxonomy import WEAKNESSES
from eval import agreement, diagnostic_eval
from eval.make_label_sheets import build as build_sheets

TOPIC = "Social media should be banned for children under 16."


@pytest.fixture
def lab(tmp_path):
    d = str(tmp_path / "lab")
    build_sheets(out_dir=d)
    return d


def _fill(d, flip=3):
    """Fill both sheets from the author's intent so the evaluation CODE can be exercised in a test.
    (Real labels must come from two people; this helper is for tests only.)"""
    key = pd.read_csv(f"{d}/key.csv").set_index("item_id")
    for name, flips in (("A", 0), ("B", flip)):
        sh = pd.read_csv(f"{d}/labeller_{name}.csv")
        sh["weakness_label"] = key.intended_weakness.reindex(sh.item_id).values
        for i in range(flips):  # labeller B disagrees on a few items
            sh.loc[i, "weakness_label"] = "unclear_claim" if sh.loc[i, "weakness_label"] != "unclear_claim" else "missing_warrant"
        sh.to_csv(f"{d}/labeller_{name}.csv", index=False)


def _finalise(lab):
    agreement.compute(f"{lab}/labeller_A.csv", f"{lab}/labeller_B.csv", f"{lab}/key.csv", lab)
    res = pd.read_csv(f"{lab}/resolve.csv")
    res["final_label"] = res.label_A
    res.to_csv(f"{lab}/resolve.csv", index=False)
    return agreement.finalise(lab)


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


def test_sheets_are_never_overwritten_once_labels_exist(lab):
    build_sheets(out_dir=lab)  # still blank: rebuilding is harmless and allowed
    _fill(lab)
    before = open(f"{lab}/labeller_A.csv").read()
    with pytest.raises(SystemExit):
        build_sheets(out_dir=lab)
    assert open(f"{lab}/labeller_A.csv").read() == before


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


def test_evaluation_needs_human_labels(tmp_path):
    with pytest.raises(SystemExit):
        diagnostic_eval.load(str(tmp_path / "missing.csv"))   # no fallback to the author's intent, no mock backend


def test_eval_respects_split_and_logs_every_test_run(lab, tmp_path, scripted, turn):
    _fill(lab)
    _finalise(lab)
    out, ref = str(tmp_path / "res"), f"{lab}/reference_labels.csv"
    llm = scripted([turn()])
    dev, _ = diagnostic_eval.run("ollama", "dev", ref, out, llm=llm)
    assert dev["system"]["n"] == 10 and "test_split_runs_so_far" not in dev
    t1, df = diagnostic_eval.run("ollama", "test", ref, out, llm=llm)
    t2, _ = diagnostic_eval.run("ollama", "test", ref, out, llm=llm)
    assert t1["system"]["n"] == 35 and t1["test_split_runs_so_far"] == 1 and t2["test_split_runs_so_far"] == 2
    assert "human_labeller_kappa" in t1 and "diag_use_llm" in t1
    assert len(t1["prompt_hash"]) == 12 and list(t1["baselines"]) == ["majority_class"]
    assert set(df.diagnosis_source) <= {"llm", "rule_fallback"}


def test_claim_wording_matches_what_data_can_support():
    from analysis.report import claim_wording
    assert "no inferential" in claim_wording({"n": 4, "improved": 4, "mean_change": 1.0, "bootstrap_95ci": (0.5, 1.5)})
    assert "Preliminary evidence" in claim_wording({"n": 8, "improved": 8, "mean_change": 1.0, "bootstrap_95ci": (0.7, 1.3)})
    assert "Inconclusive" in claim_wording({"n": 8, "improved": 5, "mean_change": 0.3, "bootstrap_95ci": (-0.2, 0.9)})
    assert "fell" in claim_wording({"n": 8, "improved": 1, "mean_change": -0.5, "bootstrap_95ci": (-0.9, -0.1)})


def test_report_flags_participant_count_mismatch(tmp_path, scripted, turn):
    from analysis.report import build as build_report
    db = Database(":memory:")
    for code in ("P01", "P02"):
        uid = db.create_user(code)
        sid = db.create_session(uid, TOPIC, "proponent")
        llm = scripted([turn({"evidence_quality": 1}), turn({"evidence_quality": 4})])
        process_turn(db, llm, sid, "Social media should be banned for children because it is harmful.")
        process_turn(db, llm, sid, "A 2019 study of 12000 teenagers found heavy use linked to depression. Therefore children need protection.")
    with db.tx() as c:  # only one of two participants rated
        c.execute("INSERT INTO feedback(user_id,session_id,ease_of_use,clarity,ai_relevance,weakness_help,improvement_help,fairness,reuse,comment) VALUES(1,1,4,4,4,4,4,4,4,'')")
    text = build_report(db, str(tmp_path / "r.md"), str(tmp_path / "none"))
    assert "Provenance" in text and "No test-split diagnostic run" in text
    assert "WARNING" in text and "Only 2 participants" in text


def test_report_and_study_summary_work_on_an_empty_database(tmp_path):
    from analysis.report import build as build_report
    db = Database(":memory:")
    text = build_report(db, str(tmp_path / "r.md"), str(tmp_path / "none"))
    assert "Provenance" in text and "no data yet" in text and "Participant counts and turns agree" in text

def test_eight_labellers_use_a_strict_majority_and_report_fleiss_kappa(lab):
    key = pd.read_csv(f"{lab}/key.csv").set_index("item_id")
    base = pd.read_csv(f"{lab}/labeller_A.csv")
    paths = []
    for k, name in enumerate("ABCDEFGH"):
        sh = base.copy()
        sh["weakness_label"] = key.intended_weakness.reindex(sh.item_id).values
        sh.loc[(k * 3) % 45, "weakness_label"] = "unclear_claim" if sh.loc[(k * 3) % 45, "weakness_label"] != "unclear_claim" else "missing_warrant"
        sh.to_csv(f"{lab}/labeller_{name}.csv", index=False)
        paths.append(f"{lab}/labeller_{name}.csv")
    stats, dis = agreement.compute_many(paths, f"{lab}/key.csv", lab)
    assert stats["n_labellers"] == 8 and 0.7 < stats["fleiss_kappa"] <= 1 and len(dis) == 0   # one stray vote never beats 7 others
    ref = agreement.finalise(lab)
    assert ref.n_labellers.iloc[0] == 8 and ref.agreed_without_discussion.all()
    assert (ref.reference_weakness.values == key.intended_weakness.reindex(ref.item_id).values).all()


def test_coach_workbooks_have_own_order_and_round_trip(lab, tmp_path, monkeypatch):
    from openpyxl import load_workbook
    from eval import coach_workbooks as cw
    monkeypatch.setattr(cw, "D", lab)
    monkeypatch.setattr(cw, "SEND", str(tmp_path / "send"))
    assert cw.make(3) == 45
    ids = [[r[0] for r in load_workbook(f"{tmp_path}/send/Coach_{c}.xlsx")["Labels"].iter_rows(min_row=2, values_only=True)] for c in "ABC"]
    assert ids[0] != ids[1] and sorted(ids[0]) == sorted(ids[1]) == sorted(ids[2])
    wb = load_workbook(f"{tmp_path}/send/Coach_B.xlsx")
    for row in wb["Labels"].iter_rows(min_row=2):
        row[4].value = "missing_warrant"
    wb.save(f"{tmp_path}/Coach_B.xlsx")
    cw.import_([str(tmp_path / "Coach_B.xlsx")])
    assert (pd.read_csv(f"{lab}/labeller_B.csv").weakness_label == "missing_warrant").all()


def test_majority_and_plurality_rules_exclude_undecided_items_instead_of_guessing(lab):
    key = pd.read_csv(f"{lab}/key.csv").set_index("item_id")
    base = pd.read_csv(f"{lab}/labeller_A.csv")
    paths = []
    for k, name in enumerate("ABCD"):                       # 4 labellers; item 0: 2-2 split, item 1: 3-1, rest unanimous
        sh = base.copy()
        sh["weakness_label"] = key.intended_weakness.reindex(sh.item_id).values
        if k >= 2:
            sh.loc[0, "weakness_label"] = "unclear_claim" if sh.loc[0, "weakness_label"] != "unclear_claim" else "missing_warrant"
        if k == 3:
            sh.loc[1, "weakness_label"] = "unclear_claim" if sh.loc[1, "weakness_label"] != "unclear_claim" else "missing_warrant"
        sh.to_csv(f"{lab}/labeller_{name}.csv", index=False)
        paths.append(f"{lab}/labeller_{name}.csv")
    agreement.compute_many(paths, f"{lab}/key.csv", lab)
    maj = agreement.finalise(lab, "majority")
    plu = agreement.finalise(lab, "plurality")
    first, second = base.item_id.iloc[0], base.item_id.iloc[1]
    assert first not in set(maj.item_id) and first not in set(plu.item_id)          # 2-2 tie: never guessed
    assert len(maj) == 44 and len(plu) == 44 and second in set(maj.item_id) and second in set(plu.item_id)   # 3-1 is a strict majority
