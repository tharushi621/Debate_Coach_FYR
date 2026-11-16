"""Comparison evaluation: the thesis system against un-targeted baselines, on the SAME human-labelled arguments.

  python -m eval.compare diagnose [ollama|openai] [--split test|dev|all]
      Weakness diagnosis: full pipeline vs single-prompt LLM vs majority class. Reports accuracy with Wilson 95% intervals,
      kappa, and an exact McNemar test on the items where the system and the single prompt disagree.

  python -m eval.compare replies [ollama|openai] [--split test] [--n 30] [--seed 7]
      Generates one reply per arm for each item (adaptive pipeline, generic opponent, single-call opponent) and writes
      BLIND rating sheets for two raters (eval/results/replies/rater_A.csv, rater_B.csv) plus the secret key (key.csv).

  python -m eval.compare analyse
      After both raters have filled their sheets: mean ratings per arm, paired adaptive-vs-generic comparison
      (Wilcoxon signed-rank, win/tie/loss), ghost-writing rate, and rater agreement (quadratic weighted kappa).

Reference labels come from eval/data/labelling/reference_labels.csv (two human labellers). Raters see the HUMAN reference
weakness, never the system's diagnosis, and never which arm wrote a reply. Everything is reported as measured, whichever arm wins.
"""
import argparse
import datetime
import json
import os
import random
import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon
from sklearn.metrics import cohen_kappa_score

from app import agents
from app.llm import OllamaLLM, OpenAICompatLLM
from eval import baselines
from eval.diagnostic_eval import REF, load, summarise, wilson

OUT = "eval/results"
RDIR = f"{OUT}/replies"
ARMS = ["adaptive", "generic", "single_call"]


def _llm(backend):
    return {"ollama": OllamaLLM, "openai": OpenAICompatLLM}[backend]()


def mcnemar_exact(ref, a, b):
    """Exact McNemar on paired correctness. Returns (only_a_right, only_b_right, two-sided p)."""
    ar = [x == r for x, r in zip(a, ref)]
    br = [x == r for x, r in zip(b, ref)]
    n10 = sum(1 for x, y in zip(ar, br) if x and not y)
    n01 = sum(1 for x, y in zip(ar, br) if y and not x)
    p = 1.0 if n10 + n01 == 0 else float(binomtest(n10, n10 + n01, 0.5).pvalue)
    return n10, n01, p


def diagnose(backend="ollama", split="test", ref_path=REF, llm=None):
    os.makedirs(OUT, exist_ok=True)
    allrows = load(ref_path)
    df = allrows if split == "all" else allrows[allrows.split == split].copy()
    llm = llm or _llm(backend)
    sys_pred, single_pred = [], []
    for _, r in df.iterrows():
        an = agents.analyse(llm, r.topic, r.side, [], r.argument)
        sc = agents.score(llm, r.topic, r.side, an, r.argument)
        sys_pred.append(agents.diagnose(sc, r.argument, an, llm=llm, topic=r.topic, side=r.side)["lowest_weakness"])
        single_pred.append(baselines.single_prompt_diagnose(llm, r.topic, r.side, r.argument))
    ref = list(df.reference_weakness)
    majority = allrows.reference_weakness.mode().iloc[0]
    arms = {"thesis_system": sys_pred, "single_prompt_llm": single_pred, "majority_class": [majority] * len(ref)}
    res = {}
    for name, pred in arms.items():
        s = summarise(ref, pred)
        res[name] = {"n": s["n"], "correct": s["correct"], "accuracy": s["accuracy"], "ci95": list(wilson(s["correct"], s["n"])),
                     "kappa": s["kappa"]}
    n10, n01, p = mcnemar_exact(ref, sys_pred, single_pred)
    meta = {"date": datetime.date.today().isoformat(), "backend": backend, "model": getattr(llm, "model", "n/a"), "split": split,
            "prompt_hash": __import__("eval.diagnostic_eval", fromlist=["x"]).prompt_hash(), "arms": res,
            "system_vs_single_prompt": {"only_system_correct": n10, "only_single_prompt_correct": n01, "mcnemar_exact_p": p},
            "invalid_single_prompt_answers": int(sum(1 for x in single_pred if x == "invalid"))}
    stem = f"{OUT}/compare_diag_{backend}_{split}_{meta['date']}"
    df.assign(system=sys_pred, single_prompt=single_pred).to_csv(stem + ".csv", index=False)
    json.dump(meta, open(stem + ".json", "w"), indent=2)
    return meta


