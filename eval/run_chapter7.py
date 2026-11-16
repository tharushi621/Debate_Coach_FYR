"""Chapter 7.7 diagnostic evaluation + comparison with a single-prompt baseline, on the 8-coach reference labels.

  python -u -m eval.run_chapter7 predict [ollama|openai]   run the real system on every labelled item ONCE (resumable)
  python -m eval.run_chapter7 analyse [openai|ollama]      score the saved predictions against both references

Fixed in advance (before any system output was seen):
  primary reference   = strict majority of the 8 coaches (more than half), undecided items excluded
  sensitivity check   = most frequent label (ties excluded)
  headline numbers    = the TEST split; the dev split is reported separately; prompts were NOT tuned on this data
Predictions are made once per item (the diagnosis does not depend on which reference is used), appended to
eval/results/ch7_predictions_<backend>.csv after every item, so an interrupted run resumes where it stopped.
Every prediction run that covers the test split is logged in eval/results/test_runs.log.
"""
import datetime
import json
import os
import sys
import time

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from app import agents
from eval import baselines
from eval.compare import mcnemar_exact
from eval.diagnostic_eval import prompt_hash, summarise, wilson

OUT = "eval/results"
def pred_path(backend):
    """One predictions file per backend, so two different models can never be mixed or resumed into each other."""
    return f"{OUT}/ch7_predictions_{backend}.csv"


REFS = {"strict_majority": "eval/data/labelling/reference_labels.csv",
        "plurality": "eval/data/labelling/reference_labels_plurality.csv"}


def _llm(backend):
    from app.llm import OllamaLLM, OpenAICompatLLM
    return {"ollama": OllamaLLM, "openai": OpenAICompatLLM}[backend]()


def predict(backend="ollama", llm=None):
    os.makedirs(OUT, exist_ok=True)
    items = pd.read_csv(REFS["plurality"])          # superset of the strict-majority items
    PRED = pred_path(backend)
    done = set(pd.read_csv(PRED).item_id) if os.path.exists(PRED) else set()
    llm = llm or _llm(backend)
    todo = items[~items.item_id.isin(done)]
    print(f"{len(items)} labelled items, {len(done)} already predicted, {len(todo)} to do; model={getattr(llm, 'model', '?')}", flush=True)
    if len(todo) and (items.split == "test").any() and not done:
        with open(f"{OUT}/test_runs.log", "a") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{backend}\t{getattr(llm, 'model', 'n/a')}\t{prompt_hash()}\n")
    for i, r in enumerate(todo.itertuples(index=False), 1):
        t = time.time()
        an = agents.analyse(llm, r.topic, r.side, [], r.argument)
        sc = agents.score(llm, r.topic, r.side, an, r.argument)
        d = agents.diagnose(sc, r.argument, an, llm=llm, topic=r.topic, side=r.side)
        single = baselines.single_prompt_diagnose(llm, r.topic, r.side, r.argument)
        row = pd.DataFrame([{"item_id": r.item_id, "split": r.split, "system": d["lowest_weakness"], "source": d["source"],
                             "single_prompt": single, "backend": backend, "model": getattr(llm, "model", "n/a"),
                             "prompt_hash": prompt_hash(), "seconds": round(time.time() - t, 1)}])
        row.to_csv(PRED, mode="a", header=not os.path.exists(PRED), index=False)
        print(f"[{i}/{len(todo)}] {r.item_id} system={d['lowest_weakness']} ({d['source']}) single={single} {row.seconds[0]}s", flush=True)


def _score(df, ref_col="reference_weakness"):
    ref = list(df[ref_col])
    majority = pd.Series(ref).mode().iloc[0]
    arms = {"thesis_system": list(df.system), "single_prompt_llm": list(df.single_prompt), "majority_class": [majority] * len(ref)}
    res = {}
    for k, pred in arms.items():
        s = summarise(ref, pred)
        res[k] = {"n": s["n"], "correct": s["correct"], "accuracy": s["accuracy"], "ci95": list(wilson(s["correct"], s["n"])), "kappa": s["kappa"]}
    n10, n01, p = mcnemar_exact(ref, list(df.system), list(df.single_prompt))
    res["system_vs_single_prompt"] = {"only_system_correct": n10, "only_single_prompt_correct": n01, "mcnemar_exact_p": p}
    labels = sorted(set(ref) | set(df.system))
    res["per_class"] = classification_report(ref, list(df.system), labels=labels, zero_division=0, output_dict=True)
    res["confusion_labels"] = labels
    res["confusion"] = confusion_matrix(ref, list(df.system), labels=labels).tolist()
    return res


