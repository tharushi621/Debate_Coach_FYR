# Project overview: purpose, technologies, design decisions

## Purpose
Students struggle to build debate arguments (unclear claims, weak evidence, missing warrants, no rebuttals), and teachers cannot give individual feedback on every argument. Existing AI tools give generic feedback or generate counterarguments without saying *why* an argument is weak, and the feedback does not shape the next turn.
This system closes that loop: it diagnoses a student's weakest argumentation dimension and uses that diagnosis to decide how the AI opponent challenges them next.

## Research questions served
RQ1 design/develop/evaluate the system; RQ2 which weaknesses can be identified (Toulmin taxonomy); RQ3 identifying the lowest dimension (rubric + priority tie-break); RQ4 targeted opponent responses (intervention rules + guardrails); RQ5 usability, usefulness, preliminary learning support (pilot + A/B arms).

## Pipeline (one debate turn)
validate -> Toulmin analysis (LLM) -> 7-dimension scoring 1-5 (LLM, clamped) -> weakness diagnosis (deterministic) -> intervention (deterministic map) -> targeted opponent reply (LLM + guardrails) -> persist all -> progress tracking.

## Technologies and why
| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | LLM ecosystem, rapid prototyping, analysis libraries |
| UI | Streamlit | Fast chat-style interface for a research prototype |
| API | FastAPI + Pydantic | Typed, lightweight endpoints, auto docs at /docs |
| Agents | Plain Python agent functions (tested core) + optional CrewAI wrapper (app/crew_flow.py) | Deterministic core is testable; CrewAI provides the role-based sequential crew described in the thesis |
| LLM | Ollama, Llama 3 8B (local, free); heuristic backend for offline tests/baseline | Zero cost, private data, reproducible (temperature 0, fixed seed) |
| Data | SQLite | Serverless, enough for a pilot; PostgreSQL is the scale-up path |
| Evaluation | pandas, scikit-learn, numpy | Accuracy, Cohen's kappa, F1, permutation tests, bootstrap CIs |
| Testing | pytest, FastAPI TestClient | Unit, integration and API tests |
| Version control | Git/GitHub | Iteration history |

## Key design decisions (viva material)
1. LLM for language, code for decisions: scoring/wording use the LLM, but weakness->intervention selection is a deterministic map, so the closed loop is auditable and reproducible.
2. Tie-break rule: relevance > claim clarity > evidence > warrant > logic > rebuttal > qualification (defines the thesis's "most consequential").
3. Robustness: JSON extraction from noisy output, score clamping to 1-5 with default 3, retries, rule fallback for the opponent reply.
4. Guardrails: opponent replies that leak scores, are not challenges, or run long are replaced by templates (NFR08, no writing the argument for the student).
5. Escalation: if the same weakness persists, the strategist asks for more concrete answers without giving them.
6. Fair comparison: arms adaptive / single-prompt / generic share one measurement path; blind human ratings are the primary outcome.

## Layout
app/ (taxonomy, llm, agents, pipeline, validation, db, api, crew_flow) · ui/ · eval/ · analysis/ · tests/ · docs/ · README.md · COMPARISON.md

## Known limitations
LLM-based path unverified until you run it with Ollama; draft labels need human labelling; small pilot; no fact-checking; English text only; the system scorer is the same instrument that drives adaptation.
