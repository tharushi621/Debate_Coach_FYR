"""Diagnostic agreement evaluation (thesis 7.7).

  python -m eval.diagnostic_eval <ollama|openai> [--split dev|test|all]

Runs the REAL system (Analyzer, Scorer, Diagnostician logic from app/agents.py on a real LLM) on the labelled
arguments and compares the diagnosed weakness with the human reference label.

Reference labels MUST come from humans: eval/data/labelling/reference_labels.csv (written by eval.agreement --finalise
or eval.lite_eval finalise). There is no fallback to the author's intended labels and no mock model.

Use --split dev while tuning prompts. Run --split test ONLY after freezing the prompts: every test run is logged
(eval/results/test_runs.log) so you can state exactly how many times the test set was looked at.
Reports accuracy with a Wilson 95% interval, Cohen's kappa vs the reference, per-class precision/recall/F1, a confusion
matrix, a majority-class baseline (a statistic of the labels, not a model) and the two labellers' own agreement.

Note: thesis 7.7 reports 24/30 = 80% on a first set of 30 prepared arguments with a single reference. This script is a
stricter, additional protocol (two labellers, dev/test split); report its numbers as such, not as a replacement."""
import argparse
import datetime
import hashlib
import json
import math
import os

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from app import agents
from app.llm import OllamaLLM, OpenAICompatLLM

REF = "eval/data/labelling/reference_labels.csv"


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def prompt_hash():
    """Fingerprint of the prompts used by the diagnosis path: proves they were frozen between the dev and test runs."""
    texts = [agents.ANALYSE_PROMPT, agents.SCORE_PROMPT, agents.DIAG_PROMPT]
    return hashlib.sha256("\n".join(texts).encode()).hexdigest()[:12]


def load(ref_path=REF):
    if not os.path.exists(ref_path):
        raise SystemExit(f"{ref_path} not found. Two people must label the sheets first "
                         "(eval/data/labelling/labeller_A.csv and labeller_B.csv), then run: python -m eval.agreement "
                         "and python -m eval.agreement --finalise")
    df = pd.read_csv(ref_path)
    need = {"topic", "side", "argument", "reference_weakness"}
    if not need <= set(df.columns):
        raise SystemExit(f"{ref_path} is missing columns: {sorted(need - set(df.columns))}")
    if df.reference_weakness.isna().any():
        raise SystemExit(f"{ref_path} has empty reference_weakness cells: resolve the disagreements first")
    if "split" not in df:
        df["split"] = "test"
    return df


def predict(df, llm):
    preds, sources = [], []
    for _, r in df.iterrows():
        an = agents.analyse(llm, r.topic, r.side, [], r.argument)
        sc = agents.score(llm, r.topic, r.side, an, r.argument)
        d = agents.diagnose(sc, r.argument, an, llm=llm, topic=r.topic, side=r.side)
        preds.append(d["lowest_weakness"])
        sources.append(d["source"])
    return preds, sources


def summarise(ref, pred):
    ref, pred = list(ref), list(pred)
    k = sum(a == b for a, b in zip(ref, pred))
    lo, hi = wilson(k, len(ref))
    return {"n": len(ref), "correct": k, "accuracy": k / len(ref), "ci95": [lo, hi],
            "kappa": float(cohen_kappa_score(ref, pred)) if len(set(ref) | set(pred)) > 1 else float("nan")}


