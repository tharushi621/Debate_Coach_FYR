"""Excel workbooks to send to the two human labellers (debate coaches), and the import of their answers.

  python -m eval.coach_workbooks make [N]     -> eval/data/labelling/send/Coach_A.xlsx ... (default N = 8, letters A to H)
  python -m eval.coach_workbooks import Coach_A.xlsx Coach_C.xlsx ...   (any number of returned files, at least 2)
        -> writes labeller_<letter>.csv for each (validated). Then run: python -m eval.agreement
Every coach gets the same 45 arguments in a DIFFERENT random order, so order effects do not favour any item.

Each workbook has an 'Instructions' sheet (what to do, label definitions, consent line) and a 'Labels' sheet with a dropdown
on the label column. The workbooks contain NO system output and NO intended labels: the coach sees only the argument.
"""
import os
import re
import sys
import string

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from app.taxonomy import WEAKNESSES

D = "eval/data/labelling"
SEND = f"{D}/send"

DEFS = {
    "unclear_claim": "The position is vague, or it is not clear what is being argued.",
    "insufficient_evidence": "A claim and reasons are given, but no specific evidence, example or source.",
    "irrelevant_evidence": "Evidence is given, but it has nothing to do with the claim or the motion.",
    "missing_warrant": "Evidence is given, but the link from the evidence to the claim is not explained.",
    "poor_relevance": "The argument does not address the debate motion at all.",
    "weak_rebuttal": "The argument is otherwise supported but ignores opposing views.",
    "logical_fallacy": "The reasoning is invalid (e.g. bandwagon, ad hominem, slippery slope, hasty generalisation).",
    "overgeneralisation": "Absolute claims (all, never, always) that are hard to defend.",
    "missing_qualification": "A developed claim with no limits or conditions on where it holds.",
}

INSTRUCTIONS = [
    "Thank you for helping with this research (an AI debate-training system for university students).",
    "",
    "WHAT YOU DO (about 30 to 45 minutes)",
    "1. Open the 'Labels' sheet. Each row is a short debate argument written for the motion shown.",
    "2. In the column 'weakness_label', pick from the dropdown the ONE weakness that matters most in that argument:",
    "   the one that, fixed first, would improve the argument the most.",
    "3. If you are undecided, prefer this order: relevance, claim clarity, evidence, warrant, logic, rebuttal, qualification.",
    "4. The 'notes' column is optional (write anything unusual, for example 'two weaknesses equally bad').",
    "5. Save the file and send it back to the researcher.",
    "",
    "RULES",
    "- Work ALONE, in one sitting. Please do not discuss items with the other coach before you have both finished.",
    "- Judge the argument as written, not whether you agree with its position.",
    "- Please do not use an AI tool to help you label. We need your own professional judgement.",
    "- There is no right or wrong answer to be graded. Your honest judgement is what we need.",
    "",
    "CONSENT",
    "Taking part is voluntary and you may stop at any time. Your name will not appear in any report; you will be listed as",
    "'Labeller A' or 'Labeller B'. Your labels will be used only to evaluate the AI system in this study.",
    "By returning the completed file you agree to this use.",
    "",
    "THE NINE LABELS",
]


def make(n=8):
    os.makedirs(SEND, exist_ok=True)
    base = pd.read_csv(f"{D}/labeller_A.csv")[["item_id", "topic", "side", "argument"]].sort_values("item_id")
    for k, who in enumerate(string.ascii_uppercase[:n]):
        src = base.sample(frac=1, random_state=1000 + k)          # own random order per coach, reproducible
        wb = Workbook()
        ws = wb.active
        ws.title = "Instructions"
        for i, line in enumerate(INSTRUCTIONS, 1):
            ws.cell(i, 1, line)
        r = len(INSTRUCTIONS) + 1
        for k, v in DEFS.items():
            ws.cell(r, 1, f"{k}: {v}")
            r += 1
        ws.column_dimensions["A"].width = 120
        ws["A1"].font = Font(bold=True, size=13)
        for cell in ("A3", "A11", "A17", f"A{len(INSTRUCTIONS)}"):
            ws[cell].font = Font(bold=True)
        lb = wb.create_sheet("Labels")
        lb.append(["item_id", "topic", "side", "argument", "weakness_label", "notes"])
        for row in src.itertuples(index=False):
            lb.append(list(row) + ["", ""])
        for col, w in zip("ABCDEF", (9, 38, 11, 90, 26, 40)):
            lb.column_dimensions[col].width = w
        for c in lb[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="0B2A5B")
        for row in lb.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
            row[4].fill = PatternFill("solid", fgColor="E8F0FF")
        dv = DataValidation(type="list", formula1='"' + ",".join(WEAKNESSES) + '"', allow_blank=False, showErrorMessage=True,
                            errorTitle="Pick from the list", error="Please choose one of the nine labels from the dropdown.")
        lb.add_data_validation(dv)
        dv.add(f"E2:E{len(src) + 1}")
        lb.freeze_panes = "A2"
        wb.save(f"{SEND}/Coach_{who}.xlsx")
    return len(src)


def import_(paths):
    done = []
    for path in paths:
        m = re.search(r"Coach_([A-Z])", os.path.basename(path), re.I)
        if not m:
            raise SystemExit(f"{path}: keep the file name Coach_<letter>.xlsx so the labeller can be identified")
        who = m.group(1).upper()
        ws = load_workbook(path, data_only=True)["Labels"]
        rows = list(ws.iter_rows(values_only=True))
        df = pd.DataFrame(rows[1:], columns=[str(c) for c in rows[0]])
        df["weakness_label"] = df["weakness_label"].astype(str).str.strip().replace({"None": ""})
        bad = df[~df.weakness_label.isin(WEAKNESSES)].item_id.tolist()
        if bad:
            raise SystemExit(f"{path}: missing or invalid labels for {bad[:10]}")
        df["notes"] = df["notes"].fillna("")
        df.sort_values("item_id").to_csv(f"{D}/labeller_{who}.csv", index=False)
        done.append(who)
    print(f"wrote labeller_{', labeller_'.join(done)}. Next: python -m eval.agreement")


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        print(f"wrote {make(n)} items x {n} coach workbooks to {SEND}")
    elif sys.argv[1:2] == ["import"] and len(sys.argv) >= 4:
        import_(sys.argv[2:])
    else:
        print(__doc__)
