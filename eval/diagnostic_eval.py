"""Diagnostic agreement evaluation (thesis 7.7).

  python -m eval.diagnostic_eval <heuristic|ollama|openai> [--split dev|test|all]

Use --split dev while tuning prompts. Run --split test ONLY after freezing the prompts: every test run is logged
(eval/results/test_runs.log) so you can state exactly how many times the test set was looked at.
Reports accuracy with a Wilson 95% interval, Cohen's kappa vs the reference, per-class precision/recall/F1, a confusion
matrix, two baselines (majority class, rule-based stand-in) and the two human labellers' own agreement.
If eval/data/labelling/reference_labels.csv does not exist, the AUTHOR'S INTENDED labels are used for a pipeline check only."""
import argparse
import datetime
import hashlib
import json
import math
import os

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from app import agents
from app.llm import HeuristicLLM, OllamaLLM, OpenAICompatLLM

REF = "eval/data/labelling/reference_labels.csv"
CAND = "eval/data/sample_arguments.csv"
ALT_REF = "eval/data/reference_labels.csv"  # written by eval.labelling (the simpler kit)


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def prompt_hash():
    """Fingerprint of every prompt: proves the prompts were frozen between the dev and test runs."""
    texts = [agents.ANALYSE_PROMPT, agents.SCORE_PROMPT, agents.DIAG_PROMPT, agents.OPPONENT_PROMPT, agents.SINGLE_PROMPT]
    return hashlib.sha256("\n".join(texts).encode()).hexdigest()[:12]


def _from_simple_kit(data="eval/data"):
    """Reference file written by eval.labelling: id, label_A, label_B, final_label (+ split.csv, sample_arguments.csv)."""
    ref = pd.read_csv(f"{data}/reference_labels.csv")
    ref["final_label"] = ref["final_label"].fillna("")
    if (ref["final_label"] == "").any():
        raise ValueError("eval/data/reference_labels.csv still has empty final_label cells: resolve the disagreements first")
    text = pd.read_csv(f"{data}/sample_arguments.csv")[["id", "topic", "side", "argument"]]
    split = pd.read_csv(f"{data}/split.csv").rename(columns={"set": "split"})
    df = ref.merge(text, on="id").merge(split, on="id")
    df["reference_weakness"] = df["final_label"]
    return df


def load(ref_path=REF):
    """Priority: eval.make_label_sheets/agreement output, then eval.labelling output, else the author's intent (pipeline check only)."""
    if os.path.exists(ref_path):
        df = pd.read_csv(ref_path)
        if "split" not in df:
            df["split"] = "test"
        return df, True
    if ref_path == REF and os.path.exists(ALT_REF) and os.path.exists("eval/data/split.csv"):
        return _from_simple_kit(), True
    df = pd.read_csv(CAND).rename(columns={"intended_weakness": "reference_weakness"})
    df["split"] = "test"
    return df, False


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


def run(backend="heuristic", split="test", ref_path=REF, out_dir="eval/results", llm=None):
    os.makedirs(out_dir, exist_ok=True)
    allrows, human = load(ref_path)
    df = allrows if split == "all" else allrows[allrows.split == split].copy()
    llm = llm or {"heuristic": HeuristicLLM, "ollama": OllamaLLM, "openai": OpenAICompatLLM}[backend]()
    preds, sources = predict(df, llm)
    df = df.assign(system_weakness=preds, diagnosis_source=sources)
    df["match"] = df.system_weakness == df.reference_weakness
    system = summarise(df.reference_weakness, df.system_weakness)
    majority = allrows.reference_weakness.mode().iloc[0]
    baselines = {"majority_class": {"label": majority, **summarise(df.reference_weakness, [majority] * len(df))}}
    if backend != "heuristic":
        hp, _ = predict(df, HeuristicLLM())
        baselines["rule_based_stand_in"] = summarise(df.reference_weakness, hp)
    labels = sorted(set(df.reference_weakness) | set(df.system_weakness))
    meta = {"date": datetime.date.today().isoformat(), "backend": backend, "model": getattr(llm, "model", "n/a"), "split": split,
            "prompt_hash": prompt_hash(), "human_reference_labels": human, "system": system, "baselines": baselines,
            "llm_diagnosis_accepted": int((df.diagnosis_source == "llm").sum()), "rule_fallback_used": int((df.diagnosis_source == "rule_fallback").sum()),
            "per_class": classification_report(df.reference_weakness, df.system_weakness, zero_division=0, output_dict=True),
            "confusion_labels": labels, "confusion": confusion_matrix(df.reference_weakness, df.system_weakness, labels=labels).tolist()}
    if {"label_A", "label_B"} <= set(allrows.columns):
        meta["human_labeller_kappa"] = float(cohen_kappa_score(allrows.label_A, allrows.label_B))
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
    if not meta["human_reference_labels"]:
        print("WARNING: reference labels are the AUTHOR'S INTENT, not human labels. Pipeline check only; do NOT report these numbers.\n")
    print(f"backend={meta['backend']} model={meta['model']} split={meta['split']} prompts={meta['prompt_hash']} n={s['n']}")
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
    ap.add_argument("backend", nargs="?", default="heuristic", choices=["heuristic", "ollama", "openai"])
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    a = ap.parse_args()
    show(run(a.backend, a.split)[0])
