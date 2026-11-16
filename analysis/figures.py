
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.pilot import ASPECTS, _skip, ratings  # noqa: E402
from analysis.report import latest_test_meta  # noqa: E402
from app.db import Database  # noqa: E402

BLUE, GREEN, NAVY = "#1d5fd1", "#1f9d63", "#0b2a5b"   # thesis 4.13.2 palette


def fig_agreement(meta, out):
    s = meta["system"]
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    ax.bar(["Correct", "Incorrect"], [s["correct"], s["n"] - s["correct"]], color=[GREEN, BLUE])
    ax.set_ylabel("Arguments")
    ax.set_title(f"Diagnostic agreement: {s['accuracy']:.0%} ({s['correct']}/{s['n']})", color=NAVY)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_feedback(rt, out):
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.barh(rt["Evaluation aspect"][::-1], rt["Mean /5"][::-1], color=BLUE)
    ax.set_xlim(0, 5); ax.set_xlabel(f"Mean rating (1 to 5), n = {int(rt['n'].max())}")
    ax.set_title("User feedback", color=NAVY)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_progression(db, out, since, exclude):
    q = ("SELECT s.session_id, u.name, t.turn_number, d.overall_score FROM debate_sessions s JOIN users u ON u.user_id=s.user_id "
         "JOIN debate_turns t ON t.session_id=s.session_id JOIN weakness_diagnoses d ON d.turn_id=t.turn_id WHERE s.mode='adaptive'"
         + (" AND s.created_at>=?" if since else "") + " ORDER BY s.session_id, t.turn_number")
    skip, by = _skip(exclude), {}
    for r in db.all(q, (since,) if since else ()):
        if (r["name"] or "").lower() not in skip:
            by.setdefault(r["session_id"], []).append((r["turn_number"], r["overall_score"]))
    by = {k: v for k, v in by.items() if len(v) >= 2}
    if not by:
        return False
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for i, pts in enumerate(by.values(), 1):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=f"Participant {i}")
    ax.set_ylim(1, 5); ax.set_xlabel("Debate turn"); ax.set_ylabel("Overall argument score")
    ax.set_title("Score progression across debate turns", color=NAVY); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)
    return True


def fig_weaknesses(db, out):
    rows = db.all("SELECT weakness, COUNT(*) AS n FROM weakness_diagnoses GROUP BY weakness ORDER BY n DESC")
    if not rows:
        return False
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.barh([r["weakness"].replace("_", " ") for r in rows][::-1], [r["n"] for r in rows][::-1], color=BLUE)
    ax.set_xlabel("Times diagnosed"); ax.set_title("Weakness frequency", color=NAVY)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)
    return True


def fig_labeller_agreement(joined_csv, out):
    """Pairwise raw agreement between the human coaches (real labels from eval/data/labelling/_joined.csv)."""
    import itertools
    import numpy as np
    import pandas as pd
    j = pd.read_csv(joined_csv, keep_default_na=False)
    cols = [c for c in j.columns if c.startswith("label_")]
    names = [c[len("label_"):] for c in cols]
    m = np.eye(len(cols))
    for a, b in itertools.combinations(range(len(cols)), 2):
        m[a, b] = m[b, a] = float((j[cols[a]] == j[cols[b]]).mean())
    off = m[~np.eye(len(cols), dtype=bool)]
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(m, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(len(cols)), [f"Coach {n}" for n in names], rotation=45, ha="right")
    ax.set_yticks(range(len(cols)), [f"Coach {n}" for n in names])
    for a in range(len(cols)):
        for b in range(len(cols)):
            ax.text(b, a, f"{m[a, b]:.0%}", ha="center", va="center", fontsize=7, color="white" if m[a, b] > .6 else NAVY)
    ax.set_title(f"Agreement between {len(cols)} human coaches (mean {off.mean():.0%})", color=NAVY, fontsize=10)
    fig.colorbar(im, ax=ax, fraction=.046); fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_reference_distribution(strict_csv, plurality_csv, out):
    """How many items each weakness has in the two human reference sets."""
    import pandas as pd
    a = pd.read_csv(strict_csv).reference_weakness.value_counts()
    b = pd.read_csv(plurality_csv).reference_weakness.value_counts()
    labels = sorted(set(a.index) | set(b.index), key=lambda k: -(b.get(k, 0)))
    y = range(len(labels))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.barh([i + .2 for i in y], [b.get(k, 0) for k in labels], height=.38, color=BLUE, label=f"Most frequent label ({len(pd.read_csv(plurality_csv))} items)")
    ax.barh([i - .2 for i in y], [a.get(k, 0) for k in labels], height=.38, color=GREEN, label=f"Strict majority ({len(pd.read_csv(strict_csv))} items)")
    ax.set_yticks(list(y), [k.replace("_", " ") for k in labels]); ax.invert_yaxis()
    ax.set_xlabel("Labelled arguments"); ax.set_title("Reference weaknesses chosen by the coaches", color=NAVY)
    ax.legend(fontsize=8, loc="lower right"); fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def _load_ch7(res_dir):
    import glob
    import json
    files = sorted(glob.glob(f"{res_dir}/ch7_results_*.json"), key=os.path.getmtime)
    return json.load(open(files[-1], encoding="utf-8")) if files else None


