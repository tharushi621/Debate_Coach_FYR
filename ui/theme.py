"""Design system: mint→lavender glass look (reference image 2) + teal score cards (reference image 1)."""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --ink:#16302f; --ink2:#4a6462; --muted:#7a8f8d; --teal:#0f8b7d; --teal2:#7fd6c2; --mint:#bfeadf;
  --lav:#d3c6f0; --lav2:#b7a5e6; --sun:#f8e3a1; --card:rgba(255,255,255,.62); --line:rgba(22,48,47,.09);
  --shadow:0 10px 30px rgba(60,90,100,.12); --r:22px; --dark:#1d2423;
}
html,body,[class*="css"],.stApp{font-family:'Inter',system-ui,sans-serif;color:var(--ink)}
.stApp{background:
  radial-gradient(900px 500px at 8% 0%,#c9f1e3 0%,transparent 60%),
  radial-gradient(900px 600px at 100% 10%,#d9cdf4 0%,transparent 60%),
  radial-gradient(700px 500px at 50% 100%,#fbefc9 0%,transparent 60%),#eef5f3;
  background-attachment:fixed}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stHeader"],
[data-testid="stToolbar"],footer,#MainMenu{display:none!important}
.block-container{max-width:1180px;padding:.8rem 1.2rem 4rem!important}
h1,h2,h3{letter-spacing:-.02em;color:var(--ink)}
/* ---------- top nav ---------- */
.st-key-topbar{position:sticky;top:8px;z-index:50;background:rgba(255,255,255,.72);backdrop-filter:blur(14px);
  border:1px solid var(--line);border-radius:999px;padding:6px 10px;box-shadow:var(--shadow);margin-bottom:18px}
.st-key-topbar [data-testid="stHorizontalBlock"]{align-items:center;gap:.4rem;flex-wrap:wrap}
.st-key-topbar [data-testid="stColumn"]{min-width:0!important;width:auto!important;flex:0 1 auto!important}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:1.05rem;white-space:nowrap}
.brand .dot{width:30px;height:30px;border-radius:50%;background:conic-gradient(from 200deg,var(--teal2),var(--lav2),var(--teal2));
  display:grid;place-items:center;font-size:15px;box-shadow:0 4px 12px rgba(15,139,125,.35)}
.chip-user{display:flex;gap:8px;align-items:center;font-size:.82rem;font-weight:600;white-space:nowrap}
.chip-user b{background:var(--mint);padding:4px 10px;border-radius:999px}
.chip-user i{font-style:normal;background:var(--sun);padding:4px 10px;border-radius:999px}
.st-key-topbar .stButton>button{border:0;background:transparent;border-radius:999px;padding:.35rem .9rem;font-weight:600;
  color:var(--ink2);transition:all .18s}
.st-key-topbar .stButton>button:hover{background:rgba(127,214,194,.35);color:var(--ink);transform:translateY(-1px)}
.st-key-topbar .stButton>button[kind="primary"]{background:var(--dark);color:#fff}
.st-key-topbar .stButton>button p{white-space:nowrap}
@media(max-width:760px){.st-key-topbar{border-radius:22px}.brand span{display:none}.chip-user i{display:none}
  .st-key-topbar .stButton>button{padding:.25rem .55rem;font-size:.82rem}}
/* ---------- buttons / inputs ---------- */
.stButton>button,.stFormSubmitButton>button{border-radius:999px;font-weight:600;border:1px solid var(--line);
  background:rgba(255,255,255,.8);transition:transform .15s,box-shadow .15s,background .15s;color:var(--ink)}
.stButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(60,90,100,.16)}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:var(--dark);color:#fff;border:0;padding:.55rem 1.3rem}
.stTextArea textarea,.stTextInput input{border-radius:16px!important;background:rgba(255,255,255,.85)!important}
.stTextArea textarea:focus,.stTextInput input:focus{box-shadow:0 0 0 3px rgba(15,139,125,.25)!important}
/* ---------- cards ---------- */
.gl{background:var(--card);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.7);border-radius:var(--r);
  padding:22px 24px;box-shadow:var(--shadow);animation:up .5s both}
.gl h3{margin:0 0 10px;font-size:1.15rem}
.gl.lift{transition:transform .2s,box-shadow .2s}.gl.lift:hover{transform:translateY(-3px);box-shadow:0 16px 34px rgba(60,90,100,.18)}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--teal);font-weight:700}
.sub{color:var(--ink2)} .muted{color:var(--muted);font-size:.85rem}
@keyframes up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@keyframes pop{0%{transform:scale(.8);opacity:0}70%{transform:scale(1.06)}100%{transform:scale(1);opacity:1}}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(15,139,125,.45)}100%{box-shadow:0 0 0 16px rgba(15,139,125,0)}}
/* ---------- XP hero + pills (image 2) ---------- */
.xp{font-size:clamp(3rem,9vw,5.6rem);font-weight:800;letter-spacing:-.04em;line-height:1;color:#1f3533}
.xp small{font-size:.38em;margin-left:.15em;font-weight:700}
.pills{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}
.pill{padding:12px 22px;border-radius:999px;font-weight:600;background:rgba(255,255,255,.55);border:1px solid var(--line);white-space:nowrap}
.pill b{margin-left:8px;font-size:1.05em}
.pill.g{background:#7fe3b8}.pill.y{background:#f8e3a1}.pill.d{background:var(--dark);color:#fff}
.bar{height:10px;background:rgba(22,48,47,.1);border-radius:99px;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--teal2),var(--teal));transition:width .8s}
/* ---------- score cards (image 1) ---------- */
.scards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.sc{background:#fff;border-radius:16px;padding:16px 16px 14px;border-left:5px solid var(--teal);box-shadow:var(--shadow);
  animation:up .5s both;transition:transform .2s}
