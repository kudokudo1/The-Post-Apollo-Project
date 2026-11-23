"""Forest B4f // SYNTHETIC ONLY transaction-coupled local terminal outbox.

The outbox is written in B3's own SQLite COMMIT/ABORT transaction. It is
NOT an independently custodied writer receipt, C5 permission or proof that a
restored/forged Forest database is genuine. Never use it to settle UNKNOWN.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from recovery_inspect_b4d import ForestLocalRecoveryInspector, RecoveryRefusal

SCHEMA = "post-apollo.forest.local-terminal.synthetic-b4f"
TABLE = "forest_local_terminal_events_b4f"
DDL = """
CREATE TABLE forest_local_terminal_events_b4f (
  event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL UNIQUE REFERENCES forest_attempts_b3(attempt_id),
  owner_key TEXT NOT NULL,
  session_id TEXT NOT NULL REFERENCES forest_sessions(session_id),
  user_turn_id TEXT NOT NULL REFERENCES forest_turns(turn_id),
  tree_key TEXT NOT NULL,
  model_key TEXT NOT NULL,
  expected_revision INTEGER NOT NULL CHECK(expected_revision >= 0),
  terminal_state TEXT NOT NULL
    CHECK(terminal_state IN ('COMMITTED','ABORTED')),
  reply_turn_id TEXT REFERENCES forest_turns(turn_id),
  recorded_at_ms INTEGER NOT NULL,
  CHECK(
    (terminal_state='COMMITTED' AND reply_turn_id IS NOT NULL)
    OR (terminal_state='ABORTED' AND reply_turn_id IS NULL)
  )
);
CREATE TRIGGER forest_b4f_deny_update
BEFORE UPDATE ON forest_local_terminal_events_b4f
BEGIN SELECT RAISE(ABORT, 'LOCAL_TERMINAL_IMMUTABLE'); END;
CREATE TRIGGER forest_b4f_deny_delete
BEFORE DELETE ON forest_local_terminal_events_b4f
BEGIN SELECT RAISE(ABORT, 'LOCAL_TERMINAL_IMMUTABLE'); END;
"""


class OutboxRefusal(Exception):
    """Fixed reason; never include SQL, source text, prompts or keys."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def bootstrap_local_terminal_outbox_synthetic(db: sqlite3.Connection) -> None:
    """Explicit disposable B1+B3 fixture only, never a live migration."""
    if not isinstance(db, sqlite3.Connection):
        raise OutboxRefusal("INVALID_STORAGE")
    if db.in_transaction:
        raise OutboxRefusal("ACTIVE_TRANSACTION")
    try:
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise OutboxRefusal("UNSUPPORTED_SCHEMA")
        if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise OutboxRefusal("FOREIGN_KEYS_REQUIRED")
        if db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='forest_attempts_b3'"
        ).fetchone() is None:
            raise OutboxRefusal("B3_SCHEMA_REQUIRED")
        if db.execute(
            "SELECT name FROM sqlite_master WHERE name=?", (TABLE,)
        ).fetchone() is not None:
            raise OutboxRefusal("LOCAL_OUTBOX_ALREADY_EXISTS")
        db.executescript("BEGIN IMMEDIATE;\n" + DDL + "\nCOMMIT;")
    except sqlite3.Error as exc:
        raise OutboxRefusal("LOCAL_OUTBOX_BOOTSTRAP_FAILED") from exc


def require_local_outbox(db: sqlite3.Connection) -> None:
    """Refuse enabled writer mode if fixture table is missing."""
    try:
        if db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE,),
        ).fetchone() is None:
            raise OutboxRefusal("LOCAL_OUTBOX_SCHEMA_MISSING")
        if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise OutboxRefusal("FOREIGN_KEYS_REQUIRED")
    except sqlite3.Error as exc:
        raise OutboxRefusal("LOCAL_OUTBOX_UNAVAILABLE") from exc


