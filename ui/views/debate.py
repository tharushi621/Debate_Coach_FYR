"""The nine-stage debate loop (stages 01–09) as one guided flow."""
import html
import secrets, streamlit as st, streamlit.components.v1 as components
from app import topics as T, progress as P, training as TR
from ui import ctx, charts, coin
from ui.widgets import timer_html, stepper_html
from ui.icons import svg
from ui.toulmin import toulmin_html, score_bars_html, objectives_html
from ui.journey import KEYS
try:  # your existing 3D debate hall (ui/stage.py); optional
    from ui.stage import stage_html
except Exception:  # pragma: no cover
    stage_html = None

# Thesis 7.9: a pilot session is a text-based debate of 5 debate turns.
TURNS, TURN_SECONDS, PREP_SECONDS = 5, 300, 60
# Thesis 4.13.2 palette: blue = interface elements, dark blue = headings and key sections, green = positive feedback,
# progress and success only. The two sides therefore use dark blue and blue, not green.
SIDE_COLOUR = {"FOR": "#0b2a5b", "AGAINST": "#1d5fd1"}


def esc(text):
    """Escape learner or model text before it is placed into raw HTML (unsafe_allow_html)."""
    return html.escape(str(text or "")).replace("\n", "<br>")


def _handle_value(handle, key):
    return handle.get(key) if isinstance(handle, dict) else getattr(handle, key, None)


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
    """Every debate is adaptive. The thesis has no control group (7.12), so there is no random arm assignment."""
    return "adaptive"


def final_scores(f):
    rs = [r for r in f["results"] if r.get("display", "full") == "full" and r.get("scores")]
    if not rs:
        return None
    dims = {d: round(sum((r["scores"].get(d) or 0) for r in rs) / len(rs), 2) for d in P.DIMS}
    last = rs[-1]
    return {"scores": dims, "overall": round(sum(dims.values()) / len(dims), 2), "weakness": last.get("weakness"),
            "explanation": last.get("explanation") or "", "intervention": last.get("intervention"),
            "objective_points": sum(P.turn_objectives(r)[1] for r in rs)}


def feedback_panel(r, idx, expanded=False):
    """Thesis Table 4.13 'Feedback panel': Toulmin structure, scores, weakness and next-step feedback, for one turn."""
    with st.expander(f"Feedback panel · argument {idx}", expanded=expanded):
        for fl in r.get("validation_flags") or []:
            st.info(fl.get("message", ""))
        an = r.get("analysis") or {}
        if an:
            st.markdown(toulmin_html(an, (r.get("affected_component") or None)), unsafe_allow_html=True)
        sc = r.get("scores") or {}
        if sc:
            st.markdown(score_bars_html(sc, r.get("overall")), unsafe_allow_html=True)
            objs, pts = P.turn_objectives(r)
            st.markdown(objectives_html(objs, pts), unsafe_allow_html=True)
        if r.get("weakness"):
            reason = r.get("reason") or r.get("diagnosis_reason")
            st.markdown(f"**Main weakness:** {P.WEAKNESS_LABEL.get(r['weakness'], r['weakness'])}" + (f". {reason}" if reason else ""))
        if r.get("intervention"):
            st.markdown(f"**AI intervention:** {P.INTERVENTION_LABEL.get(r['intervention'], r['intervention'])}")
        pg = r.get("progress") or {}
        if pg.get("previous_score") is not None:
            lab = lambda w: P.WEAKNESS_LABEL.get(w, w)
            st.markdown(f"**Progress:** overall {pg['previous_score']} → {pg['current_score']} ({pg['score_change']:+.2f}). "
                        f"Weakness: {lab(pg.get('previous_weakness'))} → {lab(pg.get('current_weakness'))}.")
            if pg.get("targeted_dimension") and pg.get("targeted_before") is not None:
                verdict = "improved" if pg.get("targeted_improved") else "did not improve"
                st.markdown(f"Targeted dimension ({P.DIM_LABEL.get(pg['targeted_dimension'])}): {pg['targeted_before']} → "
                            f"{pg['targeted_after']}, **{verdict}**.")
        if r.get("feedback"):
            st.markdown(f"**Next step:** {r['feedback']}")


# ------------------------------------------------------------------ stages
def _thesis_motions():
    try:
        return ctx.engine().topics() or T.THESIS_MOTIONS
    except Exception:
        return T.THESIS_MOTIONS


