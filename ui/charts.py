"""Pure-HTML/SVG charts (no pandas/numpy/matplotlib: works on locked-down Windows machines)."""
import math
from html import escape

from app.progress import DIMS, DIM_LABEL, band

TEAL, GRID = "#0f8b7d", "#dfe7e5"


def radar_svg(values: dict, order=None, vmax=5, center=None, center_label="Overall score", size=470):
    """Radar like reference image 1. `values` maps label->number (1..vmax)."""
    order = order or list(values)
    n = len(order); cx = cy = size / 2; R = size * .34
    pt = lambda i, r: (cx + r * math.sin(2 * math.pi * i / n), cy - r * math.cos(2 * math.pi * i / n))
    g = []
    for k in range(1, 6):
        g.append('<polygon points="%s" fill="none" stroke="%s"/>' % (
            " ".join("%.1f,%.1f" % pt(i, R * k / 5) for i in range(n)), GRID))
    for i in range(n):
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (cx, cy, *pt(i, R), GRID))
    pts = [pt(i, R * max(0, min(vmax, values.get(k) or 0)) / vmax) for i, k in enumerate(order)]
    poly = " ".join("%.1f,%.1f" % p for p in pts)
    g.append(f'<polygon points="{poly}" fill="rgba(15,139,125,.45)" stroke="{TEAL}" stroke-width="2.5" '
             'style="transform-origin:50% 50%;animation:rgrow .9s cubic-bezier(.2,.8,.2,1) both"/>')
    for i, k in enumerate(order):
        x, y = pts[i]
        g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#fff" stroke="{TEAL}" stroke-width="2.5"/>')
        lx, ly = pt(i, R + 34); vx, vy = pt(i, R * (values.get(k) or 0) / vmax + (-18 if True else 0))
        anchor = "middle" if abs(lx - cx) < 12 else "start" if lx > cx else "end"
        g.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="13" fill="#2a3f3d" font-weight="500">{escape(DIM_LABEL.get(k, k))}</text>')
        g.append(f'<text x="{lx:.1f}" y="{ly+16:.1f}" text-anchor="{anchor}" font-size="13" fill="{TEAL}" font-weight="700">{(values.get(k) or 0):.1f}</text>')
    mid = ""
    if center is not None:
        mid = (f'<text x="{cx}" y="{cy+6}" text-anchor="middle" font-size="40" font-weight="700" fill="#1f3533">{center:.1f}</text>'
               f'<text x="{cx}" y="{cy+28}" text-anchor="middle" font-size="12" fill="#4a6462">{escape(center_label)}</text>')
    return (f'<svg viewBox="-110 0 {size+220} {size}" width="100%" style="max-width:{size+220}px;display:block;margin:auto" role="img" '
            f'aria-label="Radar chart of argument scores"><style>@keyframes rgrow{{from{{transform:scale(.1);opacity:0}}to{{transform:scale(1);opacity:1}}}}</style>'
            + "".join(g) + mid + "</svg>")


def score_cards(values: dict, order=None, labels=None):
    """Teal cards: big number, % bar and a band label (Strong/Proficient/Developing/Needs improvement)."""
    out = []
    for i, k in enumerate(order or list(values)):
        v = values.get(k)
        if v is None:
            continue
        pct = round(v / 5 * 100)
        lab = band(v)
        warn = " warn" if lab in ("Developing", "Needs improvement") else ""
        out.append(f'<div class="sc{warn}" style="animation-delay:{i*70}ms"><div class="t">{escape((labels or DIM_LABEL).get(k,k))}</div>'
                   f'<div class="v">{v:.1f}</div><div class="pc">{pct}%</div>'
                   f'<div class="bar"><i style="width:{pct}%"></i></div><div class="lab">{lab}</div></div>')
    return '<div class="scards">' + "".join(out) + "</div>"


def line_svg(values, width=640, height=190, vmax=5, vmin=1):
    if not values:
        return '<div class="muted">Your trend appears after your first debate.</div>'
    pad = 28; n = len(values)
    x = lambda i: pad + (width - 2 * pad) * (i / max(n - 1, 1) if n > 1 else .5)
    y = lambda v: height - pad - (height - 2 * pad) * (v - vmin) / (vmax - vmin)
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    grid = "".join(f'<line x1="{pad}" x2="{width-pad}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}"/>'
                   f'<text x="4" y="{y(v)+4:.1f}" font-size="11" fill="#7a8f8d">{v}</text>' for v in range(vmin, vmax + 1))
    dots = "".join(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="5" fill="#fff" stroke="{TEAL}" stroke-width="2.5"><title>Debate {i+1}: {v:.2f}</title></circle>'
                   for i, v in enumerate(values))
    line = f'<polyline points="{pts}" fill="none" stroke="{TEAL}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>' if n > 1 else ""
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Overall score per debate">{grid}{line}{dots}</svg>')


def hbars(items, vmax=None, color=TEAL):
    """items: [(label, value)] horizontal bars."""
    if not items:
        return '<div class="muted">Nothing to show yet.</div>'
    vmax = vmax or max(v for _, v in items) or 1
    return "".join(f'<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:.88rem"><span>{escape(str(l))}</span><b>{v:g}</b></div>'
                   f'<div class="bar"><i style="width:{v/vmax*100:.0f}%;background:{color}"></i></div></div>' for l, v in items)