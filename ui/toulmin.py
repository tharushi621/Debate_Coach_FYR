"""Visual components for the feedback panel: Toulmin argument map, score bars, round objectives, skill mastery.
All functions return ONE line of HTML (no blank lines, no indentation) so Streamlit's markdown parser keeps it intact.
Every piece of learner or model text is escaped."""
from html import escape

from app import progress as P
from ui.icons import svg

# key, title, what it is, what to do when it is missing
COMPONENTS = {
    "claim": ("Claim", "What you are arguing", "State one clear, debatable position."),
    "grounds": ("Grounds", "The evidence behind it", "Add a specific fact, example or source."),
    "warrant": ("Warrant", "Why the evidence counts", "Explain why that evidence proves your claim."),
    "backing": ("Backing", "What supports the warrant", "Name the principle or authority behind your reasoning."),
    "qualifier": ("Qualifier", "Where the claim holds", "Limit it honestly: usually, in most cases, unless."),
    "rebuttal": ("Rebuttal", "The opposing view", "Acknowledge the strongest objection and answer it."),
}
# grid placement of the classic Toulmin layout: grounds -> warrant -> claim, with backing, qualifier and rebuttal around it
AREA = {"grounds": "g", "warrant": "w", "claim": "c", "backing": "b", "qualifier": "q", "rebuttal": "r"}


def _text(analysis, key):
    if key == "claim":
        v = analysis.get("main_claim")
    elif key == "grounds":
        v = "; ".join(analysis.get("grounds") or [])
    else:
        v = analysis.get(key)
    v = (v or "").strip() if isinstance(v, str) else v
    return v or ""


def toulmin_html(analysis, affected=None):
    """Argument map. `affected` is the Toulmin component the diagnosis points at (claim, grounds, warrant, qualifier, rebuttal)."""
    present = {k: bool(_text(analysis, k)) for k in COMPONENTS}
    n = sum(present.values())
    segs = "".join(f'<i class="{"on" if present[k] else ""}"></i>' for k in COMPONENTS)
    cards = []
    for k, (title, sub, hint) in COMPONENTS.items():
        ok = present[k]
        gap = " gap" if affected == k else ""
        body = escape(_text(analysis, k)) if ok else escape(hint)
        tag = "Found" if ok else "Missing"
        cards.append(f'<div class="tm-c {"ok" if ok else "miss"}{gap} a-{AREA[k]}"><div class="tm-h"><span class="tm-k">{title}</span>'
                     f'<span class="tm-s">{"Main gap" if gap and not ok else tag}</span></div>'
                     f'<div class="tm-sub">{sub}</div><div class="tm-b">{body}</div></div>')
    note = ""
    if affected in COMPONENTS:
        note = (f'<div class="tm-focus"><span class="tm-fk">Focus next</span>'
                f'<span>{escape(COMPONENTS[affected][0])}: {escape(COMPONENTS[affected][2])}</span></div>')
    return (f'<div class="tm"><div class="tm-top"><div><b>Argument map</b><span class="muted"> · Toulmin model</span></div>'
            f'<div class="tm-meter"><span>{n} of 6 components found</span><div class="tm-seg">{segs}</div></div></div>'
            f'<div class="tm-grid">{"".join(cards)}</div>{note}</div>')


def score_bars_html(scores, overall=None):
    rows = []
    for d in P.DIMS:
        if d not in scores:
            continue
        v = float(scores[d])
        tone = "hi" if v >= 4 else "mid" if v >= 3 else "lo"
        rows.append(f'<div class="sb"><span>{escape(P.DIM_LABEL.get(d, d))}</span><div class="bar {tone}"><i style="width:{v / 5 * 100:.0f}%"></i></div>'
                    f'<span class="n">{v:g}</span></div>')
    head = f'<div class="sb-head"><b>Dimension scores</b><span class="muted">scale 1 to 5</span>' + \
           (f'<span class="sb-ov">Overall <b>{overall:g}</b></span>' if overall is not None else "") + "</div>"
    return f'<div class="sbox">{head}{"".join(rows)}</div>'


def objectives_html(objs, points):
    items = "".join(f'<div class="ob {"ok" if met else ""}"><span class="ob-i">{svg("check", 14) if met else ""}</span>'
                    f'<span class="ob-t">{escape(label)}</span><span class="ob-p">+{pts}</span></div>' for label, met, pts in objs)
    done = sum(1 for _, m, _ in objs if m)
    return (f'<div class="obox"><div class="ob-head"><b>Round objectives</b><span class="muted">{done} of {len(objs)} met</span>'
            f'<span class="ob-pts">{svg("bolt", 14)} {points} points</span></div>{items}</div>')


def mastery_html(avg_dims):
    cards = []
    for d in P.DIMS:
        m = P.mastery(avg_dims.get(d))
        if m is None:
            continue
        nxt = f'{m["to_next"]:.1f} to {escape(m["next"])}' if m["next"] else "Top tier reached"
        cards.append(f'<div class="ms t{m["tier_idx"]}"><div class="ms-h"><span>{escape(P.DIM_LABEL[d])}</span><b>{escape(m["tier"])}</b></div>'
                     f'<div class="bar"><i style="width:{m["pct"] * 100:.0f}%"></i></div><div class="muted">{m["score"]:.1f} average · {nxt}</div></div>')
    return f'<div class="msg-grid">{"".join(cards)}</div>' if cards else '<div class="muted">Complete a debate to unlock skill tiers.</div>'
