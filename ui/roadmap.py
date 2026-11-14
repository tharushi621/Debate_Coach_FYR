"""Interactive 9-stage roadmap rendered in an iframe (self-contained HTML/CSS/JS)."""
import json
from .journey import STAGES

TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;color:#16302f;background:transparent}
:root{--teal:#0f8b7d;--mint:#bfeadf;--lav:#d3c6f0}
.wrap{padding:6px 4px}
.track{position:relative;display:flex;justify-content:space-between;gap:4px;padding:18px 4px 8px}
.step{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;text-align:center;cursor:pointer;position:relative;
  background:none;border:0;font:inherit;color:inherit;padding:0;outline:none;animation:in .5s both}
.step:not(:last-child)::after{content:"";position:absolute;top:31px;left:calc(50% + 34px);width:calc(100% - 68px);height:4px;border-radius:4px;
  background:#d6dfdd;z-index:0}
.step.done:not(:last-child)::after{background:linear-gradient(90deg,var(--teal),#7fd6c2)}
.step.current:not(:last-child)::after{background:linear-gradient(90deg,var(--teal) 40%,#d6dfdd 40%)}
.node{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;font-size:26px;background:#fff;position:relative;z-index:1;
  border:3px solid #d6dfdd;box-shadow:0 6px 16px rgba(60,90,100,.14);transition:transform .22s,box-shadow .22s,border-color .22s}
.step:hover .node,.step:focus-visible .node{transform:translateY(-6px) scale(1.07);box-shadow:0 14px 26px rgba(15,139,125,.28)}
.step.done .node{border-color:var(--teal);background:#e8f8f3}
.step.current .node{border-color:var(--teal);animation:pulse 1.6s infinite}
.step.sel .node{background:var(--teal);color:#fff;border-color:var(--teal);transform:translateY(-6px) scale(1.1)}
.num{position:absolute;top:-8px;right:-4px;background:#1d2423;color:#fff;font-size:11px;font-weight:700;border-radius:99px;min-width:22px;height:22px;
  display:grid;place-items:center;padding:0 5px}
.tick{position:absolute;bottom:-4px;right:-4px;background:var(--teal);color:#fff;border-radius:50%;width:20px;height:20px;font-size:12px;display:grid;place-items:center}
.t{margin-top:12px;font-weight:700;font-size:13px;line-height:1.2;padding:0 2px}
.s{font-size:11.5px;color:#587270;margin-top:4px;line-height:1.25;padding:0 4px}
.status{margin-top:6px;font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#7a8f8d}
.done .status{color:var(--teal)}.current .status{color:#b4730f}
.panel{margin:16px 2px 4px;background:rgba(255,255,255,.88);border-radius:22px;padding:22px 24px;box-shadow:0 10px 30px rgba(60,90,100,.14);
  border:1px solid rgba(255,255,255,.8);animation:slide .35s both}
.panel h3{margin:0 0 4px;font-size:20px}.panel .lead{margin:0 0 14px;color:#4a6462}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.cell{border-radius:16px;padding:12px 14px;background:#f2f8f6}
.cell:nth-child(2){background:#f1ecfb}.cell:nth-child(3){background:#fdf5d8}.cell:nth-child(4){background:#e6f4fb}
.cell b{display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#587270;margin-bottom:4px}
.nav{display:flex;gap:8px;margin-top:14px;justify-content:space-between;align-items:center}
.nav button{border:0;border-radius:99px;padding:8px 16px;font-weight:600;cursor:pointer;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.1);font:inherit;font-weight:600}
.nav button:hover{background:var(--mint)}.nav .hint{font-size:12px;color:#7a8f8d}
@keyframes in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes slide{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(15,139,125,.5)}100%{box-shadow:0 0 0 16px rgba(15,139,125,0)}}
@media(max-width:760px){
 .track{flex-direction:column;gap:6px;padding-left:10px}
 .step{flex-direction:row;text-align:left;gap:14px;align-items:center;padding:6px 0}
 .step:not(:last-child)::after{top:62px;left:30px;width:4px;height:calc(100% - 54px)}
 .step.current:not(:last-child)::after{background:linear-gradient(180deg,var(--teal) 40%,#d6dfdd 40%)}
 .step.done:not(:last-child)::after{background:linear-gradient(180deg,var(--teal),#7fd6c2)}
 .t{margin-top:0}.node{flex:none}.txt{flex:1}.status{margin-top:2px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body><div class="wrap">
<div class="track" id="track" role="list"></div><div id="panel"></div></div>
<script>
const S=__STAGES__, DONE=__DONE__, CUR=__CUR__;let sel=__SEL__;
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function st(i){return DONE.includes(i)?'done':i===CUR?'current':'upcoming'}
function draw(){
 document.getElementById('track').innerHTML=S.map((s,i)=>{const k=st(i);
  return `<button class="step ${k} ${i===sel?'sel':''}" data-i="${i}" role="listitem" aria-label="Stage ${s.n}: ${esc(s.title)} (${k})" style="animation-delay:${i*60}ms">
  <div class="node">${s.icon}<span class="num">${String(s.n).padStart(2,'0')}</span>${k==='done'?'<span class="tick">✓</span>':''}</div>
  <div class="txt"><div class="t">${esc(s.title)}</div><div class="s">${esc(s.short)}</div><div class="status">${k==='current'?'You are here':k}</div></div></button>`}).join('');
 document.querySelectorAll('.step').forEach(b=>b.onclick=()=>{sel=+b.dataset.i;draw();});
 if(sel===null)return document.getElementById('panel').innerHTML='<div class="panel"><p class="lead" style="margin:0">👆 Tap any stage to see what happens, why it matters, and what you will achieve.</p></div>';
 const s=S[sel];
 document.getElementById('panel').innerHTML=`<div class="panel" role="region" aria-live="polite"><h3>${s.icon} Stage ${s.n} · ${esc(s.title)}</h3>
  <p class="lead">${esc(s.what)}</p><div class="grid">
  <div class="cell"><b>Why it matters</b>${esc(s.why)}</div><div class="cell"><b>What you do</b>${esc(s.you)}</div>
  <div class="cell"><b>What the AI does</b>${esc(s.ai)}</div><div class="cell"><b>What you achieve</b>${esc(s.gain)}</div></div>
  <div class="nav"><button id="pv" ${sel===0?'disabled style="opacity:.4"':''}>← Previous</button><span class="hint">${sel+1} of ${S.length}</span>
  <button id="nx" ${sel===S.length-1?'disabled style="opacity:.4"':''}>Next →</button></div></div>`;
 document.getElementById('pv').onclick=()=>{if(sel>0){sel--;draw()}};document.getElementById('nx').onclick=()=>{if(sel<S.length-1){sel++;draw()}};
}
draw();
</script></body></html>"""


def roadmap_html(done=(), current=0, selected=None):
    """done: indexes (0-8) completed; current: index of active stage; selected: index whose panel is open (None = hint)."""
    keep = ("n", "icon", "title", "short", "what", "why", "you", "ai", "gain")
    data = [{k: s[k] for k in keep} for s in STAGES]
    return (TEMPLATE.replace("__STAGES__", json.dumps(data)).replace("__DONE__", json.dumps(sorted(done)))
            .replace("__CUR__", json.dumps(current)).replace("__SEL__", json.dumps(selected)))


def roadmap_height(mobile=False):
    return 1180 if mobile else 560