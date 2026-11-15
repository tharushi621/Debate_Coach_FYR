"""CrewAI orchestration (thesis 5.4 and 6.12).

One debate turn is ONE sequential CrewAI crew of six role based agents:

    Argument Analyzer          LLM   extracts the Toulmin components
    Argument Scorer            LLM   scores seven dimensions from 1 to 5, using the analysis as context
    Weakness Diagnostician     LLM   proposes the weakness (accepted only if valid, thesis 6.2.4)
    Pedagogical Strategist     rule  weakness -> intervention lookup (Table 3.11, deterministic)
    Adaptive Opponent          LLM   writes the targeted Socratic reply, checked by guardrails
    Progress Tracker           rule  compares with the previous turn, stores everything in SQLite

How it works, so you can explain it in the viva
  * Every agent is a real crewai.Agent with a role, goal and backstory, and every step is a
    crewai.Task chained with context=[...], so the output of one agent is what the next agent reads.
  * The LLM agents run on your local Ollama model through a small adapter (ModelLLM), so temperature 0,
    seed 7, JSON mode and the output caps stay exactly as in Chapter 7.
  * The two deterministic agents (Strategist, Tracker) use RuleLLM: still CrewAI agents, but they answer
    from code instead of from a model. That keeps the closed loop auditable and costs no model time.
  * A task callback validates each output (clamps scores, validates the diagnosis, applies the guardrails)
    and rewrites it, so the NEXT agent only ever sees validated data.

Install:  pip install crewai      Switch off with ORCHESTRATOR=python (plain functions, same results).
"""
import json
import logging
import os
import time
import warnings

