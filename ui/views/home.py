import os, streamlit as st, streamlit.components.v1 as components
from ui import ctx, hero
from ui.roadmap import roadmap_html
from app import progress as P

def roadmap_block(done=(), current=0, selected=None):
    with st.container(key="roadmap"):
        components.html(roadmap_html(done, current, selected), height=560, scrolling=False)

def render():
    user = ctx.me()
    st.markdown(hero.hero_html(), unsafe_allow_html=True)
    vid = os.path.join(os.path.dirname(__file__), "..", "assets", "intro.mp4")
    if os.path.exists(vid):
        st.video(vid)
    a, b, _ = st.columns([1.1, 1, 1.4])
    if a.button("Start Your Debate Journey →", type="primary", key="cta_start"):
        ctx.go("debate" if user else "auth")
    if b.button("Explore How It Works", key="cta_how"):
        ctx.go("how")
    st.markdown('<h2 style="margin:28px 0 2px">Your learning journey</h2>'
                '<p class="sub">Nine stages, one loop. Tap any stage to see what happens, why it matters and what you gain.</p>', unsafe_allow_html=True)
    roadmap_block(current=0 if not user else 3 if st.session_state.get("flow") else 0)
    st.markdown('<div class="mods" style="margin-top:18px">' + "".join(
        f'<div class="mod gl lift"><div class="ic">{i}</div><div><b>{t}</b><div class="muted">{d}</div></div></div>' for i, t, d in [
            ("🎯", "Targeted, not generic", "The AI presses your weakest dimension."),
            ("🧠", "Explained feedback", "Seven scored dimensions and a named weakness."),
            ("🏋️", "Practice that fits", "Exercises chosen for your gap."),
            ("📈", "Visible growth", "XP, levels, badges and history.")]) + "</div>", unsafe_allow_html=True)