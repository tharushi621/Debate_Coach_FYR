# Weakness-Targeted Adaptive Multi-Agent Debate System

Closed loop: student argument → Toulmin analysis → 7-dimension scoring → weakest-dimension diagnosis → intervention → targeted AI opponent reply → progress tracking.

## Run (free, local)
```bash
pip install -r requirements.txt
ollama pull llama3:8b                      # local LLM, no cost
export LLM_BACKEND=ollama                  # or heuristic (offline, rule-based, for tests only)
uvicorn app.api:app --port 8000            # backend  (docs: http://127.0.0.1:8000/docs)
streamlit run ui/streamlit_app.py          # UI
python -m pytest -q                        # tests (API test needs fastapi+httpx installed)
```

## Debate Arena (gamified UI)
`streamlit run ui/streamlit_app.py` opens a game-style front end: lobby -> **coin toss** (3D coin; heads = proponent, tails = opponent; the result
is drawn with OS randomness in `app/game.py` and the animation only displays it) -> **3D stage** with podiums, moving spotlights that follow the active
speaker, and a cheering crowd -> XP, levels, streaks, badges and a final results screen. The audience is deliberately encouraging, even after a low score.
* `python -m ui.preview` writes standalone HTML of the stage and coin to `ui/preview/` (no backend needed); screenshots are in `docs/ui/`.
* **Study integrity:** quality-based points, badges and applause are used only in the adaptive arm (`display == "full"`). In `single` and `generic` arms every
  turn earns the same participation XP, so the game does not reveal the arm. Tests: `tests/test_game.py`, `tests/test_ui_flow.py`.
* Tested with a stand-in Streamlit and in a real Chromium for the scenes. The live Streamlit page itself has not been run by the author of this build:
  open it once and click through lobby, toss, one turn and "End the debate" before your viva.

## First check (after setting the LLM variables)
```powershell
python -m app.smoke      # one argument through the loop; prints Appendix C JSON shapes
```

## No Ollama? Use a free cloud LLM (Windows PowerShell)
```powershell
$env:LLM_BACKEND="openai"
$env:LLM_API_KEY="<your key from console.groq.com>"
$env:LLM_BASE_URL="https://api.groq.com/openai/v1"   # default
$env:LLM_MODEL="<current model id from the provider's models page>"   # required; catalogues change (llama3-8b-8192 and llama-3.1-8b-instant are retired on Groq)
uvicorn app.api:app --port 8000
```
Report the exact model + provider in the thesis (it differs from Llama 3 8B via Ollama). Student arguments are sent to the provider: state this in the consent form.

## Study arms (the comparison that makes "best" defensible)
| Arm | What the student gets | Role |
|---|---|---|
| `adaptive` | Toulmin report, scores, diagnosis, targeted opponent | Proposed system |
| `single` | One un-decomposed LLM call: feedback + reply | Baseline B2 (typical chatbot design) |
| `generic` | Untargeted counterargument only | Baseline B1 (non-adaptive AI opponent) |

All arms are measured by the same scorer; only what the student sees and the opponent's reply differ.
Use `STUDY_MODE=random` for the UI/API to assign participants to arms with balanced counts.

## Evidence kit (the four things panels reward) - details in docs/EVIDENCE_CHECKLIST.md
```bash
# 1. Evidence quality: two blind labellers, dev/test split, frozen prompts
python -m eval.make_label_sheets                   # blind sheets for labeller A and B, private key, dev/test split
python -m eval.agreement                           # inter-labeller kappa; writes resolve.csv for disagreements
python -m eval.agreement --finalise                # reference labels once final_label is filled
python -m eval.diagnostic_eval openai --split dev  # tune prompts here (or ollama / heuristic)
python -m eval.diagnostic_eval openai --split test # ONCE, after freezing prompts; every test run is logged
# 2. Comparison: docs/STUDY_PROTOCOL.md, docs/PARTICIPANT_INFO_AND_CONSENT.md
python -m analysis.study summary | export | import r1.csv r2.csv
# 3. Honesty: every number from stored data, with consistency checks and hedged wording
python -m analysis.pilot                           # thesis Table 7.25 / 7.26 equivalents
python -m analysis.report                          # results_summary.md
# 4. Demo: docs/DEMO_SCRIPT.md
```
There are two labelling tools. `eval.labelling` is the simpler one (writes `eval/data/reference_labels.csv`); `eval.make_label_sheets` + `eval.agreement`
add a private answer key, blind validation and an explicit resolve step. The evaluation reads either, so pick one and use it for both labellers.

## Before you report numbers
1. `eval/data/sample_arguments.csv` is researcher-written with the author's intended label. That label is NOT the reference: two humans label independently, then resolve.
2. Add real student-style arguments (aim for at least 15) before labelling; researcher-only samples are a stated limitation.
3. Without `reference_labels.csv` the evaluation prints a warning and uses the author's intent: that is a pipeline check, not a result.
4. Do not report results from the `heuristic` backend as results of the system. Primary outcome of any study = blind human ratings.
