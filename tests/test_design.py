"""Design-layer checks: no emoji in the interface, safe HTML, objectives, skill tiers, XP integration."""
import glob
import re

from app import progress as P
from ui.toulmin import mastery_html, objectives_html, score_bars_html, toulmin_html

EMOJI = re.compile("[\U0001F000-\U0001FAFF⌀-⏿☀-➿⬀-⯿️‍✅✓✨]")


def test_no_emoji_anywhere_in_the_interface_code():
    files = glob.glob("ui/**/*.py", recursive=True) + ["app/progress.py", "app/topics.py", "app/training.py"]
    bad = {f: sorted(set(EMOJI.findall(open(f, encoding="utf-8").read()))) for f in files}
    assert {f: v for f, v in bad.items() if v} == {}


def test_argument_map_marks_found_missing_and_the_main_gap_and_escapes_text():
    an = {"main_claim": "<script>alert(1)</script>", "grounds": ["a study"], "warrant": None, "backing": None}
    h = toulmin_html(an, "warrant")
    assert "<script>" not in h and "&lt;script&gt;" in h
    assert h.count("tm-c ok") == 2 and "Main gap" in h and "2 of 6 components found" in h and "\n" not in h


def test_objectives_follow_the_scores_and_award_points():
    r = {"scores": {"claim_clarity": 4, "evidence_quality": 3, "warrant_strength": 2, "rebuttal_readiness": 3, "qualification": 1},
         "analysis": {"grounds": ["x"]}}
    objs, pts = P.turn_objectives(r)
    assert [m for _, m, _ in objs] == [True, True, False, True, False] and pts == 3 * P.OBJECTIVE_POINTS
    assert P.turn_objectives({"scores": {}, "analysis": {}})[1] == 0
    assert "3 points" not in objectives_html(objs, pts) and "12 points" in objectives_html(objs, pts)


def test_mastery_tiers_and_progress_to_the_next_tier():
    assert P.mastery(None) is None
    assert P.mastery(1.2)["tier"] == "Foundation" and P.mastery(3.5)["tier"] == "Proficient" and P.mastery(4.8)["next"] is None
    m = P.mastery(3.6)
    assert m["next"] == "Advanced" and 0 < m["pct"] < 1 and m["to_next"] == 0.4
    assert "Proficient" in mastery_html({"evidence_quality": 3.5}) and "Complete a debate" in mastery_html({})


def test_objective_points_become_xp_only_when_the_full_report_is_shown():
    s0 = {"xp": 0, "streak": 0, "best_streak": 0, "badges": [], "last_day": None, "recent_topics": [], "quests_done": []}
    d = {"scores": {"evidence_quality": 3}, "overall": 3.0, "category": "technology", "topic": "t", "objective_points": 20}
    s1, rep = P.finish_debate(s0, d, [], True)
    assert ("Round objectives met", 20) in rep["breakdown"] and rep["xp_gained"] == P.PARTICIPATION_XP + 20
    _, blind = P.finish_debate(s0, d, [], False)
    assert blind["xp_gained"] == P.PARTICIPATION_XP


def test_score_bars_use_tone_classes():
    h = score_bars_html({"claim_clarity": 5, "evidence_quality": 3, "warrant_strength": 1}, 3.0)
    assert 'bar hi' in h and 'bar mid' in h and 'bar lo' in h and "Overall <b>3</b>" in h


def test_ai_notice_is_not_repeated_on_result_pages_but_stays_on_the_how_it_works_page():
    """Thesis NFR09 is met once, quietly (How it works). Result pages carry no boilerplate caption."""
    for f in ("ui/views/debate.py", "ui/views/profile.py", "ui/views/progress.py"):
        assert "DISCLAIMER" not in open(f, encoding="utf-8").read(), f
    assert "AI-generated and can contain errors" in open("ui/views/how.py", encoding="utf-8").read()
