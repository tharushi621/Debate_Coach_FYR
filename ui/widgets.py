"""Small iframe widgets: countdown timers, voice dictation, journey stepper."""
from html import escape
from .journey import STAGES

def timer_html(seconds: int, label="Time left", key="t", height=70):
    return f"""<!doctype html><meta charset=utf-8><style>body{{margin:0;font-family:Inter,system-ui,sans-serif;background:transparent}}
.w{{display:flex;align-items:center;gap:12px}}.n{{font-weight:800;font-size:28px;font-variant-numeric:tabular-nums;color:#16302f}}
.l{{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#587270;font-weight:700}}
.b{{flex:1;height:8px;border-radius:9px;background:rgba(22,48,47,.1);overflow:hidden}}.b i{{display:block;height:100%;width:100%;background:linear-gradient(90deg,#7fd6c2,#0f8b7d);transition:width 1s linear}}
.low .n{{color:#c27219}}</style><div class=w id=w><div><div class=l>{escape(label)}</div><div class=n id=n></div></div><div class=b><i id=i></i></div></div>
<script>/*{escape(key)}*/let T={int(seconds)},R=T;const n=document.getElementById('n'),i=document.getElementById('i'),w=document.getElementById('w');
function f(){{const m=Math.floor(R/60),s=R%60;n.textContent=m+':'+String(s).padStart(2,'0');i.style.width=(R/T*100)+'%';w.className=R<=30?'w low':'w'}}
f();setInterval(()=>{{if(R>0){{R--;f()}}}},1000)</script>"""

def voice_html(height=170):
    return """<!doctype html><meta charset=utf-8><style>body{margin:0;font-family:Inter,system-ui,sans-serif;background:transparent}
.r{display:flex;gap:8px;flex-wrap:wrap}button{border:0;border-radius:99px;padding:8px 16px;font:600 14px Inter,system-ui;cursor:pointer;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.1)}
button.on{background:#c27219;color:#fff}textarea{width:100%;margin-top:8px;border-radius:14px;border:1px solid #cfe0dc;padding:10px;font:14px Inter,system-ui;height:70px;box-sizing:border-box}
small{color:#587270}</style><div class=r><button id=m>🎙️ Dictate</button><button id=c>Copy text</button><small id=s>Optional. Then paste into the box above.</small></div>
<textarea id=t placeholder="Your dictated words appear here…"></textarea>
<script>const SR=window.SpeechRecognition||window.webkitSpeechRecognition,m=document.getElementById('m'),t=document.getElementById('t'),s=document.getElementById('s');let rec,on=false;
if(!SR){m.disabled=true;s.textContent='Voice input is not supported in this browser — type instead.'}else{rec=new SR();rec.continuous=true;rec.interimResults=true;rec.lang='en-US';let base='';
rec.onresult=e=>{let x='';for(let i=0;i<e.results.length;i++)x+=e.results[i][0].transcript;t.value=(base+' '+x).trim()};
rec.onend=()=>{on=false;m.classList.remove('on');m.textContent='🎙️ Dictate'};
m.onclick=()=>{if(on){rec.stop();return}base=t.value;rec.start();on=true;m.classList.add('on');m.textContent='⏹ Stop';s.textContent='Listening… (audio is processed by your browser vendor)'}}
document.getElementById('c').onclick=()=>{t.select();navigator.clipboard&&navigator.clipboard.writeText(t.value);s.textContent='Copied — paste it into the box above.'}</script>"""

def stepper_html(current_key: str):
    keys = [s["key"] for s in STAGES]; ci = keys.index(current_key)
    items = []
    for i, s in enumerate(STAGES):
        st = "done" if i < ci else "cur" if i == ci else ""
        items.append(f'<div class="st {st}" title="{escape(s["title"])}"><span>{s["icon"] if i<=ci else s["n"]}</span></div>')
    css = ("<style>.stp{display:flex;align-items:center;gap:0;margin:4px 0 14px}.st{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;"
           "background:#fff;border:2px solid #d6dfdd;font-size:15px;font-weight:700;color:#7a8f8d;flex:none}.st.done{border-color:#0f8b7d;background:#e8f8f3}"
           ".st.cur{background:#0f8b7d;color:#fff;border-color:#0f8b7d;transform:scale(1.15);animation:pulse 1.6s infinite}"
           ".stp i{flex:1;height:3px;background:#d6dfdd;min-width:4px}.stp i.d{background:#0f8b7d}"
           "@media(max-width:600px){.st{width:24px;height:24px;font-size:11px}}</style>")
    out = []
    for i, it in enumerate(items):
        out.append(it)
        if i < len(items) - 1:
            out.append(f'<i class="{"d" if i < ci else ""}"></i>')
    return css + f'<div class="stp">{"".join(out)}</div><div class="eyebrow">Stage {ci+1} of 9 · {escape(STAGES[ci]["title"])}</div>'