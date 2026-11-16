"""Realistic debate-hall visuals for Debate Arena (pure HTML/CSS/SVG, no external JS).

stage_html(side, active, cheer, topic, caption, bubble_ai="", height=380) -> full HTML document
coin_html(face)                                                          -> full HTML document
"""
import base64
import html
import os
import random

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@500;700&display=swap" rel="stylesheet">'


def _fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace(f"__{k}__", str(v))
    return tpl


def _person(uid, suit, shirt, tie, skin, hair):
    return f"""<svg class="ppl" viewBox="0 0 120 150" width="120" height="150" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="{uid}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{suit[0]}"/><stop offset="1" stop-color="{suit[1]}"/></linearGradient>
<radialGradient id="{uid}f" cx=".4" cy=".35" r=".85"><stop offset="0" stop-color="{skin[0]}"/><stop offset="1" stop-color="{skin[1]}"/></radialGradient>
</defs>
<path d="M4 150 C4 113 32 100 60 100 C88 100 116 113 116 150Z" fill="url(#{uid}s)"/>
<path d="M42 100 L60 130 L74 100Z" fill="{shirt}"/>
<path d="M42 100 L60 130 L46 150 L24 150 C24 125 32 108 42 100Z" fill="rgba(0,0,0,.28)"/>
<path d="M78 100 L60 130 L74 150 L96 150 C96 125 88 108 78 100Z" fill="rgba(0,0,0,.2)"/>
<path d="M56.5 112 L63.5 112 L66 142 L60 148 L54 142Z" fill="{tie}"/>
<rect x="51" y="80" width="18" height="24" rx="7" fill="url(#{uid}f)"/>
<rect x="51" y="92" width="18" height="10" fill="rgba(0,0,0,.18)"/>
<ellipse cx="60" cy="62" rx="21" ry="26" fill="url(#{uid}f)"/>
<ellipse cx="38.6" cy="64" rx="3.4" ry="6" fill="{skin[1]}"/><ellipse cx="81.4" cy="64" rx="3.4" ry="6" fill="{skin[1]}"/>
<path d="M38 58 C33 28 87 28 82 58 C78 46 66 41 60 41 C54 41 42 46 38 58Z" fill="{hair}"/>
<circle cx="51" cy="63" r="1.9" fill="#2a1d14"/><circle cx="69" cy="63" r="1.9" fill="#2a1d14"/>
<path d="M46 57 Q51 54.5 56 57M64 57 Q69 54.5 74 57" stroke="{hair}" stroke-width="2" fill="none" stroke-linecap="round"/>
<path d="M60 64 L58.5 71 Q60 72.5 61.5 71Z" fill="rgba(0,0,0,.12)"/>
<path class="mouth" d="M53 76 Q60 80.5 67 76" stroke="#7a4a3a" fill="none" stroke-width="1.7" stroke-linecap="round"/>
</svg>"""


def _audience(cheer):
    rnd = random.Random(11)
    rows = [(44, 0.78, "#2c2836", "#463f57"), (70, 0.95, "#1c1924", "#322d3e"), (100, 1.15, "#0f0d14", "#241f2d")]
    parts = []
    for y, sc, body, rim in rows:
        x = rnd.uniform(0, 26)
        while x < 1020:
            r = 9.5 * sc
            dy = rnd.uniform(-3, 3)
            delay = rnd.uniform(0, 1.6)
            parts.append(
                f'<g class="p" style="animation-delay:{delay:.2f}s"><ellipse cx="{x:.1f}" cy="{y + r * 2.1 + dy:.1f}" rx="{r * 1.9:.1f}" ry="{r * 1.6:.1f}" fill="{body}"/>'
                f'<circle cx="{x:.1f}" cy="{y + dy:.1f}" r="{r:.1f}" fill="{body}" stroke="{rim}" stroke-width=".9"/></g>')
            x += rnd.uniform(20, 31) * sc
    return f'<svg viewBox="0 0 1000 130" preserveAspectRatio="xMidYMax slice" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


