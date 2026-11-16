"""Nickname accounts, sessions and learner state (stdlib sqlite only).  File: platform.db

Honest security note: a nickname identifies a learner; it is NOT a password. The app issues a random
session token (stored hashed, with expiry) per browser. This is adequate for a study or demo with no
personal data; add passwords or OAuth before real deployment.

Link to debate.db: every row in `debates` now stores `session_id` (the debate.db session) and
`backend_user_id`, so the two databases can be joined. Existing platform.db files are upgraded in place.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time

NICK_RE = re.compile(r"^[A-Za-z0-9_\-]{3,20}$")
TOKEN_TTL = 14 * 24 * 3600
DB_PATH = os.getenv("PLATFORM_DB", "platform.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, nick_lc TEXT NOT NULL UNIQUE,
  created REAL NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens(
  hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS debates(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, ts REAL NOT NULL, topic TEXT,
  category TEXT, difficulty TEXT, side TEXT, turns INTEGER, overall REAL,
  weakness TEXT, scores TEXT, outcome TEXT, xp INTEGER, session_id INTEGER, backend_user_id INTEGER);
CREATE TABLE IF NOT EXISTS training(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, ts REAL NOT NULL, weakness TEXT,
  kind TEXT, passed INTEGER, score REAL, attempt INTEGER);
"""
MIGRATIONS = [("debates", "session_id", "INTEGER"), ("debates", "backend_user_id", "INTEGER")]


class Store:
    def __init__(self, path=None):
        self.path = path or DB_PATH
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        for table, col, typ in MIGRATIONS:
            cols = {r["name"] for r in self.db.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self.db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        self.db.commit()

    # ---- accounts
    @staticmethod
    def check_nickname(nick: str):
        nick = (nick or "").strip()
        if not NICK_RE.match(nick):
            return "Use 3 to 20 letters, numbers or underscores."
        return None

    def available(self, nick: str) -> bool:
        return self.db.execute("SELECT 1 FROM users WHERE nick_lc=?", (nick.strip().lower(),)).fetchone() is None

    def _issue(self, uid: int) -> str:
        tok = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO tokens VALUES(?,?,?)", (hashlib.sha256(tok.encode()).hexdigest(), uid,
                                                             time.time() + TOKEN_TTL))
        self.db.commit()
        return tok

    def register(self, nick: str):
        nick = nick.strip()
        err = self.check_nickname(nick)
        if err:
            raise ValueError(err)
        if not self.available(nick):
            raise ValueError("That nickname is taken. Try another, or log in if it is yours.")
        cur = self.db.execute("INSERT INTO users(nickname,nick_lc,created,state) VALUES(?,?,?,?)",
                              (nick, nick.lower(), time.time(), json.dumps(new_state())))
        self.db.commit()
        return cur.lastrowid, self._issue(cur.lastrowid)

    def login(self, nick: str):
        r = self.db.execute("SELECT id FROM users WHERE nick_lc=?", (nick.strip().lower(),)).fetchone()
        if not r:
            raise ValueError("No learner with that nickname yet. Create a profile first.")
        return r["id"], self._issue(r["id"])

    def user_for_token(self, tok: str):
        if not tok:
            return None
        r = self.db.execute("SELECT user_id, expires FROM tokens WHERE hash=?",
                            (hashlib.sha256(tok.encode()).hexdigest(),)).fetchone()
        if not r or r["expires"] < time.time():
            return None
        return r["user_id"]

    def logout(self, tok: str):
        self.db.execute("DELETE FROM tokens WHERE hash=?", (hashlib.sha256(tok.encode()).hexdigest(),))
        self.db.commit()

    def user(self, uid: int):
        r = self.db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return {"id": r["id"], "nickname": r["nickname"], "created": r["created"],
                "state": json.loads(r["state"])} if r else None

    def save_state(self, uid: int, state: dict):
        self.db.execute("UPDATE users SET state=? WHERE id=?", (json.dumps(state), uid))
        self.db.commit()

    # ---- history
    def add_debate(self, uid, rec: dict):
        self.db.execute(
            "INSERT INTO debates(user_id,ts,topic,category,difficulty,side,turns,overall,weakness,scores,outcome,xp,"
            "session_id,backend_user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (uid, time.time(), rec.get("topic"), rec.get("category"), rec.get("difficulty"), rec.get("side"),
             rec.get("turns", 0), rec.get("overall"), rec.get("weakness"), json.dumps(rec.get("scores", {})),
             rec.get("outcome"), rec.get("xp", 0), rec.get("session_id"), rec.get("backend_user_id")))
        self.db.commit()

    def debates(self, uid, limit=200):
        rows = self.db.execute("SELECT * FROM debates WHERE user_id=? ORDER BY id", (uid,)).fetchall()[-limit:]
        return [{**dict(r), "scores": json.loads(r["scores"] or "{}")} for r in rows]

    def add_training(self, uid, weakness, kind, passed, score, attempt):
        self.db.execute("INSERT INTO training(user_id,ts,weakness,kind,passed,score,attempt) VALUES(?,?,?,?,?,?,?)",
                        (uid, time.time(), weakness, kind, int(passed), score, attempt))
        self.db.commit()

    def training(self, uid):
        return [dict(r) for r in self.db.execute("SELECT * FROM training WHERE user_id=? ORDER BY id", (uid,))]


def new_state():
    return {"xp": 0, "streak": 0, "best_streak": 0, "badges": [], "last_day": None,
            "recent_topics": [], "quests_done": []}