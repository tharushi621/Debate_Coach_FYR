"""Labeller agreement and reference labels, for TWO OR MORE human labellers.
  python -m eval.agreement             read every completed eval/data/labelling/labeller_*.csv, report agreement,
                                       write resolve.csv for items that have no clear majority
  python -m eval.agreement --finalise  after filling final_label in resolve.csv, write reference_labels.csv

Reference label rule (fixed in advance): an item's reference weakness is the label chosen by a STRICT MAJORITY of the
labellers (more than half). With two labellers that means both agree, exactly as before. Items without a strict majority go
to resolve.csv and are settled by discussion. Reported: mean pairwise raw agreement, mean pairwise Cohen's kappa and
Fleiss' kappa (the standard multi-rater agreement measure)."""
import glob
import itertools
import os
import sys
from collections import Counter

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


def fleiss_kappa(rows):
    """rows: list of label lists, one per item, each with the same number of raters."""
    n, N = len(rows[0]), len(rows)
    cats = sorted({c for r in rows for c in r})
    counts = [[r.count(c) for c in cats] for r in rows]
    p_i = [(sum(x * x for x in row) - n) / (n * (n - 1)) for row in counts]
    P = sum(p_i) / N
    p_j = [sum(row[j] for row in counts) / (N * n) for j in range(len(cats))]
    Pe = sum(p * p for p in p_j)
    return float("nan") if Pe == 1 else (P - Pe) / (1 - Pe)


def compute_many(paths, key_path=f"{D}/key.csv", out_dir=D):
    paths = list(paths)
    if len(paths) < 2:
        raise ValueError("need at least two completed labeller files")
    names = [os.path.basename(p)[len("labeller_"):-len(".csv")] for p in paths]
    sheets = [_load(p) for p in paths]
    key = pd.read_csv(key_path).set_index("item_id")
    j = sheets[0][["topic", "side", "argument"]].copy()
    for nm, sh in zip(names, sheets):
        j[f"label_{nm}"] = sh.weakness_label.reindex(j.index)
    j = j.join(key[["intended_weakness", "split"]])
    cols = [f"label_{n}" for n in names]
    votes = j[cols].apply(lambda r: Counter(r), axis=1)
    top = votes.apply(lambda c: c.most_common(1)[0])
    j["majority_label"] = [lab if cnt > len(cols) / 2 else "" for lab, cnt in top]
    pairs = list(itertools.combinations(cols, 2))
    stats = {"n": len(j), "n_labellers": len(cols), "labellers": names,
             "raw_agreement": float(sum((j[a] == j[b]).mean() for a, b in pairs) / len(pairs)),
             "kappa": float(sum(cohen_kappa_score(j[a], j[b]) for a, b in pairs) / len(pairs)),   # mean pairwise Cohen's kappa
             "fleiss_kappa": fleiss_kappa([list(r) for r in j[cols].itertuples(index=False)]),
             "items_without_majority": int((j.majority_label == "").sum())}
    dis = j[j.majority_label == ""].reset_index()[["item_id", "argument"] + cols]
    dis["votes"] = [dict(votes[i]) for i in dis.item_id]
    dis["final_label"] = ""
    dis.to_csv(f"{out_dir}/resolve.csv", index=False)
    j.to_csv(f"{out_dir}/_joined.csv")
    return stats, dis


def compute(a_path=f"{D}/labeller_A.csv", b_path=f"{D}/labeller_B.csv", key_path=f"{D}/key.csv", out_dir=D):
    """Two-labeller form (kept for compatibility)."""
    return compute_many([a_path, b_path], key_path, out_dir)


def finalise(out_dir=D, rule=None):
    """rule=None: use resolve.csv (items settled by discussion). rule='majority' | 'plurality': no discussion; items the rule
    cannot decide are EXCLUDED (never guessed). 'majority' = more than half of the labellers (primary reference, written to
    reference_labels.csv). 'plurality' = the single most frequent label, ties excluded (sensitivity check, written to
    reference_labels_plurality.csv)."""
    j = pd.read_csv(f"{out_dir}/_joined.csv", keep_default_na=False).set_index("item_id")
    cols = [c for c in j.columns if c.startswith("label_")]
    if rule in ("majority", "plurality"):
        def pick(r):
            c = Counter(r[cols]).most_common()
            top = c[0][1]
            if rule == "majority":
                return c[0][0] if top > len(cols) / 2 else ""
            return c[0][0] if sum(1 for _, n in c if n == top) == 1 else ""
        final = j.apply(pick, axis=1)
    else:
        res = pd.read_csv(f"{out_dir}/resolve.csv", keep_default_na=False).set_index("item_id") if os.path.exists(f"{out_dir}/resolve.csv") else pd.DataFrame()
        final = j.majority_label.copy()
        if len(res):
            todo = res[~res.final_label.isin(WEAKNESSES)]
            if len(todo):
                raise ValueError(f"fill a valid final_label in resolve.csv for {list(todo.index)}")
            final.loc[res.index] = res.final_label
    ref = j.reset_index()[["item_id", "topic", "side", "argument", "split"] + cols]
    ref["reference_weakness"] = final.values
    ref["agreed_without_discussion"] = (j.majority_label != "").values
    ref["n_labellers"] = len(cols)
    if rule:
        ref = ref[ref.reference_weakness != ""]
    ref.to_csv(f"{out_dir}/reference_labels{'_plurality' if rule == 'plurality' else ''}.csv", index=False)
    return ref


if __name__ == "__main__":
    if "--finalise" in sys.argv:
        rule = "plurality" if "--plurality" in sys.argv else "majority" if "--majority" in sys.argv else None
        r = finalise(rule=rule)
        print(f"wrote {D}/reference_labels.csv ({len(r)} items from {int(r.n_labellers.iloc[0])} labellers, "
              f"{int((~r.agreed_without_discussion).sum())} without a strict majority)")
    else:
        files = sorted(glob.glob(f"{D}/labeller_*.csv"))
        s, d = compute_many(files)
        print(f"{s['n']} items, {s['n_labellers']} labellers ({', '.join(s['labellers'])})")
        print(f"mean pairwise raw agreement {s['raw_agreement']:.1%}; mean pairwise Cohen's kappa {s['kappa']:.2f}; Fleiss' kappa {s['fleiss_kappa']:.2f}")
        print(f"{len(d)} items have no strict majority: written to {D}/resolve.csv. Discuss each, fill final_label, then run with --finalise")
        if len(d) == 0:
            print("No unresolved items. Run with --finalise.")
