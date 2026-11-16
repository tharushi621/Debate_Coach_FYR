"""Excel workbooks for the two blind raters of the reply comparison (thesis 7.8), and the import of their ratings.

  python -m eval.rater_workbooks make     -> eval/results/replies/send/Rater_A.xlsx and Rater_B.xlsx
  python -m eval.rater_workbooks import Rater_A.xlsx Rater_B.xlsx
        -> validated ratings are written into eval/results/replies/rater_A.csv and rater_B.csv. Then: python -m eval.compare analyse

Run  python -m eval.compare replies openai --n 30  first (it writes the blind sheets and the secret key). The workbooks show
NO information about which system wrote a reply.
"""
import os
import re
import sys

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RDIR = "eval/results/replies"
SEND = f"{RDIR}/send"
HEADER_ROW = 5          # rows 1 to 3 carry the "how to rate" banner, row 4 is blank
RATE = ["targets_weakness_1to5", "helpful_next_step_1to5", "writes_argument_for_student_yes_no"]
SHOW = ["reply_id", "topic", "student_side", "argument", "reference_weakness", "reply"]

BANNER = [
    "HOW TO RATE (about 45 minutes, work alone): for EVERY row below, fill the three blue columns G, H and I. Read the argument, then the AI reply.",
    "G = how well the reply goes after the reference weakness (1 = not at all, 3 = partly, 5 = directly).   H = would it help the student write a better next argument (1 = not helpful, 5 = very helpful).",
    "I = does the reply write or hand over the student's argument for them (yes or no).   You are not told which system wrote a reply. See the 'Instructions' sheet for details, then save and send the file back.",
]

MESSAGE = """Hi,

Thank you for helping with my final-year research on an AI debate-training system. I would like you to rate some AI replies.

What to do (about 45 minutes):
1. Open the attached Excel file. Start on the 'Ratings' sheet, where the instructions are at the top (more detail is on the 'Instructions' sheet).
2. Each row is a short student argument, the main weakness of that argument, and an AI opponent's reply.
3. For every row, fill the three blue columns: how well the reply targets the weakness (1 to 5), how helpful it is for the student's next argument (1 to 5), and whether it writes the student's argument for them (yes or no).
4. Save the file and email it back. Please keep the file name the same.

Please work on your own and do not discuss the rows with the other rater until you have both finished. Please do not use an AI tool to help you; I need your own judgement. You will only be named as 'Rater {who}'. Taking part is voluntary and you may stop at any time.

Thank you very much!
"""

INSTRUCTIONS = [
    "Thank you for helping with this research (an AI debate-training system for university students).",
    "",
    "WHAT YOU DO (about 30 to 45 minutes)",
    "Each row is a short debate argument written by a student, followed by a reply from an AI debate opponent.",
    "'reference_weakness' is the main weakness of that argument as judged by human debate coaches.",
    "For each reply, fill the three coloured columns on the 'Ratings' sheet:",
    "",
    "1. targets_weakness_1to5: how well does the reply go after that weakness?",
    "   1 = not at all (it ignores the weakness), 3 = partly, 5 = directly and clearly targets it.",
    "2. helpful_next_step_1to5: would this reply help the student write a better next argument?",
    "   1 = not helpful or confusing, 3 = somewhat helpful, 5 = very helpful and clear.",
    "3. writes_argument_for_student_yes_no: does the reply write or hand over the student's argument for them",
    "   (for example by giving the full evidence or the full line they should say)? Pick yes or no.",
    "",
    "RULES",
    "- Work ALONE, in one sitting, and do not discuss rows with the other rater until you have both finished.",
    "- You will not be told which system wrote which reply. Judge each reply only on what it says.",
    "- Please do not use an AI tool to help you rate. We need your own professional judgement.",
    "- The order of the rows is random. Rows are not grouped by system.",
    "",
    "CONSENT",
    "Taking part is voluntary and you may stop at any time. You will be named only as 'Rater A' or 'Rater B'.",
    "Your ratings will be used only to evaluate the AI system in this study. By returning the file you agree to this use.",
]


