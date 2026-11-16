"""Hero section: headline + an animated 'explainer film' drawn in pure SVG/CSS (works inside st.markdown).
Colours follow thesis 4.13.2: blue/dark blue base, green accents, white text.

To use a real video instead, drop `ui/assets/intro.mp4` next to this file; the Home view will show it
with st.video in place of the animation.
"""
FILM = """
<div class="film" aria-label="Animation: a mind forms an argument, then debates">
 <style>
 .film{position:relative;border-radius:26px;overflow:hidden;aspect-ratio:16/10;min-height:260px;background:
   radial-gradient(circle at 30% 30%,#1d5fd1 0%,#0b2a5b 58%,#071a3a 100%);box-shadow:0 20px 50px rgba(11,42,91,.35)}
 .film svg{position:absolute;inset:0;width:100%;height:100%}
 .film .nd{fill:#9fc2ff;animation:tw 2.4s ease-in-out infinite}.film .nd:nth-child(2n){animation-delay:.6s;fill:#7ee0ad}
 .film .nd:nth-child(3n){animation-delay:1.2s;fill:#ffffff}
 @keyframes tw{0%,100%{opacity:.25;transform:scale(.8)}50%{opacity:1;transform:scale(1.25)}}
 .film .ln{stroke:rgba(255,255,255,.28);stroke-width:1.2;stroke-dasharray:6 6;animation:dash 5s linear infinite}
 @keyframes dash{to{stroke-dashoffset:-60}}
 .film .brain{animation:breathe 3.6s ease-in-out infinite;transform-origin:50% 45%}
 @keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
 .film .card{position:absolute;padding:8px 14px;border-radius:12px;font-weight:700;font-size:clamp(.62rem,1.5vw,.82rem);color:#0b2a5b;
   opacity:0;animation:cardin 12s infinite}
 .film .c1{left:7%;top:16%;background:#cfe0fb;animation-delay:.5s}.film .c2{right:7%;top:30%;background:#e5f6ee;animation-delay:2s}
 .film .c3{left:12%;bottom:30%;background:#ffffff;animation-delay:3.5s}
 @keyframes cardin{0%{opacity:0;transform:translateY(14px) scale(.9)}6%,48%{opacity:1;transform:none}56%,100%{opacity:0;transform:translateY(-8px)}}
 .film .bub{position:absolute;bottom:16%;max-width:42%;padding:9px 13px;border-radius:16px;font-size:clamp(.6rem,1.4vw,.78rem);font-weight:600;opacity:0;animation:bub 12s infinite}
 .film .b1{left:6%;background:#cfe0fb;color:#0b2a5b;animation-delay:6.2s;border-bottom-left-radius:4px}
 .film .b2{right:6%;background:#e5f6ee;color:#157a4b;animation-delay:8.2s;border-bottom-right-radius:4px}
 @keyframes bub{0%{opacity:0;transform:translateY(10px)}5%,36%{opacity:1;transform:none}44%,100%{opacity:0}}
 .film .cap{position:absolute;left:0;right:0;bottom:12px;height:1.5em;text-align:center;color:#eaf1fe;font-weight:700;letter-spacing:.12em;font-size:clamp(.6rem,1.4vw,.8rem);text-transform:uppercase}
 .film .cap span{position:absolute;left:0;right:0;opacity:0;animation:cap 12s infinite}
 .film .cap span:nth-child(2){animation-delay:3s}.film .cap span:nth-child(3){animation-delay:6s}.film .cap span:nth-child(4){animation-delay:9s}
 @keyframes cap{0%{opacity:0}4%,22%{opacity:1}28%,100%{opacity:0}}
 .film .rec{position:absolute;top:12px;left:14px;font-size:.7rem;color:#fff;background:rgba(0,0,0,.35);padding:3px 10px;border-radius:99px}
 @media(prefers-reduced-motion:reduce){.film *{animation:none!important;opacity:1!important}}
 </style>
 <svg viewBox="0 0 400 250" preserveAspectRatio="xMidYMid meet">
  <g class="ln"><line x1="200" y1="110" x2="90" y2="60"/><line x1="200" y1="110" x2="320" y2="80"/><line x1="200" y1="110" x2="110" y2="185"/>
   <line x1="200" y1="110" x2="305" y2="180"/><line x1="90" y1="60" x2="110" y2="185"/><line x1="320" y1="80" x2="305" y2="180"/></g>
  <g class="brain"><path d="M200 55c-26-8-52 8-48 32-18 6-22 30-6 42-4 20 14 34 32 28 6 14 30 14 36 0 18 6 36-8 32-28 16-12 12-36-6-42 4-24-22-40-48-32z"
    fill="rgba(159,194,255,.22)" stroke="#9fc2ff" stroke-width="2.5" stroke-linejoin="round"/><path d="M200 60v100M170 90c10 6 20 6 30 0M230 90c-10 6-20 6-30 0M168 125c12 4 22 2 32-4M232 125c-12 4-22 2-32-4"
    fill="none" stroke="#cfe0fb" stroke-width="1.6" stroke-linecap="round"/></g>
  <circle class="nd" cx="90" cy="60" r="6"/><circle class="nd" cx="320" cy="80" r="6"/><circle class="nd" cx="110" cy="185" r="6"/>
  <circle class="nd" cx="305" cy="180" r="6"/><circle class="nd" cx="200" cy="110" r="4"/><circle class="nd" cx="60" cy="120" r="4"/><circle class="nd" cx="350" cy="140" r="4"/>
 </svg>
 <div class="rec">● Explainer</div>
 <div class="card c1">CLAIM · what you argue</div><div class="card c2">EVIDENCE · why it is true</div><div class="card c3">WARRANT · why it counts</div>
 <div class="bub b1">Voting should be compulsory, because…</div><div class="bub b2">But does that hold for every voter?</div>
 <div class="cap"><span>Think</span><span>Build an argument</span><span>Debate the AI</span><span>Find the gap · Grow</span></div>
</div>
"""


import base64
import os

ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def hero_photo_html():
    """If ui/assets/hero.jpg (or .png/.webp) exists, return it as an <img>; otherwise None."""
    for name in ("hero.jpg", "hero.jpeg", "hero.png", "hero.webp"):
        path = os.path.join(ASSETS, name)
        if os.path.exists(path):
            mime = "image/png" if name.endswith("png") else "image/webp" if name.endswith("webp") else "image/jpeg"
            data = base64.b64encode(open(path, "rb").read()).decode()
            return f'<img class="hero-photo" alt="Students debating" src="data:{mime};base64,{data}">'
    return None


def hero_art_html():
    """Right side of the hero: a real photo when provided, else the animated explainer."""
    return hero_photo_html() or FILM


HERO_TEXT = ('<span class="eyebrow">Learn to think. Learn to argue.</span>'
             '<h1>Train your mind to <em>argue</em> better.</h1>'
             '<p>Debate an AI opponent that finds the exact weak spot in your reasoning, whether it is evidence, logic or rebuttal, '
             'then trains you on it, level after level.</p>')