def analyse(backend="openai"):
    pred = pd.read_csv(pred_path(backend))
    out = {"date": datetime.date.today().isoformat(), "model": pred.model.iloc[0], "backend": pred.backend.iloc[0],
           "prompt_hash": pred.prompt_hash.iloc[0], "llm_diagnosis_accepted": int((pred.source == "llm").sum()),
           "rule_fallback_used": int((pred.source == "rule_fallback").sum()), "n_predicted": len(pred),
           "mean_seconds_per_item": round(float(pred.seconds.mean()), 1), "results": {}}
    for name, path in REFS.items():
        ref = pd.read_csv(path)
        lab = [c for c in ref.columns if c.startswith("label_")]
        pairs = [(a, b) for i, a in enumerate(lab) for b in lab[i + 1:]]
        j = ref.merge(pred[["item_id", "system", "source", "single_prompt"]], on="item_id")
        out["results"][name] = {"n_items": len(j), "n_labellers": len(lab)}
        for split in ("test", "dev", "all"):
            d = j if split == "all" else j[j.split == split]
            if len(d):
                out["results"][name][split] = _score(d)
    log = f"{OUT}/test_runs.log"
    out["test_split_runs_so_far"] = sum(1 for _ in open(log)) if os.path.exists(log) else 1
    # file shaped like diagnostic_eval's output, so analysis.report and analysis.figures can read the primary result
    prim = out["results"]["strict_majority"].get("test")
    if prim:
        ref = pd.read_csv(REFS["strict_majority"])
        lab = [c for c in ref.columns if c.startswith("label_")]
        kap = [cohen_kappa_score(ref[a], ref[b]) for i, a in enumerate(lab) for b in lab[i + 1:]]
        meta = {"date": out["date"], "backend": out["backend"], "model": out["model"], "split": "test", "prompt_hash": out["prompt_hash"],
                "diag_use_llm": os.getenv("DIAG_USE_LLM", "1") != "0", "system": prim["thesis_system"],
                "baselines": {"majority_class": {"label": "see ch7_results.json", **prim["majority_class"]},
                              "single_prompt_llm": prim["single_prompt_llm"]},
                "llm_diagnosis_accepted": out["llm_diagnosis_accepted"], "rule_fallback_used": out["rule_fallback_used"],
                "human_labeller_kappa": float(sum(kap) / len(kap)), "n_human_labellers": len(lab),
                "test_split_runs_so_far": out["test_split_runs_so_far"], "per_class": prim["per_class"],
                "confusion_labels": prim["confusion_labels"], "confusion": prim["confusion"]}
        json.dump(meta, open(f"{OUT}/{out['backend']}_test_{out['date']}.json", "w"), indent=2)
    json.dump(out, open(f"{OUT}/ch7_results_{out['backend']}.json", "w"), indent=2)
    return out


def show(o):
    print(f"model={o['model']} backend={o['backend']} prompts={o['prompt_hash']} items predicted={o['n_predicted']} "
          f"mean {o['mean_seconds_per_item']}s/item; LLM diagnosis accepted {o['llm_diagnosis_accepted']}, rule fallback {o['rule_fallback_used']}")
    for name, r in o["results"].items():
        print(f"\n== reference: {name} ({r['n_items']} items, {r['n_labellers']} coaches) ==")
        for split in ("test", "dev", "all"):
            if split not in r:
                continue
            print(f"-- {split} split")
            for k in ("thesis_system", "single_prompt_llm", "majority_class"):
                v = r[split][k]
                print(f"  {k:18s} {v['correct']}/{v['n']} = {v['accuracy']:.1%} (95% CI {v['ci95'][0]:.1%} to {v['ci95'][1]:.1%}) kappa {v['kappa']:.2f}")
            m = r[split]["system_vs_single_prompt"]
            print(f"  system only right {m['only_system_correct']}, single prompt only right {m['only_single_prompt_correct']}, exact McNemar p={m['mcnemar_exact_p']:.3f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "predict":
        predict(sys.argv[2] if len(sys.argv) > 2 else "ollama")
    elif cmd == "analyse":
        show(analyse(sys.argv[2] if len(sys.argv) > 2 else "openai"))
    else:
        print(__doc__)
