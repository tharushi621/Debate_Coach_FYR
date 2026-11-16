# Viva presentation: full speaking script (40 slides)

Speak in your own words; these are talking points written to be said aloud. Full run is about 25 minutes. For a 7-minute slot use only slides 1, 4, 8, 10, 13, 17, 19, 26, 27, 29, 30, 32.

---

## Part 1: Introduction

**Slide 1: Cover** (20 s)
Good morning. My research is an adaptive multi-agent debate training system. It finds the weakest part of a student's argument and aims the AI opponent's next move at that weakness. Three words sum it up: diagnose, target, improve.

**Slide 2: Roadmap** (20 s)
I will cover the problem, the literature and the gap, my aim and questions, the method, the system and its process flow, testing and evaluation, the findings, and finally the contribution. At the end there are prepared answers to likely questions.

**Slide 3: Introduction** (40 s)
Debate trains reasoning: students must state a claim, support it with evidence and answer opposition. Chatbot-assisted debates have been shown to improve argumentation skills and motivation. AI is entering education, and multi-agent systems divide expert roles so each can be inspected and replaced. These are three mature ideas, but nobody had joined them for the benefit of the human learner.

**Slide 4: Problem** (40 s)
Students struggle to build arguments. Teachers cannot give individual feedback to a whole class. And generic AI feedback such as "your argument needs improvement" changes nothing in the next turn. Compare it with a targeted reply: "harmful in what specific way, and what evidence shows it?" That makes the student do the thinking, which a vague comment never does.

**Slide 5: Why it is worth solving** (30 s)
Knowing *why* an argument is weak is the difference between feedback and guidance. The system gives immediate, individual feedback, practice that fits the student's own gap, and visible, measurable growth. It turns scarce expert coaching into something every learner can practise with.

---

## Part 2: Literature and the research gap

**Slide 6: Four research streams** (35 s)
I reviewed four streams: AI-supported debate and feedback, argument structure using the Toulmin model, LLM agents and multi-agent systems, and multi-agent debate. Each is individually well supported, which makes joining them a sound bet.

**Slide 7: What each stream shows and where it stops** (40 s)
Read across the table. AI feedback is general and does not shape the next AI turn. Toulmin and argument maps are used to analyse or draw, not to drive live practice. Multi-agent systems are judged on task accuracy, not learner progress. Multi-agent debate is AI talking to AI, with no diagnosis of a human learner. The same step is missing in every stream.

**Slide 8: The research gap** (50 s) *(pause here; this is the key slide)*
In the reviewed literature, no approach lets the diagnosed weakness of a human learner decide the AI opponent's next response. Structured analysis, scoring, diagnosis and adaptive response exist separately. The green dashed boxes are the missing connection. This research closes that loop and then tests whether it works.

**Slide 9: How this differs** (40 s)
This table is a characterisation from my Chapter 2 review; individual systems vary. General chatbots and feedback tools do some things partly. Only this research combines Toulmin analysis, separate dimension scores, naming the weakest dimension, targeting the next move at it, tracking the learner, and checking all of it against human coaches and baselines.

---

## Part 3: Aim, objectives, questions

**Slide 10: Aim** (25 s)
To design, develop and preliminarily evaluate a weakness-targeted adaptive multi-agent debate system that diagnoses weaknesses and generates adaptive AI opponent responses. Diagnose, target, support.

**Slide 11: Objectives** (35 s)
Three groups. Identify: common weaknesses, limits of current tools, Toulmin-based dimensions. Design and develop: the framework, the multi-agent architecture, the web prototype and the adaptive mechanism. Evaluate: technical testing, diagnostic validity, reply quality and usability, and change across turns. The user pilot is the one part still to be completed.

**Slide 12: Research questions** (45 s)
Five questions, each with a named source of evidence. RQ1 is answered by the prototype and the studies. RQ2, which weaknesses can be identified, by the nine-weakness taxonomy labelled by eight coaches. RQ3, finding the lowest dimension, by scoring plus the diagnosis rule tested against coaches. RQ4, can the opponent target the weakness, by blind rating of three reply types. RQ5, usability and learning support, by the ratings form and the planned pilot.

---

## Part 4: Methodology

**Slide 13: Methodology overview** (45 s)
A pragmatist paradigm with design and development research, and a preliminary mixed-methods evaluation. I chose it because the research produces an artefact that must work and help learners. A full controlled experiment needs a bigger sample and more time. Four phases: problem identification, framework design, prototype development, preliminary evaluation.