.sc:hover{transform:translateY(-4px)}
.sc .t{font-weight:600;min-height:2.6em;line-height:1.25}
.sc .v{font-size:2.5rem;font-weight:700;color:var(--teal);line-height:1.1;margin:6px 0}
.sc .pc{text-align:right;font-size:.78rem;color:var(--ink2)}
.sc .lab{font-size:.85rem;margin-top:8px}
.sc.warn{border-left-color:#d6892f}.sc.warn .v{color:#c27219}
/* ---------- activity / module cards ---------- */
.mods{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.mod{display:flex;gap:12px;align-items:center;background:rgba(255,255,255,.7);border-radius:16px;padding:14px 16px;transition:transform .18s}
.mod:hover{transform:translateY(-3px)}
.mod .ic{width:42px;height:42px;border-radius:12px;background:rgba(127,214,194,.4);display:grid;place-items:center;font-size:20px}
.mod .n{margin-left:auto;font-weight:700}
.act{border-radius:18px;padding:16px 18px;margin-bottom:12px}
.act.p{background:#cfbdf2}.act.y{background:#f8e3a1}.act.m{background:#bfeadf}
.act small{opacity:.75}.act h4{margin:4px 0;font-size:1.2rem;font-weight:800;letter-spacing:-.01em}
/* ---------- debate arena ---------- */
.turnbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.tag{padding:6px 14px;border-radius:999px;font-weight:700;font-size:.82rem;background:rgba(255,255,255,.7)}
.tag.you{background:var(--mint)}.tag.ai{background:var(--lav)}.tag.live{animation:pulse 1.4s infinite}
.msg{padding:14px 18px;border-radius:20px;margin:8px 0;max-width:86%;animation:pop .35s both;line-height:1.5}
.msg.you{background:var(--mint);margin-left:auto;border-bottom-right-radius:6px}
.msg.ai{background:#fff;border-bottom-left-radius:6px;box-shadow:var(--shadow)}
.msg .who{font-size:.7rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;opacity:.6;margin-bottom:4px}
.rule{display:flex;gap:10px;align-items:flex-start;margin:6px 0}
.rule .k{background:var(--mint);border-radius:50%;width:26px;height:26px;display:grid;place-items:center;font-weight:700;flex:none}
.badge-t{display:inline-flex;flex-direction:column;align-items:center;width:104px;padding:12px 6px;margin:4px;border-radius:16px;
  background:#fff;box-shadow:var(--shadow);font-size:.74rem;text-align:center;font-weight:600;animation:pop .45s both}
.badge-t span{font-size:1.8rem}.badge-t.off{opacity:.35;filter:grayscale(1)}
.callout{border-left:5px solid var(--teal);background:rgba(255,255,255,.75);border-radius:14px;padding:12px 16px;margin:8px 0}
.callout.lav{border-color:var(--lav2)}.callout.sun{border-color:#e0b93d}
.hero{border-radius:32px;padding:clamp(24px,5vw,56px);position:relative;overflow:hidden;
  background:linear-gradient(135deg,#bfeadf 0%,#cfd8f3 55%,#d3c6f0 100%);box-shadow:var(--shadow);margin-bottom:10px}
.hero h1{font-size:clamp(2rem,5.2vw,3.6rem);line-height:1.04;font-weight:800;margin:.3em 0 .4em;max-width:640px}
.hero p{max-width:540px;font-size:1.08rem;color:var(--ink2)}
/* roadmap iframe is taller on phones (vertical layout) */
.st-key-roadmap iframe{height:560px!important}
@media(max-width:760px){.st-key-roadmap iframe{height:1280px!important}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def inject(st):
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def active_nav_css(key: str) -> str:
    return (f"<style>.st-key-nav_{key} .stButton>button,.st-key-nav_{key} button"
            "{background:rgba(15,139,125,.16)!important;color:#0b5f56!important}</style>")