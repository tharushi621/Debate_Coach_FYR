import datetime as dt, streamlit as st
from app import progress as P, topics as T
from ui import ctx, charts
from ui.icons import svg
from ui.toulmin import mastery_html


def render():
    user = ctx.me()
    if not user:
        st.info("Log in to see your progress.")
        if st.button("Log in", type="primary", key="p_login"):
            ctx.go("auth")
        return
    s = user["state"]; db = ctx.store().debates(user["id"]); tr = ctx.store().training(user["id"])
    stats = P.profile_stats(db, tr); li = P.level_info(s["xp"]); qs = P.quests(s, db, tr)
    st.markdown(f'<div class="card"><div class="eyebrow">{user["nickname"]} · Level {li["level"]} {li["name"]}</div>'
                f'<div class="xp">{s["xp"]:,}<small>XP</small></div>'
                f'<div class="bar" style="max-width:520px"><i style="width:{li["pct"]*100:.0f}%"></i></div>'
                f'<div class="muted">{"Max level" if li["to_next"] is None else str(li["to_next"]) + " XP to " + li["next_name"]}</div>'
                f'<div class="pills"><span class="pill g">Debates<b>{stats["debates"]}</b></span><span class="pill b">Badges<b>{len(s["badges"])}</b></span>'
                f'<span class="pill">Quests left<b>{sum(not q["done"] for q in qs)}</b></span><span class="pill">Streak<b>{P.days(s["streak"])}</b></span></div></div>',
                unsafe_allow_html=True)
    if not db:
        st.markdown('<div class="card" style="margin-top:14px"><h3>Your dashboard is waiting</h3><p class="sub">Finish one debate and your radar, '
                    'trends and recommendations appear here.</p></div>', unsafe_allow_html=True)
        if st.button("Start your first debate →", type="primary", key="p_first"):
            ctx.go("debate")
        return
    sk = stats["skills"]
    a, b = st.columns([1.15, 1], gap="large")
    with a:
        st.markdown('<div class="card"><h3>Argument profile</h3>' + charts.radar_svg(stats["avg_dims"], P.DIMS, center=stats["overall_now"],
                    center_label="Latest overall") + "</div>", unsafe_allow_html=True)
    with b:
        rec = P.recommend(stats, s)
        st.markdown(f'<div class="tile blue"><small>Recommended next</small><h4>{T.CATEGORIES[rec["category"]][1]} · '
                    f'{rec["difficulty"].title()}</h4><small>{rec["why"]}</small></div>', unsafe_allow_html=True)
        oc = stats["outcomes"]
        st.markdown(f'<div class="tile green"><small>Versus your previous debate</small><h4>{oc["improved"]} improved · {oc["held"]} held · '
                    f'{oc["dipped"]} dipped</h4><small>No win/loss: the AI is a sparring partner, not a judge.</small></div>', unsafe_allow_html=True)
        # thesis 4.13.2: green only for success; open quests use the plain (blue) callout, not amber
        st.markdown('<div class="card"><h3>Quests</h3>' + "".join(
            f'<div class="callout {"green" if q["done"] else ""}"><span class="qi">{svg("check", 16) if q["done"] else svg("target", 16)}</span> {q["title"]} '
            f'<b style="float:right">{q["progress"]}</b></div>' for q in qs) + "</div>", unsafe_allow_html=True)
    st.markdown('<h3 class="section-h" style="margin-top:26px">Skills</h3>' + charts.score_cards(sk, list(sk), {k: k for k in sk}),
                unsafe_allow_html=True)
    st.markdown('<div class="card" style="margin-top:14px"><h3>Skill mastery</h3><p class="sub">Your tier on each dimension, from your average across debates.</p>'
                + mastery_html(stats["avg_dims"]) + "</div>", unsafe_allow_html=True)
    c, d = st.columns(2, gap="large")
    with c:
        st.markdown('<div class="card"><h3>Overall score per debate</h3>' + charts.line_svg(stats["trend"]) + "</div>", unsafe_allow_html=True)
    with d:
        st.markdown('<div class="card"><h3>Recent activity</h3>' + "".join(
            f'<div class="mod" style="margin:6px 0"><div class="ic">{svg("chat", 20)}</div><div><b>{d_["topic"][:44]}</b><div class="muted">'
            f'{dt.datetime.fromtimestamp(d_["ts"]):%d %b} · {d_["side"]} · {d_["overall"] or "n/a"}</div></div><div class="n">+{d_["xp"]}</div></div>'
            for d_ in reversed(db[-4:])) + "</div>", unsafe_allow_html=True)
    st.markdown('<h3 class="section-h" style="margin-top:26px">Achievements</h3>' + "".join(
        f'<div class="badge-t {"" if k in s["badges"] else "off"}" title="{v[2]}"><span>{svg(v[0], 28)}</span>{v[1]}</div>'
        for k, v in P.BADGES.items()), unsafe_allow_html=True)
