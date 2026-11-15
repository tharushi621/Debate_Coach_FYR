"""LLM backends.

OllamaLLM        real local model (Llama 3 8B), the thesis setup.
OpenAICompatLLM  any OpenAI compatible chat API (optional).
HeuristicLLM     deterministic rule based stand in. Used ONLY by unit tests and as
                 the "rule based baseline" in the diagnostic evaluation. make_llm()
                 never returns it, so a typo in LLM_BACKEND can no longer silently
                 give you mock scores.

Speed notes (why a turn is faster than before):
  * every task has an output token cap (TASK_TOKENS), so the model stops as soon as
    the JSON is finished instead of writing long explanations;
  * the prompts ask for short explanations;
  * keep_alive keeps the model in memory between turns;
  * the API warms the model up once at start up (see app/api.py).
"""
import json
import os
import re
import sys
import time

import requests

from .taxonomy import DIMENSIONS

# Maximum new tokens per task. Override with env, for example LLM_TOKENS_SCORE=700.
TASK_TOKENS = {"analyse": 380, "score": 520, "diagnose": 140, "oppose": 200, "single": 300}


def _cap(task):
    return int(os.getenv(f"LLM_TOKENS_{str(task).upper()}", TASK_TOKENS.get(task, 400)))


def extract_json(text: str) -> dict:
    """Tolerant JSON extraction (the model sometimes adds prose around the JSON)."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError("No valid JSON in LLM output")


def _flatten(messages):
    """Chat messages (list of dicts) or a plain string -> list of chat messages."""
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return [{"role": m.get("role", "user"), "content": str(m.get("content", ""))} for m in messages]


class OllamaLLM:
    """Local Llama 3 8B through Ollama (thesis setup: temperature 0, seed 7, JSON mode).

    Env: OLLAMA_MODEL (llama3:8b), OLLAMA_URL, OLLAMA_TIMEOUT (300 s per call),
    OLLAMA_KEEP_ALIVE (30m), OLLAMA_NUM_CTX (4096), LLM_VERBOSE=1 prints call times.
    """
    name = "ollama"

    def __init__(self, model="llama3:8b", url=None, timeout=None, keep_alive=None):
        self.model = model
        self.url = (url or os.getenv("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout if timeout is not None else int(os.getenv("OLLAMA_TIMEOUT", "300"))
        self.keep_alive = keep_alive or os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
        self.verbose = os.getenv("LLM_VERBOSE", "0") == "1"

    def _chat(self, messages, json_mode=True, task=None):
        opts = {"temperature": 0, "seed": 7, "num_ctx": self.num_ctx}
        if task:
            opts["num_predict"] = _cap(task)
        body = {"model": self.model, "stream": False, "keep_alive": self.keep_alive,
                "options": opts, "messages": _flatten(messages)}
        if json_mode:
            body["format"] = "json"
        try:
            r = requests.post(f"{self.url}/api/chat", timeout=self.timeout, json=body)
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.url}. Start it (the Ollama app, or "
                               "'ollama serve') and check 'ollama list'.")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Ollama did not answer within {self.timeout}s. Raise OLLAMA_TIMEOUT, "
                               f"or check speed with 'ollama run {self.model} --verbose'.")
        if r.status_code == 404:
            raise RuntimeError(f"Ollama has no model '{self.model}'. Run: ollama pull {self.model}")
        r.raise_for_status()
        return r.json()["message"]["content"]

    def warm_up(self):
        """Load the model into memory once (the first call is the slowest)."""
        t = time.time()
        self._chat([{"role": "user", "content": "Reply with the single word: ready"}], json_mode=False,
                   task="single")
        return time.time() - t

    def complete(self, messages, task=None):
        """Raw JSON text for one chat. Used by the CrewAI agents (app/crew_flow.py)."""
        return self._chat(messages, True, task)

    def json(self, task, prompt, payload=None, retries=2):
        last = None
        for _ in range(retries + 1):
            t = time.time()
            try:
                out = extract_json(self._chat([{"role": "user", "content": prompt}], True, task))
                if self.verbose:
                    print(f"[llm] {task}: {time.time() - t:.1f}s", file=sys.stderr, flush=True)
                return out
            except ValueError as e:      # bad JSON from the model: retry
                last = e
            except RuntimeError:         # connection, timeout, missing model: retrying wastes minutes
                raise
            except Exception as e:       # transient HTTP errors
                last = e
        raise RuntimeError(f"LLM failed for task {task}: {last}")


class OpenAICompatLLM:
    """Any OpenAI compatible chat API. Env: LLM_API_KEY, LLM_BASE_URL (default Groq), LLM_MODEL."""
    name = "openai-compatible"

    def __init__(self, api_key=None, base_url=None, model=None, timeout=60):
        self.key = api_key or os.getenv("LLM_API_KEY")
        self.base = (base_url or os.getenv("LLM_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
        self.model = model or os.getenv("LLM_MODEL")
        self.timeout = timeout
        if not self.key:
            raise RuntimeError("LLM_API_KEY is not set")
        if not self.model:
            raise RuntimeError("LLM_MODEL is not set: copy a current model id from your provider's page")

    def _post(self, messages, task=None, retries=3):
        last = None
        for i in range(retries + 1):
            try:
                body = {"model": self.model, "temperature": 0, "seed": 7,
                        "response_format": {"type": "json_object"}, "messages": _flatten(messages)}
                if task:
                    body["max_tokens"] = _cap(task)
                r = requests.post(f"{self.base}/chat/completions", timeout=self.timeout,
                                  headers={"Authorization": f"Bearer {self.key}"}, json=body)
                if r.status_code == 429:         # free tier rate limit: back off and retry
                    time.sleep(2 * (i + 1))
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                last = e
        raise RuntimeError(f"LLM request failed: {last}")

    def complete(self, messages, task=None):
        return self._post(messages, task)

    def json(self, task, prompt, payload=None, retries=3):
        last = None
        for _ in range(2):
            try:
                return extract_json(self._post([{"role": "user", "content": prompt}], task, retries))
            except ValueError as e:
                last = e
        raise RuntimeError(f"LLM failed for task {task}: {last}")


def make_llm():
    """LLM_BACKEND = ollama (default) | openai.  Anything else is an ERROR, never a silent mock."""
    backend = os.getenv("LLM_BACKEND", "ollama").strip().lower()
    if backend == "ollama":
        return OllamaLLM(os.getenv("OLLAMA_MODEL", "llama3:8b"))
    if backend == "openai":
        return OpenAICompatLLM()
    raise RuntimeError(f"Unknown LLM_BACKEND '{backend}'. Use 'ollama' or 'openai'. "
                       "(The rule based stand in is for unit tests only and is never selected here.)")


# --------------------------------------------------------------------------
# Rule based stand in: unit tests and the evaluation baseline ONLY.
# --------------------------------------------------------------------------
_EVID = re.compile(r"\b(study|studies|research|survey|according to|for example|for instance|e\.g\.|statistics|data|report|evidence shows|found that)\b|\d+\s?%|\b\d{2,}\b", re.I)
_WARR = re.compile(r"\b(therefore|which means|this shows|this suggests|this is why|thus|as a result|because of this|this implies|so that|which is why)\b", re.I)
_REBUT = re.compile(r"\b(however|although|critics|opponents|some argue|some may argue|while it is true|admittedly|on the other hand|one might object|proponents)\b", re.I)
_QUAL = re.compile(r"\b(may|might|often|usually|in most cases|generally|in some cases|typically|likely|unless|except|tends? to|probably)\b", re.I)
_ABS = re.compile(r"\b(all|every|everyone|everything|always|never|nobody|no one|completely|totally|entirely|obviously|undeniably)\b", re.I)
_FALLACY = re.compile(r"\b(everyone knows|everybody|slippery slope|obviously|clearly everyone|only idiots|if we allow .* then .*)\b", re.I)
_VAGUE = re.compile(r"\b(bad|good|wrong|terrible|awful|nice|stuff|things)\b", re.I)
_STOP = set("the a an of to in and or is are be for on that this it as with by should would can will from at not".split())


def _toks(s):
    return {w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in _STOP}


class HeuristicLLM:
    name = "heuristic"

    def json(self, task, prompt, payload=None, retries=0):
        return getattr(self, f"_{task}")(payload or {})

    def _analyse(self, p):
        text = p["argument"]
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        claim = sents[0] if sents else text
        grounds = [s for s in sents if _EVID.search(s)] or ([s for s in sents[1:2]] if len(sents) > 1 else [])
        m = re.search(r"\bbecause\b(.+)", text, re.I)
        if m and not grounds:
            grounds = [m.group(1).strip(" .")]
        warrant = next((s for s in sents if _WARR.search(s)), None)
        qualifier = next((s for s in sents if _QUAL.search(s)), None)
        rebuttal = next((s for s in sents if _REBUT.search(s)), None)
        out = {"main_claim": claim, "grounds": grounds, "warrant": warrant, "backing": None,
               "qualifier": qualifier, "rebuttal": rebuttal}
        out["missing_components"] = [k for k in ("grounds", "warrant", "backing", "qualifier", "rebuttal") if not out[k]]
        return out

    def _score(self, p):
        text, topic, analysis = p["argument"], p["topic"], p["analysis"]
        words = len(text.split())
        ev = len(_EVID.findall(text))
        d = {}
        vague = bool(_VAGUE.search(analysis["main_claim"] or "")) and words < 12
        d["claim_clarity"] = (1 if words < 5 else 2 if vague else 3 if words < 15 else 4)
        d["evidence_quality"] = 1 if (not analysis["grounds"] and ev == 0) else min(5, 2 + ev) if ev else 2
        d["warrant_strength"] = 4 if _WARR.search(text) and analysis["grounds"] else 2 if analysis["grounds"] else 1
        overlap = len(_toks(text) & _toks(topic)) / max(1, len(_toks(topic)))
        d["relevance"] = 1 if overlap < 0.1 else 2 if overlap < 0.25 else 3 if overlap < 0.45 else 5
        d["rebuttal_readiness"] = min(5, 1 + 2 * len(_REBUT.findall(text)))
        d["logical_validity"] = 1 if _FALLACY.search(text) else 3 if len(_ABS.findall(text)) > 1 else 4
        absolutes, quals = len(_ABS.findall(text)), len(_QUAL.findall(text))
        d["qualification"] = 1 if absolutes and not quals else min(5, 2 + quals) if quals else 2
        return {k: {"score": v, "explanation": f"heuristic:{k}"} for k, v in d.items()}

    def _diagnose(self, p):
        return {"lowest_weakness": None}

    def _oppose(self, p):
        return {"ai_opponent_response": None}

    def _single(self, p):
        return {"feedback": "Your argument could be improved with more detail and better support.",
                "ai_opponent_response": "I disagree with your position. Can you explain further and strengthen your case?"}


assert set(DIMENSIONS)  # import sanity