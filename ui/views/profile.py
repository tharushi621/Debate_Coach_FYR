import datetime as dt, streamlit as st
from app import progress as P
from ui import ctx, charts
from ui.icons import svg


def render():
    user = ctx.me()
    if not user:
        st.info("Log in to see your profile.")
        if st.button("Log in", type="primary", key="pr_login"):
            ctx.go("auth")
        return
    s = user["state"]; db = ctx.store().debates(user["id"])
    stats = P.profile_stats(db, ctx.store().training(user["id"])); li = P.level_info(s["xp"])
    with st.container(key="profile_head"):
        a, b = st.columns([5, 1])
        a.markdown(f'<div class="profile-top"><div class="brand"><div class="dot" style="width:64px;height:64px">{svg("logo", 32)}</div></div>'
                   f'<div><h1 style="margin:0">{user["nickname"]}</h1><div class="sub">Level {li["level"]} · {li["name"]} · member since '
                   f'{dt.datetime.fromtimestamp(user["created"]):%d %b %Y}</div></div></div>', unsafe_allow_html=True)
        with b.container(key="pr_logout"):
            if st.button("Log out", key="pr_logout_btn"):
                ctx.sign_out(); ctx.go("home")
    st.markdown(f'<div class="pills"><span class="pill g">XP<b>{s["xp"]:,}</b></span><span class="pill b">Debates<b>{stats["debates"]}</b></span>'
                f'<span class="pill">Arguments<b>{stats["turns"]}</b></span>'
                f'<span class="pill">Training passed<b>{stats["training_passed"]}/{stats["training_attempts"]}</b></span>'
                f'<span class="pill">Best streak<b>{P.days(s["best_streak"])}</b></span></div>', unsafe_allow_html=True)
    if db:
        dims = {k: v for k, v in stats["avg_dims"].items() if v}
        best = sorted(dims, key=dims.get, reverse=True)[:2]; worst = sorted(dims, key=dims.get)[:2]
        a, b = st.columns(2)
        a.markdown('<div class="card"><h3>Strengths</h3>' + "".join(
            f'<div class="callout green">{P.DIM_LABEL[d]} <b style="float:right">{dims[d]:.1f}</b></div>' for d in best) + "</div>",
            unsafe_allow_html=True)
        # thesis 4.13.2: amber/orange/red are not in the palette, so "to work on" uses the plain (blue) callout
        b.markdown('<div class="card"><h3>To work on</h3>' + "".join(
            f'<div class="callout">{P.DIM_LABEL[d]} <b style="float:right">{dims[d]:.1f}</b></div>' for d in worst) + "</div>",
            unsafe_allow_html=True)
        first, now = stats["overall_first"], stats["overall_now"]
        st.markdown(f'<div class="card" style="margin-top:14px"><h3>Improvement record</h3><p>First debate <b>{first:.2f}</b> → latest <b>{now:.2f}</b> '
                    f'(<b>{now-first:+.2f}</b>)</p>{charts.line_svg(stats["trend"])}</div>', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:18px">Debate history</h3>' + "".join(
            f'<div class="hist-row"><div><b>{d["topic"]}</b><div class="muted">{dt.datetime.fromtimestamp(d["ts"]):%d %b %Y} · {d["side"]} · '
            f'{d["difficulty"]} · gap: {P.WEAKNESS_LABEL.get(d["weakness"], "none")}</div></div>'
            f'<div class="n" style="margin-left:auto;font-weight:700;color:#0b2a5b">{d["overall"] or "n/a"}</div></div>'
            for d in reversed(db)), unsafe_allow_html=True)
    if db:
        st.markdown('<h3 style="margin-top:18px">Session history</h3>', unsafe_allow_html=True)
        for d in reversed(db[-10:]):
            if not d.get("session_id"):
                continue
            with st.expander(f'{d["topic"]} · {dt.datetime.fromtimestamp(d["ts"]):%d %b %Y}'):
                try:
                    rows = ctx.engine().history(d["session_id"])
                except Exception as e:
                    st.caption(f"History unavailable: {e}"); continue
                for r in rows:
                    st.markdown(f'**Argument {r["turn_number"]}:** {r["student_argument"]}')
                    if r.get("response_text"):
                        st.markdown(f'> **AI opponent:** {r["response_text"]}')
    st.markdown('<h3 style="margin-top:18px">Badges</h3>' + "".join(
        f'<div class="badge-t {"" if k in s["badges"] else "off"}" title="{v[2]}"><span>{svg(v[0], 28)}</span>{v[1]}</div>'
        for k, v in P.BADGES.items()), unsafe_allow_html=True)
