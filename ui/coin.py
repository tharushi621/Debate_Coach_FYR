"""3D coin toss (iframe). result None = idle coin; 'heads'|'tails' = play the toss and land on it.
Colours follow thesis 4.13.2: blue and dark blue (no gold), white lettering."""
def coin_html(result=None, height=300):
    land = {"heads": 0, "tails": 180}.get(result)
    spins = 5 * 360 + (land or 0)
    anim = f"toss 2.4s cubic-bezier(.2,.7,.3,1) forwards" if result else "idle 3s ease-in-out infinite"
    return f"""<!doctype html><meta charset=utf-8><style>
body{{margin:0;height:{height}px;display:grid;place-items:center;background:transparent;font-family:Inter,system-ui,sans-serif;overflow:hidden}}
.stage{{perspective:900px;height:{height-30}px;display:grid;place-items:center}}
.shadow{{position:absolute;bottom:18px;width:90px;height:16px;border-radius:50%;background:rgba(11,42,91,.22);filter:blur(6px);animation:{'sh 2.4s forwards' if result else 'none'}}}
.coin{{width:130px;height:130px;position:relative;transform-style:preserve-3d;animation:{anim}}}
.f{{position:absolute;inset:0;border-radius:50%;display:grid;place-items:center;backface-visibility:hidden;font-weight:800;color:#fff;
 background:radial-gradient(circle at 32% 28%,#9fc2ff,#1d5fd1 45%,#0b2a5b 100%);border:6px solid #154aa8;box-shadow:inset 0 0 0 5px rgba(255,255,255,.28),0 8px 20px rgba(11,42,91,.35);text-align:center;line-height:1.1}}
.f span{{display:block;font-size:22px;letter-spacing:.04em}}.f small{{font-size:12px;letter-spacing:.14em}}
.t{{transform:rotateX(180deg)}}
@keyframes toss{{0%{{transform:translateY(0) rotateX(0)}}45%{{transform:translateY(-120px) rotateX({spins*0.6}deg)}}100%{{transform:translateY(0) rotateX({spins}deg)}}}}
@keyframes idle{{0%,100%{{transform:translateY(0) rotateY(-14deg)}}50%{{transform:translateY(-10px) rotateY(14deg)}}}}
@keyframes sh{{0%{{transform:scale(1)}}45%{{transform:scale(.5);opacity:.5}}100%{{transform:scale(1)}}}}
</style><div class=stage><div class=shadow></div><div class=coin>
<div class=f><div><span>FOR</span><small>HEADS</small></div></div><div class="f t"><div><span>AGAINST</span><small>TAILS</small></div></div></div></div>"""