def s_topic(f, user):
    st.markdown("### Choose your battlefield")
    src = st.radio("Where should the motion come from?", ["Project motions", "Browse by category", "Write my own"],
                   horizontal=True, key="topic_src")
    if src == "Project motions":       # thesis 3.10.1: the predefined motions (stored in the database)
        opts = _thesis_motions()
        f["topic"] = st.selectbox("Motion", opts, index=opts.index(f["topic"]) if f["topic"] in opts else 0)
    elif src == "Write my own":         # learner-written motion
        own = st.text_input("Your motion", value="", placeholder="e.g. Cities should ban cars from their centres.")
        f["topic"] = None
        if own:
            try:
                f["topic"] = T.check_motion(own)
            except ValueError as e:
                st.warning(str(e))
    else:
        cols = st.columns(3)
        for i, c in enumerate(T.CATEGORIES):
            ic, name = T.CATEGORIES[c]
            picked = f["category"] == c
            if cols[i % 3].button(name, key=f"cat_{c}", icon=f":material/{ic}:", use_container_width=True, type="primary" if picked else "secondary"):
                f["category"] = c; f["topic"] = None; st.rerun()
        if f["category"] not in T.CATEGORIES:
            st.info("Pick a category to get a motion."); return
        st.markdown("**Difficulty**")
        f["difficulty"] = st.radio("Difficulty", list(T.DIFFICULTIES), horizontal=True, label_visibility="collapsed",
                                   format_func=str.title, index=list(T.DIFFICULTIES).index(f["difficulty"] or "beginner"))
        st.caption(T.DIFFICULTIES[f["difficulty"]])
        pool = T.TOPICS[f["category"]][f["difficulty"]]
        if f["topic"] not in pool:
            f["topic"] = T.pick(f["category"], f["difficulty"], exclude=ctx.me()["state"].get("recent_topics", []))
        if st.button("Suggest another", key="reroll", icon=":material/shuffle:"):
            f["topic"] = T.pick(f["category"], f["difficulty"], exclude=[f["topic"]]); st.rerun()
    if f["category"] not in T.CATEGORIES:
        f["category"] = "custom"
    f["difficulty"] = f["difficulty"] or "beginner"
    if not f["topic"]:
        return
    st.markdown(f'<div class="card"><div class="eyebrow">Your motion</div><h2 style="margin:.2em 0">“{esc(f["topic"])}”</h2></div>',
                unsafe_allow_html=True)
    if st.button("Accept motion →", type="primary", key="accept"):
        to("coin")


def s_coin(f, user):
    st.markdown(f'<div class="card"><div class="eyebrow">Motion</div><b>{f["topic"]}</b></div>', unsafe_allow_html=True)
    components.html(coin.coin_html(f["coin"]), height=300)
    if not f["coin"]:
        st.markdown("**Heads** = you argue **FOR**. **Tails** = you argue **AGAINST**.")
        if st.button("Flip the coin", type="primary", key="flip"):
            f["coin"] = secrets.choice(["heads", "tails"])
            f["side"] = "FOR" if f["coin"] == "heads" else "AGAINST"; st.rerun()
        st.caption("Prefer to pick? Choose your side directly (proponent or opponent):")
        c1, c2 = st.columns(2)
        for col, label, side_ in ((c1, "I argue FOR (proponent)", "FOR"), (c2, "I argue AGAINST (opponent)", "AGAINST")):
            if col.button(label, key=f"pick_{side_}"):
                f["coin"] = "chosen"; f["side"] = side_; st.rerun()
    else:
        col = SIDE_COLOUR[f["side"]]
        st.markdown(f'<div class="card" style="text-align:center"><div class="eyebrow">{"You chose" if f["coin"] == "chosen" else "It landed on " + f["coin"]}</div>'
                    f'<h1 style="color:{col};margin:.1em 0">You argue {f["side"]}</h1>'
                    f'<p class="sub">The AI takes the {"AGAINST" if f["side"]=="FOR" else "FOR"} side.</p></div>', unsafe_allow_html=True)
        if st.button("Go to stage setup →", type="primary", key="to_setup"):
            to("setup")