def run(backend="ollama", split="test", ref_path=REF, out_dir="eval/results", llm=None):
    os.makedirs(out_dir, exist_ok=True)
    allrows = load(ref_path)
    df = allrows if split == "all" else allrows[allrows.split == split].copy()
    if len(df) == 0:
        raise SystemExit(f"no rows in split '{split}'")
    llm = llm or {"ollama": OllamaLLM, "openai": OpenAICompatLLM}[backend]()
    preds, sources = predict(df, llm)
    df = df.assign(system_weakness=preds, diagnosis_source=sources)
    df["match"] = df.system_weakness == df.reference_weakness
    system = summarise(df.reference_weakness, df.system_weakness)
    majority = allrows.reference_weakness.mode().iloc[0]
    baselines = {"majority_class": {"label": majority, **summarise(df.reference_weakness, [majority] * len(df))}}
    labels = sorted(set(df.reference_weakness) | set(df.system_weakness))
    meta = {"date": datetime.date.today().isoformat(), "backend": backend, "model": getattr(llm, "model", "n/a"), "split": split,
            "prompt_hash": prompt_hash(), "diag_use_llm": os.getenv("DIAG_USE_LLM", "1") != "0",
            "system": system, "baselines": baselines,
            "llm_diagnosis_accepted": int((df.diagnosis_source == "llm").sum()), "rule_fallback_used": int((df.diagnosis_source == "rule_fallback").sum()),
            "per_class": classification_report(df.reference_weakness, df.system_weakness, zero_division=0, output_dict=True),
            "confusion_labels": labels, "confusion": confusion_matrix(df.reference_weakness, df.system_weakness, labels=labels).tolist()}
    lab_cols = [c for c in allrows.columns if c.startswith("label_")]
    if len(lab_cols) >= 2:      # mean pairwise Cohen's kappa among the human labellers (equals Cohen's kappa for two)
        import itertools
        pairs = list(itertools.combinations(lab_cols, 2))
        meta["human_labeller_kappa"] = float(sum(cohen_kappa_score(allrows[x], allrows[y]) for x, y in pairs) / len(pairs))
        meta["n_human_labellers"] = len(lab_cols)
    stem = f"{out_dir}/{backend}_{split}_{meta['date']}"
    df.to_csv(stem + ".csv", index=False)
    if split == "test":
        log = f"{out_dir}/test_runs.log"
        with open(log, "a") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{backend}\t{meta['model']}\t{meta['prompt_hash']}\n")
        meta["test_split_runs_so_far"] = sum(1 for _ in open(log))
    json.dump(meta, open(stem + ".json", "w"), indent=2)
    return meta, df


def show(meta):
    s = meta["system"]
    print(f"backend={meta['backend']} model={meta['model']} split={meta['split']} prompts={meta['prompt_hash']} "
          f"DIAG_USE_LLM={meta['diag_use_llm']} n={s['n']}")
    print(f"accuracy {s['correct']}/{s['n']} = {s['accuracy']:.1%} (95% Wilson interval {s['ci95'][0]:.1%} to {s['ci95'][1]:.1%}); kappa vs reference = {s['kappa']:.2f}")
    for name, b in meta["baselines"].items():
        print(f"baseline {name}: accuracy {b['accuracy']:.1%}, kappa {b['kappa']:.2f}")
    if "human_labeller_kappa" in meta:
        print(f"human labellers' own agreement: kappa {meta['human_labeller_kappa']:.2f}")
    print(f"LLM diagnosis accepted {meta['llm_diagnosis_accepted']} times; rule fallback used {meta['rule_fallback_used']} times")
    if "test_split_runs_so_far" in meta:
        print(f"TEST SPLIT HAS NOW BEEN RUN {meta['test_split_runs_so_far']} time(s): report this number")
    print("\nper class (precision / recall / F1 / support):")
    for k, v in meta["per_class"].items():
        if k in meta["confusion_labels"]:
            print(f"  {k:24s} {v['precision']:.2f} {v['recall']:.2f} {v['f1-score']:.2f} {int(v['support'])}")
    print("\nconfusion matrix (rows = reference, columns = system):")
    print(pd.DataFrame(meta["confusion"], index=meta["confusion_labels"], columns=meta["confusion_labels"]).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("backend", nargs="?", default="ollama", choices=["ollama", "openai"])
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--ref", default=REF, help="reference label file (default: strict-majority reference_labels.csv)")
    a = ap.parse_args()
    show(run(a.backend, a.split, a.ref)[0])