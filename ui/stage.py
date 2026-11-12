"""Self-contained HTML/CSS/JS scenes for the Streamlit UI (rendered with streamlit.components.v1.html).

stage_html(...)  : 3D debate stage. Perspective camera, tilted wooden floor, two podiums, moving spotlights that aim at the
                   active speaker, a crowd that cheers (arms up, sparkles) according to `cheer`.
coin_html(...)   : realistic coin toss: thick 3D coin (stacked rim layers), parabolic toss, spinning, bounce, shadow, result.
No external assets or libraries: works offline and inside a sandboxed iframe.
"""
import html
import random

STAGE_CSS = """
*{box-sizing:border-box;margin:0}body{background:#0b0a14;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif}
.scene{position:relative;height:__H__px;perspective:900px;overflow:hidden;background:radial-gradient(ellipse at 50% 0%,#2a2250 0%,#120f26 55%,#07060f 100%)}
.curtain{position:absolute;top:0;bottom:0;width:16%;z-index:5;background:repeating-linear-gradient(90deg,#5b0f1e 0 14px,#8c1a2f 14px 26px,#6d1224 26px 40px);box-shadow:inset 0 0 40px #000}
.curtain.l{left:0;border-right:2px solid #c9a24a}.curtain.r{right:0;border-left:2px solid #c9a24a}
.banner{position:absolute;top:10px;left:50%;transform:translateX(-50%);z-index:9;background:linear-gradient(#2b2350,#171233);border:2px solid #c9a24a;color:#ffe9a8;
 padding:6px 18px;border-radius:30px;font-weight:700;font-size:14px;letter-spacing:.5px;max-width:62%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 0 18px #c9a24a66}
.world{position:absolute;inset:0;animation:sway 9s ease-in-out infinite alternate}
@keyframes sway{from{transform:rotateY(-2.2deg)}to{transform:rotateY(2.2deg)}}
.rig{position:absolute;top:44px;left:18%;right:18%;height:10px;background:linear-gradient(#555,#222);border-radius:5px;z-index:6;box-shadow:0 3px 8px #000}
.lamp{position:absolute;top:-6px;width:26px;height:20px;background:radial-gradient(circle at 50% 80%,#fff,#ffd66b 40%,#555 70%);border-radius:4px 4px 14px 14px;box-shadow:0 0 16px #ffd66b}
.beam{position:absolute;top:50px;width:0;height:0;z-index:4;transform-origin:50% 0;mix-blend-mode:screen;pointer-events:none;transition:opacity .6s}
.beam i{position:absolute;left:-90px;top:0;width:180px;height:__BEAMH__px;clip-path:polygon(44% 0,56% 0,100% 100%,0 100%);
 background:linear-gradient(180deg,rgba(255,236,160,.95),rgba(255,226,140,.35) 55%,rgba(255,226,140,.05));filter:blur(3px)}
.beam.on{opacity:1}.beam.off{opacity:.12}
.floor{position:absolute;left:-10%;right:-10%;bottom:70px;height:46%;transform-origin:50% 100%;transform:perspective(700px) rotateX(62deg);
 background:repeating-linear-gradient(90deg,#6b4423 0 38px,#7c5230 38px 40px),linear-gradient(#8a5a33,#4b2d15);background-blend-mode:multiply;border-top:3px solid #c9a24a;box-shadow:0 -10px 40px #000 inset}
.pool{position:absolute;bottom:80px;width:230px;height:70px;border-radius:50%;background:radial-gradient(ellipse,rgba(255,226,140,.65),rgba(255,226,140,0) 70%);transition:opacity .6s;z-index:3}
.pool.on{opacity:1}.pool.off{opacity:.12}
.podium{position:absolute;bottom:96px;width:150px;z-index:7;text-align:center;transition:transform .5s}
.podium.active{transform:translateY(-8px) scale(1.06)}
.avatar{width:104px;height:120px;margin:0 auto;position:relative;animation:bob 2.4s ease-in-out infinite}
.podium.active .avatar{animation:talk .55s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-3px)}}@keyframes talk{50%{transform:translateY(-8px) rotate(-1.5deg)}}
.head{position:absolute;left:30px;top:0;width:44px;height:44px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#ffe0c2,#e2a779)}
.body{position:absolute;left:10px;top:46px;width:84px;height:74px;border-radius:40px 40px 6px 6px}
.hand{position:absolute;top:70px;width:14px;height:14px;border-radius:50%;background:#e2a779}
.pro .body{background:linear-gradient(#2ecc9a,#13795a)}.opp .body{background:linear-gradient(#ff6b6b,#a12a3a)}
.desk{height:62px;margin-top:-8px;border-radius:6px 6px 0 0;border:2px solid #c9a24a;color:#ffe9a8;font-weight:800;font-size:12px;
 display:flex;flex-direction:column;justify-content:center;gap:2px;box-shadow:0 12px 20px #000;background:linear-gradient(#3a2a1c,#1f150c)}
.desk small{font-weight:600;opacity:.85;font-size:10px;letter-spacing:.6px}
.tag{position:absolute;top:-24px;left:50%;transform:translateX(-50%);background:#ffd66b;color:#2b1d00;font-weight:900;font-size:11px;padding:3px 10px;border-radius:12px;white-space:nowrap;animation:pulse 1.1s infinite;z-index:9}
@keyframes pulse{50%{transform:translateX(-50%) scale(1.1)}}
.bubble{position:absolute;bottom:222px;left:50%;transform:translateX(-50%);width:215px;background:#fff;color:#1b1535;border-radius:14px;padding:8px 10px;font-size:11.5px;line-height:1.3;z-index:10;box-shadow:0 6px 18px #000a;animation:pop .35s ease-out}
.bubble:after{content:'';position:absolute;bottom:-9px;left:50%;margin-left:-9px;border:9px solid transparent;border-bottom:0;border-top-color:#fff}
@keyframes pop{from{transform:translateX(-50%) scale(.6);opacity:0}}
.crowd{position:absolute;left:0;right:0;bottom:0;height:90px;z-index:8;pointer-events:none}
.row{position:absolute;left:0;right:0;height:60px}
.p{position:absolute;bottom:0;width:30px;height:48px;animation:sit 2.6s ease-in-out infinite}
.p b{position:absolute;left:7px;top:0;width:16px;height:16px;border-radius:50%}
.p u{position:absolute;left:0;top:15px;width:30px;height:34px;border-radius:15px 15px 0 0}
.p s{position:absolute;top:13px;width:5px;height:0;border-radius:3px;background:inherit;transition:height .5s}
.p s.a{left:1px;transform:rotate(-18deg)}.p s.b{left:24px;transform:rotate(18deg)}
.cheer2 .p.up s,.cheer3 .p.up s{height:22px;top:-6px}
.cheer3 .p{animation:jump .5s ease-in-out infinite}
@keyframes sit{50%{transform:translateY(-2px)}}@keyframes jump{50%{transform:translateY(-12px)}}
.spark{position:absolute;width:6px;height:6px;border-radius:50%;background:#ffd66b;box-shadow:0 0 8px #ffd66b;opacity:0;z-index:12}
.cheer2 .spark,.cheer3 .spark{animation:fall 2.2s linear infinite}
@keyframes fall{0%{opacity:1;transform:translateY(-10px)}100%{opacity:0;transform:translateY(__H__px) rotate(360deg)}}
.cap{position:absolute;left:50%;bottom:6px;transform:translateX(-50%);z-index:13;background:#000b;color:#ffe9a8;font-size:12px;font-weight:700;padding:4px 14px;border-radius:20px;white-space:nowrap}
"""


