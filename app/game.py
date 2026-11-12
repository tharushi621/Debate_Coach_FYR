"""Game layer: coin toss, XP, levels, streaks, badges, audience mood.  Pure Python, no UI, fully unit-tested.

Blinding rule (important for the three-arm study): points, badges and audience reactions that depend on the quality
scores are used ONLY when the turn result has display == "full" (the adaptive arm). In the control arms every turn earns the
same participation XP and a neutral applause, so the game never reveals which arm a participant is in.
"""
import secrets

LEVELS = [(0, "Rookie Speaker"), (100, "Confident Voice"), (250, "Rising Debater"),
          (450, "Skilled Advocate"), (700, "Master Orator"), (1000, "Debate Champion")]

PARTICIPATION_XP = 30
STRONG_DIM = 4  # a dimension scored >= 4 earns a small bonus

BADGES = {
    "first_words": ("First Words", "🎤", "Delivered your first argument"),
    "warming_up": ("Warming Up", "🔥", "Completed three turns"),
    "evidence_hunter": ("Evidence Hunter", "🔎", "Evidence quality of 4 or more"),
    "tight_logic": ("Tight Logic", "🧠", "Logical validity of 4 or more"),
    "rebuttal_ready": ("Rebuttal Ready", "🛡️", "Rebuttal readiness of 4 or more"),
    "weakness_slayer": ("Weakness Slayer", "🎯", "Improved the dimension the coach targeted"),
    "new_challenge": ("New Challenge", "🧭", "Fixed a weakness and moved to the next one"),
    "on_fire": ("On Fire", "⚡", "Three improving turns in a row"),
    "standing_ovation": ("Standing Ovation", "👏", "Overall quality of 4 or more"),
}

CHEERS = ["The room is on your side. Say it with confidence.",
          "Every great debater started exactly where you are.",
          "Take a breath. The audience came to hear your point of view.",
          "A strong argument is built one clear step at a time.",
          "They are listening. Make your next point count.",
          "Mistakes are rehearsal here. The crowd loves a comeback."]


def toss(rng=None):
    """Fair coin using the OS entropy source (secrets), not a seeded generator. Heads = proponent, tails = opponent."""
    flip = (rng.randrange(2) if rng is not None else secrets.randbelow(2))
    face = "heads" if flip == 0 else "tails"
    return {"face": face, "side": "proponent" if face == "heads" else "opponent"}


def level_info(xp):
    idx = max(i for i, (need, _) in enumerate(LEVELS) if xp >= need)
    need, title = LEVELS[idx]
    if idx + 1 < len(LEVELS):
        nxt = LEVELS[idx + 1][0]
        pct = (xp - need) / (nxt - need)
    else:
        nxt, pct = None, 1.0
    return {"level": idx + 1, "title": title, "xp": xp, "next_at": nxt, "pct": round(min(max(pct, 0), 1), 3)}


def new_state():
    return {"xp": 0, "streak": 0, "best_streak": 0, "turns": 0, "badges": [], "history": []}


def cheer_for(round_number):
    return CHEERS[(round_number - 1) % len(CHEERS)]


def _audience(overall, full):
    """Return (cheer level 1-3, caption). Always encouraging; level only reflects quality in the full view."""
    if not full:
        return 2, "The audience applauds."
    if overall >= 4:
        return 3, "Standing ovation!"
    if overall >= 3:
        return 2, "Warm applause."
    return 1, "The audience nods: you can build on this."


def apply_turn(state, result):
    """Update the game state from one /debate/turn result. Returns (new_state, report). Does not mutate `state`."""
    st = {**state, "badges": list(state["badges"]), "history": list(state["history"])}
    full = result.get("display") == "full"
    st["turns"] += 1
    before = level_info(st["xp"])
    parts, earned = [], []

    def grant(bid):
        if bid not in st["badges"]:
            st["badges"].append(bid)
            earned.append(bid)

    grant("first_words")
    if st["turns"] >= 3:
        grant("warming_up")

    overall = None
    if full:
        overall = float(result["scores"]["overall_quality"])
        dims = {k: v["score"] for k, v in result["scores"]["dimensions"].items()}
        prog = result.get("progress") or {}
        parts.append(("Argument quality", round(overall / 5 * 60)))
        strong = [k for k, v in dims.items() if v is not None and v >= STRONG_DIM]
        if strong:
            parts.append((f"Strong dimensions x{len(strong[:3])}", 5 * len(strong[:3])))
        improved = prog.get("targeted_improved")
        gained = (prog.get("score_change") or 0) > 0
        if improved:
            parts.append(("Improved the targeted weakness", 25))
            grant("weakness_slayer")
        if prog.get("weakness_changed") and improved:
            parts.append(("Moved on to a new challenge", 10))
            grant("new_challenge")
        st["streak"] = st["streak"] + 1 if (improved or gained) else 0
        st["best_streak"] = max(st["best_streak"], st["streak"])
        if st["streak"] >= 2:
            parts.append((f"Streak x{st['streak']}", 5 * min(st["streak"], 4)))
        if st["streak"] >= 3:
            grant("on_fire")
        if dims.get("evidence_quality", 0) and dims["evidence_quality"] >= 4:
            grant("evidence_hunter")
        if dims.get("logical_validity", 0) and dims["logical_validity"] >= 4:
            grant("tight_logic")
        if dims.get("rebuttal_readiness", 0) and dims["rebuttal_readiness"] >= 4:
            grant("rebuttal_ready")
        if overall >= 4:
            grant("standing_ovation")
    else:
        parts.append(("Participation", PARTICIPATION_XP))

    gained_xp = sum(p for _, p in parts)
    st["xp"] += gained_xp
    after = level_info(st["xp"])
    level, caption = _audience(overall, full)
    st["history"].append({"turn": st["turns"], "xp": gained_xp, "overall": overall if full else None})
    report = {"xp_gained": gained_xp, "breakdown": parts, "badges_earned": earned, "level": after,
              "level_up": after["level"] > before["level"], "cheer_level": level, "audience_caption": caption, "full": full}
    return st, report
