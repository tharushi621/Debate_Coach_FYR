"""Small iframe widgets: countdown timers and the journey stepper.
Colours follow thesis 4.13.2: blue = primary, green = progress/success, dark blue = key text."""
from html import escape
from .journey import STAGES

def timer_html(seconds: int, label="Time left", key="t", height=70):
    return f"""<!doctype html><meta charset=utf-8><style>body{{margin:0;font-family:Inter,system-ui,sans-serif;background:transparent}}
.w{{display:flex;align-items:center;gap:12px}}.n{{font-weight:800;font-size:28px;font-variant-numeric:tabular-nums;color:#0b2a5b}}
.l{{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#64748b;font-weight:700}}
.b{{flex:1;height:8px;border-radius:9px;background:#e8eef8;overflow:hidden}}.b i{{display:block;height:100%;width:100%;background:linear-gradient(90deg,#1d5fd1,#1f9d63);transition:width 1s linear}}
.low .n{{color:#b45309}}</style><div class=w id=w><div><div class=l>{escape(label)}</div><div class=n id=n></div></div><div class=b><i id=i></i></div></div>
<script>/*{escape(key)}*/let T={int(seconds)},R=T;const n=document.getElementById('n'),i=document.getElementById('i'),w=document.getElementById('w');
function f(){{const m=Math.floor(R/60),s=R%60;n.textContent=m+':'+String(s).padStart(2,'0');i.style.width=(R/T*100)+'%';w.className=R<=30?'w low':'w'}}
f();setInterval(()=>{{if(R>0){{R--;f()}}}},1000)</script>"""

def stepper_html(current_key: str):
    keys = [s["key"] for s in STAGES]; ci = keys.index(current_key)
    items = []
    for i, s in enumerate(STAGES):
        st = "done" if i < ci else "cur" if i == ci else ""
        items.append(f'<div class="st {st}" title="{escape(s["title"])}"><span>{s["icon"] if i<=ci else s["n"]}</span></div>')
    css = ("<style>.stp{display:flex;align-items:center;gap:0;margin:4px 0 14px}.st{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;"
           "background:#fff;border:2px solid #e2e8f3;font-size:15px;font-weight:700;color:#64748b;flex:none}.st.done{border-color:#1f9d63;background:#e5f6ee;color:#157a4b}"
           ".st.cur{background:#1d5fd1;color:#fff;border-color:#1d5fd1;transform:scale(1.15);animation:pulse 1.6s infinite}"
           ".stp i{flex:1;height:3px;background:#e2e8f3;min-width:4px}.stp i.d{background:#1f9d63}"
           ".st svg{width:17px;height:17px}@media(max-width:600px){.st{width:24px;height:24px;font-size:11px}}</style>")
    out = []
    for i, it in enumerate(items):
        out.append(it)
        if i < len(items) - 1:
            out.append(f'<i class="{"d" if i < ci else ""}"></i>')
    return css + f'<div class="stp">{"".join(out)}</div><div class="eyebrow">Stage {ci+1} of 9 · {escape(STAGES[ci]["title"])}</div>'
