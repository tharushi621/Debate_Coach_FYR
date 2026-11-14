"""Shared session helpers for all views."""
import os, streamlit as st
from app.platform_store import Store
from ui.engine import make_engine

STUDY_MODE = os.getenv("STUDY_MODE", "adaptive")   # adaptive | single | generic | random

@st.cache_resource
def store() -> Store:
    return Store()

@st.cache_resource
def engine():
    return make_engine()

def go(page: str):
    st.session_state["page"] = page
    st.rerun()

def me():
    """Logged-in user dict or None (validates the session token on every run)."""
    tok = st.session_state.get("token")
    uid = store().user_for_token(tok) if tok else None
    if not uid:
        st.session_state.pop("token", None); st.session_state.pop("uid", None)
        return None
    st.session_state["uid"] = uid
    return store().user(uid)

def sign_in(uid, tok):
    st.session_state.update(uid=uid, token=tok)
    st.session_state.pop("flow", None)

def sign_out():
    tok = st.session_state.get("token")
    if tok:
        store().logout(tok)
    for k in ("token", "uid", "flow"):
        st.session_state.pop(k, None)