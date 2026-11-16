# Pilot checklist (thesis 7.9 and 7.10): one group, no control arm

This replaces the three-arm design in STUDY_PROTOCOL.md, which the thesis does not use (Section 7.12: no control group).
The aim is a small, honest, preliminary pilot. Report whatever it shows.

## Before you start (decide and write these down, with today's date)
- [ ] Number of participants: ______ (aim for 7 to 10). Stop at this number, whatever the results look like.
- [ ] Each participant plays ONE debate of 5 turns, then fills the ratings form in the app.
- [ ] Exclusion rule: a participant who does not finish 5 turns is reported as "did not complete", not silently dropped.
- [ ] Date the pilot starts (used as `--since`): ____-__-__
- [ ] Your own nicknames (developer and test accounts), to exclude: ______________
- [ ] Which model runs the pilot: ______________ (use the same one for the whole pilot and name it in the thesis addendum)

## Setting up
- [ ] Backend running with your Groq key and model, and `/health` shows the model.
- [ ] Streamlit app running. Restart both after any code change.
- [ ] `ENGINE` is not `demo` (the page shows a yellow DEMO banner if it is).
- [ ] Each participant gets a participant code as their nickname (for example P01, P02). No real names.
- [ ] Give each participant `docs/PARTICIPANT_INFO_AND_CONSENT.md` first and keep their agreement.

## During a session (about 30 minutes)
1. Short briefing (5 minutes): what the system does, that scores can be wrong, that they may stop at any time.
2. Participant logs in with their code and plays one full 5-turn debate (they may pick a motion and a side).
3. Participant completes the ratings form at the end ("Rate this debate").
4. Optional: 5 minute interview and your own observation notes (thesis 3.4.5 and 3.4.6).

## After the pilot
```powershell
python -m analysis.pilot --since <start date> --exclude <your nicknames>
python -m analysis.report --since <start date> --exclude <your nicknames>
python -m analysis.figures --pilot --since <start date> --exclude <your nicknames>
```
- [ ] Check the Turns column shows 5 for each participant (report any that did not).
- [ ] Use ONE participant count everywhere in the write-up. The report prints a cross-check against the thesis text.
- [ ] State the limits: small sample, no control group, one model, short period.
- [ ] Say "preliminary evidence that scores improved", not "the system improves learning".
