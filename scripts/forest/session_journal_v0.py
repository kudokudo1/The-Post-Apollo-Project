"""Forest Core B1 // injected-connection conversation journal (synthetic only).

NO production data path, identity issuer, encryption, file opener, background
process, or live Forest service. A trusted host must supply a scoped SQLite
connection and independently authorize the claimed owner before using this.
"""
from __future__ import annotations

import re
import sqlite3
import time
import uuid
from contextlib import contextmanager

SCHEMA_VERSION = 1
MAX_BODY = 16000
MAX_TITLE = 160
MAX_PAGE = 100
MAX_MESSAGES_PER_SESSION = 100000
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)

CREATE_SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE forest_sessions (
    session_id TEXT PRIMARY KEY,
    owner_key TEXT NOT NULL,
    tree_key TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('OPEN','PAUSED','ARCHIVED')),
    revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);
CREATE INDEX forest_sessions_owner_updated
ON forest_sessions(owner_key, updated_at_ms DESC);
CREATE TABLE forest_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES forest_sessions(session_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK(ordinal > 0),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    body TEXT NOT NULL,
    recorded_at_ms INTEGER NOT NULL,
    UNIQUE(session_id, ordinal)
);
CREATE INDEX forest_turns_order ON forest_turns(session_id, ordinal);
PRAGMA user_version = 1;
COMMIT;
"""


class JournalRefusal(Exception):
    """Static refusal code. Avoid echoing private content into logs."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _key(value: object) -> str:
    if type(value) is not str or KEY.fullmatch(value) is None:
        raise JournalRefusal("INVALID_IDENTIFIER")
    return value


def _time(value: object) -> int:
    if type(value) is not int or not 0 < value <= 2**63 - 1:
        raise JournalRefusal("INVALID_TIME")
    return value


def _text(value: object, max_size: int) -> str:
    if (type(value) is not str or not value or "\x00" in value
            or len(value.encode("utf-8")) > max_size):
        raise JournalRefusal("INVALID_TEXT")
    return value


def bootstrap_synthetic(db: sqlite3.Connection) -> None:
    """Explicit fixture bootstrap. Never infer an unknown database is empty."""
    if db.in_transaction:
        raise JournalRefusal("ACTIVE_TRANSACTION")
    if db.execute("PRAGMA user_version").fetchone()[0] != 0:
        raise JournalRefusal("UNSUPPORTED_SCHEMA")
    if db.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchone()[0]:
        raise JournalRefusal("EXISTING_DATABASE")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(CREATE_SCHEMA)


@contextmanager
def _write(db: sqlite3.Connection):
    if db.in_transaction:
        raise JournalRefusal("ACTIVE_TRANSACTION")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