def _esc(t, n=150):
    t = (t or "").strip()
    return html.escape(t if len(t) <= n else t[: n - 1].rstrip() + "…")


def _crowd(cheer, seed=7):
    rnd = random.Random(seed)
    skins = ["#e2a779", "#c98b5e", "#f1c9a5", "#8d5a3b", "#b57a52"]
    cloth = ["#2a2340", "#35294f", "#1f1b33", "#3b2c44", "#262046", "#30223a"]
    out = []
    for r, (bottom, scale, n) in enumerate(((22, 1.0, 17), (-6, 1.25, 13))):
        people = []
        for i in range(n):
            x = (i + 0.5) / n * 100 + rnd.uniform(-1.8, 1.8)
            up = "up" if rnd.random() < 0.7 else ""
            delay = rnd.uniform(0, 2)
            people.append(
                f'<div class="p {up}" style="left:{x:.1f}%;animation-delay:{delay:.2f}s;transform:scale({scale})">'
                f'<b style="background:{rnd.choice(skins)}"></b><u style="background:{rnd.choice(cloth)}"></u>'
                f'<s class="a" style="background:{rnd.choice(skins)}"></s><s class="b" style="background:{rnd.choice(skins)}"></s></div>')
        out.append(f'<div class="row" style="bottom:{bottom}px;z-index:{9 + r}">{"".join(people)}</div>')
    return "".join(out)


