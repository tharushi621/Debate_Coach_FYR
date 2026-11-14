# ArguMind — Interactive Debate Learning Platform (Streamlit)

Header-only navigation (Home · How It Works · Start Debate · My Progress · Profile · Login/Logout),
animated hero film, clickable 9-stage roadmap, full nine-stage debate loop, nickname accounts,
XP/levels/badges/quests, radar + score-card dashboards. Visual language follows your two reference images.

## IMPORTANT: this is an overlay for your existing project
My build sandbox lost the earlier project folder, so these files are **new or replacement files only**.
Unzip *over* your `D:\D_BSE_0012_FYP\debate_coach` (it adds files; the only existing file it replaces is
`ui/streamlit_app.py` — copy the old one aside first if you want it). Your thesis pipeline (`app/agents.py`,
`pipeline.py`, `api.py`, `llm.py`, `db.py`, `game.py`) is **not touched**.

## Run
```powershell
# 1. backend (your existing LLM pipeline) — terminal A
python -m uvicorn app.api:app --port 8000
# 2. platform UI — terminal B
python -m streamlit run ui/streamlit_app.py
```
Needs Streamlit >= 1.39 (keyed containers are used for the header). No pandas/numpy required by the new UI.
Try the interface **without any LLM**: `$env:ENGINE="demo"` before step 2 (shows a DEMO banner; never report those outputs).

| Env var | Meaning |
|---|---|
| `ENGINE` | `api` (default, your thesis backend) or `demo` |
| `API_URL`, `API_TIMEOUT` | backend address / timeout (default 900 s) |
| `STUDY_MODE` | `adaptive` (default), `single`, `generic`, `random` — blinding preserved (see below) |
| `PLATFORM_DB` | sqlite file for accounts/progress (default `platform.db`) |

## Backend contract (checked against your attached code)
`ui/engine.py → ApiEngine` uses exactly your `app/api.py` shapes: `/users {name}`, `/sessions {user_id, topic, student_side: proponent|opponent, mode}`,
`/debate/turn {session_id, argument}` and reads `scores.dimensions.<dim>.score`, `diagnosis.lowest_weakness`, `intervention.type`,
`ai_opponent_response`, `feedback`, `display`. HTTP 400 messages from your `validate()` are shown to the learner as "please revise".
If `ui/stage.py` (your 3D debate hall) exists, the arena shows it automatically.

## How it maps to your 9 stages
01 topic bank (6 categories × 3 levels) · 02 `secrets` coin toss + 3D coin · 03 briefing, rules, prep timer ·
04 arena (turn indicator, timers, progress, optional voice dictation) · 05 radar + 7 score cards + named weakness ·
06 rule-based exercises per weakness family with checks/retry (practice feedback — not the thesis scorer) ·
07 profile update · 08 personalised path (trend, recurring weaknesses, drills) · 09 XP/badges/level-up + next-debate recommendation.

## Honest notes (for your viva)
- **No win/loss.** The AI is not a judge; the platform shows Improved / Held / Dipped versus your own previous debate.
- **Blinding kept.** In `single`/`generic` arms no analysis dashboard, quality XP or quality badges are shown (participation XP only).
- **Nickname ≠ password.** Sessions use random tokens stored hashed with expiry; it identifies learners, it does not authenticate them. Add passwords before any public deployment.
- **Voice input** uses the browser's Web Speech API (audio goes to the browser vendor); the text must be pasted into the box.
- **Hero "video"** is a code-animated explainer. Put `ui/assets/intro.mp4` there to show a real video.
- **Tested here:** 14 unit/flow tests using a fake `streamlit`, plus Playwright screenshots of the HTML components. **Not tested here:** the real Streamlit runtime (not installable in my sandbox) and your real backend. Expect small CSS tweaks on first run.
- Local Llama 3 8B takes minutes per turn; for a live viva use a fast cloud model or a recording.
