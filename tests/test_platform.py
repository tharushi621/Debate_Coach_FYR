import datetime as dt, pytest
from app import progress as P, topics as T, training as TR
from app.platform_store import Store

D = dt.date(2026, 11, 14)

def test_nickname_rules_and_availability():
    s = Store(":memory:")
    assert s.check_nickname("ab") and s.check_nickname("bad name!") and not s.check_nickname("good_one")
    uid, tok = s.register("Quick_Fox")
    assert not s.available("quick_fox")            # case-insensitive
    with pytest.raises(ValueError): s.register("QUICK_FOX")
    assert s.user_for_token(tok) == uid

def test_token_hashed_expires_and_logout():
    s = Store(":memory:"); uid, tok = s.register("tharu")
    raw = [r[0] for r in s.db.execute("SELECT hash FROM tokens")]
    assert tok not in raw                           # only hash stored
    s.db.execute("UPDATE tokens SET expires=0"); assert s.user_for_token(tok) is None
    _, t2 = s.login("tharu"); assert s.user_for_token(t2) == uid
    s.logout(t2); assert s.user_for_token(t2) is None
    with pytest.raises(ValueError): s.login("nobody")

def test_levels_monotonic():
    assert P.level_info(0)["level"] == 1 and P.level_info(2200)["to_next"] is None
    assert [P.level_info(x)["level"] for x in (0, 150, 400, 800, 1400, 2200)] == [1, 2, 3, 4, 5, 6]

def test_streak():
    s = {"streak": 0, "best_streak": 0, "last_day": None}
    P.touch_streak(s, D); P.touch_streak(s, D)
    assert s["streak"] == 1
    P.touch_streak(s, D + dt.timedelta(1)); assert s["streak"] == 2
    P.touch_streak(s, D + dt.timedelta(5)); assert s["streak"] == 1 and s["best_streak"] == 2

def _deb(**kw):
    base = dict(topic="t", category="technology", difficulty="beginner", overall=3.0,
                scores={d: 3 for d in P.DIMS}, weakness="missing_warrant")
    base.update(kw); return base

def test_blinding_no_quality_xp_for_control_arms():
    st = {"xp": 0, "streak": 0, "best_streak": 0, "badges": [], "last_day": None, "recent_topics": []}
    hi = _deb(scores={d: 5 for d in P.DIMS}, overall=5)
    _, rep = P.finish_debate(st, hi, [], full=False, today=D)
    assert rep["xp_gained"] == P.PARTICIPATION_XP and rep["badges"] == ["first_words"] and rep["outcome"] == "n/a"
    _, rep2 = P.finish_debate(st, hi, [], full=True, today=D)
    assert rep2["xp_gained"] > P.PARTICIPATION_XP and "evidence_hunter" in rep2["badges"]

def test_finish_debate_does_not_mutate_and_levels_up():
    st = {"xp": 120, "streak": 0, "best_streak": 0, "badges": [], "last_day": None, "recent_topics": []}
    snap = dict(st)
    s2, rep = P.finish_debate(st, _deb(), [], True, today=D)
    assert st == snap and rep["level_up"] and s2["xp"] > 150

def test_outcome_labels():
    assert P.outcome(None, 3) == "baseline" and P.outcome(3, 3.5) == "improved"
    assert P.outcome(3, 3.05) == "held" and P.outcome(3, 2.5) == "dipped"

def test_training_feedback_is_actionable():
    bad = TR.evaluate("evidence", "Cities are good.")
    assert not bad["passed"] and "Add" in bad["feedback"] or "Say" in bad["feedback"]
    good = TR.evaluate("evidence", "According to a 2021 WHO study, cities with cycle lanes saw 12% fewer obesity cases, which supports the claim.")
    assert good["passed"]
    assert TR.evaluate("rebuttal", "Granted, shops may lose some parking customers, but footfall rises because pedestrians spend more.")["passed"]

