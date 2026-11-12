"""Smoke test: python -m app.smoke   (uses LLM_BACKEND / LLM_* env vars)
Sends one argument through the closed loop and prints the outputs in the Appendix C JSON shapes."""
import json

from .db import Database
from .llm import make_llm
from .pipeline import process_turn

TOPIC = "Social media should be banned for children under 16."
ARG = "Social media should be banned for children because it is harmful."


def main():
    try:
        llm = make_llm()
        db = Database(":memory:")
        sid = db.create_session(db.create_user("smoke"), TOPIC, "proponent")
        r = process_turn(db, llm, sid, ARG)
    except Exception as e:  # connection, key, model-name problems land here
        print(f"SMOKE TEST FAILED: {e}")
        raise SystemExit(1)
    dims = r["scores"]["dimensions"]
    print("backend:", getattr(llm, "name", "?"), "| model:", getattr(llm, "model", "n/a"))
    print("\n--- Toulmin analysis (Appendix C) ---")
    print(json.dumps({k: r["analysis"].get(k) for k in ("main_claim", "grounds", "warrant", "backing", "qualifier", "rebuttal", "missing_components")}, indent=2))
    print("\n--- Argument scores (Appendix C) ---")
    print(json.dumps({**dims, "overall_quality": r["scores"]["overall_quality"]}, indent=2))
    d = r["diagnosis"]
    print("\n--- Diagnosis (Appendix C) ---")
    print(json.dumps({"lowest_weakness": d["lowest_weakness"], "affected_component": d["affected_component"],
                      "diagnosis_reason": d["diagnosis_reason"], "recommended_intervention": d["recommended_intervention"]}, indent=2))
    print(f"\ndiagnosis source: {d['source']} | intervention: {r['intervention']['type']} | guardrail fallback used: {r['guardrail_fallback']}")
    print("\n--- AI opponent ---\n" + r["ai_opponent_response"])


if __name__ == "__main__":
    main()