STAGE_TPL = """<!doctype html><html><head><meta charset="utf-8">__FONTS__
<style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif}
.stage{position:relative;width:100%;height:__H__px;overflow:hidden;border-radius:18px;border:1px solid rgba(212,175,106,.35);
 box-shadow:0 18px 50px rgba(0,0,0,.55), inset 0 0 0 1px rgba(255,255,255,.04);background:#0b0910}
.wall{position:absolute;left:0;right:0;top:0;height:62%;
 background:linear-gradient(180deg,rgba(0,0,0,.55),rgba(0,0,0,0) 45%,rgba(0,0,0,.35)),
 repeating-linear-gradient(90deg,#3a2616 0 56px,#1f130b 56px 58px,#432c19 58px 114px,#1f130b 114px 116px)}
.wall:after{content:"";position:absolute;left:0;right:0;bottom:0;height:22%;background:linear-gradient(#1b110a,#2a1a0f);border-top:3px solid #6b4a2a;box-shadow:0 -2px 8px rgba(0,0,0,.5)}
.rail{position:absolute;top:0;left:0;right:0;height:9px;background:linear-gradient(#050408,#1b1823);z-index:6}
.floor{position:absolute;left:0;right:0;top:62%;bottom:0;
 background:linear-gradient(180deg,#120c08 0%,#2b1f16 40%,#120c08 100%),
 repeating-linear-gradient(90deg,rgba(255,255,255,.04) 0 2px,transparent 2px 64px)}
.floor:before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(180deg,rgba(255,255,255,.035) 0 1px,transparent 1px 18px)}
.banner{position:absolute;top:20px;left:50%;transform:translateX(-50%);max-width:50%;padding:7px 24px 9px;text-align:center;z-index:5;
 background:linear-gradient(#64182a,#3a0d18);border:1px solid #d4af6a;border-radius:4px;box-shadow:0 8px 20px rgba(0,0,0,.55), inset 0 0 0 3px rgba(0,0,0,.25)}
.banner small{display:block;font-size:9px;letter-spacing:3px;color:#e7c982;font-weight:700}
.banner b{display:block;font-family:'Playfair Display',Georgia,serif;font-weight:600;font-size:14px;line-height:1.25;color:#fbf1d6;margin-top:2px}
.live{position:absolute;top:18px;left:16px;z-index:7;display:flex;gap:8px;align-items:center;font-size:10px;letter-spacing:2px;font-weight:700;color:#f3ecdc;
 background:rgba(10,8,14,.7);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:4px 10px}
.live i{width:8px;height:8px;border-radius:50%;background:#e5484d;box-shadow:0 0 8px #e5484d;animation:blink 1.4s infinite}
.spot{position:absolute;top:8px;width:340px;height:300px;clip-path:polygon(43% 0,57% 0,100% 100%,0 100%);z-index:2;pointer-events:none;
 background:linear-gradient(rgba(255,243,210,.62),rgba(255,243,210,.04));mix-blend-mode:screen;opacity:.14;transition:opacity .6s}
.spot.on{opacity:.9;animation:flick 5s infinite}
.lamp{position:absolute;top:2px;width:26px;height:12px;border-radius:0 0 14px 14px;background:linear-gradient(#26222e,#0c0a10);z-index:7;border-bottom:3px solid #4c4658}
.lamp.on{border-bottom-color:#fff1c4;box-shadow:0 6px 14px 2px rgba(255,236,170,.65)}
.pool{position:absolute;bottom:58px;width:250px;height:44px;border-radius:50%;z-index:1;opacity:.12;transition:opacity .6s;
 background:radial-gradient(ellipse at center,rgba(255,236,180,.8),rgba(255,236,180,0) 70%);transform:translateX(-50%)}
.pool.on{opacity:.95}
.spk{position:absolute;bottom:78px;width:150px;transform:translateX(-50%);z-index:3}
.avatar{height:150px;display:flex;justify-content:center;filter:brightness(.62) saturate(.85);transition:filter .6s}
.spk.on .avatar{filter:brightness(1.08) saturate(1.05) drop-shadow(0 0 14px rgba(255,235,180,.35));animation:sway 2.8s ease-in-out infinite}
.podium{position:relative;height:92px;margin-top:-34px;border-radius:5px 5px 2px 2px;z-index:2;
 background:linear-gradient(90deg,#2d1a0e,#563520 18%,#7a4e2c 50%,#563520 82%,#2d1a0e);box-shadow:0 14px 22px rgba(0,0,0,.6)}
.podium:before{content:"";position:absolute;left:-8px;right:-8px;top:-9px;height:13px;border-radius:4px;background:linear-gradient(#a5703f,#6b4427 60%,#4a2d18);box-shadow:0 3px 6px rgba(0,0,0,.5)}
.podium:after{content:"";position:absolute;left:12px;right:12px;top:14px;bottom:8px;border:2px solid rgba(0,0,0,.32);border-radius:3px;
 background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(0,0,0,.18))}
.plaque{position:absolute;left:50%;top:30px;transform:translateX(-50%);z-index:3;min-width:96px;text-align:center;padding:3px 10px 4px;border-radius:3px;
 background:linear-gradient(#e8cc86,#a87f33);box-shadow:0 2px 4px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.55)}
.plaque b{display:block;font-size:10px;letter-spacing:2px;color:#3a2606}.plaque small{display:block;font-size:8px;letter-spacing:1.5px;font-weight:700;color:#fff;margin-top:1px;border-radius:2px;padding:1px 4px}
.plaque small.for{background:#2e8b6a}.plaque small.against{background:#a63d40}
.mic{position:absolute;left:50%;top:-52px;transform:translateX(-50%);z-index:4}
.tag{position:absolute;left:50%;top:-8px;transform:translate(-50%,-100%);font-size:9px;font-weight:700;letter-spacing:2px;color:#fff;background:#d6393d;padding:2px 8px;border-radius:10px;opacity:0;transition:opacity .4s;z-index:5;white-space:nowrap}
.spk.on .tag{opacity:1}
.spk.on .mouth{animation:talk .32s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center}
.bubble{position:absolute;left:38%;top:86px;width:27%;max-height:112px;overflow:hidden;z-index:6;padding:9px 12px;border-radius:12px;font-size:11.5px;line-height:1.35;color:#1b1722;
 background:linear-gradient(#fffaf0,#efe6d2);box-shadow:0 10px 24px rgba(0,0,0,.5)}
.bubble:after{content:"";position:absolute;right:-9px;top:22px;border:9px solid transparent;border-left-color:#efe6d2;border-right:0}
.bubble em{display:block;font-style:normal;font-size:8.5px;font-weight:700;letter-spacing:2px;color:#9a6b1c;margin-bottom:2px}
.cap{position:absolute;left:50%;bottom:86px;transform:translateX(-50%);z-index:6;width:min(44%,420px);text-align:center;padding:7px 14px;font-size:12px;color:#f6efdc;
 background:rgba(12,10,17,.78);border:1px solid rgba(212,175,106,.45);border-left:4px solid #d4af6a;border-radius:6px;backdrop-filter:blur(4px)}
.crowd{position:absolute;left:0;right:0;bottom:0;height:84px;z-index:4;pointer-events:none}
.crowd:before{content:"";position:absolute;inset:-26px 0 0;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(5,4,8,.9));z-index:-1}
.crowd .p{animation:bob __DUR__s ease-in-out infinite;transform-box:fill-box}
.vig{position:absolute;inset:0;z-index:8;pointer-events:none;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 52%,rgba(0,0,0,.6) 100%)}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-__AMP__px)}}
@keyframes sway{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
@keyframes talk{from{transform:scaleY(.4)}to{transform:scaleY(1.8)}}
@keyframes blink{50%{opacity:.25}}
@keyframes flick{0%,100%{opacity:.9}45%{opacity:.78}50%{opacity:.92}}
</style></head><body>
<div class="stage">
 <div class="wall"></div><div class="floor"></div><div class="rail"></div>
 <div class="lamp __YOUON__" style="left:calc(24% - 13px)"></div><div class="lamp __AION__" style="left:calc(76% - 13px)"></div>
 <div class="spot __YOUON__" style="left:calc(24% - 170px)"></div><div class="spot __AION__" style="left:calc(76% - 170px)"></div>
 <div class="pool __YOUON__" style="left:24%"></div><div class="pool __AION__" style="left:76%"></div>
 <div class="live"><i></i>LIVE DEBATE</div>
 <div class="banner"><small>THE MOTION</small><b>__TOPIC__</b></div>
 __BUBBLE__
 <div class="spk __YOUON__" style="left:24%">
  <div class="tag">SPEAKING</div><div class="avatar">__YOU__</div>
  <div class="podium"><div class="mic">__MIC__</div><div class="plaque"><b>YOU</b><small class="__YOUCLS__">__YOUTAG__</small></div></div>
 </div>
 <div class="spk __AION__" style="left:76%">
  <div class="tag">SPEAKING</div><div class="avatar">__AI__</div>
  <div class="podium"><div class="mic">__MIC__</div><div class="plaque"><b>OPPONENT</b><small class="__AICLS__">__AITAG__</small></div></div>
 </div>
 <div class="cap">__CAPTION__</div>
 <div class="crowd">__CROWD__</div>
 <div class="vig"></div>
</div></body></html>"""