def stage_html(student_side="proponent", active="you", cheer=1, motion="", caption="", bubble_ai="", bubble_you="", height=430):
    """active: 'you' | 'ai' | None.  cheer: 1 (supportive) .. 3 (standing ovation)."""
    cheer = min(max(int(cheer), 1), 3)
    you_left = student_side == "proponent"  # proponent stands stage-left
    slots = {"left": ("you" if you_left else "ai"), "right": ("ai" if you_left else "you")}

    def podium(pos, who):
        pro = (who == "you") == (student_side == "proponent")
        role = "PROPONENT" if pro else "OPPONENT"
        who_txt = "YOU" if who == "you" else "AI OPPONENT"
        is_active = active == who
        tag = ('<div class="tag">YOUR TURN</div>' if who == "you" else '<div class="tag">SPEAKING…</div>') if is_active else ""
        b = bubble_you if who == "you" else bubble_ai
        bub = f'<div class="bubble">{_esc(b)}</div>' if b else ""
        x = "left:21%" if pos == "left" else "right:21%"
        return (f'<div class="podium {"active" if is_active else ""} {"pro" if pro else "opp"}" style="{x}">{tag}{bub}'
                f'<div class="avatar"><div class="head"></div><div class="body"></div></div>'
                f'<div class="desk">{who_txt}<small>{role}</small></div></div>')

    def beam(pos, who, offset):
        on = "on" if active == who else "off"
        cx = 24 if pos == "left" else 76
        angle = 0
        return (f'<div class="beam {on}" style="left:calc({cx + offset}% );transform:rotate({angle + (-offset * 1.2)}deg)"><i></i></div>')

    pools = "".join(
        f'<div class="pool {"on" if active == slots[p] else "off"}" style="{"left:6%" if p == "left" else "right:6%"}"></div>' for p in ("left", "right"))
    beams = beam("left", slots["left"], -2) + beam("left", slots["left"], 3) + beam("right", slots["right"], -3) + beam("right", slots["right"], 2)
    sparks = "".join(f'<div class="spark" style="left:{(i * 53) % 100}%;top:{20 + (i * 17) % 40}px;animation-delay:{(i % 7) * .3:.1f}s"></div>' for i in range(14))
    css = STAGE_CSS.replace("__H__", str(height)).replace("__BEAMH__", str(int(height * 0.62)))
    title = _esc(motion, 70) or "Debate Arena"
    cap = f'<div class="cap">{_esc(caption, 90)}</div>' if caption else ""
    return (f'<style>{css}</style><div class="scene cheer{cheer}"><div class="curtain l"></div><div class="curtain r"></div>'
            f'<div class="banner">🎙️ {title}</div><div class="world"><div class="rig">'
            f'<div class="lamp" style="left:20%"></div><div class="lamp" style="left:36%"></div><div class="lamp" style="right:36%"></div><div class="lamp" style="right:20%"></div></div>'
            f'{beams}<div class="floor"></div>{pools}{podium("left", slots["left"])}{podium("right", slots["right"])}</div>'
            f'<div class="crowd">{_crowd(cheer)}</div>{sparks}{cap}</div>')


