"""Design system. Palette follows thesis section 4.13.2:
   blue  = primary (navigation, buttons, headers of panels)
   green = positive feedback, progress, strengths, successful states
   dark blue = headings and key sections
   white = page background, black = primary text
"""
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --ink:#0b1220; --ink2:#334155; --muted:#64748b;
  --navy:#0b2a5b; --blue:#1d5fd1; --blue2:#154aa8; --blue-l:#eaf1fe; --blue-m:#cfe0fb;
  --green:#1f9d63; --green2:#157a4b; --green-l:#e5f6ee;
  --amber:#b45309; --amber-l:#fdf3e1;
  --line:#e2e8f3; --bg:#ffffff; --panel:#f5f8fd;
  --shadow:0 8px 28px rgba(11,42,91,.08); --r:18px;
}
html,body,[class*="css"],.stApp{font-family:'Inter',system-ui,sans-serif;color:var(--ink)}
.stApp{background:var(--bg)}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stHeader"],
[data-testid="stToolbar"],footer,#MainMenu{display:none!important}
.block-container{max-width:1160px;padding:.9rem 1.2rem 4rem!important}
h1,h2,h3,h4{color:var(--navy);letter-spacing:-.02em}
h1{font-weight:800} h2,h3{font-weight:700}
p{line-height:1.6}

/* ---------------- header: one row, everything vertically centred ---------------- */
.st-key-topbar{position:sticky;top:10px;z-index:60;background:rgba(255,255,255,.94);backdrop-filter:blur(10px);
  border:1px solid var(--line);border-radius:18px;padding:8px 14px;box-shadow:var(--shadow);margin-bottom:22px}
.st-key-topbar [data-testid="stHorizontalBlock"]{align-items:center!important;gap:.2rem!important;flex-wrap:nowrap!important}
.st-key-topbar [data-testid="stColumn"]{flex:0 0 auto!important;width:auto!important;min-width:0!important}
.st-key-topbar [data-testid="stColumn"]:has(.st-key-nav_spacer){flex:1 1 auto!important}
.st-key-topbar [data-testid="stVerticalBlock"]{gap:0!important}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:1.08rem;color:var(--navy);white-space:nowrap;margin-right:14px}
.brand .dot{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,var(--blue),var(--navy));
  display:grid;place-items:center;font-size:17px;box-shadow:0 4px 12px rgba(29,95,209,.35)}
.chip-user{display:flex;gap:8px;align-items:center;font-size:.82rem;font-weight:600;white-space:nowrap;margin-right:6px}
.chip-user b{background:var(--blue-l);color:var(--navy);padding:6px 12px;border-radius:999px}
.chip-user i{font-style:normal;background:var(--green-l);color:var(--green2);padding:6px 12px;border-radius:999px}
.st-key-topbar .stButton>button{border:0;background:transparent;border-radius:10px;padding:.45rem .95rem;font-weight:600;
  color:var(--ink2);min-height:0;transition:background .15s,color .15s}
.st-key-topbar .stButton>button:hover{background:var(--blue-l);color:var(--blue2);transform:none;box-shadow:none}
.st-key-topbar .stButton>button p{white-space:nowrap;font-size:.92rem}
.st-key-topbar .stButton>button[kind="primary"]{background:var(--blue);color:#fff}
.st-key-nav_logout button{border:1px solid var(--line)!important;background:#fff!important;color:var(--ink2)!important}
@media(max-width:900px){.brand span{display:none}.chip-user i{display:none}
  .st-key-topbar .stButton>button{padding:.35rem .55rem}}

/* ---------------- buttons, inputs ---------------- */
.stButton>button,.stFormSubmitButton>button{border-radius:12px;font-weight:600;border:1px solid var(--line);background:#fff;
  color:var(--ink);transition:transform .15s,box-shadow .15s,background .15s;padding:.55rem 1.2rem}
.stButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(11,42,91,.12);border-color:var(--blue-m)}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:var(--blue);color:#fff;border:0}
.stButton>button[kind="primary"]:hover,.stFormSubmitButton>button[kind="primary"]:hover{background:var(--blue2)}
.stTextArea textarea,.stTextInput input{border-radius:12px!important;background:#fff!important;border:1px solid var(--line)!important}
.stTextArea textarea:focus,.stTextInput input:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(29,95,209,.18)!important}
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{border-radius:10px 10px 0 0;font-weight:600;padding:.5rem 1rem}
.stTabs [aria-selected="true"]{color:var(--blue2)!important}
.stTabs [data-baseweb="tab-highlight"]{background:var(--blue)!important}

/* ---------------- cards and text ---------------- */
.card{background:#fff;border:1px solid var(--line);border-radius:var(--r);padding:22px 24px;box-shadow:var(--shadow);animation:up .45s both}
.card.tint{background:var(--panel)} .card h3{margin:0 0 10px;font-size:1.12rem}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);font-weight:700}
.sub{color:var(--ink2)} .muted{color:var(--muted);font-size:.86rem}
.section-h{margin:34px 0 4px;font-size:1.5rem}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes pop{0%{transform:scale(.96);opacity:0}100%{transform:scale(1);opacity:1}}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(29,95,209,.45)}100%{box-shadow:0 0 0 14px rgba(29,95,209,0)}}

