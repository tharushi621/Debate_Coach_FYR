"""The nine-stage debate loop (stages 01–09) as one guided flow."""
import secrets, streamlit as st, streamlit.components.v1 as components
from app import topics as T, progress as P, training as TR
from ui import ctx, charts, coin
from ui.widgets import timer_html, voice_html, stepper_html
from ui.journey import KEYS
try:                                    # your existing 3D debate hall (ui/stage.py); optional
    from ui.stage import stage_html
except Exception:                       # pragma: no cover
    stage_html = None

TURNS, TURN_SECONDS, PREP_SECONDS = 3, 300, 60


def new_flow(category=None, difficulty=None):
    return {"stage": "topic", "category": category, "difficulty": difficulty, "topic": None, "side": None,
            "coin": None, "log": [], "results": [], "handle": None, "mode": None, "train": {"attempt": 0, "done": False},
            "finished": None, "tkey": 0}


def flow():
    if "flow" not in st.session_state:
        st.session_state["flow"] = new_flow()
    return st.session_state["flow"]


def to(stage):
    flow()["stage"] = stage
    st.rerun()


def arm():
    m = ctx.STUDY_MODE
    return secrets.choice(["adaptive", "single", "generic"]) if m == "random" else m


def final_scores(f):
    rs = [r for r in f["results"] if r.get("display") == "full"]
    if not rs:
        return None
    dims = {d: round(sum(r["scores"][d] for r in rs) / len(rs), 2) for d in P.DIMS}
    last = rs[-1]
    return {"scores": dims, "overall": round(sum(dims.values()) / len(dims), 2), "weakness": last["weakness"],
            "explanation": last["explanation"], "intervention": last["intervention"]}


