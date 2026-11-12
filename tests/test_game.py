import random

from app import game
from ui.stage import coin_html, stage_html


def res(overall=4.2, display="full", improved=None, change=None, changed=None, **dims):
    d = {k: {"score": 3} for k in ("evidence_quality", "logical_validity", "rebuttal_readiness")}
    d.update({k: {"score": v} for k, v in dims.items()})
    return {"display": display, "scores": {"overall_quality": overall, "dimensions": d},
            "progress": {"targeted_improved": improved, "score_change": change, "weakness_changed": changed}}


def test_toss_is_fair_and_maps_sides():
    out = [game.toss() for _ in range(2000)]
    heads = sum(o["face"] == "heads" for o in out)
    assert 850 < heads < 1150
    assert all((o["side"] == "proponent") == (o["face"] == "heads") for o in out)
    assert game.toss(random.Random(1)) == game.toss(random.Random(1))  # injectable for tests


def test_levels():
    assert game.level_info(0)["level"] == 1
    assert game.level_info(100)["title"] == "Confident Voice"
    assert game.level_info(5000)["pct"] == 1.0 and game.level_info(5000)["next_at"] is None
    assert 0 < game.level_info(150)["pct"] < 1


def test_full_turn_points_badges_and_no_mutation():
    s0 = game.new_state()
    s1, rep = game.apply_turn(s0, res(4.2, improved=True, change=0.5, changed=True, evidence_quality=4))
    assert s0["xp"] == 0 and s0["badges"] == []  # input untouched
    names = {l for l, _ in rep["breakdown"]}
    assert "Improved the targeted weakness" in names and "Moved on to a new challenge" in names
    assert {"first_words", "weakness_slayer", "new_challenge", "evidence_hunter", "standing_ovation"} <= set(s1["badges"])
    assert rep["xp_gained"] == s1["xp"] > 60 and rep["cheer_level"] == 3


def test_streak_builds_and_resets():
    s = game.new_state()
    for _ in range(3):
        s, rep = game.apply_turn(s, res(3.0, improved=True, change=0.2))
    assert s["streak"] == 3 and "on_fire" in s["badges"] and "warming_up" in s["badges"]
    s, _ = game.apply_turn(s, res(2.0, improved=False, change=-0.5))
    assert s["streak"] == 0 and s["best_streak"] == 3


def test_blinded_arms_get_flat_xp_and_no_quality_signal():
    """Control arms must not reveal quality through points, badges or audience."""
    for display in ("feedback_reply", "reply_only"):
        low, hi = game.new_state(), game.new_state()
        low, r_low = game.apply_turn(low, res(1.0, display=display))
        hi, r_hi = game.apply_turn(hi, res(5.0, display=display, evidence_quality=5))
        assert r_low["xp_gained"] == r_hi["xp_gained"] == game.PARTICIPATION_XP
        assert r_low["cheer_level"] == r_hi["cheer_level"] == 2
        assert set(low["badges"]) == set(hi["badges"]) == {"first_words"}


def test_low_score_still_encouraging():
    _, rep = game.apply_turn(game.new_state(), res(1.5))
    assert rep["cheer_level"] == 1 and "build" in rep["audience_caption"] and rep["xp_gained"] > 0


def test_level_up_flag():
    s = game.new_state()
    s["xp"] = 95
    _, rep = game.apply_turn(s, res(4.0))
    assert rep["level_up"] and rep["level"]["level"] >= 2


def test_stage_html_roles_and_escaping():
    h = stage_html("opponent", "you", 3, "<script>x</script>", "ok", bubble_ai="<b>hi</b>")
    assert "<script>x" not in h and "&lt;script&gt;" in h and "&lt;b&gt;hi" in h
    assert "YOUR TURN" in h and "cheer3" in h
    # opponent student stands stage-right; proponent AI stage-left
    assert h.index("AI OPPONENT") < h.index(">YOU<")
    assert stage_html("proponent", "ai", 1).count("SPEAKING") == 1
    assert "beam on" in stage_html("proponent", None, 1) or "beam off" in stage_html("proponent", None, 1)


def test_coin_html_modes():
    assert 'RESULT = null' in coin_html(None)
    assert 'RESULT = "heads"' in coin_html("heads") and 'RESULT = "tails"' in coin_html("tails")
    try:
        coin_html("edge")
        raise AssertionError("should reject")
    except ValueError:
        pass
