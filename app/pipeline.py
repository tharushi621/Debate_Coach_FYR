"""One debate turn = the closed loop (thesis 4.8.1).

mode="adaptive": diagnosis -> intervention -> targeted opponent reply.
mode="generic":  same analysis/scoring, but the opponent gives an untargeted
                 counterargument. This is the control condition for the A/B study.
"""
from . import agents
from .taxonomy import DIMENSIONS
from .validation import soft_flags, validate

GENERIC_REPLY = ("I disagree with your position. There are strong arguments on the other side of this motion, "
                 "and I think they outweigh yours. Can you respond to that and continue your case?")


def process_turn(db, llm, session_id, argument):
    sess = db.get_session(session_id)
    if not sess:
        raise KeyError("session not found")
    topic, side, mode = sess["topic"], sess["student_side"], sess["mode"]
    history = db.previous_arguments(session_id)
    clean = validate(argument, topic, history)

    analysis = agents.analyse(llm, topic, side, history, clean)
    scores = agents.score(llm, topic, side, analysis, clean)
    diagnosis = agents.diagnose(scores, clean, analysis, llm=llm, topic=topic, side=side)

    previous = db.last_turn(session_id)
    repeats = sum(1 for h in db.history(session_id) if h["weakness"] == diagnosis["lowest_weakness"])
    prev_weak = previous["weakness"] if previous else None

    # Measurement (analysis/scores/diagnosis) is identical in every arm so outcomes are comparable;
    # only what the student SEES and how the opponent replies differs.
    if mode == "adaptive":
        intervention = agents.strategise(diagnosis, prev_weak, repeats)
        reply, used_fallback = agents.oppose(llm, topic, side, clean, analysis, diagnosis, intervention)
        fb, display = agents.feedback(scores, diagnosis), "full"
    elif mode == "single":
        intervention = {"type": "single_prompt", "description": "One un-decomposed LLM call (baseline)."}
        fb, reply = agents.single_prompt_baseline(llm, topic, side, clean)
        used_fallback, display = False, "feedback_reply"
    else:  # generic
        intervention = {"type": "generic_counter", "description": "Untargeted counterargument (control condition)."}
        reply, used_fallback, fb, display = GENERIC_REPLY, False, "", "reply_only"
    number = db.next_turn_number(session_id)
    tid = db.save_turn(session_id, number, clean, analysis, scores, diagnosis, intervention, reply, fb, used_fallback)
    progress = agents.track(scores, diagnosis, previous)
    return {"turn_id": tid, "turn_number": number, "analysis": analysis, "scores": scores, "diagnosis": diagnosis,
            "intervention": intervention, "ai_opponent_response": reply, "guardrail_fallback": used_fallback,
            "feedback": fb, "progress": progress, "display": display, "mode": mode,
            "validation_flags": soft_flags(clean, topic, analysis)}
