"""LLM backends (real models only).

OllamaLLM        real local model (Llama 3 8B), the thesis setup (Chapter 7, Section 7.3).
OpenAICompatLLM  any OpenAI compatible chat API (thesis 6.16, optional).

There is no mock or heuristic stand in. make_llm() raises on an unknown LLM_BACKEND, so a typo can
never silently produce fake scores.

Speed notes:
  * every task has an output token cap (TASK_TOKENS), so the model stops as soon as the JSON is finished;
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

# Maximum new tokens per task. Override with env, for example LLM_TOKENS_SCORE=700.
TASK_TOKENS = {"analyse": 260, "score": 360, "diagnose": 90, "oppose": 150, "warm": 16}


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
    """Local Llama 3 8B through Ollama (temperature 0, seed 7, JSON mode).

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
                   task="warm")
        return time.time() - t

    def complete(self, messages, task=None):
        """Raw JSON text for one chat. Used by the CrewAI agents (app/crew_flow.py)."""
        return self._chat(messages, True, task)

    def json(self, task, prompt, payload=None, retries=2):
        """`payload` is accepted for call compatibility and ignored: the real model reads only the prompt."""
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
    """Any OpenAI compatible chat API. Env: LLM_API_KEY, LLM_BASE_URL (default Groq), LLM_MODEL (for example openai/gpt-oss-20b),
    LLM_REASONING_EFFORT (low), LLM_REASONING_TOKENS (extra tokens for reasoning models, 700)."""
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
        """One chat call. Ordinary errors are retried `retries` times. A rate limit (HTTP 429) does NOT use up those attempts:
        wait for the time the server asks for (Retry-After, at most 90 s) and try again, up to LLM_RATE_RETRIES times (8)."""
        last, i, rate_waits = None, 0, 0
        max_rate = int(os.getenv("LLM_RATE_RETRIES", "8"))
        while i <= retries:
            try:
                body = {"model": self.model, "temperature": 0, "seed": 7,
                        "response_format": {"type": "json_object"}, "messages": _flatten(messages)}
                reasoning = "gpt-oss" in (self.model or "").lower()
                if reasoning:       # reasoning models spend tokens thinking: keep that short and leave room for the JSON
                    body["reasoning_effort"] = os.getenv("LLM_REASONING_EFFORT", "low")
                if task:
                    body["max_tokens"] = _cap(task) + (int(os.getenv("LLM_REASONING_TOKENS", "700")) if reasoning else 0)
                r = requests.post(f"{self.base}/chat/completions", timeout=self.timeout,
                                  headers={"Authorization": f"Bearer {self.key}"}, json=body)
                if r.status_code == 429:
                    rate_waits += 1
                    try:
                        asked = float(r.headers.get("retry-after") or 0)
                    except ValueError:
                        asked = 0.0
                    wait = min(90.0, max(asked, 5.0 * rate_waits))
                    last = f"rate limited by the provider (HTTP 429): {r.text[:160]}"
                    if rate_waits > max_rate:
                        raise RuntimeError(f"LLM rate limit not lifting after {max_rate} waits. {last}")
                    print(f"[llm] rate limited, waiting {wait:.0f}s ({rate_waits}/{max_rate})", file=sys.stderr, flush=True)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except RuntimeError as e:
                if "rate limit not lifting" in str(e):
                    raise
                last = e
            except Exception as e:
                last = e
            i += 1
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
    raise RuntimeError(f"Unknown LLM_BACKEND '{backend}'. Use 'ollama' or 'openai'.")


# --------------------------------------------------------------------------
# Lexical helpers (word lists, not data). Used by agents.py (_ABS: absolute words for the
# overgeneralisation check) and validation.py (_toks: topic overlap for the relevance flag).
# --------------------------------------------------------------------------
_ABS = re.compile(r"\b(all|every|everyone|everything|always|never|nobody|no one|completely|totally|entirely|obviously|undeniably)\b", re.I)
_STOP = set("the a an of to in and or is are be for on that this it as with by should would can will from at not".split())


def _toks(s):
    return {w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in _STOP}