def test_every_weakness_has_a_training_family():
    for w, k in P.TRAIN_KIND.items():
        assert TR.exercise_for(k)["prompt"]

def test_topics_complete_and_no_repeat():
    for c in T.CATEGORIES:
        for d in T.DIFFICULTIES: assert len(T.TOPICS[c][d]) >= 2
    a = T.TOPICS["science"]["advanced"][0]
    assert T.pick("science", "advanced", exclude=[a]) != a

def test_recommend_steps_up_and_changes_category():
    s = Store(":memory:"); uid, _ = s.register("kate")
    s.add_debate(uid, _deb(overall=4.4, difficulty="beginner"))
    stats = P.profile_stats(s.debates(uid), [])
    r = P.recommend(stats, {"recent_topics": []})
    assert r["difficulty"] == "intermediate" and r["category"] != "technology"


# ---- ApiEngine against the REAL response shapes of app/api.py + app/pipeline.py
class _Resp:
    def __init__(self, code, body): self.status_code, self._b, self.text = code, body, str(body)
    def json(self): return self._b


def _engine(routes):
    import sys, types
    sys.path.insert(0, ".")
    from ui.engine import ApiEngine
    e = ApiEngine(base="http://x")
    calls = []
    def post(url, json=None, timeout=None):
        calls.append((url, json)); out = routes[url.replace("http://x", "")](json); return out if isinstance(out, _Resp) else _Resp(200, out)
    e.requests = types.SimpleNamespace(post=post, exceptions=types.SimpleNamespace(RequestException=OSError))
    return e, calls


TURN = {"turn_id": 1, "turn_number": 1, "analysis": {}, "diagnosis": {"lowest_weakness": "missing_warrant", "diagnosis_reason": "The link is not explained.", "dimension": "warrant_strength"},
        "scores": {"dimensions": {d: {"score": 3, "explanation": f"why {d}"} for d in P.DIMS} | {"warrant_strength": {"score": 2, "explanation": "no link"}}, "overall_quality": 2.86},
        "intervention": {"type": "warrant_challenge_question", "description": "..."}, "ai_opponent_response": "Why does that follow?",
        "guardrail_fallback": False, "feedback": "Strength: ...", "progress": {}, "display": "full", "mode": "adaptive", "validation_flags": []}


def test_api_engine_maps_real_shapes():
    e, calls = _engine({"/users": lambda j: {"user_id": 7}, "/sessions": lambda j: {"session_id": 11, "mode": "adaptive"},
                        "/debate/turn": lambda j: TURN})
    h = e.start("Voting should be compulsory.", "FOR", "adaptive", nickname="tharu")
    r = e.turn(h, "An argument.")
    assert calls[0] == ("http://x/users", {"name": "tharu"})
    assert calls[1][1] == {"user_id": 7, "topic": "Voting should be compulsory.", "student_side": "proponent", "mode": "adaptive"}
    assert calls[2][1] == {"session_id": 11, "argument": "An argument."}
    assert r["overall"] == 2.86 and r["weakness"] == "missing_warrant" and r["scores"]["warrant_strength"] == 2
    assert r["intervention"] == "warrant_challenge_question" and r["opponent"] == "Why does that follow?"
    assert r["explanations"]["warrant_strength"] == "no link"


def test_api_engine_error_kinds_and_side_mapping():
    e, calls = _engine({"/users": lambda j: {"user_id": 1}, "/sessions": lambda j: {"session_id": 2},
                        "/debate/turn": lambda j: _Resp(400, {"detail": "Argument too short."})})
    e.requests.post = lambda url, json=None, timeout=None: (_Resp(200, {"user_id": 1, "session_id": 2}) if "debate" not in url else _Resp(400, {"detail": "Argument too short."}))
    h = e.start("t", "AGAINST", "adaptive", nickname="a")
    with pytest.raises(ValueError, match="too short"): e.turn(h, "x")
