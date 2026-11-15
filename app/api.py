"""FastAPI backend. Run: uvicorn app.api:app --port 8000     (interactive docs: http://127.0.0.1:8000/docs)

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

TOPICS = [
    "Social media should be banned for children under 16.",
    "Artificial intelligence should be used to grade student assignments.",
    "Universities should replace written examinations with project based assessment.",
    "Remote learning is more effective than traditional classroom learning.",
    "Governments should regulate the use of generative AI tools.",
]
ARMS = ["adaptive", "single", "generic"]


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
        mode: str = "adaptive"       # adaptive | single | generic | random (balanced assignment for the study)

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
        return TOPICS

    @app.post("/users")
    def users(u: UserIn):
        name = u.name.strip()
        if not name:
            raise HTTPException(422, "name is required")
        uid, created = app.state.db.get_or_create_user(name, u.role)
        return {"user_id": uid, "created": created}

    @app.post("/sessions")
    def sessions(s: SessionIn):
        if s.student_side not in ("proponent", "opponent") or s.mode not in ("adaptive", "single", "generic", "random"):
            raise HTTPException(422, "invalid side or mode")
        mode = s.mode
        if mode == "random":     # balanced: assign to the arm with fewest sessions so far (random tie break)
            import random
            counts = {m: 0 for m in ARMS}
            for r in app.state.db.all("SELECT mode, COUNT(*) n FROM debate_sessions GROUP BY mode"):
                if r["mode"] in counts:
                    counts[r["mode"]] = r["n"]
            low = min(counts.values())
            mode = random.choice([m for m, n in counts.items() if n == low])
        sid = app.state.db.create_session(s.user_id, s.topic, s.student_side, mode)
        return {"session_id": sid, "mode": mode if s.mode != "random" else "hidden"}

    @app.post("/debate/turn")
    def turn(t: TurnIn):
        try:
            return process_turn(app.state.db, app.state.llm, t.session_id, t.argument)
        except ValidationError as e:
            raise HTTPException(400, str(e))
        except KeyError:
            raise HTTPException(404, "session not found")
        except RuntimeError as e:
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
        app.state.db.add_feedback(f.user_id, f.session_id, vals, f.comment)
        return {"ok": True}

    return app


app = build_app() if os.getenv("BUILD_DEFAULT_APP", "1") == "1" else None