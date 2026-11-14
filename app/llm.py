"""LLM backends.

OllamaLLM   - real local model (Llama 3 8B etc.), zero cost.
HeuristicLLM - deterministic rule-based stand-in. Used for offline tests, CI,
               and as the *non-LLM baseline* in the evaluation (shows what the
               LLM adds over keyword rules). Never presented as the LLM itself.
"""
import json
import re

import requests

from .taxonomy import DIMENSIONS


def extract_json(text: str) -> dict:
    """Tolerant JSON extraction (thesis challenge: LLM adds prose around JSON)."""
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


class OllamaLLM:
    """Local Llama 3 8B through Ollama's native API (thesis setup: temperature 0, seed 7, JSON mode).
    Env: OLLAMA_MODEL (default llama3:8b), OLLAMA_URL, OLLAMA_TIMEOUT seconds per call (default 300), OLLAMA_KEEP_ALIVE (default 30m),
    LLM_VERBOSE=1 prints the time each call takes (so a slow CPU run is visibly working, not hung)."""
    name = "ollama"

    def __init__(self, model="llama3:8b", url=None, timeout=None, keep_alive=None):
        import os
        self.model = model
        self.url = (url or os.getenv("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout if timeout is not None else int(os.getenv("OLLAMA_TIMEOUT", "300"))
        self.keep_alive = keep_alive or os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self.verbose = os.getenv("LLM_VERBOSE", "0") == "1"

    def _chat(self, messages, json_mode=True):
        body = {"model": self.model, "stream": False, "keep_alive": self.keep_alive,
                "options": {"temperature": 0, "seed": 7}, "messages": messages}
        if json_mode:
            body["format"] = "json"
        try:
            r = requests.post(f"{self.url}/api/chat", timeout=self.timeout, json=body)
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.url}. Start it (the Ollama app, or 'ollama serve') and check 'ollama list'.")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Ollama did not answer within {self.timeout}s. Raise OLLAMA_TIMEOUT, or check speed with 'ollama run {self.model} --verbose'.")
        if r.status_code == 404:
            raise RuntimeError(f"Ollama has no model '{self.model}'. Run: ollama pull {self.model}")
        r.raise_for_status()
        return r.json()["message"]["content"]

    def warm_up(self):
        """Load the model into memory once (the first call is the slowest), so later calls are not mistaken for a hang."""
        import time
        t = time.time()
        self._chat([{"role": "user", "content": "Reply with the single word: ready"}], json_mode=False)
        return time.time() - t

    def json(self, task, prompt, payload=None, retries=2):
        import sys
        import time
        last = None
        for _ in range(retries + 1):
            t = time.time()
            try:
                out = extract_json(self._chat([{"role": "user", "content": prompt}]))
                if self.verbose:
                    print(f"[llm] {task}: {time.time() - t:.1f}s", file=sys.stderr, flush=True)
                return out
            except ValueError as e:  # bad JSON from the model: retry
                last = e
            except RuntimeError:  # connection / timeout / missing model: retrying only wastes minutes
                raise
            except Exception as e:  # transient HTTP errors
                last = e
        raise RuntimeError(f"LLM failed for task {task}: {last}")


class OpenAICompatLLM:
    """Any OpenAI-compatible chat API (Groq, OpenRouter, Together, OpenAI...). Free tiers exist.
    Env: LLM_API_KEY, LLM_BASE_URL (default Groq), LLM_MODEL."""
    name = "openai-compatible"

    def __init__(self, api_key=None, base_url=None, model=None, timeout=60):
        import os
        self.key = api_key or os.getenv("LLM_API_KEY")
        self.base = (base_url or os.getenv("LLM_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
        self.model = model or os.getenv("LLM_MODEL")
        self.timeout = timeout
        if not self.key:
            raise RuntimeError("LLM_API_KEY is not set")
        if not self.model:  # model catalogues change; never default to one that may be retired
            raise RuntimeError("LLM_MODEL is not set: copy a current model id from your provider's models page")

    def json(self, task, prompt, payload=None, retries=3):
        import time
        last = None
        for i in range(retries + 1):
            try:
                r = requests.post(f"{self.base}/chat/completions", timeout=self.timeout,
                                  headers={"Authorization": f"Bearer {self.key}"},
                                  json={"model": self.model, "temperature": 0, "seed": 7,
                                        "response_format": {"type": "json_object"},
                                        "messages": [{"role": "user", "content": prompt}]})
                if r.status_code == 429:  # free-tier rate limit: back off and retry
                    time.sleep(2 * (i + 1))
                    continue
                r.raise_for_status()
                return extract_json(r.json()["choices"][0]["message"]["content"])
            except Exception as e:
                last = e
        raise RuntimeError(f"LLM failed for task {task}: {last}")


def make_llm():
    """LLM_BACKEND = ollama (default) | openai (any OpenAI-compatible API) | heuristic (tests only)."""
    import os
    backend = os.getenv("LLM_BACKEND", "ollama")
    if backend == "ollama":
        return OllamaLLM(os.getenv("OLLAMA_MODEL", "llama3:8b"))  # timeout, url, keep-alive come from OLLAMA_* env vars
    if backend == "openai":
        return OpenAICompatLLM()
    return HeuristicLLM()


# ---------------------------------------------------------------------------
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

    # -- analyser -----------------------------------------------------------
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

    # -- scorer -------------------------------------------------------------
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

    # -- diagnostician subtype resolution ------------------------------------
    def _diagnose(self, p):
        return {"lowest_weakness": None}

    # -- opponent -----------------------------------------------------------
    def _oppose(self, p):
        return {"ai_opponent_response": None}

    # -- single-prompt baseline (offline stand-in: deliberately generic) -----
    def _single(self, p):
        return {"feedback": "Your argument could be improved with more detail and better support.",
                "ai_opponent_response": "I disagree with your position. Can you explain further and strengthen your case?"}


assert set(DIMENSIONS)  # import sanity