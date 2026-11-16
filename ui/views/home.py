import os, streamlit as st
from ui import ctx, hero
from ui.icons import svg
from ui.roadmap import roadmap_vertical


def roadmap_block(done=None, current=0, selected=None):
    """Vertical roadmap. Stages before `current` show as done."""
    done = tuple(range(current)) if done is None else done
    with st.container(key="roadmap"):
        st.markdown(roadmap_vertical(done, current, selected), unsafe_allow_html=True)


def render():
    user = ctx.me()
    with st.container(key="hero"):
        left, right = st.columns([1.05, 1], gap="large")
        with left:
            st.markdown(hero.HERO_TEXT, unsafe_allow_html=True)
            b1, b2 = st.columns([1.5, 1.1])
            if b1.button("Start Your Debate Journey →", key="cta_start"):
                ctx.go("debate" if user else "auth")
            if b2.button("Explore How It Works", key="cta_how"):
                ctx.go("how")
        with right:
            st.markdown(hero.hero_art_html(), unsafe_allow_html=True)
    vid = os.path.join(os.path.dirname(__file__), "..", "assets", "intro.mp4")
    if os.path.exists(vid):
        st.video(vid)
    st.markdown('<div class="facts">' + "".join(
        f'<div class="fact"><div class="ic">{i}</div><div><b>{t}</b><span class="muted">{d}</span></div></div>' for i, t, d in [
            (svg("target", 22), "Targeted, not generic", "The AI presses your weakest dimension."),
            (svg("layers", 22), "Explained feedback", "Seven scored dimensions and a named weakness."),
            (svg("tool", 22), "Practice that fits", "Exercises chosen for your gap."),
            (svg("trend", 22), "Visible growth", "XP, levels, badges and history.")]) + "</div>", unsafe_allow_html=True)
    st.markdown('<h2 class="section-h">Your learning journey</h2>'
                '<p class="sub">Nine stages, one loop. Open any stage to see what happens, why it matters and what you gain.</p>',
                unsafe_allow_html=True)
    roadmap_block(current=3 if user and st.session_state.get("flow") else 0)
    with st.container(key="cta_band"):
        a, b = st.columns([3, 1.4])
        a.markdown("### Ready for your first debate?\nPick a topic, flip a coin and start arguing in under a minute.")
        if b.button("Start Your Debate Journey →", type="primary", key="home_band"):
            ctx.go("debate" if user else "auth")
