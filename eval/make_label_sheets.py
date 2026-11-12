"""Build blind labelling sheets:  python -m eval.make_label_sheets
Reads eval/data/sample_arguments.csv and writes, into eval/data/labelling/:
  labeller_A.csv, labeller_B.csv  - what each labeller receives (no intended label; different item order)
  key.csv                         - KEEP PRIVATE: item_id -> original id, intended weakness, dev/test split
  LABELLING_GUIDE.md              - definitions and rules to hand to both labellers
The dev split (about 22%, at least one per weakness) is for prompt tuning; the test split is for the final reported run."""
import os
import random

import pandas as pd

from app.taxonomy import WEAKNESSES

SEED = 2026
DEFS = {
    "unclear_claim": "The position is vague, or it is not clear what is being argued.",
    "insufficient_evidence": "A claim and reasons are given, but no specific evidence, example or source.",
    "irrelevant_evidence": "Evidence is given, but it has nothing to do with the claim or the motion.",
    "missing_warrant": "Evidence is given, but the link from the evidence to the claim is not explained.",
    "poor_relevance": "The argument does not address the debate motion at all.",
    "weak_rebuttal": "The argument is otherwise supported but ignores opposing views.",
    "logical_fallacy": "The reasoning is invalid (for example bandwagon, ad hominem, slippery slope, hasty generalisation).",
    "overgeneralisation": "Absolute claims (all, never, always) that are hard to defend.",
    "missing_qualification": "A developed claim with no limits or conditions on where it holds.",
}


def build(cand_path="eval/data/sample_arguments.csv", out_dir="eval/data/labelling"):
    df = pd.read_csv(cand_path)
    if "source" not in df:
        df["source"] = "researcher"
    order = list(df.index)
    random.Random(SEED).shuffle(order)
    df = df.loc[order].reset_index(drop=True)
    df["item_id"] = [f"L{i + 1:03d}" for i in range(len(df))]
    dev, seen = set(), set()
    for _, r in df.iterrows():  # one per weakness first, so every class can be tuned on
        if r.intended_weakness not in seen:
            seen.add(r.intended_weakness)
            dev.add(r.item_id)
    for item in df.item_id:
        if len(dev) >= round(0.22 * len(df)):
            break
        dev.add(item)
    df["split"] = ["dev" if i in dev else "test" for i in df.item_id]
    os.makedirs(out_dir, exist_ok=True)
    sheet = df[["item_id", "topic", "side", "argument"]].copy()
    sheet["weakness_label"], sheet["notes"] = "", ""
    sheet.to_csv(f"{out_dir}/labeller_A.csv", index=False)
    sheet.sample(frac=1, random_state=SEED + 1).to_csv(f"{out_dir}/labeller_B.csv", index=False)
    df[["item_id", "id", "intended_weakness", "source", "split"]].to_csv(f"{out_dir}/key.csv", index=False)
    guide = ["# Labelling guide\n", "Label each argument with ONE weakness from the list below, in the `weakness_label` column, exactly as spelled.\n",
             "Choose the single most consequential weakness: the one that, fixed first, would improve the argument most. If undecided, prefer this order: "
             "relevance, claim clarity, evidence, warrant, logic, rebuttal, qualification.\n",
             "Work alone, in one sitting. Do not discuss items with the other labeller and do not look at any system output.\n", "\n| Label | Meaning |\n| --- | --- |"]
    guide += [f"| `{w}` | {DEFS[w]} |" for w in WEAKNESSES]
    open(f"{out_dir}/LABELLING_GUIDE.md", "w").write("\n".join(guide) + "\n")
    return df


if __name__ == "__main__":
    d = build()
    print(f"{len(d)} items; dev={sum(d.split == 'dev')} test={sum(d.split == 'test')}. Give labeller_A.csv / labeller_B.csv + LABELLING_GUIDE.md to two people; keep key.csv private.")
