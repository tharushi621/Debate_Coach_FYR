"""SQLite persistence (thesis Table 4.12).  File: debate.db in the project root."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT DEFAULT 'student', created_at TEXT);
CREATE TABLE IF NOT EXISTS debate_sessions(session_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic TEXT NOT NULL,
  student_side TEXT NOT NULL CHECK(student_side IN ('proponent','opponent')), mode TEXT DEFAULT 'adaptive', created_at TEXT);
CREATE TABLE IF NOT EXISTS debate_turns(turn_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, turn_number INTEGER NOT NULL,
  student_argument TEXT NOT NULL, timestamp TEXT, UNIQUE(session_id, turn_number));
CREATE TABLE IF NOT EXISTS argument_analyses(analysis_id INTEGER PRIMARY KEY AUTOINCREMENT, turn_id INTEGER, claim TEXT, grounds TEXT, warrant TEXT,
  backing TEXT, qualifier TEXT, rebuttal TEXT, missing_components TEXT);
CREATE TABLE IF NOT EXISTS argument_scores(score_id INTEGER PRIMARY KEY AUTOINCREMENT, turn_id INTEGER, dimension TEXT, score INTEGER, explanation TEXT);
CREATE TABLE IF NOT EXISTS weakness_diagnoses(diagnosis_id INTEGER PRIMARY KEY AUTOINCREMENT, turn_id INTEGER, weakness TEXT, affected_component TEXT,
  diagnosis_reason TEXT, overall_score REAL, source TEXT);
CREATE TABLE IF NOT EXISTS interventions(intervention_id INTEGER PRIMARY KEY AUTOINCREMENT, diagnosis_id INTEGER, intervention_type TEXT, strategy_description TEXT);
CREATE TABLE IF NOT EXISTS ai_responses(response_id INTEGER PRIMARY KEY AUTOINCREMENT, turn_id INTEGER, intervention_type TEXT, response_text TEXT,
  feedback_text TEXT, timestamp TEXT, fallback_used INTEGER DEFAULT 0, latency_s REAL, orchestrator TEXT);
CREATE TABLE IF NOT EXISTS evaluation_cases(case_id INTEGER PRIMARY KEY AUTOINCREMENT, argument_text TEXT, reference_weakness TEXT,
  system_weakness TEXT, match_result INTEGER, split TEXT, run_date TEXT, backend TEXT);
CREATE TABLE IF NOT EXISTS feedback(feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session_id INTEGER,
  ease_of_use INTEGER, clarity INTEGER, ai_relevance INTEGER, weakness_help INTEGER, improvement_help INTEGER, fairness INTEGER, reuse INTEGER, comment TEXT);
"""

