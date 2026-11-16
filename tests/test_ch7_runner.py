"""The Chapter 7 runner, resumability and scoring (scripted model: a test double, produces no thesis data)."""
import pandas as pd

from eval import run_chapter7 as rc
from tests.test_compare import FakeLLM


def _setup(tmp_path, monkeypatch):
    rows = [{"item_id": f"L{i:03d}", "topic": "Social media should be banned for children under 16.", "side": "proponent",
             "argument": f"Social media harms children number {i}, so ban it.", "split": "test" if i % 3 else "dev",
             "label_A": "missing_warrant", "label_B": "missing_warrant", "reference_weakness": "missing_warrant" if i % 2 else "insufficient_evidence",
             "agreed_without_discussion": True, "n_labellers": 2} for i in range(6)]
    pd.DataFrame(rows).to_csv(tmp_path / "plu.csv", index=False)
    pd.DataFrame(rows[:4]).to_csv(tmp_path / "maj.csv", index=False)
    monkeypatch.setattr(rc, "OUT", str(tmp_path / "res"))
    monkeypatch.setattr(rc, "REFS", {"strict_majority": str(tmp_path / "maj.csv"), "plurality": str(tmp_path / "plu.csv")})


def test_predict_resumes_and_analyse_scores_both_references(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rc.predict("ollama", llm=FakeLLM())
    first = pd.read_csv(rc.pred_path("ollama"))
    assert len(first) == 6
    rc.predict("ollama", llm=FakeLLM())                 # nothing left to do: no duplicates
    assert len(pd.read_csv(rc.pred_path("ollama"))) == 6
    out = rc.analyse("ollama")
    assert out["results"]["strict_majority"]["n_items"] == 4 and out["results"]["plurality"]["n_items"] == 6
    t = out["results"]["plurality"]["all"]["thesis_system"]
    assert t["n"] == 6 and 0 <= t["accuracy"] <= 1
    assert (tmp_path / "res" / f"ollama_test_{out['date']}.json").exists()
