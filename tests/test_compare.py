"""The comparison evaluation, checked with a scripted model (a test double: it produces no thesis data)."""
import pandas as pd

from eval import baselines, compare
from app.taxonomy import DIMENSIONS


class FakeLLM:
    name = model = "scripted"

    def json(self, task, prompt, payload=None, retries=0):
        if "Score this debate" in prompt:
            return {d: {"score": 4 if d != "evidence_quality" else 1, "explanation": "x"} for d in DIMENSIONS}
        if "argument analyst" in prompt:
            return {"main_claim": "c", "grounds": [], "warrant": None}
        if "weakness diagnostician" in prompt:
            return {}
        if "most consequential weakness of this argument" in prompt:
            return {"lowest_weakness": "missing_warrant"}
        if "First decide" in prompt:
            return {"lowest_weakness": "insufficient_evidence", "ai_opponent_response": "What evidence supports that?"}
        return {"ai_opponent_response": "What specific evidence supports that claim?"}


def _ref(tmp_path, n=8):
    rows = [{"item_id": f"L{i:03d}", "topic": "Social media should be banned for children under 16.", "side": "proponent",
             "argument": f"Social media is harmful to children number {i}, so it should be banned.",
             "reference_weakness": "insufficient_evidence" if i % 2 else "missing_warrant", "split": "test"} for i in range(n)]
    p = tmp_path / "ref.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p)


def test_baselines_return_valid_labels_and_replies():
    llm = FakeLLM()
    assert baselines.single_prompt_diagnose(llm, "t", "proponent", "a") == "missing_warrant"
    assert baselines.generic_opponent(llm, "t", "proponent", "a").endswith("?")
    assert baselines.single_call_opponent(llm, "t", "proponent", "a")[0] == "insufficient_evidence"


def test_mcnemar_counts_discordant_pairs():
    n10, n01, p = compare.mcnemar_exact(["a", "a", "b", "b"], ["a", "a", "x", "x"], ["x", "x", "b", "x"])
    assert (n10, n01) == (2, 1) and 0 < p <= 1


def test_diagnose_compares_all_arms_on_the_same_items(tmp_path, monkeypatch):
    monkeypatch.setattr(compare, "OUT", str(tmp_path))
    m = compare.diagnose("ollama", "test", _ref(tmp_path), llm=FakeLLM())
    assert set(m["arms"]) == {"thesis_system", "single_prompt_llm", "majority_class"} and m["arms"]["thesis_system"]["n"] == 8
    assert m["arms"]["thesis_system"]["accuracy"] == 0.5      # insufficient_evidence is right on the odd items only


def test_blind_sheets_hide_the_arm_and_analysis_reads_ratings(tmp_path):
    out = str(tmp_path / "r")
    items, rows = compare.replies("ollama", "test", 6, 7, _ref(tmp_path), llm=FakeLLM(), out_dir=out)
    assert (items, rows) == (6, 18)
    sheet = pd.read_csv(f"{out}/rater_A.csv")
    assert "arm" not in sheet.columns and set(sheet.columns) >= {"reply", "reference_weakness"}
    key = pd.read_csv(f"{out}/key.csv").set_index("reply_id")
    for who, bonus in (("A", 0), ("B", 1)):
        s = pd.read_csv(f"{out}/rater_{who}.csv")
        arms = s.reply_id.map(key.arm)
        s["targets_weakness_1to5"] = [5 if a == "adaptive" else 3 for a in arms]
        s["helpful_next_step_1to5"] = [min(5, (4 if a == "adaptive" else 2) + bonus) for a in arms]
        s["writes_argument_for_student_yes_no"] = "no"
        s.to_csv(f"{out}/rater_{who}.csv", index=False)
    r = compare.analyse(out)
    assert r["mean_by_arm"]["adaptive"]["targets"] == 5 and r["mean_by_arm"]["generic"]["targets"] == 3
    assert r["targets: adaptive vs generic"]["win"] == 6


def test_rater_workbooks_round_trip_into_the_analysis(tmp_path, monkeypatch):
    from openpyxl import load_workbook
    from eval import rater_workbooks as rw
    out = str(tmp_path / "r")
    compare.replies("ollama", "test", 4, 7, _ref(tmp_path), llm=FakeLLM(), out_dir=out)
    monkeypatch.setattr(rw, "RDIR", out)
    monkeypatch.setattr(rw, "SEND", f"{out}/send")
    assert rw.make() == 12
    key = pd.read_csv(f"{out}/key.csv").set_index("reply_id")
    files = []
    for who in "AB":
        wb = load_workbook(f"{out}/send/Rater_{who}.xlsx")
        assert wb.sheetnames == ["Instructions", "Ratings"] and "arm" not in [c.value for c in wb["Ratings"][rw.HEADER_ROW]]
        assert "HOW TO RATE" in wb["Ratings"]["A1"].value          # the instructions are on the sheet the rater works in
        for row in wb["Ratings"].iter_rows(min_row=rw.HEADER_ROW + 1):
            adaptive = key.arm[row[0].value] == "adaptive"
            row[6].value, row[7].value, row[8].value = (5 if adaptive else 2), (4 if adaptive else 2), "no"
        wb.save(f"{tmp_path}/Rater_{who}.xlsx")
        files.append(str(tmp_path / f"Rater_{who}.xlsx"))
    rw.import_(files)
    res = compare.analyse(out)
    assert res["mean_by_arm"]["adaptive"]["targets"] == 5 and res["mean_by_arm"]["generic"]["targets"] == 2
    # an incomplete workbook is rejected, never silently imported
    wb = load_workbook(files[0])
    wb["Ratings"].cell(rw.HEADER_ROW + 1, 7).value = None
    wb.save(files[0])
    import pytest
    with pytest.raises(SystemExit):
        rw.import_([files[0]])