/* ---------------- hero (CTAs sit inside it) ---------------- */
.st-key-hero{background:linear-gradient(135deg,#0b2a5b 0%,#154aa8 62%,#1d5fd1 100%);border-radius:28px;padding:clamp(22px,4vw,44px);
  box-shadow:0 18px 46px rgba(11,42,91,.28);margin-bottom:8px}
.st-key-hero [data-testid="stHorizontalBlock"]{align-items:center;gap:2rem}
.st-key-hero .eyebrow{color:#9fc2ff}
.st-key-hero h1{color:#fff;font-size:clamp(2rem,4.6vw,3.2rem);line-height:1.08;margin:.3em 0 .4em}
.st-key-hero h1 em{font-style:normal;color:#7ee0ad}
.st-key-hero p{color:#dbe7ff;font-size:1.06rem;max-width:520px}
.st-key-cta_start button{background:#fff!important;color:var(--navy)!important;border:0!important;padding:.75rem 1.5rem!important;font-weight:700}
.st-key-cta_how button{background:transparent!important;color:#fff!important;border:1.5px solid rgba(255,255,255,.55)!important;padding:.75rem 1.5rem!important}
.st-key-cta_how button:hover{background:rgba(255,255,255,.12)!important}
.hero-img{width:100%;border-radius:20px;display:block;box-shadow:0 16px 40px rgba(0,0,0,.35);aspect-ratio:4/3;object-fit:cover}
.hero-art{border-radius:20px;aspect-ratio:4/3;background:radial-gradient(circle at 70% 25%,rgba(126,224,173,.35),transparent 45%),
  linear-gradient(160deg,rgba(255,255,255,.14),rgba(255,255,255,.04));border:1px solid rgba(255,255,255,.25);display:grid;place-items:center;
  color:#fff;font-size:4rem}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-top:16px}
.fact{display:flex;gap:12px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:var(--shadow)}
.fact .ic{width:42px;height:42px;border-radius:12px;background:var(--blue-l);display:grid;place-items:center;font-size:20px;flex:none}
.fact b{display:block;color:var(--navy)}

/* ---------------- vertical roadmap (zigzag path, tap a stage to open it) ---------------- */
.rm{position:relative;max-width:1000px;margin:18px auto 6px;padding:6px 0}
.rm:before{content:"";position:absolute;left:50%;top:0;bottom:0;width:4px;transform:translateX(-50%);border-radius:4px;
  background:linear-gradient(180deg,var(--blue-m),var(--blue-l))}
.rm-item{position:relative;width:50%;padding:0 58px 22px 0;box-sizing:border-box}
.rm-item:nth-child(even){margin-left:50%;padding:0 0 22px 58px}
.rm-num{position:absolute;top:16px;right:-23px;width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:#fff;
  border:3px solid var(--blue-m);font-weight:800;color:var(--navy);z-index:2;box-shadow:0 6px 16px rgba(11,42,91,.14)}
.rm-item:nth-child(even) .rm-num{left:-23px;right:auto}
.rm-item:before{content:"";position:absolute;top:38px;right:0;width:36px;height:3px;background:var(--blue-m)}
.rm-item:nth-child(even):before{left:0;right:auto}
.rm-item.done .rm-num{background:var(--green);border-color:var(--green);color:#fff}
.rm-item.done:before{background:var(--green)}
.rm-item.cur .rm-num{background:var(--blue);border-color:var(--blue);color:#fff;animation:pulse 1.6s infinite}
.rm-item.cur:before{background:var(--blue)}
.rm-card{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden;transition:transform .18s,box-shadow .18s}
.rm-card:hover{transform:translateY(-3px);box-shadow:0 14px 32px rgba(11,42,91,.14)}
.rm-card summary{list-style:none;cursor:pointer;display:flex;gap:14px;align-items:center;padding:16px 18px}
.rm-card summary::-webkit-details-marker{display:none}
.rm-ic{width:48px;height:48px;border-radius:14px;background:var(--blue-l);display:grid;place-items:center;font-size:24px;flex:none}
.rm-item.done .rm-ic{background:var(--green-l)}
.rm-t{font-weight:700;color:var(--navy);line-height:1.2} .rm-s{font-size:.84rem;color:var(--muted);margin-top:2px}
.rm-st{margin-left:auto;font-size:.66rem;letter-spacing:.08em;font-weight:700;text-transform:uppercase;color:var(--muted);white-space:nowrap}
.rm-item.done .rm-st{color:var(--green2)} .rm-item.cur .rm-st{color:var(--blue2)}
.rm-card[open] summary{border-bottom:1px solid var(--line);background:var(--panel)}
.rm-body{padding:16px 18px 18px;display:grid;grid-template-columns:1fr 1fr;gap:10px}
.rm-body p{margin:0;font-size:.9rem;grid-column:1/-1;color:var(--ink2)}
.rm-cell{background:var(--panel);border-radius:12px;padding:10px 12px;font-size:.86rem}
.rm-cell:nth-of-type(2n){background:var(--blue-l)} .rm-cell b{display:block;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--blue2);margin-bottom:3px}
@media(max-width:820px){
  .rm:before{left:23px}
  .rm-item,.rm-item:nth-child(even){width:100%;margin-left:0;padding:0 0 18px 64px}
  .rm-num,.rm-item:nth-child(even) .rm-num{left:0;right:auto}
  .rm-item:before,.rm-item:nth-child(even):before{left:46px;right:auto;width:18px}
  .rm-body{grid-template-columns:1fr}}

/* ---------------- call to action band ---------------- */
.st-key-cta_band{background:var(--blue-l);border:1px solid var(--blue-m);border-radius:22px;padding:22px 26px;margin-top:26px}
.st-key-cta_band [data-testid="stHorizontalBlock"]{align-items:center}
.st-key-cta_band h3{margin:0 0 4px}
.st-key-cta_band .stButton>button{background:var(--blue);color:#fff;border:0;padding:.8rem 1.4rem;float:right}

/* ---------------- sign in page ---------------- */
.auth-left{background:linear-gradient(160deg,#0b2a5b,#1d5fd1);border-radius:24px;padding:34px 30px;color:#fff;height:100%;box-shadow:0 18px 40px rgba(11,42,91,.25)}
.auth-left h2{color:#fff;font-size:1.9rem;line-height:1.15;margin:.3em 0 .5em}
.auth-left .eyebrow{color:#9fc2ff} .auth-left p{color:#dbe7ff}
.auth-step{display:flex;gap:12px;align-items:flex-start;margin:14px 0}
.auth-step .k{width:30px;height:30px;border-radius:50%;background:rgba(255,255,255,.16);display:grid;place-items:center;font-weight:700;flex:none}
.auth-step b{display:block}
.auth-note{margin-top:20px;background:rgba(255,255,255,.12);border-radius:12px;padding:10px 14px;font-size:.86rem}
.st-key-auth_card{background:#fff;border:1px solid var(--line);border-radius:24px;padding:26px 28px;box-shadow:var(--shadow)}

/* ---------------- stepper, pills, bars ---------------- */
.pills{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.pill{padding:9px 18px;border-radius:999px;font-weight:600;background:var(--panel);border:1px solid var(--line);white-space:nowrap}
.pill b{margin-left:8px}
.pill.g{background:var(--green-l);border-color:#bfe5d0;color:var(--green2)} .pill.b{background:var(--blue-l);border-color:var(--blue-m);color:var(--navy)}
.pill.d{background:var(--navy);color:#fff;border-color:var(--navy)}
.bar{height:10px;background:#e8eef8;border-radius:99px;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--blue),var(--green));transition:width .8s}
.xp{font-size:clamp(3rem,9vw,5rem);font-weight:800;letter-spacing:-.04em;line-height:1;color:var(--navy)} .xp small{font-size:.38em;margin-left:.15em}

/* ---------------- score cards ---------------- */
.scards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.sc{background:#fff;border:1px solid var(--line);border-left:5px solid var(--green);border-radius:16px;padding:16px;box-shadow:var(--shadow);animation:up .5s both}
.sc .t{font-weight:600;min-height:2.4em;line-height:1.25;color:var(--navy)}
.sc .v{font-size:2.3rem;font-weight:800;color:var(--green2);line-height:1.1;margin:6px 0}
.sc .pc{text-align:right;font-size:.78rem;color:var(--muted)} .sc .lab{font-size:.85rem;margin-top:8px}
.sc.warn{border-left-color:var(--amber)} .sc.warn .v{color:var(--amber)}

/* ---------------- arena ---------------- */
.ah{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px 18px;box-shadow:var(--shadow);margin-bottom:14px}
.ah-top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.ah-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.ah-tile{background:var(--panel);border-radius:12px;padding:10px 14px}
.ah-tile small{display:block;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.ah-tile b{font-size:1.02rem;color:var(--navy)}
.ah-tile.on{background:var(--blue-l)} .ah-tile.for b{color:var(--green2)} .ah-tile.against b{color:var(--blue2)}
.ah .bar{margin-top:12px}
.motion-bar{background:var(--navy);color:#fff;border-radius:14px;padding:12px 18px;margin:12px 0;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.motion-bar small{letter-spacing:.14em;color:#9fc2ff;font-weight:700;font-size:.66rem;text-transform:uppercase}
.motion-bar b{font-size:1.02rem}
.msg{padding:14px 18px;border-radius:18px;margin:8px 0;max-width:86%;animation:pop .3s both;line-height:1.55}
.msg.you{background:var(--blue-l);border:1px solid var(--blue-m);margin-left:auto;border-bottom-right-radius:6px}
.msg.ai{background:#fff;border:1px solid var(--line);border-bottom-left-radius:6px;box-shadow:var(--shadow)}
.msg .who{font-size:.68rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.callout{border-left:5px solid var(--blue);background:var(--panel);border-radius:12px;padding:12px 16px;margin:8px 0}
.callout.green{border-color:var(--green);background:var(--green-l)} .callout.amber{border-color:var(--amber);background:var(--amber-l)}
.rule{display:flex;gap:10px;align-items:flex-start;margin:8px 0}
.rule .k{background:var(--blue-l);color:var(--blue2);border-radius:50%;width:26px;height:26px;display:grid;place-items:center;font-weight:700;flex:none}
.tl{display:grid;grid-template-columns:130px 1fr auto;gap:10px;align-items:start;padding:10px 0;border-bottom:1px solid var(--line)}
.tl:last-child{border-bottom:0} .tl b{color:var(--navy)}
.chip{font-size:.72rem;font-weight:700;border-radius:999px;padding:3px 10px;white-space:nowrap}
.chip.ok{background:var(--green-l);color:var(--green2)} .chip.miss{background:var(--amber-l);color:var(--amber)}
.sb{display:grid;grid-template-columns:150px 1fr 40px;gap:12px;align-items:center;margin:9px 0}
.sb .bar{height:12px} .sb .n{font-weight:700;text-align:right;color:var(--navy)}
.sb-note{font-size:.8rem;color:var(--muted);margin:-4px 0 6px 162px}
.ai-note{font-size:.8rem;color:var(--muted);border-top:1px dashed var(--line);margin-top:14px;padding-top:10px}

/* ---------------- progress / profile tiles ---------------- */
.tile{border-radius:18px;padding:18px 20px;margin-bottom:14px;border:1px solid var(--line);background:#fff;box-shadow:var(--shadow)}
.tile.blue{background:var(--blue);color:#fff;border:0} .tile.blue h4,.tile.blue small{color:#fff}
.tile.green{background:var(--green-l);border-color:#bfe5d0}
.tile small{color:var(--muted);font-weight:600} .tile h4{margin:4px 0;font-size:1.25rem;font-weight:800}
.mods{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.mod{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:16px;padding:14px 16px}
.mod .ic{width:42px;height:42px;border-radius:12px;background:var(--blue-l);display:grid;place-items:center;font-size:20px;flex:none}
.mod .n{margin-left:auto;font-weight:700;color:var(--navy)}
.badge-t{display:inline-flex;flex-direction:column;align-items:center;width:112px;padding:14px 6px;margin:4px;border-radius:16px;background:#fff;
  border:1px solid var(--line);box-shadow:var(--shadow);font-size:.76rem;text-align:center;font-weight:600;animation:pop .4s both}
.badge-t span{font-size:1.8rem} .badge-t.off{opacity:.35;filter:grayscale(1)}
.hist-row{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:6px 0}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* ---------------- layout fixes: header, profile head, sign in tabs, facts ---------------- */
.st-key-topbar [data-testid="stColumn"]>div{display:flex;align-items:center}
.st-key-topbar .stButton{margin:0}
.st-key-profile_head{background:#fff;border:1px solid var(--line);border-radius:var(--r);padding:18px 22px;box-shadow:var(--shadow);margin-bottom:14px}
.st-key-profile_head [data-testid="stHorizontalBlock"]{align-items:center}
.st-key-pr_logout button{border:1px solid var(--line);background:#fff;color:var(--ink2);width:100%}
.st-key-auth_card .stTabs [data-baseweb="tab-list"]{margin-bottom:12px}
.st-key-auth_card .stButton>button{width:100%}
.st-key-hero .stButton>button{white-space:nowrap}
.st-key-roadmap{margin-top:6px}
.rm-card summary{outline:none}
.profile-top{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.hero-photo{width:100%;border-radius:20px;display:block;aspect-ratio:4/3;object-fit:cover;box-shadow:0 16px 40px rgba(0,0,0,.35)}

/* ================= design refresh: header, hero buttons, icons, argument map, objectives, mastery ================= */
.brand{padding-right:18px;margin-right:8px;border-right:1px solid var(--line)}
.brand .dot{font-size:0;color:#fff} .brand .dot svg{width:20px;height:20px}
.st-key-topbar{padding:8px 16px}
.st-key-topbar [data-testid="stHorizontalBlock"]{align-items:center!important;gap:.35rem!important;flex-wrap:nowrap!important}
.st-key-topbar [data-testid="stElementContainer"]{width:auto!important;margin:0!important}
.st-key-topbar .stButton>button{height:40px;min-height:40px;padding:0 18px;border-radius:10px;font-weight:600;
  display:flex;align-items:center;justify-content:center}
.st-key-topbar .stButton>button p{font-size:.92rem;line-height:1;margin:0}
.chip-user{gap:8px;margin-right:8px}
.chip-user b,.chip-user i{display:inline-flex;align-items:center;height:32px;padding:0 14px;box-sizing:border-box}
.st-key-nav_logout button{height:40px!important}

/* hero buttons: the pale paragraph colour must not reach the text inside a button */
.st-key-hero .stButton>button{min-height:52px;border-radius:12px;padding:.7rem 1.6rem}
.st-key-hero .stButton>button p{color:inherit!important;max-width:none!important;margin:0;font-size:1rem;font-weight:700;line-height:1.2}
.st-key-cta_start button,.st-key-cta_start button p{color:var(--navy)!important}
.st-key-cta_start button:hover{background:var(--blue-l)!important;box-shadow:0 10px 24px rgba(0,0,0,.25)!important}
.st-key-cta_how button,.st-key-cta_how button p{color:#fff!important}

/* icons */
.fact .ic,.mod .ic,.rm-ic{color:var(--blue2)} .rm-item.done .rm-ic{color:var(--green2)}
.fact .ic svg,.mod .ic svg,.rm-ic svg{width:22px;height:22px}
.badge-t span{display:grid;place-items:center;height:34px;color:var(--blue2)} .badge-t span svg{width:28px;height:28px}
.qi{display:inline-flex;vertical-align:-3px;margin-right:4px}
.callout.green .qi{color:var(--green2)}

/* argument map */
.tm{border:1px solid var(--line);border-radius:18px;padding:16px;background:#fff;margin:6px 0 14px}
.tm-top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.tm-meter{display:flex;align-items:center;gap:10px;font-size:.82rem;color:var(--muted);font-weight:600}
.tm-seg{display:flex;gap:4px} .tm-seg i{width:26px;height:8px;border-radius:99px;background:#e8eef8} .tm-seg i.on{background:var(--green)}
.tm-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;
  grid-template-areas:"g w c" "b q r"}
.tm-c{position:relative;border-radius:14px;padding:12px 14px;background:var(--panel);border:1px solid var(--line);min-width:0}
.tm-c.ok{background:#fff;border-left:4px solid var(--green)}
.tm-c.miss{background:#fff;border:1.5px dashed #b9c6dd}
.tm-c.miss .tm-b{color:var(--muted);font-style:italic}
.tm-c.gap{border-color:var(--blue);box-shadow:0 0 0 3px rgba(29,95,209,.16)}
.tm-focus{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:14px;background:var(--navy);color:#fff;border-radius:12px;padding:10px 16px;font-size:.92rem}
.tm-fk{font-size:.66rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#9fc2ff}
.tm-h{display:flex;justify-content:space-between;align-items:center;gap:8px}
.tm-k{font-weight:800;color:var(--navy);font-size:.95rem}
.tm-s{font-size:.64rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;border-radius:99px;padding:3px 9px;white-space:nowrap}
.tm-c.ok .tm-s{background:var(--green-l);color:var(--green2)} .tm-c.miss .tm-s{background:var(--blue-l);color:var(--blue2)}
.tm-c.gap .tm-s{background:var(--navy);color:#fff}
.tm-sub{font-size:.76rem;color:var(--muted);margin:2px 0 6px}
.tm-b{font-size:.9rem;line-height:1.45;word-break:break-word}
.a-g{grid-area:g}.a-w{grid-area:w}.a-c{grid-area:c}.a-b{grid-area:b}.a-q{grid-area:q}.a-r{grid-area:r}.a-f{grid-area:f}
.a-g:after,.a-w:after{content:"";position:absolute;right:-14px;top:50%;width:14px;height:2px;background:var(--blue-m)}
.a-g:before,.a-w:before{content:"";position:absolute;right:-15px;top:50%;margin-top:-4px;border:5px solid transparent;border-left:7px solid var(--blue-m);border-right:0}
@media(max-width:760px){.tm-grid{grid-template-columns:1fr;grid-template-areas:"c" "g" "w" "b" "q" "r"}
  .a-g:after,.a-w:after,.a-g:before,.a-w:before{display:none}}

/* score bars and objectives */
.sbox,.obox{border:1px solid var(--line);border-radius:18px;padding:14px 16px;background:#fff;margin-bottom:14px}
.sb-head,.ob-head{display:flex;gap:10px;align-items:baseline;margin-bottom:8px}
.sb-ov{margin-left:auto;background:var(--blue-l);border-radius:99px;padding:4px 12px;font-weight:600;color:var(--navy)}
.bar.hi>i{background:var(--green)} .bar.mid>i{background:var(--blue)} .bar.lo>i{background:#7f9bc9}
.ob-head{align-items:center}
.ob-pts{margin-left:auto;display:inline-flex;gap:6px;align-items:center;background:var(--navy);color:#fff;border-radius:99px;padding:4px 12px;font-weight:700;font-size:.82rem}
.ob{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:.92rem}
.ob-i{width:22px;height:22px;border-radius:50%;border:2px solid var(--line);display:grid;place-items:center;flex:none;color:#fff}
.ob.ok .ob-i{background:var(--green);border-color:var(--green)} .ob-t{flex:1}
.ob-p{font-weight:700;color:var(--muted)} .ob.ok .ob-p{color:var(--green2)}

/* skill mastery */
.msg-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:10px}
.ms{border:1px solid var(--line);border-radius:14px;padding:12px 14px;background:#fff}
.ms-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-weight:600;color:var(--navy)}
.ms-h b{font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;border-radius:99px;padding:3px 9px;background:var(--blue-l);color:var(--blue2)}
.ms.t3 .ms-h b,.ms.t4 .ms-h b{background:var(--green-l);color:var(--green2)}
.ms .muted{margin-top:6px;font-size:.78rem}

/* Streamlit gives every markdown block margin-bottom:-1rem to cancel a paragraph's margin. HTML blocks (cards, chips) have no
   such paragraph, so that negative margin only swallows the gap below them (a button touching the card above it) and, in
   the header, shrinks the chip's slot so it drops below the nav text. Remove it when the block ends with an HTML element. */
[data-testid="stMarkdownContainer"]:has(> div:last-child),[data-testid="stMarkdownContainer"]:has(> svg:last-child){margin-bottom:0!important}
.st-key-topbar [data-testid="stMarkdownContainer"]{margin-bottom:0!important}
.st-key-topbar .stButton>button p,.st-key-topbar .stButton>button [data-testid="stMarkdownContainer"]{display:block!important;line-height:1!important;margin:0!important}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:stretch;margin-bottom:6px}
@media(max-width:760px){.pair{grid-template-columns:1fr}}
"""


def inject(st):
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def active_nav_css(key: str) -> str:
    return (f"<style>.st-key-nav_{key} .stButton>button,.st-key-nav_{key} button"
            "{background:var(--blue-l)!important;color:var(--blue2)!important;box-shadow:inset 0 -3px 0 var(--blue)!important}</style>")