MIC = """<svg width="26" height="52" viewBox="0 0 26 52"><path d="M13 52 C13 30 13 26 13 18" stroke="#2a2a30" stroke-width="2.4" fill="none"/>
<rect x="8" y="2" width="10" height="18" rx="5" fill="url(#mg)" stroke="#111" stroke-width="1"/><defs><linearGradient id="mg" x1="0" x2="1"><stop offset="0" stop-color="#555"/><stop offset=".5" stop-color="#bbb"/><stop offset="1" stop-color="#444"/></linearGradient></defs></svg>"""

ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def _hall_photo():
    """Data URI of ui/assets/debate_hall.(jpg|png|webp) if you provide a real photo, else None."""
    for name, mime in (("debate_hall.jpg", "image/jpeg"), ("debate_hall.jpeg", "image/jpeg"),
                       ("debate_hall.png", "image/png"), ("debate_hall.webp", "image/webp")):
        path = os.path.join(ASSETS, name)
        if os.path.exists(path):
            return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()
    return None


PHOTO_TPL = """<!doctype html><html><head><meta charset="utf-8">__FONTS__
<style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif}
.stage{position:relative;width:100%;height:__H__px;overflow:hidden;border-radius:18px;border:1px solid #e2e8f3;background:#0b2a5b url(__IMG__) center/cover no-repeat;box-shadow:0 12px 34px rgba(11,42,91,.25)}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(7,26,58,.6),rgba(7,26,58,0) 40%,rgba(7,26,58,.1) 60%,rgba(7,26,58,.78))}
.live{position:absolute;top:16px;left:16px;display:flex;gap:8px;align-items:center;font-size:10px;letter-spacing:2px;font-weight:700;color:#fff;background:rgba(7,26,58,.7);border:1px solid rgba(255,255,255,.2);border-radius:20px;padding:4px 10px}
.live i{width:8px;height:8px;border-radius:50%;background:#e5484d;animation:blink 1.4s infinite}
.banner{position:absolute;top:14px;left:50%;transform:translateX(-50%);max-width:58%;padding:8px 22px 10px;text-align:center;background:rgba(11,42,91,.92);border:1px solid rgba(255,255,255,.25);border-radius:10px;color:#fff}
.banner small{display:block;font-size:9px;letter-spacing:3px;color:#9fc2ff;font-weight:700}
.banner b{display:block;font-family:'Playfair Display',Georgia,serif;font-weight:600;font-size:15px;line-height:1.25;margin-top:2px}
.spk{position:absolute;bottom:16px;width:min(240px,40%);padding:10px 14px;border-radius:14px;background:rgba(255,255,255,.95);border:2px solid transparent;box-shadow:0 8px 22px rgba(0,0,0,.35);opacity:.86}
.spk.you{left:3%}.spk.ai{right:3%}
.spk.on{opacity:1;border-color:#1d5fd1;box-shadow:0 0 0 4px rgba(29,95,209,.35),0 8px 22px rgba(0,0,0,.35)}
.spk b{display:block;font-size:12px;letter-spacing:2px;color:#0b2a5b}
.spk small{display:inline-block;margin-top:4px;font-size:10px;letter-spacing:1.5px;font-weight:700;color:#fff;border-radius:999px;padding:2px 10px}
.spk small.for{background:#1f9d63}.spk small.against{background:#1d5fd1}
.spk em{float:right;font-style:normal;font-size:9px;letter-spacing:2px;font-weight:700;color:#1d5fd1;opacity:0}
.spk.on em{opacity:1}
.bubble{position:absolute;right:3%;bottom:96px;width:min(36%,320px);max-height:110px;overflow:hidden;padding:9px 12px;border-radius:12px;font-size:11.5px;line-height:1.35;color:#0b1220;background:#fff;box-shadow:0 10px 24px rgba(0,0,0,.4)}
.bubble em{display:block;font-style:normal;font-size:8.5px;font-weight:700;letter-spacing:2px;color:#1d5fd1;margin-bottom:2px}
.cap{position:absolute;left:50%;bottom:20px;transform:translateX(-50%);max-width:30%;text-align:center;padding:6px 12px;font-size:11.5px;color:#fff;background:rgba(7,26,58,.75);border-radius:8px}
@keyframes blink{50%{opacity:.25}}
</style></head><body><div class="stage"><div class="shade"></div>
<div class="live"><i></i>LIVE DEBATE</div>
<div class="banner"><small>THE MOTION</small><b>__TOPIC__</b></div>
__BUBBLE__
<div class="spk you __YOUON__"><em>SPEAKING</em><b>YOU</b><small class="__YOUCLS__">__YOUTAG__</small></div>
<div class="spk ai __AION__"><em>SPEAKING</em><b>OPPONENT</b><small class="__AICLS__">__AITAG__</small></div>
<div class="cap">__CAPTION__</div>
</div></body></html>"""