def fig_comparison(res, out, ref="strict_majority", split="test"):
    """Accuracy of the thesis system vs the single-prompt baseline vs the majority class, with 95% Wilson intervals."""
    r = res["results"][ref][split]
    arms = [("thesis_system", "Thesis system", GREEN), ("single_prompt_llm", "Single prompt", BLUE), ("majority_class", "Majority class", "#9aa7bd")]
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    for i, (k, lab, col) in enumerate(arms):
        v = r[k]
        ax.bar(i, v["accuracy"], color=col, yerr=[[v["accuracy"] - v["ci95"][0]], [v["ci95"][1] - v["accuracy"]]], capsize=4)
        ax.text(i, v["accuracy"] + .02, f"{v['correct']}/{v['n']}", ha="center", fontsize=8, color=NAVY)
    ax.set_xticks(range(len(arms)), [a[1] for a in arms]); ax.set_ylim(0, 1.05); ax.set_ylabel("Accuracy vs coach reference")
    ax.set_title(f"Diagnosis accuracy ({ref.replace('_', ' ')}, {split} split, model {res['model']})", color=NAVY, fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_confusion(res, out, ref="strict_majority", split="test"):
    import numpy as np
    r = res["results"][ref][split]
    labs, cm = [k.replace("_", " ") for k in r["confusion_labels"]], np.array(r["confusion"])
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labs)), labs, rotation=45, ha="right", fontsize=8); ax.set_yticks(range(len(labs)), labs, fontsize=8)
    for a in range(len(labs)):
        for b in range(len(labs)):
            if cm[a, b]:
                ax.text(b, a, int(cm[a, b]), ha="center", va="center", color="white" if cm[a, b] > cm.max() / 2 else NAVY)
    ax.set_xlabel("System diagnosis"); ax.set_ylabel("Coach reference"); ax.set_title("Confusion matrix", color=NAVY)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def build(db, out_dir="figures", res_dir="eval/results", since=None, exclude=(), pilot=False):
    os.makedirs(out_dir, exist_ok=True)
    made = {}
    meta = latest_test_meta(res_dir)
    if meta and meta.get("system"):
        fig_agreement(meta, f"{out_dir}/fig_diagnostic_agreement.png"); made["agreement"] = True
    else:
        print("skipped diagnostic agreement: no test-split run in", res_dir)
    if pilot:      # figures drawn from debate.db: ONLY for real pilot participants (use --since and --exclude to drop your own sessions)
        rt = ratings(db, "adaptive", since, exclude)
        if rt is not None and len(rt):
            fig_feedback(rt, f"{out_dir}/fig_user_feedback.png"); made["feedback"] = True
        else:
            print("skipped user feedback: no stored ratings")
        if fig_progression(db, f"{out_dir}/fig_score_progression.png", since, exclude):
            made["progression"] = True
        else:
            print("skipped score progression: no sessions with 2+ turns")
        if fig_weaknesses(db, f"{out_dir}/fig_weakness_frequency.png"):
            made["weaknesses"] = True
        else:
            print("skipped weakness frequency: no diagnoses stored")
    else:
        print("skipped user feedback, score progression and weakness frequency: they come from debate.db, so pass --pilot only for real participants")
    lab = "eval/data/labelling"
    if os.path.exists(f"{lab}/_joined.csv"):
        fig_labeller_agreement(f"{lab}/_joined.csv", f"{out_dir}/fig_coach_agreement.png"); made["coach_agreement"] = True
    else:
        print("skipped coach agreement: no _joined.csv (run eval.agreement)")
    if os.path.exists(f"{lab}/reference_labels.csv") and os.path.exists(f"{lab}/reference_labels_plurality.csv"):
        fig_reference_distribution(f"{lab}/reference_labels.csv", f"{lab}/reference_labels_plurality.csv", f"{out_dir}/fig_reference_distribution.png")
        made["reference_distribution"] = True
    ch7 = _load_ch7(res_dir)
    if ch7:
        fig_comparison(ch7, f"{out_dir}/fig_system_vs_baselines.png"); fig_confusion(ch7, f"{out_dir}/fig_confusion_matrix.png")
        made["comparison"] = made["confusion"] = True
    else:
        print("skipped system vs baselines and confusion matrix: run eval.run_chapter7 predict, then analyse")
    return made


if __name__ == "__main__":
    a = sys.argv[1:]
    flag = lambda n, d=None: a[a.index(n) + 1] if n in a else d
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    print(build(Database(pos[0] if pos else "debate.db"), flag("--out", "figures"), since=flag("--since"),
                exclude=(flag("--exclude", "") or "").split(","), pilot="--pilot" in a))