# Columns added after the first release. Existing debate.db files are upgraded in place, no data is lost.
MIGRATIONS = [("ai_responses", "latency_s", "REAL"), ("ai_responses", "orchestrator", "TEXT"),
              ("evaluation_cases", "split", "TEXT"), ("evaluation_cases", "run_date", "TEXT"),
              ("evaluation_cases", "backend", "TEXT")]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path="debate.db"):
        self.path = path
        self._keep = sqlite3.connect(path, check_same_thread=False)
        self._keep.row_factory = sqlite3.Row
        self._keep.executescript(SCHEMA)
        for table, col, typ in MIGRATIONS:
            cols = {r["name"] for r in self._keep.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self._keep.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        self._keep.commit()

    @contextmanager
    def tx(self):
        try:
            yield self._keep
            self._keep.commit()
        except Exception:
            self._keep.rollback()
            raise

    def one(self, sql, args=()):
        r = self._keep.execute(sql, args).fetchone()
        return dict(r) if r else None

    def all(self, sql, args=()):
        return [dict(r) for r in self._keep.execute(sql, args).fetchall()]

    # ---- users / sessions / turns
    def create_user(self, name, role="student"):
        with self.tx() as c:
            return c.execute("INSERT INTO users(name,role,created_at) VALUES(?,?,?)", (name, role, now())).lastrowid

    def get_or_create_user(self, name, role="student"):
        """One row per nickname: restarting the UI no longer creates a new user every time."""
        r = self.one("SELECT user_id FROM users WHERE lower(name)=lower(?) ORDER BY user_id LIMIT 1", (name,))
        return (r["user_id"], False) if r else (self.create_user(name, role), True)

    def create_session(self, user_id, topic, side, mode="adaptive"):
        with self.tx() as c:
            return c.execute("INSERT INTO debate_sessions(user_id,topic,student_side,mode,created_at) VALUES(?,?,?,?,?)",
                             (user_id, topic, side, mode, now())).lastrowid

    def get_session(self, sid):
        return self.one("SELECT * FROM debate_sessions WHERE session_id=?", (sid,))

    def next_turn_number(self, sid):
        return self.one("SELECT COALESCE(MAX(turn_number),0)+1 AS n FROM debate_turns WHERE session_id=?", (sid,))["n"]

    def previous_arguments(self, sid):
        return [r["student_argument"] for r in self.all(
            "SELECT student_argument FROM debate_turns WHERE session_id=? ORDER BY turn_number", (sid,))]

    def history(self, sid):
        return self.all("""SELECT t.turn_number, t.student_argument, d.weakness, d.diagnosis_reason, d.overall_score,
            r.intervention_type, r.response_text, r.feedback_text, r.fallback_used, r.latency_s
            FROM debate_turns t LEFT JOIN weakness_diagnoses d ON d.turn_id=t.turn_id
            LEFT JOIN ai_responses r ON r.turn_id=t.turn_id WHERE t.session_id=? ORDER BY t.turn_number""", (sid,))

    def turn_scores(self, turn_id):
        return {r["dimension"]: r["score"] for r in self.all(
            "SELECT dimension,score FROM argument_scores WHERE turn_id=?", (turn_id,))}

    def last_turn(self, sid):
        t = self.one("""SELECT t.turn_id, t.turn_number, d.weakness, d.overall_score FROM debate_turns t
            JOIN weakness_diagnoses d ON d.turn_id=t.turn_id WHERE t.session_id=? ORDER BY t.turn_number DESC LIMIT 1""", (sid,))
        if t:
            t["scores"] = self.turn_scores(t["turn_id"])
        return t

    def save_turn(self, sid, number, argument, analysis, scores, diagnosis, intervention, response,
                  feedback_text, fallback_used=0, latency=None, orchestrator=None):
        """Persist one whole turn atomically (analysis, 7 scores, diagnosis, intervention, reply)."""
        with self.tx() as c:
            tid = c.execute("INSERT INTO debate_turns(session_id,turn_number,student_argument,timestamp) VALUES(?,?,?,?)",
                            (sid, number, argument, now())).lastrowid
            j = lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v
            c.execute("INSERT INTO argument_analyses(turn_id,claim,grounds,warrant,backing,qualifier,rebuttal,missing_components) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (tid, analysis.get("main_claim"), j(analysis.get("grounds")), analysis.get("warrant"),
                       analysis.get("backing"), analysis.get("qualifier"), analysis.get("rebuttal"),
                       j(analysis.get("missing_components"))))
            for dim, v in scores["dimensions"].items():
                c.execute("INSERT INTO argument_scores(turn_id,dimension,score,explanation) VALUES(?,?,?,?)",
                          (tid, dim, v["score"], v["explanation"]))
            did = c.execute("INSERT INTO weakness_diagnoses(turn_id,weakness,affected_component,diagnosis_reason,overall_score,source) "
                            "VALUES(?,?,?,?,?,?)",
                            (tid, diagnosis["lowest_weakness"], diagnosis["affected_component"],
                             diagnosis["diagnosis_reason"], scores["overall_quality"], diagnosis.get("source"))).lastrowid
            c.execute("INSERT INTO interventions(diagnosis_id,intervention_type,strategy_description) VALUES(?,?,?)",
                      (did, intervention["type"], intervention["description"]))
            c.execute("INSERT INTO ai_responses(turn_id,intervention_type,response_text,feedback_text,timestamp,fallback_used,latency_s,orchestrator) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (tid, intervention["type"], response, feedback_text, now(), int(bool(fallback_used)), latency, orchestrator))
            return tid

    # ---- evaluation and ratings
    def add_evaluation_cases(self, rows, split=None, backend=None):
        """rows: iterable of (argument_text, reference_weakness, system_weakness). Used by eval/diagnostic_eval.py."""
        rows, stamp = list(rows), now()
        with self.tx() as c:
            c.executemany("INSERT INTO evaluation_cases(argument_text,reference_weakness,system_weakness,match_result,split,run_date,backend) "
                          "VALUES(?,?,?,?,?,?,?)",
                          [(a, ref, sysw, int(ref == sysw), split, stamp, backend) for a, ref, sysw in rows])
        return len(rows)

    def add_feedback(self, user_id, session_id, ratings, comment=""):
        with self.tx() as c:
            c.execute("INSERT INTO feedback(user_id,session_id,ease_of_use,clarity,ai_relevance,weakness_help,improvement_help,fairness,reuse,comment) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?)", (user_id, session_id, *ratings, comment))