"""Optional CrewAI orchestration (thesis Ch.5.4 / 6.12).

Requires `pip install crewai` and a local Ollama model. The agents here wrap the
same functions used by app/pipeline.py, so behaviour is identical; CrewAI adds the
role/goal/backstory structure and sequential task context the thesis describes.
Keep this thin: the deterministic pipeline is the tested source of truth.
"""


def build_crew(topic, side, argument, llm_name="ollama/llama3:8b"):
    from crewai import Agent, Crew, Process, Task  # imported lazily

    def mk(role, goal):
        return Agent(role=role, goal=goal, backstory=f"Specialist in {role.lower()} for educational debate.", llm=llm_name, allow_delegation=False)

    analyst = mk("Argument Analyzer", "Extract Toulmin components as JSON")
    scorer = mk("Argument Scorer", "Score seven dimensions 1-5 as JSON")
    diag = mk("Weakness Diagnostician", "Identify the single most consequential weakness")
    strat = mk("Pedagogical Strategist", "Choose the intervention for the weakness")
    opp = mk("Adaptive Opponent", "Write a Socratic reply targeting the weakness; never write the student's argument")
    ctx = f"Motion: {topic}. Student side: {side}. Argument: {argument}"
    t1 = Task(description=f"Extract Toulmin components. {ctx}", expected_output="JSON", agent=analyst)
    t2 = Task(description="Score the argument on the rubric.", expected_output="JSON", agent=scorer, context=[t1])
    t3 = Task(description="Diagnose the weakest dimension.", expected_output="JSON", agent=diag, context=[t2])
    t4 = Task(description="Select the intervention.", expected_output="JSON", agent=strat, context=[t3])
    t5 = Task(description="Generate the opponent reply.", expected_output="2-4 sentence reply", agent=opp, context=[t3, t4])
    return Crew(agents=[analyst, scorer, diag, strat, opp], tasks=[t1, t2, t3, t4, t5], process=Process.sequential)