**Slide 14: Diagnosis framework** (45 s)
This is the instrument. Toulmin parts feed seven scored dimensions: claim clarity, evidence quality, warrant strength, relevance, rebuttal readiness, logical validity and qualification. The lowest dimension names one of nine weaknesses, and each weakness has one fixed teaching move. Because the mapping is explicit, every AI move can be explained.

**Slide 15: Evaluation design** (40 s)
Four strands answer four questions. Does it work: technical testing. Is the diagnosis right: eight coaches labelled 45 arguments. Do targeted replies help: blind rating of 30 arguments, three reply types, two raters. Do learners benefit: the user pilot, which is planned. The first three are complete.

**Slide 16: Rigour** (40 s)
Reference labels come from eight coaches, not from me. The reference rule was fixed before the system was run. Prompts were frozen and the test split was evaluated once. The system and its rivals use the same model. Raters were blind to which system wrote each reply. Automatic checks flag copied ratings. So the findings can be defended whichever way they fall.

---

## Part 5: System, process flow, demo

**Slide 17: Process flow** (60 s) *(key slide)*
Walk left to right along the top, then back along the bottom. The student submits an argument. It is validated, analysed into Toulmin parts and scored on seven dimensions. The weakest dimension becomes a named weakness, which selects one teaching move. The opponent writes a Socratic reply aimed only at that weakness. The tracker compares with the last turn and stores everything. The student revises and the loop repeats for five turns. The green steps are the novel link: the diagnosis does not just describe the student, it decides what the opponent does next.

**Slide 18: Worked example** (45 s)
The student says social media should be banned because it is harmful. Analysis finds a claim and grounds but no warrant, qualifier or rebuttal. These scores are illustrative: evidence is lowest. So the weakness is insufficient evidence and the move is to demand specific evidence. The opponent asks what evidence shows the harm is caused by social media rather than other factors.

**Slide 19: Architecture** (40 s)
Seven agents on a CrewAI crew: orchestrator, analyser, scorer, diagnostician, strategist, opponent and progress tracker. Four use the language model; three are deterministic rules. Separation makes each step logged, inspectable and replaceable.

**Slide 20: Why each feature** (45 s)
Toulmin analysis shows which part is weak. Seven dimensions, because one overall score cannot say why an argument fails. The nine-weakness map, because each weakness needs a different move. Socratic replies make the student supply the reasoning. Guardrails keep the thinking with the learner. Progress tracking makes improvement visible. Choosing your own motion and side gives learners agency.

**Slide 21: Why this tech stack** (45 s)
CrewAI maps one-to-one to my role-based agents. FastAPI is light and easy to test. Streamlit lets effort go into the mechanism rather than the front end. SQLite needs no setup and stores every turn for audit. For the model: Llama 3 8B ran at 156 to 170 seconds per turn on my laptop, so I use GPT OSS 20B through an API at about 3 to 4 seconds per call, with Llama 3 8B kept as the local backup. Analysis uses pandas, scikit-learn, SciPy and matplotlib.

**Slide 22: Implementation highlights** (45 s)
The system never trusts one model call: invalid scores are corrected, and if the model names an invalid weakness a rule takes over. Guardrails replace replies that leak scores or write the student's argument. Every turn is stored for audit. Rate limits are waited out and long runs resume. The model is swapped by one setting. Integrity checks flag copied ratings.

**Slide 23: Live demo plan** (30 s)
Seven steps: choose a motion, pick a side, write an argument, read the argument map, see the targeted reply, check progress, open the profile. Steps four and five are the ones to watch. I have screenshots as a backup if the network fails. *(Then run the live demo.)*

---

## Part 6: Testing and evaluation

**Slide 24: Testing and validation** (40 s)
88 automated tests pass. Unit tests cover validation, scoring and mapping. Integration tests cover the agents with the database and API. System tests run the full crew. Regression tests cover failures met during development. Browser compatibility checks are still to be completed manually.

**Slide 25: Metrics** (45 s)
Accuracy with a 95% interval, because samples are small. Cohen's and Fleiss' kappa to set the human ceiling. Exact McNemar to compare two systems on the same items. Weighted kappa for the 1 to 5 ratings. Win, tie, loss with Wilcoxon for reply comparison. And a ghost-writing rate to protect against over-reliance on AI.

---

## Part 7: Findings

**Slide 26: Finding 1, human benchmark** (40 s)
Eight real coaches labelled 45 arguments. Their agreement is moderate: Fleiss' kappa 0.53, and each coach agrees with the majority of the others about 68.5% of the time on average. So the task is hard even for experts, and the benchmark is credible.

