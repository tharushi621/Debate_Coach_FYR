"""Thin HTTP client for the FastAPI backend. All network errors become ApiError with a message that is safe to show."""
import os

import requests


class ApiError(Exception):
    def __init__(self, message, kind="error"):
        super().__init__(message)
        self.kind = kind  # "validation" (HTTP 400: the student can fix it) | "error"


class Client:
    def __init__(self, base=None, timeout=90):
        self.base = (base or os.getenv("API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout

    def _call(self, method, path, **kw):
        try:
            r = requests.request(method, self.base + path, timeout=self.timeout, **kw)
        except requests.exceptions.RequestException:
            raise ApiError(f"Cannot reach the backend at {self.base}. Start it with: uvicorn app.api:app --port 8000")
        if r.status_code == 200:
            return r.json()
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(str(detail), "validation" if r.status_code == 400 else "error")

    def topics(self):
        return self._call("GET", "/topics")

    def create_user(self, name):
        return self._call("POST", "/users", json={"name": name})["user_id"]

    def create_session(self, user_id, topic, side, mode):
        return self._call("POST", "/sessions", json={"user_id": user_id, "topic": topic, "student_side": side, "mode": mode})

    def turn(self, session_id, argument):
        return self._call("POST", "/debate/turn", json={"session_id": session_id, "argument": argument})

    def history(self, session_id):
        return self._call("GET", f"/sessions/{session_id}/history")

    def feedback(self, payload):
        return self._call("POST", "/feedback", json=payload)
