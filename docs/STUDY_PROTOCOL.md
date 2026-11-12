# Study protocol: small comparative pilot (DRAFT: fill brackets and date-stamp before collecting data)

Date stamped: [YYYY-MM-DD]  Supervisor: [name]  Ethics approval ref: [ref]

## Question
Does a weakness-targeted AI opponent improve argument quality more than (B) one un-decomposed LLM call giving feedback and a reply, or (C) a generic, untargeted opponent?

## Hypotheses (stated before data)
- H1: the adaptive arm shows a larger mean change in blind human-rated overall score (first to last argument) than the generic arm.
- H2: the same against the single-prompt arm.
These are the only confirmatory comparisons. Everything else is descriptive.

## Design
Between-subjects, three arms: `adaptive`, `single`, `generic`. Balanced random assignment (`STUDY_MODE=random`). Same motion pool and side choice for all. Five turns per participant. The interface hides the arm name, but arms look different, so participants may guess; raters are fully blind.

## Sample
At least 10 per arm (30 total). This is pilot-sized: no power claim; report effect sizes and intervals. Stop at the planned n; do not stop early because results look good.

## Procedure (about 30 minutes)
Consent, 5-minute briefing, five-turn debate, seven ratings in the app, short interview, observation notes.

## Measures
- Primary: change in mean rubric score between each participant's first and last argument, rated by two blind raters (`python -m analysis.study export`, then `import`). Report rater agreement (quadratic weighted kappa).
- Secondary: change in the system's own overall score; the seven ratings; share of turns where the targeted dimension rose (`python -m analysis.pilot <db> <mode>`).

## Analysis plan
Permutation test on the difference in mean change, 95% bootstrap interval and Cohen's d, for H1 and H2 (report both unadjusted p-values and say there are two). Exclusions fixed now: fewer than 3 turns completed, or technical failure that prevented replies. Report every exclusion and its arm.

## Decision rules (stated in advance)
Support for a hypothesis only if the interval for the difference lies above zero. Otherwise the result is "inconclusive", and it is reported that way.

## Ethics and data
Voluntary; withdrawal at any time; participant codes only; data stored [where]; cloud model disclosure as in the consent form; AI feedback may contain errors.

## Reporting
All arms, all exclusions, any deviation from this protocol, the model and dates, and the number of times the diagnostic test set was run.
