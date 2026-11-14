import streamlit as st
from ui import ctx

def render():
    st.markdown('<div class="eyebrow">Welcome</div><h1 style="margin:.1em 0">Pick a nickname and start.</h1>'
                '<p class="sub">No email, no password, no forms. Your nickname saves your progress and debate history.</p>', unsafe_allow_html=True)
    s = ctx.store()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="gl"><h3>✨ New here? Register</h3>', unsafe_allow_html=True)
        nick = st.text_input("Choose a nickname", key="reg_nick", max_chars=20, placeholder="e.g. quick_fox")
        if nick:
            err = s.check_nickname(nick)
            if err: st.warning(err)
            elif s.available(nick): st.success(f"“{nick.strip()}” is available ✓")
            else: st.error("That nickname is taken.")
        if st.button("Create my profile", type="primary", key="do_reg"):
            try:
                uid, tok = s.register(nick); ctx.sign_in(uid, tok); ctx.go("home")
            except ValueError as e:
                st.error(str(e))
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="gl"><h3>👋 Welcome back</h3>', unsafe_allow_html=True)
        nick2 = st.text_input("Your nickname", key="login_nick", max_chars=20)
        if st.button("Log in", type="primary", key="do_login"):
            try:
                uid, tok = s.login(nick2); ctx.sign_in(uid, tok); ctx.go("home")
            except ValueError as e:
                st.error(str(e))
        st.markdown("</div>", unsafe_allow_html=True)
    st.caption("A nickname identifies you; it is not a password. Don’t put personal details in it.")