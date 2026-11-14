import datetime as dt, streamlit as st
from app import progress as P, topics as T
from ui import ctx, charts


def render():
    user = ctx.me()
    if not user:
        st.info("Log in to see your progress."); 
        if st.button("Log in", type="primary", key="p_login"): ctx.go("auth")
        return
    s = user["state"]; db = ctx.store().debates(user["id"]); tr = ctx.store().training(user["id"])
    stats = P.profile_stats(db, tr); li = P.level_info(s["xp"]); qs = P.quests(s, db, tr)
    st.markdown(f'<div class="gl"><div class="eyebrow">{user["nickname"]} · Level {li["level"]} {li["name"]}</div>'
                f'<div class="xp">{s["xp"]:,}<small>XP</small></div>'
                f'<div class="bar" style="max-width:520px"><i style="width:{li["pct"]*100:.0f}%"></i></div>'
                f'<div class="muted">{"Max level" if li["to_next"] is None else str(li["to_next"]) + " XP to " + li["next_name"]}</div>'
                f'<div class="pills"><span class="pill g">Debates<b>{stats["debates"]}</b></span><span class="pill y">Badges<b>{len(s["badges"])}</b></span>'
                f'<span class="pill">Quests left<b>{sum(not q["done"] for q in qs)}</b></span><span class="pill">Streak<b>{s["streak"]}🔥</b></span></div></div>', unsafe_allow_html=True)
    if not db:
        st.markdown('<div class="gl" style="margin-top:14px"><h3>Your dashboard is waiting</h3><p class="sub">Finish one debate and your radar, trends and recommendations appear here.</p></div>', unsafe_allow_html=True)
        if st.button("Start your first debate →", type="primary", key="p_first"): ctx.go("debate")
        return
    a, b = st.columns([1.25, 1], gap="large")
    with a:
        sk = stats["skills"]
        st.markdown('<div class="gl"><h3>Argument profile</h3>' + charts.radar_svg(stats["avg_dims"], P.DIMS, center=stats["overall_now"], center_label="Latest overall") + "</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>" + charts.score_cards(sk, list(sk), {k: k for k in sk}), unsafe_allow_html=True)
        st.markdown('<div class="gl" style="margin-top:14px"><h3>Overall score per debate</h3>' + charts.line_svg(stats["trend"]) + "</div>", unsafe_allow_html=True)
    with b:
        rec = P.recommend(stats, s)
        st.markdown(f'<div class="act p"><small>Recommended next</small><h4>{T.CATEGORIES[rec["category"]][1]} · {rec["difficulty"].title()}</h4><small>{rec["why"]}</small></div>', unsafe_allow_html=True)
        oc = stats["outcomes"]
        st.markdown(f'<div class="act y"><small>Versus your previous debate</small><h4>{oc["improved"]} improved · {oc["held"]} held · {oc["dipped"]} dipped</h4>'
                    '<small>No win/loss: the AI is a sparring partner, not a judge.</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="gl"><h3>Quests</h3>' + "".join(f'<div class="callout {"" if q["done"] else "sun"}">{"✅" if q["done"] else "🎯"} {q["title"]} <b style="float:right">{q["progress"]}</b></div>' for q in qs) + "</div>", unsafe_allow_html=True)
        st.markdown('<div class="gl" style="margin-top:14px"><h3>Recent activity</h3>' + "".join(
            f'<div class="mod" style="margin:6px 0"><div class="ic">🎙️</div><div><b>{d["topic"][:44]}</b><div class="muted">{dt.datetime.fromtimestamp(d["ts"]):%d %b} · {d["side"]} · {d["overall"] or "—"}</div></div><div class="n">+{d["xp"]}</div></div>'
            for d in reversed(db[-4:])) + "</div>", unsafe_allow_html=True)
    st.markdown('<h3 style="margin-top:20px">Achievements</h3>' + "".join(
        f'<div class="badge-t {"" if k in s["badges"] else "off"}" title="{v[2]}"><span>{v[0]}</span>{v[1]}</div>' for k, v in P.BADGES.items()), unsafe_allow_html=True)