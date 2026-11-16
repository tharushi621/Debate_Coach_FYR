"""FastAPI backend. Run: uvicorn app.api:app --port 8000     (interactive docs: http://127.0.0.1:8000/docs)

Endpoints (thesis Table 6.3): GET /topics, POST /users, POST /sessions, POST /debate/turn, GET /sessions/{id}/next-turn.
Also: GET /health, GET /sessions/{id}/history, POST /feedback (the pilot questionnaire, thesis 7.9).
Env: LLM_BACKEND=ollama|openai, ORCHESTRATOR=crewai|python, DEBATE_DB=debate.db, WARMUP=1|0
"""
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .db import Database
from .llm import make_llm
from .pipeline import process_turn
from .validation import ValidationError

from .topics import THESIS_MOTIONS, check_motion  # noqa: E402


def build_app(db=None, llm=None):
    app = FastAPI(title="Weakness Targeted Adaptive Debate System")
    app.state.db = db or Database(os.getenv("DEBATE_DB", "debate.db"))
    app.state.llm = llm or make_llm()      # raises on an unknown LLM_BACKEND: no silent mock
    app.state.warm = {"state": "idle", "seconds": None}

    @app.on_event("startup")
    def _warm():
        """Load the model into memory in the background so the first student turn is not the slow one."""
        m = app.state.llm
        if os.getenv("WARMUP", "1") == "1" and hasattr(m, "warm_up"):
            def go():
                app.state.warm["state"] = "loading"
                try:
                    app.state.warm["seconds"] = round(m.warm_up(), 1)
                    app.state.warm["state"] = "ready"
                except Exception as e:     # not fatal: the first real turn will report the problem
                    app.state.warm["state"] = f"failed: {e}"
            threading.Thread(target=go, daemon=True).start()

    class UserIn(BaseModel):
        name: str
        role: str = "student"

    class SessionIn(BaseModel):
        user_id: int
        topic: str
        student_side: str
        mode: str = "adaptive"       # kept for client compatibility; only "adaptive" exists (thesis 7.12: no control group)

    class TurnIn(BaseModel):
        session_id: int
        argument: str

    class FeedbackIn(BaseModel):
        user_id: int
        session_id: int
        ease_of_use: int
        clarity: int
        ai_relevance: int
        weakness_help: int
        improvement_help: int
        fairness: int
        reuse: int
        comment: str = ""

    @app.get("/health")
    def health():
        m = app.state.llm
        return {"ok": True, "llm": getattr(m, "name", "?"), "model": getattr(m, "model", "n/a"),
                "orchestrator": os.getenv("ORCHESTRATOR", "crewai"), "warm_up": app.state.warm}

    @app.get("/topics")
    def topics():
        return app.state.db.topics()

    class TopicIn(BaseModel):
        motion: str

    @app.post("/topics")
    def add_topic(t: TopicIn):
        try:
            return {"motion": app.state.db.add_topic(check_motion(t.motion))}
        except ValueError as e:
            raise HTTPException(422, str(e))

    @app.post("/sessions/{sid}/end")
    def end_session(sid: int):
        if not app.state.db.get_session(sid):
            raise HTTPException(404, "session not found")
        app.state.db.end_session(sid)
        return {"session_id": sid, "status": "ended"}

    @app.post("/users")
    def users(u: UserIn):
        name = u.name.strip()
        if not name:
            raise HTTPException(422, "name is required")
        uid, created = app.state.db.get_or_create_user(name, u.role)
        return {"user_id": uid, "created": created}

    @app.post("/sessions")
    def sessions(s: SessionIn):
        # Table 6.1 'Debate-side validation': the side must be proponent or opponent.
        if s.student_side not in ("proponent", "opponent") or s.mode != "adaptive":
            raise HTTPException(422, "invalid side or mode (only 'adaptive' is supported)")
        try:
            topic = check_motion(s.topic)
        except ValueError as e:
            raise HTTPException(422, str(e))
        app.state.db.add_topic(topic) if topic not in app.state.db.topics() else None
        sid = app.state.db.create_session(s.user_id, topic, s.student_side, "adaptive")
        return {"session_id": sid, "mode": "adaptive"}

    @app.post("/debate/turn")
    def turn(t: TurnIn):
        try:
            return process_turn(app.state.db, app.state.llm, t.session_id, t.argument)
        except ValidationError as e:
            raise HTTPException(400, str(e))
        except KeyError:        # Table 6.1 'Session validation'
            raise HTTPException(404, "session not found")
        except (RuntimeError, ConnectionError, TimeoutError) as e:
            raise HTTPException(503, f"LLM unavailable: {e}")

    @app.get("/sessions/{sid}/next-turn")
    def next_turn(sid: int):
        return {"next_turn": app.state.db.next_turn_number(sid)}

    @app.get("/sessions/{sid}/history")
    def history(sid: int):
        return app.state.db.history(sid)

    @app.post("/feedback")
    def feedback(f: FeedbackIn):
        vals = [f.ease_of_use, f.clarity, f.ai_relevance, f.weakness_help, f.improvement_help, f.fairness, f.reuse]
        if any(not 1 <= v <= 5 for v in vals):
            raise HTTPException(422, "ratings must be between 1 and 5")
        if not app.state.db.get_session(f.session_id):   # a rating must belong to a real session
            raise HTTPException(404, "session not found")
        app.state.db.add_feedback(f.user_id, f.session_id, vals, f.comment)
        return {"ok": True}

    return app


app = build_app() if os.getenv("BUILD_DEFAULT_APP", "1") == "1" else None