# Quiet by default: no telemetry, no trace prompts.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
logging.getLogger("crewai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message="A function callback cannot be saved")

from . import agents as A
from .llm import extract_json

_CACHE = {}


def available():
    try:
        import crewai  # noqa: F401
        return True
    except Exception:
        return False


def _classes():
    """Import CrewAI lazily and build the two adapter classes once."""
    if _CACHE:
        return _CACHE
    try:
        from crewai import Agent, BaseLLM, Crew, Process, Task
    except ImportError as e:
        raise RuntimeError("CrewAI is not installed. Run: pip install crewai   "
                           "(or set ORCHESTRATOR=python to use the plain pipeline)") from e

    class _Base(BaseLLM):
        def __init__(self, label):
            super().__init__(model=label, temperature=0)

        def supports_function_calling(self):
            return False

        def supports_stop_words(self):
            return False

        def get_context_window_size(self):
            return 8192

    class ModelLLM(_Base):
        """CrewAI -> your Ollama (or OpenAI compatible) model. Retries bad JSON, records the time."""

        def __init__(self, inner, task, ctx):
            super().__init__(f"{getattr(inner, 'name', 'llm')}:{task}")
            self.inner, self.task, self.ctx = inner, task, ctx

        def call(self, messages, tools=None, callbacks=None, available_functions=None,
                 from_task=None, from_agent=None, response_model=None):
            t, last = time.time(), None
            for _ in range(3):
                raw = self.inner.complete(messages, self.task)
                try:
                    out = json.dumps(extract_json(raw))
                    self.ctx["timings"][self.task] = round(time.time() - t, 1)
                    return out
                except ValueError as e:
                    last = e
            raise RuntimeError(f"LLM failed for task {self.task}: {last}")

    class RuleLLM(_Base):
        """A CrewAI agent that answers from deterministic code (no model call)."""

        def __init__(self, task, fn, ctx):
            super().__init__(f"rules:{task}")
            self.task, self.fn, self.ctx = task, fn, ctx

        def call(self, messages, tools=None, callbacks=None, available_functions=None,
                 from_task=None, from_agent=None, response_model=None):
            t = time.time()
            out = json.dumps(self.fn())
            self.ctx["timings"][self.task] = round(time.time() - t, 2)
            return out

    _CACHE.update(Agent=Agent, Crew=Crew, Process=Process, Task=Task, ModelLLM=ModelLLM, RuleLLM=RuleLLM)
    return _CACHE


def run_turn(db, llm, sid, topic, side, history, argument, previous, finish):
    """Run the crew for one adaptive turn.

    finish(analysis, scores, diagnosis, intervention, reply, fallback, feedback, latency) must save
    the turn and return (turn_id, turn_number). It is called by the Progress Tracker agent.
    """
    C = _classes()
    Agent, Crew, Process, Task = C["Agent"], C["Crew"], C["Process"], C["Task"]
    ModelLLM, RuleLLM = C["ModelLLM"], C["RuleLLM"]
    t_start = time.time()
    ctx = {"timings": {}}
    prev_weak = previous["weakness"] if previous else None

    def agent(role, goal, backstory, model):
        return Agent(role=role, goal=goal, backstory=backstory, llm=model, allow_delegation=False,
                     verbose=False, max_retry_limit=0, max_iter=3)

    # ---------------------------------------------------------------- rule based steps
    def strategist_fn():
        repeats = sum(1 for h in db.history(sid) if h["weakness"] == ctx["diagnosis"]["lowest_weakness"])
        ctx["intervention"] = A.strategise(ctx["diagnosis"], prev_weak, repeats)
        return ctx["intervention"]

    def tracker_fn():
        ctx["progress"] = A.track(ctx["scores"], ctx["diagnosis"], previous)
        ctx["feedback"] = A.feedback(ctx["scores"], ctx["diagnosis"])
        ctx["tid"], ctx["number"] = finish(ctx["analysis"], ctx["scores"], ctx["diagnosis"], ctx["intervention"],
                                           ctx["reply"], ctx["fallback"], ctx["feedback"],
                                           round(time.time() - t_start, 1))
        return {"saved_turn_id": ctx["tid"], "progress": ctx["progress"]}

    use_llm_diag = os.getenv("DIAG_USE_LLM", "1") != "0"

    # ---------------------------------------------------------------- agents
    analyst = agent("Argument Analyzer",
                    "Extract the Toulmin components of the student's argument as JSON.",
                    "You are a careful argumentation analyst. You extract only what the student wrote.",
                    ModelLLM(llm, "analyse", ctx))
    scorer = agent("Argument Scorer",
                   "Score seven argumentation dimensions from 1 to 5 using the rubric, as JSON.",
                   "You score consistently against a fixed rubric and explain each score briefly.",
                   ModelLLM(llm, "score", ctx))
    diagnostician = agent("Weakness Diagnostician",
                          "Identify the single most consequential weakness, as JSON.",
                          "You read the scores and name the one weakness that matters most.",
                          ModelLLM(llm, "diagnose", ctx) if use_llm_diag else RuleLLM("diagnose", lambda: {}, ctx))
    strategist = agent("Pedagogical Strategist",
                       "Select the intervention that fits the diagnosed weakness.",
                       "You apply the weakness to intervention map (thesis Table 3.11) without improvising.",
                       RuleLLM("strategise", strategist_fn, ctx))
    opponent = agent("Adaptive Opponent",
                     "Write a short Socratic reply that targets only the diagnosed weakness.",
                     "You are a respectful debate opponent and tutor. You never reveal scores and never "
                     "write the student's argument for them.",
                     ModelLLM(llm, "oppose", ctx))
    tracker = agent("Progress Tracker",
                    "Compare this turn with the previous one and store the results.",
                    "You keep the learner's record and measure change on the targeted dimension.",
                    RuleLLM("track", tracker_fn, ctx))

    # ---------------------------------------------------------------- callbacks (validate, then rewrite)
    def cb_analyse(out):
        ctx["analysis"] = A.normalise_analysis(extract_json(out.raw), topic, argument)
        out.raw = json.dumps({k: ctx["analysis"].get(k) for k in
                              ("main_claim", "grounds", "warrant", "backing", "qualifier", "rebuttal",
                               "missing_components")})

    def cb_score(out):
        ctx["scores"] = A.normalise_scores(extract_json(out.raw))
        out.raw = json.dumps({**ctx["scores"]["dimensions"], "overall_quality": ctx["scores"]["overall_quality"]})

    def cb_diagnose(out):
        ctx["diagnosis"] = A.resolve_diagnosis(ctx["scores"], argument, ctx["analysis"], extract_json(out.raw))
        d = ctx["diagnosis"]
        out.raw = json.dumps({"lowest_weakness": d["lowest_weakness"], "affected_component": d["affected_component"],
                              "diagnosis_reason": d["diagnosis_reason"]})

    def cb_oppose(out):
        text = extract_json(out.raw).get("ai_opponent_response")
        ctx["reply"], ctx["fallback"] = A.guard_reply(text, ctx["intervention"], topic, side, argument, ctx["analysis"])
        out.raw = json.dumps({"ai_opponent_response": ctx["reply"]})

    # ---------------------------------------------------------------- tasks (chained by context)
    t1 = Task(description=A.ANALYSE_PROMPT.format(topic=topic, side=side, history=history[-3:], argument=argument),
              expected_output="One JSON object with the Toulmin components.", agent=analyst, callback=cb_analyse)
    t2 = Task(description=A.SCORE_PROMPT.format(topic=topic, side=side, analysis=A.FROM_CONTEXT, argument=argument),
              expected_output="One JSON object with seven scored dimensions.", agent=scorer, context=[t1],
              callback=cb_score)
    t3 = Task(description=A.DIAG_PROMPT.format(topic=topic, side=side, argument=argument, weaknesses=A.WEAKNESSES,
                                               scores=A.FROM_CONTEXT),
              expected_output="One JSON object naming the weakness.", agent=diagnostician, context=[t2],
              callback=cb_diagnose)
    t4 = Task(description="Select the pedagogical intervention for the diagnosed weakness using the fixed "
                          "weakness to intervention map.",
              expected_output="One JSON object with the intervention type and description.", agent=strategist,
              context=[t3])
    t5 = Task(description=A.OPPONENT_PROMPT.format(topic=topic, side=side, argument=argument,
                                                   weakness=A.FROM_CONTEXT, reason=A.FROM_CONTEXT,
                                                   instruction=A.FROM_CONTEXT),
              expected_output="One JSON object with the opponent reply.", agent=opponent, context=[t3, t4],
              callback=cb_oppose)
    t6 = Task(description="Compare this turn with the previous turn, then store the turn in the database.",
              expected_output="One JSON object with the progress summary.", agent=tracker, context=[t2, t3, t5])

    Crew(agents=[analyst, scorer, diagnostician, strategist, opponent, tracker], tasks=[t1, t2, t3, t4, t5, t6],
         process=Process.sequential, verbose=False).kickoff()

    ctx["timings"]["total"] = round(time.time() - t_start, 1)
    return ctx