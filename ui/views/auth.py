import streamlit as st
from ui import ctx


def render():
    s = ctx.store()
    left, right = st.columns([1, 1.1], gap="large")
    with left:
        st.markdown(
            '<div class="auth-left"><span class="eyebrow">ArguMind</span>'
            '<h2>Practice debating. See exactly what to improve.</h2>'
            '<p>Argue against an AI opponent, find the weak spot in your reasoning, then train it.</p>'
            '<div class="auth-step"><div class="k">1</div><div><b>Choose a nickname</b>That is all you need to start.</div></div>'
            '<div class="auth-step"><div class="k">2</div><div><b>Debate the AI</b>Short rounds on a motion matched to your level.</div></div>'
            '<div class="auth-step"><div class="k">3</div><div><b>Grow</b>Get your score, your main gap, practice and rewards.</div></div>'
            '<div class="auth-note">No email and no password. Your nickname saves your progress and debate history.</div></div>',
            unsafe_allow_html=True)
    with right:
        with st.container(key="auth_card"):
            st.markdown('<div class="eyebrow">Welcome</div><h2 style="margin:.1em 0 .6em">Start in seconds</h2>', unsafe_allow_html=True)
            t_reg, t_login = st.tabs(["New here? Create profile", "Welcome back? Log in"])
            with t_reg:
                nick = st.text_input("Choose a nickname", key="reg_nick", max_chars=20, placeholder="for example quick_fox")
                if nick:
                    err = s.check_nickname(nick)
                    if err:
                        st.warning(err)
                    elif s.available(nick):
                        st.success(f"“{nick.strip()}” is available.")
                    else:
                        st.error("That nickname is taken.")
                if st.button("Create my profile", type="primary", key="do_reg"):
                    try:
                        uid, tok = s.register(nick)
                        ctx.sign_in(uid, tok)
                        ctx.go("home")
                    except ValueError as e:
                        st.error(str(e))
            with t_login:
                nick2 = st.text_input("Your nickname", key="login_nick", max_chars=20)
                if st.button("Log in", type="primary", key="do_login"):
                    try:
                        uid, tok = s.login(nick2)
                        ctx.sign_in(uid, tok)
                        ctx.go("home")
                    except ValueError as e:
                        st.error(str(e))
            st.caption("A nickname identifies you. It is not a password, so do not put personal details in it.")