# ------------------------------------------------------------------ stages
def s_topic(f, user):
    st.markdown("### Choose your battlefield")
    cats = list(T.CATEGORIES)
    cols = st.columns(3)
    for i, c in enumerate(cats):
        ic, name = T.CATEGORIES[c]
        picked = f["category"] == c
        if cols[i % 3].button(f"{ic}  {name}", key=f"cat_{c}", use_container_width=True, type="primary" if picked else "secondary"):
            f["category"] = c; st.rerun()
    st.markdown("**Difficulty**")
    f["difficulty"] = st.radio("Difficulty", list(T.DIFFICULTIES), horizontal=True, label_visibility="collapsed",
                               format_func=str.title, index=list(T.DIFFICULTIES).index(f["difficulty"] or "beginner"))
    st.caption(T.DIFFICULTIES[f["difficulty"]])
    if not f["category"]:
        st.info("Pick a category to get a motion."); return
    if not f["topic"]:
        f["topic"] = T.pick(f["category"], f["difficulty"], exclude=ctx.me()["state"].get("recent_topics", []))
    st.markdown(f'<div class="gl"><div class="eyebrow">Your motion</div><h2 style="margin:.2em 0">“{f["topic"]}”</h2></div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    if a.button("🔀 Suggest another", key="reroll"):
        f["topic"] = T.pick(f["category"], f["difficulty"], exclude=[f["topic"]]); st.rerun()
    if b.button("Accept motion →", type="primary", key="accept"):
        to("coin")


def s_coin(f, user):
    st.markdown(f'<div class="gl"><div class="eyebrow">Motion</div><b>{f["topic"]}</b></div>', unsafe_allow_html=True)
    components.html(coin.coin_html(f["coin"]), height=300)
    if not f["coin"]:
        st.markdown("**Heads** = you argue **FOR**. **Tails** = you argue **AGAINST**.")
        if st.button("🪙 Flip the coin", type="primary", key="flip"):
            f["coin"] = secrets.choice(["heads", "tails"])
            f["side"] = "FOR" if f["coin"] == "heads" else "AGAINST"; st.rerun()
    else:
        col = "#0f8b7d" if f["side"] == "FOR" else "#7a4fd1"
        st.markdown(f'<div class="gl" style="text-align:center"><div class="eyebrow">It landed on {f["coin"]}</div>'
                    f'<h1 style="color:{col};margin:.1em 0">You argue {f["side"]}</h1>'
                    f'<p class="sub">The AI takes the {"AGAINST" if f["side"]=="FOR" else "FOR"} side.</p></div>', unsafe_allow_html=True)
        if st.button("Go to stage setup →", type="primary", key="to_setup"):
            to("setup")


def s_setup(f, user):
    opp = "AGAINST" if f["side"] == "FOR" else "FOR"
    st.markdown(f'<div class="gl"><div class="eyebrow">Briefing</div><h2 style="margin:.2em 0">“{f["topic"]}”</h2>'
                f'<div class="pills"><span class="pill g">You<b>{f["side"]}</b></span><span class="pill">AI opponent<b>{opp}</b></span>'
                f'<span class="pill y">{f["difficulty"].title()}</span></div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.markdown(f"""<div class="gl"><h3>📜 Rules & time</h3>
<div class="rule"><div class="k">1</div><div>{TURNS} rounds. Each round you write one argument, then the AI replies.</div></div>
<div class="rule"><div class="k">2</div><div>{TURN_SECONDS//60} minutes per argument (a guide — the timer does not cut you off).</div></div>
<div class="rule"><div class="k">3</div><div>Aim for claim + evidence + a reason linking them.</div></div>
<div class="rule"><div class="k">4</div><div>There is no winner; you compare with your own past scores.</div></div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="gl"><h3>🎯 Your objective</h3><p>Defend <b>{f["side"]}</b> convincingly and survive the AI’s sharpest objection.</p>
<h3>🗺️ Stages</h3><p class="sub">Opening argument → AI counter → your rebuttal → AI counter → closing → diagnosis.</p></div>""", unsafe_allow_html=True)
    st.markdown("#### ⏳ Preparation")
    components.html(timer_html(PREP_SECONDS, "Preparation time", f"prep{f['tkey']}"), height=70)
    st.caption("Outline your claim, one piece of evidence, and the warrant that links them. You can enter whenever you’re ready.")
    if st.button("Enter the arena →", type="primary", key="enter"):
        f["mode"] = arm()
        try:
            f["handle"] = ctx.engine().start(f["topic"], f["side"], f["mode"], nickname=user["nickname"])
        except Exception as e:
            st.error(f"Could not start the debate: {e}"); return
        to("arena")


def s_arena(f, user):
    n = len(f["results"]); opp = "AGAINST" if f["side"] == "FOR" else "FOR"
    over = n >= TURNS
    st.markdown(f'<div class="turnbar"><span class="tag you {"live" if not over else ""}">🎤 Your turn</span>'
                f'<span class="tag ai">🤖 AI · {opp}</span><span class="tag">Round {min(n+1,TURNS)} / {TURNS}</span></div>', unsafe_allow_html=True)
    st.progress(n / TURNS, text=f"Debate progress · {n}/{TURNS} arguments")
    if stage_html:
        side = "proponent" if f["side"] == "FOR" else "opponent"
        last_ai = next((t for w, t in reversed(f["log"]) if w == "ai"), "")
        try:
            components.html(stage_html(side, "you" if not over else "ai", n, f["topic"], "", bubble_ai=last_ai[:140]), height=380)
        except Exception:
            pass
    st.markdown(f'<div class="callout"><b>Motion:</b> {f["topic"]} &nbsp;·&nbsp; <b>You:</b> {f["side"]}</div>', unsafe_allow_html=True)
    for who, text in f["log"]:
        k = "you" if who == "you" else "ai"
        st.markdown(f'<div class="msg {k}"><div class="who">{"You" if k=="you" else "AI opponent"}</div>{text}</div>', unsafe_allow_html=True)
    if over:
        st.success("Debate complete — time to see where you can improve.")
        if st.button("Analyse my arguments →", type="primary", key="analyse"): to("diagnosis")
        return
    components.html(timer_html(TURN_SECONDS, "Time for this argument", f"t{n}"), height=70)
    with st.form(f"arg{n}", clear_on_submit=False):
        text = st.text_area("Your argument", height=150, key=f"argtxt{n}", placeholder="State your claim, give evidence, and explain why it supports your claim…")
        go_ = st.form_submit_button("Send argument", type="primary")
    with st.expander("🎙️ Voice input (optional)"):
        components.html(voice_html(), height=170)
    if go_:
        if len(text.split()) < 5:
            st.warning("Write at least a sentence so the AI has something to analyse."); return
        with st.spinner("The AI is analysing your argument and preparing a rebuttal… (local models can take a few minutes)"):
            try:
                r = ctx.engine().turn(f["handle"], text.strip())
            except ValueError as e:      # HTTP 400 from validation: the learner can fix it
                st.warning(f"Please revise your argument: {e}"); return
            except Exception as e:
                st.error(f"The backend returned an error: {e}"); return
        f["results"].append(r); f["log"] += [("you", text.strip()), ("ai", r["opponent"] or "(no reply)")]
        if r.get("display") != "reply_only" and r.get("feedback") and r.get("display") != "full":
            f["log"].append(("ai", f"💬 {r['feedback']}"))
        st.rerun()
    if n >= 1 and st.button("Finish early", key="finish_early"): to("diagnosis")


def s_diagnosis(f, user):
    fs = final_scores(f)
    if not fs:
        st.info("In this study arm the analysis dashboard is not shown. Your debate is saved — continue to your profile.")
        if st.button("Continue →", type="primary", key="skipdiag"): f["train"]["done"] = True; to("profile")
        return
    f["fs"] = fs
    st.markdown('<div class="gl"><div class="eyebrow">Weakness diagnosis</div>'
                f'<h2 style="margin:.2em 0">Your main gap: {P.WEAKNESS_LABEL.get(fs["weakness"], fs["weakness"])}</h2>'
                f'<p class="sub">{fs["explanation"] or "This was the lowest-scoring part of your reasoning."}</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="gl" style="margin-top:14px">' + charts.radar_svg(fs["scores"], P.DIMS, center=fs["overall"]) + "</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>" + charts.score_cards(fs["scores"], P.DIMS), unsafe_allow_html=True)
    ex = f["results"][-1].get("explanations") or {}
    if any(ex.values()):
        with st.expander("Why these scores? (per-dimension explanations from the analysis)"):
            for d in P.DIMS:
                if ex.get(d): st.markdown(f"**{P.DIM_LABEL[d]}** — {ex[d]}")
    low = sorted(fs["scores"], key=fs["scores"].get)[:2]
    st.markdown(f'<div class="callout lav" style="margin-top:14px"><b>Focus next:</b> {", ".join(P.DIM_LABEL[d] for d in low)}.</div>', unsafe_allow_html=True)
    if f["results"][-1].get("guardrail_fallback"):
        st.caption("The AI’s last reply used a safe template because the model’s draft failed a quality check.")
    if st.button("Train this weakness →", type="primary", key="to_train"): to("training")


def s_training(f, user):
    fs = f["fs"]; kind = P.TRAIN_KIND.get(fs["weakness"], "logic"); tr = f["train"]
    ex = TR.exercise_for(kind, tr["attempt"])
    st.markdown(f'<div class="gl"><div class="eyebrow">AI counterargument training · {kind}</div><h2 style="margin:.2em 0">{ex["title"]}</h2>'
                f'<p style="white-space:pre-line">{ex["prompt"]}</p><div class="muted">💡 {ex["hint"]}</div></div>', unsafe_allow_html=True)
    txt = st.text_area("Your answer", key=f"tr{tr['attempt']}_{tr.get('n',0)}", height=120)
    a, b = st.columns(2)
    if a.button("Check my answer", type="primary", key="check"):
        res = TR.evaluate(kind, txt)
        tr["last"] = res; tr["n"] = tr.get("n", 0)
        u = ctx.me()
        first = not any(t["passed"] for t in ctx.store().training(u["id"]))
        wd = P.WEAKNESS_DIM.get(fs["weakness"])
        state, rep = P.training_result(u["state"], wd, wd, res["passed"], first)
        ctx.store().save_state(u["id"], state)
        ctx.store().add_training(u["id"], fs["weakness"], kind, res["passed"], res["score"], tr["attempt"] + 1)
        tr["rep"] = rep; tr["done"] = tr["done"] or res["passed"]
    res = tr.get("last")
    if res:
        for lab, ok, tip in res["checks"]:
            st.markdown(f'<div class="callout {"" if ok else "sun"}">{"✅" if ok else "⚠️"} <b>{lab}</b>{"" if ok else " — " + tip}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="callout lav"><b>Feedback:</b> {res["feedback"]} &nbsp; <b>+{tr["rep"]["xp_gained"]} XP</b></div>', unsafe_allow_html=True)
        if tr["rep"]["badges"]: st.balloons()
    c, d = st.columns(2)
    if c.button("🔁 Try another exercise", key="retry"):
        tr["attempt"] += 1; tr["last"] = None; st.rerun()
    if d.button("Update my profile →", type="primary", key="to_profile"): to("profile")


def s_profile(f, user):
    if not f.get("finished"):
        fs = f.get("fs") or {"scores": {}, "overall": None, "weakness": None}
        full = bool(f.get("fs"))
        hist = ctx.store().debates(user["id"])
        rec = {"topic": f["topic"], "category": f["category"], "difficulty": f["difficulty"], "overall": fs["overall"],
               "scores": fs["scores"]}
        state, rep = P.finish_debate(user["state"], rec, hist, full)
        ctx.store().save_state(user["id"], state)
        ctx.store().add_debate(user["id"], {**rec, "side": f["side"], "turns": len(f["results"]), "weakness": fs["weakness"],
                                            "outcome": rep["outcome"], "xp": rep["xp_gained"]})
        f["finished"] = {"report": rep, "prev": hist[-1]["overall"] if hist else None, "overall": fs["overall"]}
        user = ctx.me()
    fin = f["finished"]; stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    st.markdown('<div class="eyebrow">Profile updated</div><h2 style="margin:.1em 0">Your record just grew.</h2>', unsafe_allow_html=True)
    prev, now = fin["prev"], fin["overall"]
    delta = "" if prev is None or now is None else f' ({now-prev:+.2f} vs last debate)'
    li = P.level_info(user["state"]["xp"])
    st.markdown(f'<div class="pills"><span class="pill g">Level<b>{li["level"]} · {li["name"]}</b></span><span class="pill y">Debates<b>{stats["debates"]}</b></span>'
                f'<span class="pill">Overall<b>{("%.2f" % now) if now else "—"}{delta}</b></span><span class="pill">Streak<b>{user["state"]["streak"]}🔥</b></span></div>', unsafe_allow_html=True)
    if stats["skills"]:
        st.markdown(charts.score_cards(stats["skills"], list(stats["skills"]), {k: k for k in stats["skills"]}), unsafe_allow_html=True)
    if st.button("See how to improve →", type="primary", key="to_improve"): to("improve")


def s_improve(f, user):
    stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    rec = P.recommend(stats, user["state"])
    st.markdown(f'<div class="gl"><div class="eyebrow">Skill improvement</div><h2 style="margin:.2em 0">Your personalised path</h2><p class="sub">{rec["why"]}</p></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.markdown('<div class="gl"><h3>📈 Progress over time</h3>' + charts.line_svg(stats["trend"]) + "</div>", unsafe_allow_html=True)
    c2.markdown('<div class="gl"><h3>🎯 Recurring weaknesses</h3>' + charts.hbars(
        [(P.WEAKNESS_LABEL.get(k, k), v) for k, v in sorted(stats["weak_counts"].items(), key=lambda x: -x[1])]) + "</div>", unsafe_allow_html=True)
    drills = [("🏋️", "Weakness drill", f"Train: {P.WEAKNESS_LABEL.get(rec['focus'], 'any skill')}"), ("🧩", "Argument construction", "Claim → evidence → warrant"),
              ("🛡️", "Rebuttal training", "Answer the strongest objection"), ("🧠", "Critical-thinking challenge", f"{rec['difficulty'].title()} motion in {T.CATEGORIES[rec['category']][1]}")]
    st.markdown('<div class="mods" style="margin-top:14px">' + "".join(f'<div class="mod"><div class="ic">{i}</div><div><b>{t}</b><div class="muted">{d}</div></div></div>' for i, t, d in drills) + "</div>", unsafe_allow_html=True)
    if st.button("Claim my rewards →", type="primary", key="to_level"): to("levelup")


def s_levelup(f, user):
    rep = f["finished"]["report"]; li = rep["level"]
    if rep["level_up"]: st.balloons()
    st.markdown(f'<div class="gl" style="text-align:center"><div class="eyebrow">{"LEVEL UP!" if rep["level_up"] else "Debate complete"}</div>'
                f'<div class="xp">+{rep["xp_gained"]}<small>XP</small></div><h3>Level {li["level"]} · {li["name"]}</h3>'
                f'<div class="bar" style="max-width:420px;margin:auto"><i style="width:{li["pct"]*100:.0f}%"></i></div>'
                f'<div class="muted">{"Max level reached" if li["to_next"] is None else str(li["to_next"]) + " XP to " + li["next_name"]}</div></div>', unsafe_allow_html=True)
    st.markdown("".join(f'<div class="callout">＋{v} XP · {k}</div>' for k, v in rep["breakdown"]), unsafe_allow_html=True)
    if rep["badges"]:
        st.markdown("**New badges**<br>" + "".join(f'<div class="badge-t"><span>{P.BADGES[b][0]}</span>{P.BADGES[b][1]}</div>' for b in rep["badges"]), unsafe_allow_html=True)
    stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    rec = P.recommend(stats, user["state"])
    st.markdown(f'<div class="act p"><small>Recommended next debate</small><h4>{T.CATEGORIES[rec["category"]][1]} · {rec["difficulty"].title()}</h4><small>{rec["why"]}</small></div>', unsafe_allow_html=True)
    if st.button("Start next debate →", type="primary", key="next"):
        st.session_state["flow"] = new_flow(rec["category"], rec["difficulty"]); st.rerun()


STAGE_FN = {"topic": s_topic, "coin": s_coin, "setup": s_setup, "arena": s_arena, "diagnosis": s_diagnosis,
            "training": s_training, "profile": s_profile, "improve": s_improve, "levelup": s_levelup}


def render():
    user = ctx.me()
    if not user:
        st.info("Register or log in with a nickname to start your debate journey."); 
        if st.button("Continue", type="primary", key="need_login"): ctx.go("auth")
        return
    f = flow()
    if f["stage"] in ("diagnosis", "training", "improve", "levelup", "profile") and not f["results"]:
        st.session_state["flow"] = f = new_flow()
    st.markdown(stepper_html(f["stage"]), unsafe_allow_html=True)
    STAGE_FN[f["stage"]](f, user)