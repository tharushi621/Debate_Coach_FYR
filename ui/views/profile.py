import datetime as dt, streamlit as st
from app import progress as P
from ui import ctx, charts


def render():
    user = ctx.me()
    if not user:
        st.info("Log in to see your profile."); 
        if st.button("Log in", type="primary", key="pr_login"): ctx.go("auth")
        return
    s = user["state"]; db = ctx.store().debates(user["id"]); stats = P.profile_stats(db, ctx.store().training(user["id"])); li = P.level_info(s["xp"])
    st.markdown(f'<div class="gl" style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><div class="brand"><div class="dot" style="width:64px;height:64px;font-size:30px">🧠</div></div>'
                f'<div><h1 style="margin:0">{user["nickname"]}</h1><div class="sub">Level {li["level"]} · {li["name"]} · member since {dt.datetime.fromtimestamp(user["created"]):%d %b %Y}</div></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pills"><span class="pill g">XP<b>{s["xp"]:,}</b></span><span class="pill y">Debates<b>{stats["debates"]}</b></span><span class="pill">Arguments<b>{stats["turns"]}</b></span>'
                f'<span class="pill">Training passed<b>{stats["training_passed"]}/{stats["training_attempts"]}</b></span><span class="pill">Best streak<b>{s["best_streak"]}🔥</b></span></div>', unsafe_allow_html=True)
    if db:
        dims = {k: v for k, v in stats["avg_dims"].items() if v}
        best = sorted(dims, key=dims.get, reverse=True)[:2]; worst = sorted(dims, key=dims.get)[:2]
        a, b = st.columns(2)
        a.markdown('<div class="gl"><h3>💪 Strengths</h3>' + "".join(f'<div class="callout">{P.DIM_LABEL[d]} <b style="float:right">{dims[d]:.1f}</b></div>' for d in best) + "</div>", unsafe_allow_html=True)
        b.markdown('<div class="gl"><h3>🎯 To work on</h3>' + "".join(f'<div class="callout sun">{P.DIM_LABEL[d]} <b style="float:right">{dims[d]:.1f}</b></div>' for d in worst) + "</div>", unsafe_allow_html=True)
        first, now = stats["overall_first"], stats["overall_now"]
        st.markdown(f'<div class="gl" style="margin-top:14px"><h3>Improvement record</h3><p>First debate <b>{first:.2f}</b> → latest <b>{now:.2f}</b> '
                    f'(<b>{now-first:+.2f}</b>)</p>{charts.line_svg(stats["trend"])}</div>', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:18px">Debate history</h3>' + "".join(
            f'<div class="mod" style="margin:6px 0"><div class="ic">{P.BADGES["first_words"][0]}</div><div><b>{d["topic"]}</b><div class="muted">{dt.datetime.fromtimestamp(d["ts"]):%d %b %Y} · {d["side"]} · {d["difficulty"]} · gap: {P.WEAKNESS_LABEL.get(d["weakness"], "—")}</div></div><div class="n">{d["overall"] or "—"}</div></div>'
            for d in reversed(db)), unsafe_allow_html=True)
    st.markdown('<h3 style="margin-top:18px">Badges</h3>' + "".join(f'<div class="badge-t {"" if k in s["badges"] else "off"}"><span>{v[0]}</span>{v[1]}</div>' for k, v in P.BADGES.items()), unsafe_allow_html=True)
    if st.button("Log out", key="pr_logout"):
        ctx.sign_out(); ctx.go("home")