**Slide 27: Finding 2, diagnosis accuracy** (50 s)
Honestly, the pipeline did not beat a single prompt at diagnosis. On the strict reference, 21 test items, the system scored 57.1% and the single prompt 76.2%. The difference is not significant (McNemar p 0.34) and the sample is small. Splitting the work across agents does not raise accuracy here; its value is explainability and the targeted loop.

**Slide 28: Finding 3, error pattern** (40 s)
Over all 39 items the system chose missing warrant 11 times, more than any other weakness, and found poor relevance in only 1 of 5 such items. My hypothesis is that the lowest-score rule favours warrant on short arguments. That is to be tested, and the next step is a calibrated rule retested on new coach-labelled items.

**Slide 29: Finding 4, reply quality** (60 s)
Two blind raters scored replies from three systems on 30 arguments. Targeted replies were far more helpful than generic: 3.62 against 2.38, with 29 wins, 1 tie and 0 losses. On targeting, 3.77 against 2.67. Against a single-call opponent the difference is not meaningful. Rater agreement was 0.87 and 0.64 weighted kappa. No reply wrote the student's argument: 0 of 90.

**Slide 30: Final results** (40 s)
Supported: targeted replies beat generic ones, no ghost-writing, the system runs end to end and passes 88 tests, and a human reference from eight coaches now exists. Not yet shown: diagnostic accuracy above a single prompt, learning gains in students, a benefit from seven agents beyond transparency, and results beyond one model and small samples.

**Slide 31: Recommendations** (35 s)
For teachers and students: use targeted Socratic replies as a sparring partner, not a judge. For builders of educational AI: calibrate diagnosis, and test against human coaches and a one-prompt rival. For researchers: a larger pilot, evidence retrieval, multiple weaknesses and a teacher dashboard.

---

## Part 8: Contribution and close

**Slide 32: Contributions** (45 s)
Four contributions. A closed-loop framework where diagnosis determines the AI's next reply. A diagnosis instrument that other tutoring systems can reuse. A working multi-agent prototype. And a transparent evaluation protocol that others can copy to judge educational AI honestly.

**Slide 33: Findings to contributions** (40 s)
Targeted beating generic supports the closed-loop framework. Parity with a single call tells designers the value of agents is auditability, not quality. Moderate coach agreement shows the task is hard and the benchmark valuable. The diagnosis gap shows a concrete improvement path. Every contribution is backed by a measured finding.

**Slide 34: Limitations** (40 s)
Samples are small, one main model was used, arguments were prepared by me, the student pilot is still to run, and the generic opponent is recognisable by style. I handled these with intervals and exact tests, the same model for every system, eight independent coaches, and by calling results preliminary. The measured values here supersede the provisional estimates printed in Chapter 7.

**Slide 35: Future work** (30 s)
Near term: run the 7 to 10 participant pilot, calibrate the warrant and relevance rules, retest. Next: several weaknesses at once, evidence retrieval, a teacher dashboard. Later: Sinhala, Tamil and voice, a controlled study, and long-term transfer.

---

## Backup: use only if asked

**Slide 36: Value and novelty.** The new element is that the reply is driven by a structured diagnosis; blind raters scored targeted replies far above generic (3.62 vs 2.38). I tested a single prompt and report that it diagnoses as well or better. Beneficiaries are students without a sparring partner and teachers in large classes. Guardrails prevent the AI replacing the student's thinking (0 of 90).

**Slide 37: Method and evaluation.** Toulmin splits an argument into parts so a weakness ties to a specific part. Validation used eight coaches, a rule fixed beforehand and a same-model rival. Ratings are trusted because raters were blind and agreement was 0.87 and 0.64. GPT OSS 20B was used because Llama 3 8B took 156 to 170 seconds per turn on my laptop against about 3 to 4 seconds per call; Llama 3 8B remains the local backup, and this choice is disclosed.

**Slide 38: Results and limits.** 57% trails the single prompt at 76%, and coaches themselves agree only about 59 to 69%; the error pattern is clear so the fix is targeted. Samples are small, so I report intervals and call results preliminary. The student pilot is planned for 7 to 10 volunteers, with protocol and tools ready. First change: calibrate the warrant rule and add a relevance check.

**Slide 39: References.** Numbers match the thesis reference list.

**Slide 40: Thank you.** Diagnose the weakest dimension, target it with the next move, track the improvement. Thank you; I am happy to take questions.

---

## Quick tips
- Never say "80% accuracy" or quote Chapter 7's provisional numbers; use only the numbers on the slides.
- If asked "is 57% good?" answer honestly: it trails a single prompt, it is a small sample, and I know the exact fix.
- If asked about the pilot: it is planned and ready, not yet run.