def show_diag(m):
    print(f"backend={m['backend']} model={m['model']} split={m['split']} (same items, same labels for every arm)")
    for k, v in m["arms"].items():
        print(f"  {k:20s} {v['correct']}/{v['n']} = {v['accuracy']:.1%}  (95% CI {v['ci95'][0]:.1%} to {v['ci95'][1]:.1%})  kappa {v['kappa']:.2f}")
    d = m["system_vs_single_prompt"]
    print(f"system right & single prompt wrong: {d['only_system_correct']};  single prompt right & system wrong: {d['only_single_prompt_correct']};"
          f"  exact McNemar p = {d['mcnemar_exact_p']:.3f}")
    print("Report this whichever way it falls. With few items the interval is wide; do not claim more than it shows.")


def replies(backend="ollama", split="test", n=30, seed=7, ref_path=REF, llm=None, out_dir=RDIR):
    """Resumable: every finished argument is appended to _partial.jsonl, so a failed run continues where it stopped."""
    import time
    os.makedirs(out_dir, exist_ok=True)
    df = load(ref_path)
    df = df if split == "all" else df[df.split == split]
    df = df.sample(n=min(n, len(df)), random_state=seed)
    llm = llm or _llm(backend)
    partial = f"{out_dir}/_partial.jsonl"
    done = {}
    if os.path.exists(partial):
        for line in open(partial, encoding="utf-8"):
            if line.strip():
                rec = json.loads(line)
                done[rec["item_id"]] = rec["texts"]
    print(f"generating replies for {len(df)} arguments (6 model calls each); {len(done)} already finished and kept", flush=True)
    t_all = time.time()
    for i, (_, r) in enumerate(df.iterrows(), 1):
        if r.item_id in done:
            continue
        t_item = time.time()
        an = agents.analyse(llm, r.topic, r.side, [], r.argument)
        sc = agents.score(llm, r.topic, r.side, an, r.argument)
        dg = agents.diagnose(sc, r.argument, an, llm=llm, topic=r.topic, side=r.side)
        iv = agents.strategise(dg)
        ad, _fb = agents.oppose(llm, r.topic, r.side, r.argument, an, dg, iv)
        ge = baselines.generic_opponent(llm, r.topic, r.side, r.argument)
        _w, sc_reply = baselines.single_call_opponent(llm, r.topic, r.side, r.argument)
        done[r.item_id] = {"adaptive": ad, "generic": ge, "single_call": sc_reply}
        with open(partial, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"item_id": r.item_id, "texts": done[r.item_id]}) + "\n")
        print(f"[{i}/{len(df)}] {r.item_id} done in {time.time() - t_item:.0f}s (total {time.time() - t_all:.0f}s)", flush=True)
    rows, key = [], []
    for _, r in df.iterrows():
        order = ARMS[:]
        random.Random(f"{seed}:{r.item_id}").shuffle(order)        # arm order depends only on the item, so resuming never changes it
        for pos, arm in enumerate(order, 1):
            rid = f"{r.item_id}-{pos}"
            rows.append({"reply_id": rid, "topic": r.topic, "student_side": r.side, "argument": r.argument,
                         "reference_weakness": r.reference_weakness, "reply": done[r.item_id][arm],
                         "targets_weakness_1to5": "", "helpful_next_step_1to5": "", "writes_argument_for_student_yes_no": ""})
            key.append({"reply_id": rid, "item_id": r.item_id, "arm": arm})
    sheet = pd.DataFrame(rows).sample(frac=1, random_state=seed + 1)     # raters see replies in random order
    for who in ("A", "B"):
        sheet.to_csv(f"{out_dir}/rater_{who}.csv", index=False)
    pd.DataFrame(key).to_csv(f"{out_dir}/key.csv", index=False)
    return len(df), len(rows)


