"""Debate Arena: gamified front end.   Run from the project root:  streamlit run ui/streamlit_app.py
(the backend must be running:  uvicorn app.api:app --port 8000)

Flow: lobby -> coin toss (heads = proponent, tails = opponent) -> 3D stage with spotlights -> finished summary.
Game scoring follows app/game.py; in the control study arms the game shows participation XP only (no quality scores)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

from app import game  # noqa: E402
from ui import client as api_client  # noqa: E402
from ui.stage import coin_html, stage_html  # noqa: E402

CSS = """
<style>
.stApp{background:radial-gradient(ellipse at 50% -10%,#241d4a 0%,#0e0b1f 60%,#07060f 100%);}
h1,h2,h3,h4,p,label,span,div{color:#efeaff}
.hud{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 12px}
.card{flex:1;min-width:130px;background:linear-gradient(#211a45,#15112e);border:1px solid #c9a24a66;border-radius:14px;padding:10px 14px}
.card .k{font-size:11px;letter-spacing:1px;color:#b9b3d9;text-transform:uppercase}.card .v{font-size:24px;font-weight:800;color:#ffe9a8}
.bar{height:10px;background:#0006;border-radius:6px;overflow:hidden;margin-top:6px}.bar i{display:block;height:100%;background:linear-gradient(90deg,#ffd66b,#ff9f43)}
.chip{display:inline-block;background:#2b2350;border:1px solid #c9a24a;border-radius:20px;padding:3px 10px;margin:2px;font-size:13px;color:#ffe9a8}
.chip.gain{border-color:#2ecc9a;color:#9bf3d4}.cheer{background:#ffd66b22;border-left:4px solid #ffd66b;padding:8px 12px;border-radius:8px;margin:6px 0}
</style>
"""

BLIND_NOTE = "Scores and diagnoses are AI-generated and may contain errors. Use this for practice, not grading."


def get_client():
    return api_client.Client()


def hud(level, state, round_no):
    nxt = f'{level["xp"]} / {level["next_at"]} XP' if level["next_at"] else f'{level["xp"]} XP (max level)'
    st.markdown(
        f'<div class="hud"><div class="card"><div class="k">Level {level["level"]}</div><div class="v">{level["title"]}</div>'
        f'<div class="bar"><i style="width:{int(level["pct"] * 100)}%"></i></div><div class="k" style="margin-top:4px">{nxt}</div></div>'
        f'<div class="card"><div class="k">Round</div><div class="v">{round_no}</div></div>'
        f'<div class="card"><div class="k">Streak</div><div class="v">{"🔥" if state["streak"] else "·"} {state["streak"]}</div></div>'
        f'<div class="card"><div class="k">Badges</div><div class="v">{len(state["badges"])}/{len(game.BADGES)}</div></div></div>',
        unsafe_allow_html=True)


def badge_chips(ids):
    return "".join(f'<span class="chip">{game.BADGES[b][1]} {game.BADGES[b][0]}</span>' for b in ids)


def show_stage(slot, ss, active, cheer, caption="", bubble_ai=""):
    with slot.container():
        components.html(stage_html(ss.side, active, cheer, ss.topic, caption, bubble_ai=bubble_ai), height=440)


def lobby(ss, client):
    st.title("🎤 Debate Arena")
    st.caption(BLIND_NOTE)
    st.markdown("Step on stage. A crowd is waiting to hear **you**. Flip a coin to learn which side you will defend.")
    name = st.text_input("Participant code (no real name needed)")
    try:
        topics = client.topics()
    except api_client.ApiError as e:
        st.error(str(e))
        st.stop()
    topic = st.selectbox("Motion", topics)
    if st.button("Enter the arena 🎟️"):
        if not name.strip():
            st.warning("Please type your participant code first.")
        else:
            try:
                ss.user_id = client.create_user(name.strip())
            except api_client.ApiError as e:
                st.error(str(e))
                st.stop()
            ss.update(name=name.strip(), topic=topic, phase="toss", toss=None)
            st.rerun()
    st.stop()


def toss_phase(ss, client):
    st.title("🪙 The coin toss")
    st.markdown(f"**Motion:** {ss.topic}")
    st.caption("Heads = you argue FOR the motion (proponent). Tails = you argue AGAINST it (opponent). The flip is random and cannot be repeated.")
    components.html(coin_html(ss.toss["face"] if ss.toss else None), height=340)
    if not ss.toss:
        if st.button("🪙 Flip the coin", type="primary"):
            ss.toss = game.toss()
            st.rerun()
        st.stop()
    side = ss.toss["side"]
    st.success(f"It's {ss.toss['face'].upper()}! You are the {side.upper()}.")
    if st.button("Take the stage 🎬", type="primary"):
        try:
            res = client.create_session(ss.user_id, ss.topic, side, os.getenv("STUDY_MODE", "adaptive"))
        except api_client.ApiError as e:
            st.error(str(e))
            st.stop()
        ss.update(side=side, session_id=res["session_id"], log=[], game=game.new_state(), report=None, phase="stage")
        st.rerun()
    st.stop()


def sidebar(ss, client, full):
    with st.sidebar:
        st.subheader("🏅 Badge cabinet")
        earned = ss.game["badges"]
        st.markdown(badge_chips(earned) or "_Earn your first badge by speaking._", unsafe_allow_html=True)
        st.subheader("Session history")
        try:
            hist = client.history(ss.session_id)
        except api_client.ApiError:
            hist = []
        for h in hist:
            label = f'Turn {h["turn_number"]}' + (f': {(h["weakness"] or "").replace("_", " ")}' if full else "")
            with st.expander(label):
                st.write(h["student_argument"])
                st.caption(h["response_text"] or "")
        with st.expander("Rate this session"):
            labels = [("ease_of_use", "Ease of use"), ("clarity", "Clarity of feedback"), ("ai_relevance", "Relevance of AI responses"),
                      ("weakness_help", "Helped me identify my weakness"), ("improvement_help", "Helped me improve my next argument"),
                      ("fairness", "Fairness of the assessment"), ("reuse", "I would use it again")]
            vals = {k: st.slider(label, 1, 5, 3, key=f"r_{k}") for k, label in labels}
            comment = st.text_area("Comments (optional)")
            if st.button("Submit ratings"):
                try:
                    client.feedback({"user_id": ss.user_id, "session_id": ss.session_id, **vals, "comment": comment})
                    st.success("Thank you!")
                except api_client.ApiError:
                    st.error("Could not save ratings.")


def round_report(ss, last, rep):
    """Points, badges, audience reaction, and (adaptive arm only) the full coaching view."""
    chips = "".join(f'<span class="chip gain">+{pts} {label}</span>' for label, pts in rep["breakdown"])
    st.markdown(f'**Round {ss.game["turns"]} · +{rep["xp_gained"]} XP** &nbsp; {chips}', unsafe_allow_html=True)
    fresh = not rep.get("fx_done")  # toast/balloons once per round, not on every later rerun
    rep["fx_done"] = True
    if rep["badges_earned"]:
        st.markdown("**New badge!** " + badge_chips(rep["badges_earned"]), unsafe_allow_html=True)
        if fresh:
            st.toast("New badge: " + ", ".join(game.BADGES[b][0] for b in rep["badges_earned"]), icon="🏅")
    if rep["level_up"]:
        if fresh:
            st.balloons()
        st.success(f'LEVEL UP! You are now Level {rep["level"]["level"]}: {rep["level"]["title"]}')
    for f in last.get("validation_flags", []):
        st.warning(f["message"])
    mode = last["display"]
    if mode == "feedback_reply":
        st.info(last["feedback"])
    if mode != "full":
        return
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Your scorecard")
        dims = last["scores"]["dimensions"]
        st.bar_chart(pd.Series({k.replace("_", " "): v["score"] for k, v in dims.items()}))
        st.metric("Overall", f'{last["scores"]["overall_quality"]}/5')
        st.info(f'Main weakness: **{last["diagnosis"]["lowest_weakness"].replace("_", " ")}**\n\n{last["diagnosis"]["diagnosis_reason"]}')
        st.caption(f'Opponent strategy this turn: {last["intervention"]["type"].replace("_", " ")}')
        st.success(last["feedback"])
    with c2:
        st.markdown("#### Toulmin structure")
        a = last["analysis"]
        for k in ("main_claim", "grounds", "warrant", "backing", "qualifier", "rebuttal"):
            st.write(f"**{k.replace('_', ' ').title()}:** {a.get(k) or '_not identified_'}")
        p = last["progress"]
        if p["score_change"] is not None:
            st.markdown("#### Progress")
            st.metric("Overall change", f'{p["score_change"]:+}')
            st.write(f'Targeted: **{p["targeted_dimension"]}** {p["targeted_before"]} → {p["targeted_after"]}')


def stage_phase(ss, client):
    last = ss.log[-1]["r"] if ss.log else None
    full = bool(last) and last["display"] == "full"
    rep = ss.report
    st.markdown(CSS, unsafe_allow_html=True)
    st.caption(BLIND_NOTE)
    slot = st.empty()
    cheer = rep["cheer_level"] if rep else 1
    caption = rep["audience_caption"] if rep else game.cheer_for(1)
    show_stage(slot, ss, "you", cheer, caption, bubble_ai=last["ai_opponent_response"] if last else "")
    hud(game.level_info(ss.game["xp"]), ss.game, ss.game["turns"] + 1)
    st.markdown(f'<div class="cheer">📣 {game.cheer_for(ss.game["turns"] + 1)}</div>', unsafe_allow_html=True)
    for e in ss.log:
        with st.chat_message("user", avatar="🧑‍🎤"):
            st.write(e["arg"])
        with st.chat_message("assistant", avatar="🤖"):
            st.write(e["r"]["ai_opponent_response"])
    arg = st.chat_input("Take the mic: make your argument")
    if arg:
        show_stage(slot, ss, "ai", cheer, "Your opponent is preparing a rebuttal…")
        try:
            r = client.turn(ss.session_id, arg)
        except api_client.ApiError as e:
            show_stage(slot, ss, "you", cheer, "Try again: the crowd is waiting")
            (st.warning if e.kind == "validation" else st.error)(str(e))
            st.stop()
        ss.log.append({"arg": arg, "r": r})
        ss.game, ss.report = game.apply_turn(ss.game, r)
        st.rerun()
    if last and rep:
        round_report(ss, last, rep)
    sidebar(ss, client, full)
    if ss.log and st.button("🏁 End the debate"):
        ss.phase = "finished"
        st.rerun()


def finished(ss, client):
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🏆 Final results")
    lvl = game.level_info(ss.game["xp"])
    st.markdown(f'### {lvl["title"]} · Level {lvl["level"]} · {ss.game["xp"]} XP')
    st.markdown(badge_chips(ss.game["badges"]) or "_No badges this time. Next debate!_", unsafe_allow_html=True)
    rows = [h for h in ss.game["history"]]
    if rows:
        df = pd.DataFrame(rows).set_index("turn")
        st.bar_chart(df["xp"])
        if df["overall"].notna().any():
            st.line_chart(df["overall"].dropna())
    st.markdown(f'<div class="cheer">👏 The audience thanks you for {ss.game["turns"]} rounds of courage. Every round makes the next one easier.</div>', unsafe_allow_html=True)
    sidebar(ss, client, bool(ss.log) and ss.log[-1]["r"]["display"] == "full")
    if st.button("Debate again 🔁"):
        for k in ("session_id", "log", "game", "report", "toss", "side", "topic", "phase"):
            ss.pop(k, None)
        st.rerun()


def main():
    st.set_page_config(page_title="Debate Arena", page_icon="🎤", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    ss = st.session_state
    client = get_client()
    ss.setdefault("phase", "lobby")
    {"lobby": lobby, "toss": toss_phase, "stage": stage_phase, "finished": finished}[ss.phase](ss, client)


main()
