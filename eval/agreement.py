"""Labeller agreement and reference labels.
  python -m eval.agreement             compute agreement from completed labeller_A/B, write resolve.csv for disagreements
  python -m eval.agreement --finalise  after filling final_label in resolve.csv, write reference_labels.csv"""
import os
import sys

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from app.taxonomy import WEAKNESSES

D = "eval/data/labelling"


def _load(path):
    df = pd.read_csv(path).set_index("item_id")
    bad = df[~df.weakness_label.isin(WEAKNESSES)]
    if len(bad):
        raise ValueError(f"{path}: invalid or empty labels for {list(bad.index)[:10]} (allowed: {WEAKNESSES})")
    return df


def compute(a_path=f"{D}/labeller_A.csv", b_path=f"{D}/labeller_B.csv", key_path=f"{D}/key.csv", out_dir=D):
    A, B, key = _load(a_path), _load(b_path), pd.read_csv(key_path).set_index("item_id")
    j = A[["topic", "side", "argument", "weakness_label"]].rename(columns={"weakness_label": "label_A"}).join(B[["weakness_label"]].rename(columns={"weakness_label": "label_B"}))
    j = j.join(key[["intended_weakness", "split"]])
    stats = {"n": len(j), "raw_agreement": float((j.label_A == j.label_B).mean()), "kappa": float(cohen_kappa_score(j.label_A, j.label_B)),
             "both_match_intended": float(((j.label_A == j.intended_weakness) & (j.label_B == j.intended_weakness)).mean())}
    dis = j[j.label_A != j.label_B].reset_index()[["item_id", "argument", "label_A", "label_B"]]
    dis["final_label"] = ""
    dis.to_csv(f"{out_dir}/resolve.csv", index=False)
    j.to_csv(f"{out_dir}/_joined.csv")
    return stats, dis


def finalise(out_dir=D):
    j = pd.read_csv(f"{out_dir}/_joined.csv").set_index("item_id")
    res = pd.read_csv(f"{out_dir}/resolve.csv").set_index("item_id") if os.path.exists(f"{out_dir}/resolve.csv") else pd.DataFrame()
    final = j.label_A.copy()
    if len(res):
        todo = res[~res.final_label.isin(WEAKNESSES)]
        if len(todo):
            raise ValueError(f"fill a valid final_label in resolve.csv for {list(todo.index)}")
        final.loc[res.index] = res.final_label
    ref = j.reset_index()[["item_id", "topic", "side", "argument", "split", "label_A", "label_B"]]
    ref["reference_weakness"] = final.values
    ref["agreed_without_discussion"] = (ref.label_A == ref.label_B).values
    ref.to_csv(f"{out_dir}/reference_labels.csv", index=False)
    return ref


if __name__ == "__main__":
    if "--finalise" in sys.argv:
        r = finalise()
        print(f"wrote {D}/reference_labels.csv ({len(r)} items, {int((~r.agreed_without_discussion).sum())} resolved by discussion)")
    else:
        s, d = compute()
        print(f"n={s['n']} raw agreement={s['raw_agreement']:.1%} Cohen's kappa={s['kappa']:.2f} (labellers both matched the author's intent on {s['both_match_intended']:.1%})")
        print(f"{len(d)} disagreements written to {D}/resolve.csv: discuss each, fill final_label, then run with --finalise")
        if len(d) == 0:
            print("No disagreements. Run with --finalise.")