def analyse(out_dir=RDIR):
    key = pd.read_csv(f"{out_dir}/key.csv").set_index("reply_id")
    cols = {"targets_weakness_1to5": "targets", "helpful_next_step_1to5": "helpful", "writes_argument_for_student_yes_no": "ghost"}
    sheets = {}
    for who in ("A", "B"):
        d = pd.read_csv(f"{out_dir}/rater_{who}.csv").set_index("reply_id")[list(cols)].rename(columns=cols)
        if d[["targets", "helpful"]].isna().any().any():
            raise SystemExit(f"rater_{who}.csv still has empty ratings")
        d["ghost"] = d["ghost"].astype(str).str.strip().str.lower().isin(["yes", "y", "1", "true"])
        sheets[who] = d.join(key)
    A, B = sheets["A"], sheets["B"].loc[sheets["A"].index]
    # a column where BOTH raters gave the same single answer every time (for example all "no") carries no evidence of copying
    same = [k for k in ("targets", "helpful", "ghost")
            if bool((A[k].to_numpy() == B[k].to_numpy()).all()) and A[k].nunique() > 1]
    if same:     # two independent people never give the same rating on every row; this means copied ratings
        res = {"WARNING": "The two raters' ratings are IDENTICAL in every row for: " + ", ".join(same) + ". This is NOT independent "
                          "two-rater data for those questions. Do not report agreement for them. Report as a single rater, "
                          "or collect an independent second rating.",
               "rater_agreement_qwk": None if len(same) >= 2 else {
                   k: (None if k in same else float(cohen_kappa_score(A[k].astype(int), B[k].astype(int), weights="quadratic")))
                   for k in ("targets", "helpful")}}
    else:
        res = {"rater_agreement_qwk": {k: float(cohen_kappa_score(A[k].astype(int), B[k].astype(int), weights="quadratic"))
                                       for k in ("targets", "helpful")}}
    mean = pd.DataFrame({k: (A[k].astype(float) + B[k].astype(float)) / 2 for k in ("targets", "helpful")}).join(A[["item_id", "arm"]])
    res["mean_by_arm"] = mean.groupby("arm")[["targets", "helpful"]].mean().round(2).to_dict("index")
    res["ghostwriting_rate_by_arm"] = ((A.ghost | B.ghost).groupby(A.arm).mean().round(3)).to_dict()
    piv = {k: mean.pivot(index="item_id", columns="arm", values=k) for k in ("targets", "helpful")}
    for k in piv:
        for other in ("generic", "single_call"):
            diff = (piv[k]["adaptive"] - piv[k][other]).to_numpy()
            win, loss, tie = int((diff > 0).sum()), int((diff < 0).sum()), int((diff == 0).sum())
            p = float(wilcoxon(diff).pvalue) if np.any(diff != 0) else 1.0
            res[f"{k}: adaptive vs {other}"] = {"win": win, "tie": tie, "loss": loss, "mean_diff": round(float(diff.mean()), 2),
                                                "wilcoxon_p": ("<0.0001" if p < 0.0001 else round(p, 4)), "n_items": len(diff)}
    json.dump(res, open(f"{out_dir}/analysis.json", "w"), indent=2)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["diagnose", "replies", "analyse"])
    ap.add_argument("backend", nargs="?", default="ollama", choices=["ollama", "openai"])
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--ref", default=REF)
    a = ap.parse_args()
    if a.cmd == "diagnose":
        show_diag(diagnose(a.backend, a.split, a.ref))
    elif a.cmd == "replies":
        items, rows = replies(a.backend, a.split, a.n, a.seed, a.ref)
        print(f"{items} items -> {rows} replies written to {RDIR}/rater_A.csv and rater_B.csv. "
              "Give each rater ONE file and nothing else. Do not open key.csv until both are done.")
    else:
        print(json.dumps(analyse(), indent=2))
    sys.exit(0)