def s_setup(f, user):
    opp = "AGAINST" if f["side"] == "FOR" else "FOR"
    st.markdown(f'<div class="card"><div class="eyebrow">Briefing</div><h2 style="margin:.2em 0">“{f["topic"]}”</h2>'
                f'<div class="pills"><span class="pill g">You<b>{f["side"]}</b></span><span class="pill b">AI opponent<b>{opp}</b></span>'
                f'<span class="pill">{f["difficulty"].title()}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="pair"><div class="card"><h3>Rules and time</h3>
<div class="rule"><div class="k">1</div><div>{TURNS} rounds. Each round you write one argument, then the AI replies.</div></div>
<div class="rule"><div class="k">2</div><div>{TURN_SECONDS//60} minutes per argument (a guide, the timer does not cut you off).</div></div>
<div class="rule"><div class="k">3</div><div>Aim for claim + evidence + a reason linking them.</div></div>
<div class="rule"><div class="k">4</div><div>There is no winner; you compare with your own past scores.</div></div></div>
<div class="card"><h3>Your objective</h3><p>Defend <b>{f["side"]}</b> convincingly and survive the AI’s sharpest objection.</p>
<h3>Stages</h3><p class="sub">{TURNS} arguments: open, answer each AI counter by strengthening your weakest point, then close. Then your diagnosis.</p></div></div>""", unsafe_allow_html=True)
    st.markdown("#### Preparation")
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
    mine = "for" if f["side"] == "FOR" else "against"
    st.markdown(f'<div class="ah"><div class="ah-top"><span class="eyebrow">Debate arena</span>'
                f'<span class="muted">{n} of {TURNS} arguments sent</span></div>'
                f'<div class="ah-grid"><div class="ah-tile {"on" if not over else ""}"><small>Speaking now</small><b>{"You" if not over else "Debate finished"}</b></div>'
                f'<div class="ah-tile {mine}"><small>Your side</small><b>{f["side"]}</b></div>'
                f'<div class="ah-tile"><small>Round</small><b>{min(n+1, TURNS)} of {TURNS}</b></div></div>'
                f'<div class="bar"><i style="width:{n / TURNS * 100:.0f}%"></i></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="motion-bar"><small>The motion</small><b>{esc(f["topic"])}</b></div>', unsafe_allow_html=True)
    if stage_html:
        side = "proponent" if f["side"] == "FOR" else "opponent"
        last_ai = next((t for w, t in reversed(f["log"]) if w == "ai"), "")
        try:
            components.html(stage_html(side, "you" if not over else "ai", n, f["topic"], "", bubble_ai=last_ai[:140]), height=380)
        except Exception:
            pass
    for who, text in f["log"]:
        k = "you" if who == "you" else "ai"
        st.markdown(f'<div class="msg {k}"><div class="who">{"You" if k=="you" else "AI opponent"}</div>{esc(text)}</div>', unsafe_allow_html=True)
    for i, r in enumerate(f["results"], 1):   # thesis Table 4.13: the feedback panel after each argument
        feedback_panel(r, i, expanded=(i == n))
    if over:
        st.success("Debate complete. Time to see where you can improve.")
        if st.button("Analyse my arguments →", type="primary", key="analyse"):
            to("diagnosis")
        return
    components.html(timer_html(TURN_SECONDS, "Time for this argument", f"t{n}"), height=70)
    with st.form(f"arg{n}", clear_on_submit=False):
        text = st.text_area("Your argument", height=150, key=f"argtxt{n}",
                            placeholder="State your claim, give evidence, and explain why it supports your claim…")
        go_ = st.form_submit_button("Send argument", type="primary")
    if go_:
        if len(text.split()) < 5:
            st.warning("Write at least a sentence so the AI has something to analyse."); return
        with st.spinner("The AI is analysing your argument and preparing a rebuttal… (local models can take a few minutes)"):
            try:
                r = ctx.engine().turn(f["handle"], text.strip())
            except ValueError as e:  # HTTP 400 from validation: the learner can fix it
                st.warning(f"Please revise your argument: {e}"); return
            except Exception as e:
                st.error(f"The backend returned an error: {e}"); return
        f["results"].append(r)
        f["log"] += [("you", text.strip()), ("ai", r.get("opponent") or "(no reply)")]
        st.rerun()
    if n >= 1 and st.button("Finish early", key="finish_early"):
        to("diagnosis")


def s_diagnosis(f, user):
    fs = final_scores(f)
    if not fs:
        st.info("No analysis is available for this debate. Your debate is saved. Continue to your profile.")
        if st.button("Continue →", type="primary", key="skipdiag"):
            f["train"]["done"] = True; to("profile")
        return
    f["fs"] = fs
    st.markdown('<div class="card"><div class="eyebrow">Weakness diagnosis</div>'
                f'<h2 style="margin:.2em 0">Your main gap: {P.WEAKNESS_LABEL.get(fs["weakness"], fs["weakness"])}</h2>'
                f'<p class="sub">{esc(fs["explanation"]) or "This was the lowest-scoring part of your reasoning."}</p></div>', unsafe_allow_html=True)
    turns = [r["overall"] for r in f["results"] if r.get("overall") is not None]
    if len(turns) > 1:   # thesis Table 4.13 'Progress dashboard': score changes across turns
        st.markdown('<div class="card" style="margin-top:14px"><h3>Score across your turns</h3>' + charts.line_svg(turns) + "</div>",
                    unsafe_allow_html=True)
    rs = f["results"]; ov = [r["overall"] for r in rs if r.get("overall") is not None]
    ivs = [P.INTERVENTION_LABEL.get(r.get("intervention"), r.get("intervention")) for r in rs if r.get("intervention")]
    ws = [P.WEAKNESS_LABEL.get(r.get("weakness"), r.get("weakness")) for r in rs if r.get("weakness")]
    improved = [r["progress"]["targeted_improved"] for r in rs[1:] if (r.get("progress") or {}).get("targeted_improved") is not None]
    st.markdown('<div class="card" style="margin-top:14px"><h3>Progress report</h3>'
                f'<p>Arguments completed: <b>{len(rs)}</b>' + (f' · Initial score <b>{ov[0]}</b> → final <b>{ov[-1]}</b> ({ov[-1]-ov[0]:+.2f})' if ov else "") + '</p>'
                + (f'<p>Targeted weakness improved in <b>{sum(improved)}</b> of {len(improved)} later turns.</p>' if improved else "")
                + (f'<p>Remaining weakness (last turn): <b>{esc(ws[-1])}</b></p>' if ws else "")
                + (f'<p>Interventions received: {esc(", ".join(dict.fromkeys(ivs)))}</p>' if ivs else "") + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="card" style="margin-top:14px">' + charts.radar_svg(fs["scores"], P.DIMS, center=fs["overall"]) + "</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>" + charts.score_cards(fs["scores"], P.DIMS), unsafe_allow_html=True)
    ex = f["results"][-1].get("explanations") or {}
    if any(ex.values()):
        with st.expander("Why these scores? Explanations for each dimension"):
            for d in P.DIMS:
                if ex.get(d):
                    st.markdown(f"**{P.DIM_LABEL[d]}**: {ex[d]}")
    low = sorted(fs["scores"], key=fs["scores"].get)[:2]
    st.markdown(f'<div class="callout" style="margin-top:14px"><b>Focus next:</b> {", ".join(P.DIM_LABEL[d] for d in low)}.</div>',
                unsafe_allow_html=True)
    if f["results"][-1].get("guardrail_fallback"):
        st.caption("The AI’s last reply used a safe template because the model’s draft failed a quality check.")
    if st.button("Train this weakness →", type="primary", key="to_train"):
        to("training")


def s_training(f, user):
    fs = f["fs"]; kind = P.TRAIN_KIND.get(fs["weakness"], "logic"); tr = f["train"]
    ex = TR.exercise_for(kind, tr["attempt"])
    st.markdown(f'<div class="card"><div class="eyebrow">AI counterargument training · {kind}</div><h2 style="margin:.2em 0">{ex["title"]}</h2>'
                f'<p style="white-space:pre-line">{ex["prompt"]}</p><div class="muted">Hint: {ex["hint"]}</div></div>', unsafe_allow_html=True)
    txt = st.text_area("Your answer", key=f"tr{tr['attempt']}_{tr.get('n',0)}", height=120)
    a, b = st.columns(2)
    if a.button("Check my answer", type="primary", key="check"):
        res = TR.evaluate(kind, txt)
        tr["last"] = res; tr["n"] = tr.get("n", 0)
        u = ctx.me()
        first = not any(t["passed"] for t in ctx.store().training(u["id"]))
        wd = P.WEAKNESS_DIM.get(fs["weakness"])
        # the badge needs the exercise to train the learner's weakest dimension (before: wd was passed twice, so any pass earned it)
        state, rep = P.training_result(u["state"], wd, TR.KIND_DIM.get(kind), res["passed"], first)
        ctx.store().save_state(u["id"], state)
        ctx.store().add_training(u["id"], fs["weakness"], kind, res["passed"], res["score"], tr["attempt"] + 1)
        tr["rep"] = rep; tr["done"] = tr["done"] or res["passed"]
    res = tr.get("last")
    if res:
        for lab, ok, tip in res["checks"]:
            st.markdown(f'<div class="callout {"green" if ok else ""}"><span class="qi">{svg("check", 16) if ok else svg("alert", 16)}</span> <b>{lab}</b>{"" if ok else ": " + tip}</div>',
                        unsafe_allow_html=True)
        st.markdown(f'<div class="callout"><b>Feedback:</b> {res["feedback"]} &nbsp; <b>+{tr["rep"]["xp_gained"]} XP</b></div>',
                    unsafe_allow_html=True)
        if tr["rep"]["badges"]:
            st.balloons()
        c, d = st.columns(2)
        if c.button("Try another exercise", key="retry", icon=":material/refresh:"):
            tr["attempt"] += 1; tr["last"] = None; st.rerun()
        if d.button("Update my profile →", type="primary", key="to_profile"):
            to("profile")


def s_profile(f, user):
    if not f.get("finished"):
        fs = f.get("fs") or {"scores": {}, "overall": None, "weakness": None}
        full = bool(f.get("fs"))
        hist = ctx.store().debates(user["id"])
        rec = {"topic": f["topic"], "category": f["category"], "difficulty": f["difficulty"], "overall": fs["overall"],
               "scores": fs["scores"], "objective_points": fs.get("objective_points", 0)}
        state, rep = P.finish_debate(user["state"], rec, hist, full)
        ctx.store().save_state(user["id"], state)
        # session_id / backend_user_id link platform.db to debate.db (needed to review the arguments of a past debate)
        ctx.store().add_debate(user["id"], {**rec, "side": f["side"], "turns": len(f["results"]), "weakness": fs["weakness"],
                                            "outcome": rep["outcome"], "xp": rep["xp_gained"],
                                            "session_id": _handle_value(f["handle"], "session_id"),
                                            "backend_user_id": _handle_value(f["handle"], "user_id")})
        try:
            ctx.engine().end(f["handle"])      # session status -> ended (thesis 4.11.1 end_session)
        except Exception:
            pass
        f["finished"] = {"report": rep, "prev": hist[-1]["overall"] if hist else None, "overall": fs["overall"]}
        user = ctx.me()
    fin = f["finished"]; stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    st.markdown('<div class="eyebrow">Profile updated</div><h2 style="margin:.1em 0">Your record just grew.</h2>', unsafe_allow_html=True)
    prev, now = fin["prev"], fin["overall"]
    delta = "" if prev is None or now is None else f' ({now-prev:+.2f} vs last debate)'
    li = P.level_info(user["state"]["xp"])
    st.markdown(f'<div class="pills"><span class="pill g">Level<b>{li["level"]} · {li["name"]}</b></span><span class="pill b">Debates<b>{stats["debates"]}</b></span>'
                f'<span class="pill">Overall<b>{("%.2f" % now) if now else "n/a"}{delta}</b></span>'
                f'<span class="pill">Streak<b>{P.days(user["state"]["streak"])}</b></span></div>', unsafe_allow_html=True)
    if stats["skills"]:
        st.markdown(charts.score_cards(stats["skills"], list(stats["skills"]), {k: k for k in stats["skills"]}), unsafe_allow_html=True)
    if st.button("See how to improve →", type="primary", key="to_improve"):
        to("improve")


def s_improve(f, user):
    stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    rec = P.recommend(stats, user["state"])
    st.markdown(f'<div class="card"><div class="eyebrow">Skill improvement</div><h2 style="margin:.2em 0">Your personalised path</h2>'
                f'<p class="sub">{rec["why"]}</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="pair"><div class="card"><h3>Progress over time</h3>' + charts.line_svg(stats["trend"]) + "</div>"
                '<div class="card"><h3>Recurring weaknesses</h3>' + charts.hbars(
        [(P.WEAKNESS_LABEL.get(k, k), v) for k, v in sorted(stats["weak_counts"].items(), key=lambda x: -x[1])]) + "</div></div>",
                unsafe_allow_html=True)
    drills = [(svg("dumbbell", 20), "Weakness drill", f"Train: {P.WEAKNESS_LABEL.get(rec['focus'], 'any skill')}"),
              (svg("layers", 20), "Argument construction", "Claim → evidence → warrant"),
              (svg("shield", 20), "Rebuttal training", "Answer the strongest objection"),
              (svg("scale", 20), "Critical thinking challenge", f"{rec['difficulty'].title()} motion in {T.CATEGORIES[rec['category']][1]}")]
    st.markdown('<div class="mods" style="margin-top:14px">' + "".join(
        f'<div class="mod"><div class="ic">{i}</div><div><b>{t}</b><div class="muted">{d}</div></div></div>' for i, t, d in drills) + "</div>",
        unsafe_allow_html=True)
    if st.button("Claim my rewards →", type="primary", key="to_level"):
        to("levelup")


def s_levelup(f, user):
    rep = f["finished"]["report"]; li = rep["level"]
    if rep["level_up"]:
        st.balloons()
    st.markdown(f'<div class="card" style="text-align:center"><div class="eyebrow">{"LEVEL UP!" if rep["level_up"] else "Debate complete"}</div>'
                f'<div class="xp">+{rep["xp_gained"]}<small>XP</small></div><h3>Level {li["level"]} · {li["name"]}</h3>'
                f'<div class="bar" style="max-width:420px;margin:auto"><i style="width:{li["pct"]*100:.0f}%"></i></div>'
                f'<div class="muted">{"Max level reached" if li["to_next"] is None else str(li["to_next"]) + " XP to " + li["next_name"]}</div></div>',
                unsafe_allow_html=True)
    st.markdown("".join(f'<div class="callout green">＋{v} XP · {k}</div>' for k, v in rep["breakdown"]), unsafe_allow_html=True)
    if rep["badges"]:
        st.markdown("**New badges**<br>" + "".join(f'<div class="badge-t"><span>{svg(P.BADGES[b][0], 28)}</span>{P.BADGES[b][1]}</div>' for b in rep["badges"]),
                    unsafe_allow_html=True)
    stats = P.profile_stats(ctx.store().debates(user["id"]), ctx.store().training(user["id"]))
    rec = P.recommend(stats, user["state"])
    st.markdown(f'<div class="tile blue"><small>Recommended next debate</small><h4>{T.CATEGORIES[rec["category"]][1]} · '
                f'{rec["difficulty"].title()}</h4><small>{rec["why"]}</small></div>', unsafe_allow_html=True)
    with st.expander("Rate this debate (pilot questionnaire)"):
        if f.get("rated"):
            st.success("Thank you, your ratings were saved.")
        else:
            labels = ["Ease of use", "Clarity of feedback", "Relevance of the AI's responses", "Helpful for spotting my weakness",
                      "Helpful for improving my next argument", "Fairness of the assessment", "I would use it again"]
            vals = [st.slider(l, 1, 5, 3, key=f"rate{i}") for i, l in enumerate(labels)]
            note = st.text_area("Comment (optional)", key="rate_note")
            if st.button("Submit ratings", key="rate_go"):
                try:
                    ctx.engine().rate(f["handle"], vals, note); f["rated"] = True; st.rerun()
                except Exception as e:
                    st.error(f"Could not save ratings: {e}")
    if st.button("Start next debate →", type="primary", key="next"):
        st.session_state["flow"] = new_flow(rec["category"], rec["difficulty"]); st.rerun()


STAGE_FN = {"topic": s_topic, "coin": s_coin, "setup": s_setup, "arena": s_arena, "diagnosis": s_diagnosis,
            "training": s_training, "profile": s_profile, "improve": s_improve, "levelup": s_levelup}


def render():
    user = ctx.me()
    if not user:
        st.info("Register or log in with a nickname to start your debate journey.")
        if st.button("Continue", type="primary", key="need_login"):
            ctx.go("auth")
        return
    f = flow()
    if f["stage"] in ("diagnosis", "training", "improve", "levelup", "profile") and not f["results"]:
        st.session_state["flow"] = f = new_flow()
    st.markdown(stepper_html(f["stage"]), unsafe_allow_html=True)
    STAGE_FN[f["stage"]](f, user)