COIN_HTML = """
<style>
*{box-sizing:border-box;margin:0}body{background:radial-gradient(ellipse at 50% 0%,#2a2250,#0b0a14 70%);font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}
#wrap{position:relative;height:__H__px;perspective:800px;display:flex;align-items:center;justify-content:center}
#coin{position:absolute;left:50%;top:50%;width:150px;height:150px;margin:-75px 0 0 -75px;transform-style:preserve-3d;will-change:transform}
#coin .layer,#coin .face{position:absolute;inset:0;border-radius:50%}
#coin .layer{background:radial-gradient(circle at 50% 50%,#b8861b,#8a5f0e);border:2px solid #7a5208}
#coin .face{backface-visibility:hidden;display:flex;flex-direction:column;align-items:center;justify-content:center;
 background:radial-gradient(circle at 32% 28%,#fff4b8,#f2c230 38%,#c18a14 72%,#9a6a0c);border:6px double #8a5f0e;color:#6b4506;font-weight:900;text-shadow:0 1px 0 #ffe9a0;box-shadow:inset 0 0 18px #7a520888}
#coin .face .big{font-size:46px;line-height:1}#coin .face .sm{font-size:13px;letter-spacing:3px;margin-top:4px}
#shadow{position:absolute;left:50%;bottom:42px;width:140px;height:26px;margin-left:-70px;border-radius:50%;background:radial-gradient(ellipse,#000d,#0000 70%)}
#msg{position:absolute;left:0;right:0;bottom:8px;text-align:center;color:#ffe9a8;font-weight:800;font-size:19px;text-shadow:0 2px 8px #000;min-height:28px}
#msg.win{animation:glow 1.1s ease-in-out infinite alternate}@keyframes glow{to{text-shadow:0 0 18px #ffd66b,0 2px 8px #000;transform:scale(1.04)}}
.hint{position:absolute;top:10px;left:0;right:0;text-align:center;color:#b9b3d9;font-size:13px}
</style>
<div id="wrap"><div class="hint">__HINT__</div><div id="shadow"></div><div id="coin"></div><div id="msg"></div></div>
<script>
(function(){
 var RESULT = __RESULT__, H = __H__, coin = document.getElementById('coin'), shadow = document.getElementById('shadow'), msg = document.getElementById('msg');
 var html = '';
 for (var i=-7;i<=7;i++) html += '<div class="layer" style="transform:translateZ('+i+'px)"></div>';
 html += '<div class="face" style="transform:translateZ(8px)"><div class="big">🗣️</div><div class="sm">HEADS</div></div>';
 html += '<div class="face" style="transform:rotateX(180deg) translateZ(8px)"><div class="big">⚖️</div><div class="sm">TAILS</div></div>';
 coin.innerHTML = html;
 var restY = H/2 - 75;
 function place(y, rx, ry, rz, s){ coin.style.transform = 'translateY('+y+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ('+rz+'deg) scale('+s+')'; }
 if (!RESULT) {                                  // idle: coin hovers and slowly turns
   var t0 = performance.now();
   (function idle(now){ var t=(now-t0)/1000; place(Math.sin(t*2)*6, 12, t*40, 0, 1); shadow.style.opacity = .7 - Math.sin(t*2)*.1; requestAnimationFrame(idle); })(t0);
   return;
 }
 var up = RESULT === 'heads' ? 0 : 180, spins = 5 + Math.floor(Math.random()*3), DUR = 2300, peak = H*0.36, t0 = performance.now();
 function ease(x){ return 1 - Math.pow(1-x, 2.2); }
 function frame(now){
   var p = Math.min((now - t0)/DUR, 1);
   var air = Math.min(p/0.78, 1);                 // flight phase
   var y = -peak * 4*air*(1-air);                 // parabola: up and down
   var rx = (spins*360 + up) * ease(air);         // spin about the horizontal axis, decelerating
   var wob = Math.sin(air*Math.PI)*14;            // slight off-axis wobble in the air
   var s = 1 + 0.35*(4*air*(1-air));              // gets closer to the camera at the top
   if (p > 0.78) {                                // landing: damped bounces
     var q = (p-0.78)/0.22, b = Math.abs(Math.sin(q*Math.PI*2.5))*Math.pow(1-q,2)*28;
     y = -b; s = 1; wob = 0; rx = spins*360 + up;
   }
   place(y, rx, 0, wob, s);
   var lift = Math.abs(y)/peak;
   shadow.style.transform = 'scale('+(1 - lift*0.6)+')'; shadow.style.opacity = 0.75 - lift*0.5;
   if (p < 1) { requestAnimationFrame(frame); }
   else {
     place(0, spins*360 + up, 0, 0, 1);
     msg.className = 'win';
     msg.textContent = RESULT === 'heads' ? 'HEADS: you are the PROPONENT' : 'TAILS: you are the OPPONENT';
   }
 }
 place(0, 0, 0, 0, 1); requestAnimationFrame(frame);
})();
</script>
"""


def coin_html(result=None, height=330):
    """result: None (idle hovering coin) | 'heads' | 'tails' (animate the toss and land on that face).
    The outcome is decided in Python (app.game.toss, OS randomness); the animation only displays it."""
    if result not in (None, "heads", "tails"):
        raise ValueError("result must be None, 'heads' or 'tails'")
    hint = "Press the button below to flip the coin" if result is None else "Heads = proponent · Tails = opponent"
    return (COIN_HTML.replace("__H__", str(height)).replace("__RESULT__", "null" if result is None else f'"{result}"').replace("__HINT__", hint))
