"""A running app must pick up edits to app/ without a restart (a stale app.progress once crashed the Progress and Profile pages)."""
import sys
import types

from streamlit.testing.v1 import AppTest

import os
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "streamlit_app.py")


def test_stale_cached_modules_are_replaced_on_the_next_run(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "p.db"))
    monkeypatch.setenv("ENGINE", "demo")
    for name in [m for m in sys.modules if m == "app" or m.startswith(("app.", "ui."))]:
        del sys.modules[name]
    from app.platform_store import Store
    store = Store(str(tmp_path / "p.db"))
    uid, tok = store.register("tester")
    scores = {"claim_clarity": 4, "evidence_quality": 2, "warrant_strength": 3, "relevance": 5, "rebuttal_readiness": 2,
              "logical_validity": 4, "qualification": 3}
    store.add_debate(uid, {"topic": "Voting should be compulsory.", "category": "politics", "difficulty": "beginner", "side": "FOR",
                           "turns": 5, "overall": 3.2, "weakness": "weak_rebuttal", "scores": scores, "outcome": "baseline", "xp": 50})
    # simulate the old process: an outdated app.progress (no mastery, emoji badge names) is already cached
    stale = types.ModuleType("app.progress")
    stale.BADGES = {"first_words": ("\U0001F3A4", "First Words", "x")}
    sys.modules["app.progress"] = stale
    sys._argumind_stamp = None
    for page in ("progress", "profile"):
        at = AppTest.from_file(SCRIPT, default_timeout=60)
        at.session_state["token"] = tok
        at.session_state["page"] = page
        at.run()
        assert not at.exception, [str(e.value) for e in at.exception]
        assert hasattr(sys.modules["app.progress"], "mastery")
