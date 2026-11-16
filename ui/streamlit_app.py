"""Debate Learning Platform: Streamlit entry point.   Run:  python -m streamlit run ui/streamlit_app.py"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
import glob


def _drop_stale_modules():
    """Streamlit only reloads modules inside ui/. After any edit in app/ or ui/, drop the cached project modules so the next
    click uses the new code (no restart needed). Runs only when a file changed, so normal use keeps its caches."""
    files = glob.glob(os.path.join(_ROOT, "app", "*.py")) + glob.glob(os.path.join(_ROOT, "ui", "**", "*.py"), recursive=True)
    stamp = max(os.path.getmtime(f) for f in files)
    if getattr(sys, "_argumind_stamp", None) != stamp:
        for name in [m for m in sys.modules if m in ("app", "ui") or m.startswith(("app.", "ui."))]:
            del sys.modules[name]
        sys._argumind_stamp = stamp


_drop_stale_modules()
import streamlit as st

st.set_page_config(page_title="ArguMind · Debate Learning", page_icon=":material/forum:", layout="wide", initial_sidebar_state="collapsed")

from ui import theme, ctx                       # noqa: E402
from ui.icons import svg                        # noqa: E402
from ui.views import home, how, auth, debate, progress, profile   # noqa: E402
from app import progress as P                   # noqa: E402

PAGES = {"home": home, "how": how, "auth": auth, "debate": debate, "progress": progress, "profile": profile}
NAV = [("home", "Home"), ("how", "How It Works"), ("debate", "Start Debate"), ("progress", "My Progress"), ("profile", "Profile")]


def header(user, page):
    """One aligned row: brand, nav buttons, flexible spacer, user chip, login or logout (sizes set in theme.py)."""
    st.markdown(theme.active_nav_css(page), unsafe_allow_html=True)
    with st.container(key="topbar"):
        cols = st.columns([1.5] + [1] * len(NAV) + [2.4, 1.1, 0.9])
        cols[0].markdown(f'<div class="brand"><div class="dot">{svg("logo", 20)}</div><span>ArguMind</span></div>', unsafe_allow_html=True)
        for c, (k, label) in zip(cols[1:1 + len(NAV)], NAV):
            with c.container(key=f"nav_{k}"):
                if st.button(label, key=f"navbtn_{k}"):
                    ctx.go(k)
        with cols[len(NAV) + 1].container(key="nav_spacer"):
            st.write("")
        if user:
            li = P.level_info(user["state"]["xp"])
            cols[-2].markdown(f'<div class="chip-user"><b>{user["nickname"]}</b><i>Lv {li["level"]}</i></div>', unsafe_allow_html=True)
            if cols[-1].button("Log out", key="nav_logout"):
                ctx.sign_out(); ctx.go("home")
        else:
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
        st.warning("DEMO engine active: an offline rule based stand in, not the thesis system. Never report these outputs as results.")
    PAGES[page].render()


main()