def test_reply_generation_resumes_after_a_failure_without_redoing_finished_items(tmp_path):
    import pytest

    class Flaky(FakeLLM):
        def __init__(self, fail_after):
            self.n_analyse, self.fail_after = 0, fail_after

        def json(self, task, prompt, payload=None, retries=0):
            if "argument analyst" in prompt:
                self.n_analyse += 1
                if self.n_analyse > self.fail_after:
                    raise RuntimeError("simulated rate limit")
            return super().json(task, prompt, payload, retries)
    out, ref = str(tmp_path / "r"), _ref(tmp_path)
    with pytest.raises(RuntimeError):
        compare.replies("ollama", "test", 5, 7, ref, llm=Flaky(3), out_dir=out)
    saved = [line for line in open(f"{out}/_partial.jsonl") if line.strip()]
    assert len(saved) == 3                                   # the three finished items survived the failure
    second = Flaky(99)
    items, rows = compare.replies("ollama", "test", 5, 7, ref, llm=second, out_dir=out)
    assert (items, rows) == (5, 15) and second.n_analyse == 2   # only the two missing items were generated
    assert len(pd.read_csv(f"{out}/key.csv")) == 15


def test_rate_limit_is_waited_out_and_never_reported_as_none(monkeypatch):
    import pytest
    import requests
    from app import llm as llm_mod
    waits = []

    class R:
        def __init__(self, code, headers=None):
            self.status_code, self.headers, self.text = code, headers or {}, "slow down"

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}
    seq = [R(429, {"retry-after": "1"}), R(429), R(200)]
    monkeypatch.setattr(requests, "post", lambda *a, **k: seq.pop(0))
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: waits.append(s))
    m = llm_mod.OpenAICompatLLM(api_key="k", model="m")
    assert m._post([{"role": "user", "content": "x"}], "score", retries=0) == "{}" and len(waits) == 2
    monkeypatch.setattr(requests, "post", lambda *a, **k: R(429))
    monkeypatch.setenv("LLM_RATE_RETRIES", "2")
    with pytest.raises(RuntimeError, match="rate limit not lifting.*429"):
        m._post([{"role": "user", "content": "x"}], "score", retries=0)


def test_identical_ratings_in_both_files_are_flagged_not_reported_as_agreement(tmp_path):
    out = str(tmp_path / "r")
    compare.replies("ollama", "test", 4, 7, _ref(tmp_path), llm=FakeLLM(), out_dir=out)
    s = pd.read_csv(f"{out}/rater_A.csv")
    s["targets_weakness_1to5"] = [4, 3, 5, 2, 4, 1] * 2
    s["helpful_next_step_1to5"] = [3, 3, 4, 2, 5, 1] * 2
    s["writes_argument_for_student_yes_no"] = ["no", "no", "yes", "no", "no", "yes"] * 2
    for who in "AB":
        s.to_csv(f"{out}/rater_{who}.csv", index=False)       # the same ratings in both files
    r = compare.analyse(out)
    assert "IDENTICAL" in r["WARNING"] and r["rater_agreement_qwk"] is None


def test_a_single_copied_column_is_flagged_even_when_another_column_differs(tmp_path):
    out = str(tmp_path / "r")
    compare.replies("ollama", "test", 4, 7, _ref(tmp_path), llm=FakeLLM(), out_dir=out)
    base = pd.read_csv(f"{out}/rater_A.csv")
    base["targets_weakness_1to5"] = [1, 2, 3, 4, 5, 3] * 2
    base["writes_argument_for_student_yes_no"] = ["no", "no", "yes", "no", "yes", "no"] * 2
    a, b = base.copy(), base.copy()
    a["helpful_next_step_1to5"] = [5, 4, 3, 2, 4, 5] * 2
    b["helpful_next_step_1to5"] = [4, 4, 2, 2, 5, 5] * 2
    a.to_csv(f"{out}/rater_A.csv", index=False)
    b.to_csv(f"{out}/rater_B.csv", index=False)
    r = compare.analyse(out)
    assert "targets" in r["WARNING"] and "ghost" in r["WARNING"] and "helpful" not in r["WARNING"].split("for:")[1].split(".")[0]
    assert r["rater_agreement_qwk"] is None or r["rater_agreement_qwk"].get("targets") is None


def test_an_all_no_ghostwriting_column_is_not_mistaken_for_copying(tmp_path):
    out = str(tmp_path / "r")
    compare.replies("ollama", "test", 4, 7, _ref(tmp_path), llm=FakeLLM(), out_dir=out)
    base = pd.read_csv(f"{out}/rater_A.csv")
    base["writes_argument_for_student_yes_no"] = "no"
    a, b = base.copy(), base.copy()
    a["targets_weakness_1to5"], b["targets_weakness_1to5"] = [5, 4, 3, 2, 4, 5] * 2, [4, 4, 2, 2, 5, 5] * 2
    a["helpful_next_step_1to5"], b["helpful_next_step_1to5"] = [3, 4, 3, 2, 4, 3] * 2, [4, 3, 3, 1, 4, 5] * 2
    a.to_csv(f"{out}/rater_A.csv", index=False)
    b.to_csv(f"{out}/rater_B.csv", index=False)
    r = compare.analyse(out)
    assert "WARNING" not in r and set(r["rater_agreement_qwk"]) == {"targets", "helpful"}