def stage_html(side, active, cheer, topic, caption, bubble_ai="", height=380):
    cheer = max(1, min(int(cheer or 1), 5))
    you_for = (side == "proponent")
    you_on = "on" if active == "you" else ""
    ai_on = "on" if active == "ai" else ""
    topic = html.escape(topic if len(topic) < 150 else topic[:147] + "...")
    bubble = ""
    if bubble_ai:
        txt = bubble_ai.strip()
        txt = txt if len(txt) <= 170 else txt[:167].rsplit(" ", 1)[0] + "..."
        bubble = f'<div class="bubble"><em>OPPONENT</em>{html.escape(txt)}</div>'
    img = _hall_photo()
    if img:
        return _fill(PHOTO_TPL, FONTS=FONTS, H=height, IMG=img, TOPIC=topic, BUBBLE=bubble, CAPTION=html.escape(caption or ""),
                     YOUON=you_on, AION=ai_on, YOUTAG="FOR" if you_for else "AGAINST", AITAG="AGAINST" if you_for else "FOR",
                     YOUCLS="for" if you_for else "against", AICLS="against" if you_for else "for")
    you = _person("y", ("#1c2b4a", "#0e1730"), "#f4f1ea", "#a63d40", ("#e8c29d", "#c18f66"), "#3a2a1c")
    ai = _person("a", ("#2c2c33", "#16161b"), "#e9e6df", "#2e6f9e", ("#c99872", "#9a6a47"), "#15110e")
    return _fill(STAGE_TPL, FONTS=FONTS, H=height, TOPIC=topic, BUBBLE=bubble, CAPTION=html.escape(caption or ""),
                 YOU=you, AI=ai, MIC=MIC, YOUON=you_on, AION=ai_on,
                 YOUTAG="FOR" if you_for else "AGAINST", AITAG="AGAINST" if you_for else "FOR",
                 YOUCLS="for" if you_for else "against", AICLS="against" if you_for else "for",
                 CROWD=_audience(cheer), AMP=f"{0.6 + cheer * 1.7:.1f}", DUR=f"{2.5 - cheer * 0.32:.2f}")