def append_terminal_in_writer_transaction(
    db: sqlite3.Connection, attempt_id: str, state: str
) -> None:
    """B3-internal call AFTER an actual COMMITTED/ABORTED status change.

    The function deliberately takes no owner/model/permit/response from wire.
    All event scope fields are selected from the original persisted attempt.
    It never commits or opens a connection on its own.
    """
    if not db.in_transaction or state not in ("COMMITTED", "ABORTED"):
        raise OutboxRefusal("INVALID_LOCAL_TERMINAL_WRITE")
    row = db.execute(
        "SELECT a.owner_key,a.session_id,a.user_turn_id,s.tree_key,"
        "a.model_key,a.expected_revision,a.status,a.reply_turn_id,"
        "a.created_at_ms,a.updated_at_ms,"
        "u.role,u.session_id,u.ordinal,u.recorded_at_ms,"
        "t.role,t.session_id,t.ordinal,t.model_key,t.provider_key,"
        "t.recorded_at_ms,s.revision "
        "FROM forest_attempts_b3 AS a "
        "JOIN forest_sessions AS s ON s.session_id=a.session_id "
        "LEFT JOIN forest_turns AS u ON u.turn_id=a.user_turn_id "
        "LEFT JOIN forest_turns AS t ON t.turn_id=a.reply_turn_id "
        "WHERE a.attempt_id=?", (attempt_id,),
    ).fetchone()
    if row is None:
        raise OutboxRefusal("LOCAL_TERMINAL_INTEGRITY_HOLD")
    (owner, session, user_turn, tree, model, revision, saved_state,
     reply_turn, created, updated, user_role, user_session, user_ordinal,
     user_time, reply_role, reply_session, reply_ordinal, reply_model,
     reply_provider, reply_time, session_revision) = row
    if (saved_state != state or not owner or not tree or not model
            or type(revision) is not int or revision < 0
            or type(user_ordinal) is not int or user_ordinal < 1
            or type(session_revision) is not int
            or session_revision < revision
            or type(created) is not int or type(updated) is not int
            or type(user_time) is not int
            or user_time > created or updated < created
            or user_role != "user" or user_session != session
            or revision < user_ordinal):
        raise OutboxRefusal("LOCAL_TERMINAL_INTEGRITY_HOLD")
    if state == "COMMITTED":
        if (not reply_turn or reply_role != "assistant"
                or reply_session != session
                or reply_ordinal != user_ordinal + 1
                or reply_model != model or reply_provider != "ollama"
                or type(reply_time) is not int or reply_time < created
                or session_revision < revision + 1):
            raise OutboxRefusal("LOCAL_TERMINAL_INTEGRITY_HOLD")
    elif reply_turn is not None:
        raise OutboxRefusal("LOCAL_TERMINAL_INTEGRITY_HOLD")

    db.execute(
        "INSERT INTO forest_local_terminal_events_b4f "
        "(event_id,attempt_id,owner_key,session_id,user_turn_id,tree_key,"
        "model_key,expected_revision,terminal_state,reply_turn_id,recorded_at_ms)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("e_" + uuid.uuid4().hex, attempt_id, owner, session, user_turn,
         tree, model, revision, state, reply_turn, updated),
    )


class ForestLocalTerminalOutboxInspector:
    """Read-only B4f local event view, called only AFTER host-side auth.

    Exact scope requires verified host owner + original attempt/session IDs.
    B4e verifies the local original user/reply lineage first. Neither module
    authenticates the issuer, protected writer or independent journal head.
    """

    def __init__(self, journal):
        self._base = ForestLocalRecoveryInspector(journal)
        self._db = journal.db
        require_local_outbox(self._db)

    def inspect(self, *, owner: str, session_id: str,
                attempt_id: str) -> dict[str, Any]:
        try:
            base = self._base.inspect(
                owner=owner, session_id=session_id, attempt_id=attempt_id)
        except RecoveryRefusal as exc:
            raise OutboxRefusal("LOCAL_ATTEMPT_UNAVAILABLE") from exc
        try:
            row = self._db.execute(
                "SELECT e.event_id,e.terminal_state,e.reply_turn_id,"
                "e.owner_key,e.session_id,e.user_turn_id,e.tree_key,"
                "e.model_key,e.expected_revision,e.recorded_at_ms,"
                "a.status,a.reply_turn_id,a.user_turn_id,a.model_key,"
                "a.expected_revision,a.updated_at_ms,s.tree_key "
                "FROM forest_local_terminal_events_b4f AS e "
                "JOIN forest_attempts_b3 AS a ON a.attempt_id=e.attempt_id "
                "JOIN forest_sessions AS s ON s.session_id=a.session_id "
                "WHERE e.attempt_id=? AND e.owner_key=? AND e.session_id=? "
                "AND a.owner_key=? AND a.session_id=? AND s.owner_key=?",
                (attempt_id, owner, session_id, owner, session_id, owner),
            ).fetchone()
        except sqlite3.Error as exc:
            raise OutboxRefusal("LOCAL_OUTBOX_UNAVAILABLE") from exc
        terminal = "LOCAL_EVENT_NOT_OBSERVED"
        event_id = None
        if row is not None:
            (event_id, state, reply_id, event_owner, event_session, event_user,
             event_tree, event_model, event_revision, event_time, saved_state,
             saved_reply, saved_user, saved_model, saved_revision, saved_time,
             saved_tree) = row
            if (event_owner != owner or event_session != session_id
                    or state != saved_state
                    or state not in ("COMMITTED", "ABORTED")
                    or base["forestWriteState"] != "FOREST_" + state
                    or reply_id != saved_reply or event_user != saved_user
                    or event_model != saved_model
                    or event_revision != saved_revision
                    or event_tree != saved_tree or event_time != saved_time):
                raise OutboxRefusal("LOCAL_EVENT_INTEGRITY_HOLD")
            terminal = "LOCAL_" + state
        return {
            "schema": SCHEMA,
            "attemptId": attempt_id,
            "sessionId": session_id,
            "forestWriteState": base["forestWriteState"],
            "localTerminalEvent": terminal,
            "localEventId": event_id,
            "c5Settlement": "UNKNOWN_HOLD",
            "terminalReceiptAuthenticated": False,
            "custodyAuthenticated": False,
            "safeToRetryInference": False,
            "safeToReleaseRevocation": False,
            "productionAuthority": False,
        }
