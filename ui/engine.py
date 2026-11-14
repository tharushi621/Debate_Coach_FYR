"""Debate engines the UI can talk to. One interface, two implementations.

  ApiEngine  -> your real thesis backend (uvicorn app.api:app). USE THIS FOR THE VIVA.
  DemoEngine -> offline rule-based stand-in so the interface can be explored with no LLM running.
                Everything it produces is labelled DEMO in the UI and must never be reported as results.

Normalised turn result (what every view consumes):
  {overall, scores{dim:1-5}, weakness, explanation, intervention, opponent, feedback, display,
   mode, guardrail_fallback}
"""
import os, re

from app.progress import DIMS, WEAKNESS_DIM

PRIORITY = ["relevance", "claim_clarity", "evidence_quality", "warrant_strength",
            "logical_validity", "rebuttal_readiness", "qualification"]
DIM_WEAKNESS = {"claim_clarity": "unclear_claim", "evidence_quality": "insufficient_evidence",
                "warrant_strength": "missing_warrant", "logical_validity": "logical_fallacy",
                "rebuttal_readiness": "weak_rebuttal", "relevance": "poor_relevance",
                "qualification": "missing_qualification"}


def _num(v, default=3.0):
    if isinstance(v, dict):
        v = v.get("score", v.get("value"))
    try:
        return max(1.0, min(5.0, float(v)))
    except (TypeError, ValueError):
        return default


