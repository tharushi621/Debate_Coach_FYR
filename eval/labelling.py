"""Labelling kit for the diagnostic evaluation (thesis 7.7).

  python -m eval.labelling make
      -> labeller_sheet_A.csv, labeller_sheet_B.csv  (same arguments, different order, NO hints, blank 'label' column)
      -> split.csv  (about 20% 'dev' for prompt tuning, the rest 'test' for the reported result)
  python -m eval.labelling reference sheetA_done.csv sheetB_done.csv
      -> inter-labeller agreement (Cohen's kappa), disagreements.csv, reference_labels.csv
         Discuss each disagreement, type the agreed weakness in 'final_label', then run the evaluation.

Labels must be one of the nine weakness names. The 'intended_weakness' column in sample_arguments.csv is only the
author's intent for a draft; it is NOT the reference. The reference is what two humans agree on."""
import random
import sys

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from app.taxonomy import WEAKNESSES

DATA = "eval/data"
SEED = 2026


def make(data=DATA):
    df = pd.read_csv(f"{data}/sample_arguments.csv")
    for name, k in (("A", 1), ("B", 2)):
        sheet = df[["id", "topic", "side", "argument"]].sample(frac=1, random_state=SEED + k).copy()
        sheet["label"] = ""
        sheet.to_csv(f"{data}/labeller_sheet_{name}.csv", index=False)
    rng, split = random.Random(SEED), []
    for _, g in df.groupby("intended_weakness"):
        ids = list(g["id"])
        rng.shuffle(ids)
        n_dev = max(1, round(0.2 * len(ids)))
        split += [(i, "dev" if j < n_dev else "test") for j, i in enumerate(ids)]
    pd.DataFrame(split, columns=["id", "set"]).sort_values("id").to_csv(f"{data}/split.csv", index=False)
    print(f"Wrote two blind sheets and split.csv ({len(split)} arguments). Give one sheet to each labeller; they must not confer.")
    print("Valid labels:", ", ".join(WEAKNESSES))


def reference(a_path, b_path, data=DATA):
    a, b = pd.read_csv(a_path), pd.read_csv(b_path)
    for name, d in (("A", a), ("B", b)):
        bad = sorted(set(d["label"].dropna()) - set(WEAKNESSES))
        if bad or d["label"].isna().any():
            raise SystemExit(f"Labeller {name}: every row needs one valid weakness label. Problems: {bad or 'empty cells'}")
    m = a[["id", "label"]].merge(b[["id", "label"]], on="id", suffixes=("_A", "_B"))
    kappa = cohen_kappa_score(m["label_A"], m["label_B"])
    agree = (m["label_A"] == m["label_B"]).mean()
    m["final_label"] = m.apply(lambda r: r["label_A"] if r["label_A"] == r["label_B"] else "", axis=1)
    m.to_csv(f"{data}/reference_labels.csv", index=False)
    dis = m[m["final_label"] == ""]
    dis.merge(pd.read_csv(f"{data}/sample_arguments.csv")[["id", "argument"]], on="id").to_csv(f"{data}/disagreements.csv", index=False)
    print(f"Inter-labeller agreement: {agree:.1%} raw, Cohen's kappa {kappa:.2f}, n={len(m)}")
    print(f"{len(dis)} disagreements written to disagreements.csv. Resolve them by discussion and type each agreed weakness")
    print("into the 'final_label' column of reference_labels.csv. Report both the kappa and how you resolved disagreements.")
    return kappa, agree


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "make":
        make()
    elif len(sys.argv) == 4 and sys.argv[1] == "reference":
        reference(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