def make():
    os.makedirs(SEND, exist_ok=True)
    for who in ("A", "B"):
        src = pd.read_csv(f"{RDIR}/rater_{who}.csv")
        wb = Workbook()
        ws = wb.active
        ws.title = "Instructions"
        for i, line in enumerate(INSTRUCTIONS, 1):
            ws.cell(i, 1, line)
        ws.column_dimensions["A"].width = 125
        ws["A1"].font = Font(bold=True, size=13)
        for row in ws.iter_rows(min_col=1, max_col=1):
            c = row[0]
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if c.value and (c.value.isupper() or c.value.startswith(("WHAT YOU DO", "RULES", "CONSENT"))):
                c.font = Font(bold=True, color="0B2A5B")
        rt = wb.create_sheet("Ratings")
        for i, line in enumerate(BANNER, 1):
            rt.cell(i, 1, line)
            rt.merge_cells(start_row=i, start_column=1, end_row=i, end_column=9)
            rt.cell(i, 1).alignment = Alignment(wrap_text=True, vertical="center")
            rt.row_dimensions[i].height = 22 if i == 1 else 34
        rt["A1"].font = Font(bold=True, size=12, color="0B2A5B")
        rt["A1"].fill = rt["A2"].fill = rt["A3"].fill = PatternFill("solid", fgColor="FFF6D6")
        rt.append([])
        rt.append(SHOW + RATE)
        for r in src[SHOW].itertuples(index=False):
            rt.append(list(r) + ["", "", ""])
        for col, w in zip("ABCDEFGHI", (10, 30, 11, 60, 22, 60, 18, 18, 18)):
            rt.column_dimensions[col].width = w
        for c in rt[HEADER_ROW]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="0B2A5B")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for row in rt.iter_rows(min_row=HEADER_ROW + 1):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
            for c in row[6:]:
                c.fill = PatternFill("solid", fgColor="E8F0FF")
        first, n = HEADER_ROW + 1, HEADER_ROW + len(src)
        num = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=False, showErrorMessage=True,
                             errorTitle="1 to 5", error="Enter a whole number from 1 to 5.")
        yn = DataValidation(type="list", formula1='"yes,no"', allow_blank=False, showErrorMessage=True,
                            errorTitle="yes or no", error="Pick yes or no from the list.")
        rt.add_data_validation(num)
        rt.add_data_validation(yn)
        num.add(f"G{first}:H{n}")
        yn.add(f"I{first}:I{n}")
        rt.freeze_panes = f"A{HEADER_ROW + 1}"
        wb.save(f"{SEND}/Rater_{who}.xlsx")
        open(f"{SEND}/message_for_Rater_{who}.txt", "w", encoding="utf-8").write(MESSAGE.format(who=who))
    return len(src)


def import_(paths):
    done = []
    for path in paths:
        if not os.path.exists(path):
            raise SystemExit(
                f"File not found: {path}\n"
                "Use the real location of the file the rater sent back, for example "
                "C:/Users/<you>/Downloads/Rater_A.xlsx (the paths in the instructions are only examples).")
        m = re.search(r"Rater_([A-Z])", os.path.basename(path), re.I)
        if not m:
            raise SystemExit(f"{path}: keep the file name Rater_<letter>.xlsx so the rater can be identified")
        who = m.group(1).upper()
        ws = load_workbook(path, data_only=True)["Ratings"]
        rows = list(ws.iter_rows(values_only=True))
        h = next(i for i, r in enumerate(rows) if r and r[0] == "reply_id")
        df = pd.DataFrame(rows[h + 1:], columns=[str(c) for c in rows[h]]).dropna(subset=["reply_id"])
        for col in RATE[:2]:
            v = pd.to_numeric(df[col], errors="coerce")
            bad = df.reply_id[~v.isin([1, 2, 3, 4, 5])].tolist()
            if bad:
                raise SystemExit(f"{path}: column {col} must be 1 to 5 for every row; missing or invalid at {bad[:8]}")
            df[col] = v.astype(int)
        yn = df[RATE[2]].astype(str).str.strip().str.lower()
        bad = df.reply_id[~yn.isin(["yes", "no"])].tolist()
        if bad:
            raise SystemExit(f"{path}: {RATE[2]} must be yes or no; missing or invalid at {bad[:8]}")
        df[RATE[2]] = yn
        df.to_csv(f"{RDIR}/rater_{who}.csv", index=False)
        done.append(who)
    print(f"wrote rater_{', rater_'.join(done)}.csv. Next: python -m eval.compare analyse")


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        print(f"wrote {make()} replies x 2 rater workbooks to {SEND}")
    elif sys.argv[1:2] == ["import"] and len(sys.argv) >= 3:
        import_(sys.argv[2:])
    else:
        print(__doc__)
