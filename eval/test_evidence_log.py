"""Chapter 7.4-7.6 test evidence: runs the real automated tests, maps the passing ones to the thesis test cases, writes a log.

  python -m eval.test_evidence_log      -> docs/TEST_EVIDENCE.md  (date, machine, python, every result as run)

Only what the automated tests actually executed is marked PASS. Cases that need a person (browser compatibility, the user
interface look) are listed as MANUAL and stay "not yet recorded" until you tick them in docs/TEST_EVIDENCE.md by hand.
"""
import datetime
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

# thesis test case -> automated tests that exercise it (substring of the pytest test name)
CASES = [
    ("7.4 TC1 Debate topic selection", ["thesis_motions_are_stored", "custom_motion_is_validated"]),
    ("7.4 TC2 Debate side selection", ["only_supports_the_adaptive_mode", "api_flow_and_persistence"]),
    ("7.4 TC3 Empty argument validation", ["validation", "invalid", "empty"]),
    ("7.4 TC4 Short argument validation", ["validation", "short"]),
    ("7.4 TC5 Toulmin component extraction", ["analysis", "normalise_analysis", "missing_components"]),
    ("7.4 TC6 Score range 1-5", ["score", "clamp"]),
    ("7.4 TC7 Overall score calculation", ["overall", "score"]),
    ("7.4 TC8 Weakness-to-intervention mapping", ["intervention", "mapping", "every_weakness"]),
    ("7.4 TC9 LLM JSON parsing", ["extract_json", "json"]),
    ("7.4 TC10 Database record creation", ["every_table_gets_rows"]),
    ("7.5 TC1 Session creation and argument submission", ["api_flow_and_persistence"]),
    ("7.5 TC2-4 Analysis -> scoring -> diagnosis -> opponent", ["full_turn_and_progress", "crew_runs_all_agents"]),
    ("7.5 TC5 Adaptive response stored in database", ["every_table_gets_rows", "fallback_and_source_are_persisted"]),
    ("7.5 TC6 Progress tracking integration", ["progress_has_the_thesis_6_2_7_fields", "full_turn_and_progress"]),
    ("7.6 TC1/2 End-to-end and multi-turn workflow", ["crew_runs_all_agents", "full_turn_and_progress"]),
    ("7.6 TC3 API functionality", ["api_flow_and_persistence", "api_exposes_topics"]),
    ("7.6 TC5 Database persistence across restart", ["data_survives_restart"]),
]
MANUAL = ["7.6 TC4 Browser compatibility (Chrome, Edge, Firefox): open the Streamlit app in each browser and tick here",
          "7.6 TC1 End-to-end through the real Streamlit page with a real model: play one debate and tick here"]


def run():
    xml = "docs/_pytest_results.xml"
    p = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
                       capture_output=True, text=True)
    root = ET.parse(xml).getroot()
    res = {}
    for tc in root.iter("testcase"):
        bad = tc.find("failure") is not None or tc.find("error") is not None
        skipped = tc.find("skipped") is not None
        res[tc.get("name")] = "FAIL" if bad else "SKIP" if skipped else "PASS"
    lines = [f"# Test evidence (generated {datetime.datetime.now():%Y-%m-%d %H:%M})", "",
             f"Machine: {platform.platform()} · Python {platform.python_version()}",
             f"Automated run: {sum(v == 'PASS' for v in res.values())} passed, {sum(v == 'FAIL' for v in res.values())} failed, "
             f"{sum(v == 'SKIP' for v in res.values())} skipped, out of {len(res)} tests (`pytest tests`).", "",
             "| Thesis test case | Automated tests that exercised it | Result |", "|---|---|---|"]
    for case, keys in CASES:
        hit = {n: r for n, r in res.items() if any(k in n for k in keys)}
        status = "NOT COVERED" if not hit else "FAIL" if "FAIL" in hit.values() else "PASS"
        lines.append(f"| {case} | {len(hit)} | {status} |")
    lines += ["", "## Manual checks (not run by the computer; tick when you have really done them)", ""] + [f"- [ ] {m}" for m in MANUAL]
    lines += ["", "## Every automated test as run", ""] + [f"- {r}: {n}" for n, r in sorted(res.items())]
    open("docs/TEST_EVIDENCE.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return p.returncode, res


if __name__ == "__main__":
    code, res = run()
    print(f"wrote docs/TEST_EVIDENCE.md ({len(res)} tests)")
    sys.exit(0)