COIN_TPL = """<!doctype html><html><head><meta charset="utf-8">__FONTS__
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:transparent;font-family:Inter,system-ui,sans-serif;overflow:hidden}
.room{position:relative;height:100%;border-radius:18px;border:1px solid rgba(212,175,106,.3);
 background:radial-gradient(ellipse at 50% 0%,rgba(255,236,190,.22),rgba(0,0,0,0) 55%),radial-gradient(ellipse at 50% 100%,#0d3b2c 0%,#07140f 70%),#07110d}
.table{position:absolute;left:50%;bottom:34px;width:340px;height:64px;transform:translateX(-50%);border-radius:50%;background:radial-gradient(ellipse,#14573f,#0a2b1f 70%);box-shadow:0 0 0 3px #4a2e18, 0 14px 30px rgba(0,0,0,.6)}
.scene{position:absolute;left:50%;top:34px;width:150px;height:150px;transform:translateX(-50%);perspective:900px}
.toss{width:150px;height:150px;animation:__TOSS__}
.coin{position:relative;width:150px;height:150px;transform-style:preserve-3d;animation:__SPIN__}
.face,.edge{position:absolute;inset:0;border-radius:50%}
.edge{background:repeating-conic-gradient(#b48a37 0 3deg,#6f4f14 3deg 6deg)}
.face{backface-visibility:hidden;overflow:hidden;
 background:radial-gradient(circle at 30% 26%,#fff6cf 0%,#ecca74 20%,#c99b36 52%,#8c6619 100%);
 box-shadow:inset 0 0 0 5px rgba(120,80,10,.45), inset 0 0 22px rgba(70,40,0,.55)}
.face:before{content:"";position:absolute;inset:13px;border-radius:50%;border:2px dashed rgba(100,65,5,.55)}
.face:after{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 34%,rgba(255,255,255,.5) 48%,transparent 62%);background-size:260% 100%;animation:sheen 3.2s linear infinite}
.front{transform:translateZ(7px)}.back{transform:rotateX(180deg) translateZ(7px)}
.in{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2;color:#7e5714;
 text-shadow:0 1px 0 rgba(255,240,190,.75),0 -1px 0 rgba(80,50,5,.55)}
.in .g{font-family:'Playfair Display',Georgia,serif;font-size:50px;line-height:1;font-weight:700}
.in .w{font-size:12px;letter-spacing:4px;font-weight:700;margin-top:4px}.in .s{font-size:8px;letter-spacing:2px;font-weight:700;margin-top:3px;opacity:.9}
.shadow{position:absolute;left:50%;top:196px;width:120px;height:18px;transform:translateX(-50%);border-radius:50%;background:radial-gradient(rgba(0,0,0,.65),transparent 70%);animation:__SHADOW__}
.result{position:absolute;left:0;right:0;bottom:6px;text-align:center;color:#f6efdc;font-family:'Playfair Display',Georgia,serif;font-size:18px;letter-spacing:1px;opacity:__RESOP__;animation:__RES__}
.result span{display:block;font-family:Inter,sans-serif;font-size:11px;letter-spacing:2px;color:#e7c982;margin-top:2px}
@keyframes idle{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
@keyframes idlespin{0%,100%{transform:rotateX(-14deg) rotateY(-24deg)}50%{transform:rotateX(-8deg) rotateY(24deg)}}
@keyframes toss{0%{transform:translateY(0)}38%{transform:translateY(-120px)}100%{transform:translateY(0)}}
@keyframes spin{0%{transform:rotateX(0)}100%{transform:rotateX(__DEG__deg)}}
@keyframes shad{0%{transform:translateX(-50%) scale(1)}38%{transform:translateX(-50%) scale(.55);opacity:.5}100%{transform:translateX(-50%) scale(1)}}
@keyframes sheen{from{background-position:140% 0}to{background-position:-60% 0}}
@keyframes show{to{opacity:1}}
</style></head><body><div class="room">
<div class="table"></div>
<div class="scene"><div class="toss"><div class="coin">
__EDGES__
<div class="face front"><div class="in"><div class="g">&#9733;</div><div class="w">HEADS</div><div class="s">FOR THE MOTION</div></div></div>
<div class="face back"><div class="in"><div class="g">&#9878;</div><div class="w">TAILS</div><div class="s">AGAINST THE MOTION</div></div></div>
</div></div></div>
<div class="shadow"></div>
<div class="result">__RESULT__</div>
</div></body></html>"""


def coin_html(face=None):
    edges = "".join(f'<div class="edge" style="transform:translateZ({z}px)"></div>' for z in range(-6, 7, 2))
    if face is None:
        vals = dict(TOSS="idle 2.6s ease-in-out infinite", SPIN="idlespin 5s ease-in-out infinite",
                    SHADOW="none", DEG=0, RESULT="", RESOP=0, RES="none")
    else:
        heads = face == "heads"
        vals = dict(TOSS="toss 2.2s cubic-bezier(.3,.6,.4,1) forwards", SPIN=f"spin 2.2s cubic-bezier(.2,.7,.3,1) forwards",
                    SHADOW="shad 2.2s cubic-bezier(.3,.6,.4,1) forwards", DEG=1800 if heads else 1980,
                    RESULT=f'{"HEADS" if heads else "TAILS"}<span>{"YOU ARGUE FOR THE MOTION" if heads else "YOU ARGUE AGAINST THE MOTION"}</span>',
                    RESOP=0, RES="show .6s ease 2.3s forwards")
    return _fill(COIN_TPL, FONTS=FONTS, EDGES=edges, **vals)