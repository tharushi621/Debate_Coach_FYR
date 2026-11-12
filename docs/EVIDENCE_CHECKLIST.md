# Evidence checklist: the four pillars, with "done when" criteria

## 1. Evidence quality
- [ ] Add at least 15 real student-style arguments to `eval/data/sample_arguments.csv` (ask classmates; with permission). Total 45 or more, about 5 per weakness. `intended_weakness` is only your guess.
- [ ] `python -m eval.make_label_sheets`. Give `labeller_A.csv`, `labeller_B.csv` and `LABELLING_GUIDE.md` to two different people (a debate coach or your supervisor as one). Keep `key.csv` private.
- [ ] Labellers work alone and do not see system output. `python -m eval.agreement` prints their kappa. Discuss each disagreement, fill `final_label` in `resolve.csv`, run `python -m eval.agreement --finalise`.
- [ ] Tune prompts using `python -m eval.diagnostic_eval openai --split dev` only.
- [ ] Freeze prompts. Note the `prompt fingerprint` the tool prints. Run `--split test` once. If you rerun it, the log records every look; report the count.
- [ ] Blind re-scoring of pilot arguments: `python -m analysis.study export`, two raters, `python -m analysis.study import r1.csv r2.csv`.
Done when: you can state labeller kappa, test-set accuracy with its interval, the two baselines, how many times the test set was run, and the model and date.

## 2. Comparison
- [ ] Supervisor agrees in writing. Ethics approval obtained (docs/PARTICIPANT_INFO_AND_CONSENT.md).
- [ ] Protocol (docs/STUDY_PROTOCOL.md) filled in and date-stamped BEFORE the first participant: email it to your supervisor or commit it.
- [ ] 10 or more participants per arm, `STUDY_MODE=random`, five turns each.
- [ ] Primary outcome: blind human-rated change, first to last argument. Run `python -m analysis.study summary` and the import step.
Done when: every arm is reported, including a null result, with intervals and the exclusions you pre-specified.

## 3. Honesty
- [ ] One participant count everywhere. `python -m analysis.report` warns when tables disagree.
- [ ] Every figure in the thesis comes from `results_summary.md` or a file in `eval/results/`. Keep these files and the database.
- [ ] Wording matches the data (the report prints a suitable sentence): "preliminary evidence", never "proved" or "significant" from a small pilot.
- [ ] Limitations section written by you first (section 10 of the guideline).

## 4. Demo and answers
- [ ] docs/DEMO_SCRIPT.md rehearsed five times with the frozen prompts and the real model.
- [ ] Two-minute screen recording saved on two devices.
- [ ] Section 10 questions answered aloud to a friend, timed.