def _pick(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


class DemoEngine:
    name = "demo"
    label = "DEMO engine (offline rules — not the thesis system)"

    EVID = ("for example", "study", "research", "according to", "data", "%", "survey", "found that")
    LINK = ("because", "therefore", "since", "this means", "as a result")
    HEDGE = ("usually", "often", "generally", "in many cases", "may", "might", "unless", "typically")
    ABS = ("always", "never", "everyone", "nobody", "obviously")
    REB = ("however", "but ", "although", "even if", "granted", "you claim", "your point")

    def start(self, topic, side, mode="adaptive", nickname=None):
        return {"topic": topic, "side": side, "mode": mode, "n": 0}

    def turn(self, h, argument):
        low = argument.lower(); n = len(re.findall(r"\w+", argument)); h["n"] += 1
        has = lambda cues: any(c in low for c in cues)
        s = {"claim_clarity": 4.0 if 8 <= n <= 60 else 2.0 if n < 6 else 3.0,
             "evidence_quality": 4.0 if has(self.EVID) and re.search(r"\d", low) else 3.0 if has(self.EVID) else 2.0,
             "warrant_strength": 4.0 if has(self.LINK) else 2.0,
             "logical_validity": 2.0 if has(self.ABS) else 3.5,
             "rebuttal_readiness": 4.0 if has(self.REB) else 2.0,
             "relevance": 4.0 if any(w in low for w in re.findall(r"\w{5,}", h["topic"].lower())) else 2.5,
             "qualification": 4.0 if has(self.HEDGE) else 2.0}
        overall = round(sum(s.values()) / 7, 2)
        low_dim = min(PRIORITY, key=lambda d: (s[d], PRIORITY.index(d)))
        w = DIM_WEAKNESS[low_dim]
        asks = {"unclear_claim": "State your claim in a single, clear sentence.",
                "insufficient_evidence": "What specific evidence supports that?",
                "poor_relevance": "How does that bear on the motion itself?",
                "missing_warrant": "What connects your evidence to your conclusion?",
                "weak_rebuttal": "How would you answer the strongest objection?",
                "logical_fallacy": "Does that hold for every case, or only some?",
                "missing_qualification": "Under what conditions would your claim fail?"}
        opp = (f"I take the other side of this motion. "
               f"Your case rests on a gap I will press: {asks[w]}")
        return {"overall": overall, "scores": s, "weakness": w,
                "explanations": {}, "explanation": f"Lowest dimension: {low_dim.replace('_', ' ')} ({s[low_dim]:.1f}/5).",
                "intervention": {"unclear_claim": "claim_clarification_request", "insufficient_evidence": "evidence_request",
                                 "poor_relevance": "relevance_redirect", "missing_warrant": "warrant_challenge_question",
                                 "weak_rebuttal": "counter_rebuttal_challenge", "logical_fallacy": "fallacy_probe",
                                 "missing_qualification": "qualification_probe"}[w],
                "opponent": opp, "feedback": "", "display": "full", "mode": h["mode"], "guardrail_fallback": False}


class ApiEngine:
    """Adapter for YOUR thesis FastAPI backend (app/api.py), using its real request/response shapes:

      POST /users      {"name"}                                   -> {"user_id"}
      POST /sessions   {"user_id","topic","student_side","mode"}  -> {"session_id","mode"}   (side: proponent|opponent)
      POST /debate/turn {"session_id","argument"}                 -> process_turn() dict
         scores = {"dimensions": {dim: {"score","explanation"}}, "overall_quality"}
         diagnosis = {"lowest_weakness","diagnosis_reason","dimension",...}; intervention = {"type","description"}
      HTTP 400 = the student can fix it (validation); 503 = LLM unavailable.
    """
    name = "api"
    label = "Thesis backend (LLM pipeline)"
    SIDE = {"FOR": "proponent", "AGAINST": "opponent"}

    def __init__(self, base=None, timeout=None):
        import requests
        self.requests = requests
        self.base = (base or os.getenv("API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = float(timeout or os.getenv("API_TIMEOUT", "900"))   # CPU-only Llama 3 8B: minutes per turn
        self._uid = {}

    def _post(self, path, body):
        try:
            r = self.requests.post(self.base + path, json=body, timeout=self.timeout)
        except self.requests.exceptions.RequestException:
            raise RuntimeError(f"Cannot reach the backend at {self.base}. Start it with: python -m uvicorn app.api:app --port 8000")
        if r.status_code == 200:
            return r.json()
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        if r.status_code == 400:
            raise ValueError(str(detail))            # fixable by the learner
        raise RuntimeError(str(detail))

    def _user(self, nickname):
        if nickname not in self._uid:
            self._uid[nickname] = self._post("/users", {"name": nickname})["user_id"]
        return self._uid[nickname]

    def start(self, topic, side, mode="adaptive", nickname="learner"):
        d = self._post("/sessions", {"user_id": self._user(nickname), "topic": topic,
                                     "student_side": self.SIDE[side], "mode": mode})
        return {"sid": d["session_id"], "topic": topic, "side": side, "mode": mode}

    def turn(self, h, argument):
        d = self._post("/debate/turn", {"session_id": h["sid"], "argument": argument})
        dims = (d.get("scores") or {}).get("dimensions") or {}
        scores = {k: _num(dims.get(k)) for k in DIMS}
        expl = {k: str((dims.get(k) or {}).get("explanation", "")) for k in DIMS}
        diag = d.get("diagnosis") or {}
        iv = d.get("intervention") or {}
        overall = (d.get("scores") or {}).get("overall_quality")
        if overall is None:
            overall = sum(scores.values()) / len(scores)
        return {"overall": round(_num(overall), 2), "scores": scores, "explanations": expl,
                "weakness": diag.get("lowest_weakness", ""), "explanation": diag.get("diagnosis_reason", ""),
                "intervention": iv.get("type", ""), "opponent": d.get("ai_opponent_response", ""),
                "feedback": d.get("feedback", ""), "display": d.get("display", "full"),
                "mode": d.get("mode", h["mode"]), "guardrail_fallback": bool(d.get("guardrail_fallback")),
                "flags": d.get("validation_flags") or [], "progress": d.get("progress") or {}}


def make_engine():
    kind = os.getenv("ENGINE", "api").lower()
    return DemoEngine() if kind == "demo" else ApiEngine()