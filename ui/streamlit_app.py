"""Debate Learning Platform — Streamlit entry point.   Run:  python -m streamlit run ui/streamlit_app.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

st.set_page_config(page_title="ArguMind · Debate Learning", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

from ui import theme, ctx                       # noqa: E402
from ui.views import home, how, auth, debate, progress, profile   # noqa: E402
from app import progress as P                   # noqa: E402

PAGES = {"home": home, "how": how, "auth": auth, "debate": debate, "progress": progress, "profile": profile}
NAV = [("home", "Home"), ("how", "How It Works"), ("debate", "Start Debate"), ("progress", "My Progress"), ("profile", "Profile")]


def header(user, page):
    st.markdown(theme.active_nav_css(page), unsafe_allow_html=True)
    with st.container(key="topbar"):
        cols = st.columns([1.5] + [1] * len(NAV) + [1.3, 1.2])
        cols[0].markdown('<div class="brand"><div class="dot">🧠</div><span>ArguMind</span></div>', unsafe_allow_html=True)
        for c, (k, label) in zip(cols[1:1 + len(NAV)], NAV):
            with c.container(key=f"nav_{k}"):
                if st.button(label, key=f"navbtn_{k}"):
                    ctx.go(k)
        if user:
            li = P.level_info(user["state"]["xp"])
            cols[-2].markdown(f'<div class="chip-user"><b>{user["nickname"]}</b><i>Lv {li["level"]}</i></div>', unsafe_allow_html=True)
            if cols[-1].button("Log out", key="nav_logout"):
                ctx.sign_out(); ctx.go("home")
        else:
            cols[-2].write("")
            if cols[-1].button("Login", key="nav_login", type="primary"):
                ctx.go("auth")


def main():
    theme.inject(st)
    page = st.session_state.setdefault("page", "home")
    user = ctx.me()
    header(user, page)
    if ctx.STUDY_MODE != "adaptive" and user:
        st.caption(f"Study mode: {ctx.STUDY_MODE}")
    if os.getenv("ENGINE", "api").lower() == "demo":
        st.warning("DEMO engine active: offline rule-based stand-in, not the thesis system. Never report these outputs as results.")
    PAGES[page].render()


main()