class ForestSessionJournal:
    """Host-injected store. owner_key is a scope filter, NOT authentication."""

    def __init__(self, db: sqlite3.Connection):
        if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise JournalRefusal("UNSUPPORTED_SCHEMA")
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise JournalRefusal("FOREIGN_KEYS_REQUIRED")
        self.db = db

    def _owned(self, owner: str, session: str):
        row = self.db.execute(
            "SELECT session_id, tree_key, title, state, revision, "
            "created_at_ms, updated_at_ms FROM forest_sessions "
            "WHERE owner_key = ? AND session_id = ?",
            (_key(owner), _key(session)),
        ).fetchone()
        if row is None:
            raise JournalRefusal("NOT_FOUND")
        keys = ("session_id", "tree_key", "title", "state", "revision",
                "created_at_ms", "updated_at_ms")
        return dict(zip(keys, row))

    def create_session(self, owner: str, tree: str, title: str, *,
                       now_ms: int) -> dict:
        owner = _key(owner)
        tree = _key(tree)
        title = _text(title, MAX_TITLE)
        now_ms = _time(now_ms)
        session = "s_" + uuid.uuid4().hex
        with _write(self.db):
            self.db.execute(
                "INSERT INTO forest_sessions "
                "(session_id,owner_key,tree_key,title,state,revision,"
                "created_at_ms,updated_at_ms) VALUES (?,?,?,?,?,?,?,?)",
                (session, owner, tree, title, "OPEN", 0, now_ms, now_ms),
            )
        return self._owned(owner, session)

    def session(self, owner: str, session_id: str) -> dict:
        return self._owned(owner, session_id)

    def sessions(self, owner: str, *, limit: int = MAX_PAGE) -> list[dict]:
        owner = _key(owner)
        if type(limit) is not int or not 1 <= limit <= MAX_PAGE:
            raise JournalRefusal("INVALID_LIMIT")
        rows = self.db.execute(
            "SELECT session_id,tree_key,title,state,revision,created_at_ms,"
            "updated_at_ms FROM forest_sessions WHERE owner_key = ? "
            "ORDER BY updated_at_ms DESC, session_id LIMIT ?",
            (owner, limit),
        ).fetchall()
        keys = ("session_id", "tree_key", "title", "state", "revision",
                "created_at_ms", "updated_at_ms")
        return [dict(zip(keys, row)) for row in rows]

    def append_turn(self, owner: str, session_id: str, *,
                    expected_revision: int, role: str, body: str,
                    provider: str = "", model: str = "",
                    now_ms: int) -> dict:
        owner = _key(owner)
        session_id = _key(session_id)
        now_ms = _time(now_ms)
        body = _text(body, MAX_BODY)
        if type(expected_revision) is not int or expected_revision < 0:
            raise JournalRefusal("INVALID_REVISION")
        if role not in ("user", "assistant") or type(role) is not str:
            raise JournalRefusal("INVALID_ROLE")
        if role == "assistant":
            provider, model = _key(provider), _key(model)
        elif provider or model:
            raise JournalRefusal("UNEXPECTED_MODEL_IDENTITY")
        with _write(self.db):
            session = self._owned(owner, session_id)
            if session["state"] != "OPEN":
                raise JournalRefusal("SESSION_NOT_OPEN")
            if session["revision"] != expected_revision:
                raise JournalRefusal("STALE_REVISION")
            ordinal = self.db.execute(
                "SELECT COALESCE(MAX(ordinal),0) FROM forest_turns "
                "WHERE session_id = ?", (session_id,)
            ).fetchone()[0] + 1
            if ordinal > MAX_MESSAGES_PER_SESSION:
                raise JournalRefusal("TURN_LIMIT")
            turn_id = "t_" + uuid.uuid4().hex
            self.db.execute(
                "INSERT INTO forest_turns "
                "(turn_id,session_id,ordinal,role,provider_key,model_key,"
                "body,recorded_at_ms) VALUES (?,?,?,?,?,?,?,?)",
                (turn_id, session_id, ordinal, role, provider, model, body, now_ms),
            )
            self.db.execute(
                "UPDATE forest_sessions SET revision = revision + 1, "
                "updated_at_ms = ? WHERE session_id = ?",
                (now_ms, session_id),
            )
        return {"turn_id": turn_id, "ordinal": ordinal,
                "revision": expected_revision + 1}

    def turns(self, owner: str, session_id: str, *,
              after: int = 0, limit: int = MAX_PAGE) -> list[dict]:
        self._owned(_key(owner), _key(session_id))
        if (type(after) is not int or after < 0
                or type(limit) is not int or not 1 <= limit <= MAX_PAGE):
            raise JournalRefusal("INVALID_PAGE")
        rows = self.db.execute(
            "SELECT turn_id,ordinal,role,provider_key,model_key,body,"
            "recorded_at_ms FROM forest_turns WHERE session_id = ? "
            "AND ordinal > ? ORDER BY ordinal ASC LIMIT ?",
            (session_id, after, limit),
        ).fetchall()
        keys = ("turn_id", "ordinal", "role", "provider", "model", "body",
                "recorded_at_ms")
        return [dict(zip(keys, row)) for row in rows]

    def set_state(self, owner: str, session_id: str, *,
                  expected_revision: int, next_state: str,
                  now_ms: int) -> dict:
        owner = _key(owner)
        session_id = _key(session_id)
        now_ms = _time(now_ms)
        if (type(expected_revision) is not int or expected_revision < 0
                or next_state not in ("OPEN", "PAUSED", "ARCHIVED")
                or type(next_state) is not str):
            raise JournalRefusal("INVALID_STATE")
        with _write(self.db):
            row = self._owned(owner, session_id)
            if row["revision"] != expected_revision:
                raise JournalRefusal("STALE_REVISION")
            if row["state"] == "ARCHIVED" or (
                row["state"] == "OPEN" and next_state == "OPEN"
            ) or (
                row["state"] == "PAUSED" and next_state == "PAUSED"
            ):
                raise JournalRefusal("INVALID_TRANSITION")
            self.db.execute(
                "UPDATE forest_sessions SET state = ?,revision = revision + 1,"
                "updated_at_ms = ? WHERE session_id = ?",
                (next_state, now_ms, session_id),
            )
        return self._owned(owner, session_id)
