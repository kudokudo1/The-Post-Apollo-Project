"""Forest B3 // SYNTHETIC ONLY durable Ollama turn coordination.

No UI, server, identity issuer, filesystem opener, session bootstrap or live
activation. The trusted future host must authenticate the owner, choose and
protect its SQLite connection, and authorize model execution separately.

An existing *committed user turn* is required. A durable reservation is
created BEFORE any model inference. A model reply is inserted atomically
with the reservation's completion ONLY after a valid, exhausted B2 stream.
Failures/cancellation leave an ABORTED reservation that cannot auto-retry.
"""
from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing

from ollama_chat_transport import (
    ChatRefusal, _messages, _model_name, _number, stream_chat,
    MIN_CONTEXT, MAX_CONTEXT, MAX_OUTPUT_TOKENS,
)
from ollama_inventory import InventoryFailure, _target
from session_journal_v0 import (
    ForestSessionJournal, JournalRefusal, MAX_BODY, MAX_MESSAGES_PER_SESSION,
    _key, _text, _time, _write,
)

ATTEMPT_SCHEMA = """
CREATE TABLE forest_attempts_b3 (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES forest_sessions(session_id),
    user_turn_id TEXT NOT NULL REFERENCES forest_turns(turn_id),
    owner_key TEXT NOT NULL,
    expected_revision INTEGER NOT NULL,
    model_key TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK(status IN ('RESERVED','COMMITTED','ABORTED')),
    reply_turn_id TEXT REFERENCES forest_turns(turn_id),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    UNIQUE(session_id, user_turn_id)
);
CREATE UNIQUE INDEX forest_attempts_b3_one_live
ON forest_attempts_b3(session_id) WHERE status = 'RESERVED';
"""


class BridgeRefusal(Exception):
    """Static failure reason; never include prompt, model output, or SQL text."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def bootstrap_attempts_synthetic(db: sqlite3.Connection) -> None:
    """Only for an explicit disposable B1 fixture; no live migrations."""
    if db.in_transaction:
        raise BridgeRefusal("ACTIVE_TRANSACTION")
    if db.execute("PRAGMA user_version").fetchone()[0] != 1:
        raise BridgeRefusal("UNSUPPORTED_SCHEMA")
    existing = db.execute(
        "SELECT name FROM sqlite_master WHERE name='forest_attempts_b3'"
    ).fetchone()
    if existing is not None:
        raise BridgeRefusal("ATTEMPT_SCHEMA_EXISTS")
    # B1 deliberately permits no implicit schema bootstrap.
    db.executescript("BEGIN IMMEDIATE;\n" + ATTEMPT_SCHEMA + "\nCOMMIT;")


class ForestTurnBridge:
    """An injectable test seam, not a protected multi-user service."""

    def __init__(self, journal: ForestSessionJournal, *,
                 clock_ms: Callable[[], int],
                 streamer: Callable = stream_chat):
        if not isinstance(journal, ForestSessionJournal):
            raise BridgeRefusal("INVALID_JOURNAL")
        if not callable(clock_ms) or not callable(streamer):
            raise BridgeRefusal("INVALID_DEPENDENCY")
        self.journal = journal
        self.db = journal.db
        self.clock_ms = clock_ms
        self.streamer = streamer
        if self.db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='forest_attempts_b3'"
        ).fetchone() is None:
            raise BridgeRefusal("ATTEMPT_SCHEMA_MISSING")

    def _reserve(self, owner: str, session_id: str, revision: int,
                 model: str) -> tuple[str, list[dict[str, str]]]:
        if type(revision) is not int or revision < 0:
            raise BridgeRefusal("INVALID_REVISION")
        owner, session_id, model = _key(owner), _key(session_id), _model_name(model)
        now = _time(self.clock_ms())
        attempt_id = "a_" + uuid.uuid4().hex

        with _write(self.db):
            current = self.journal.session(owner, session_id)
            if current["state"] != "OPEN":
                raise BridgeRefusal("SESSION_NOT_OPEN")
            if current["revision"] != revision:
                raise BridgeRefusal("STALE_REVISION")
            if now < current["updated_at_ms"]:
                raise BridgeRefusal("TIME_ROLLBACK")

            rows = self.db.execute(
                "SELECT turn_id,role,body FROM forest_turns "
                "WHERE session_id=? ORDER BY ordinal DESC LIMIT 16",
                (session_id,),
            ).fetchall()
            if not rows or rows[0][1] != "user":
                raise BridgeRefusal("USER_TURN_REQUIRED")
            messages = [
                {"role": role, "content": body}
                for _, role, body in reversed(rows)
            ]
            # Reuse B2's exact prompt constraints before making reservation.
            _messages(messages)
            user_turn_id = rows[0][0]
            try:
                self.db.execute(
                    "INSERT INTO forest_attempts_b3 "
                    "(attempt_id,session_id,user_turn_id,owner_key,"
                    "expected_revision,model_key,status,reply_turn_id,"
                    "created_at_ms,updated_at_ms) "
                    "VALUES (?,?,?,?,?,?,'RESERVED',NULL,?,?)",
                    (attempt_id, session_id, user_turn_id, owner,
                     revision, model, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise BridgeRefusal("ATTEMPT_ALREADY_EXISTS") from exc

        return attempt_id, messages

    def _commit(self, owner: str, session_id: str, attempt_id: str,
                revision: int, model: str, response: str) -> dict[str, object]:
        # Never persist an unbounded output even if the model stream allows it.
        answer = _text(response, MAX_BODY)
        now = _time(self.clock_ms())
        with _write(self.db):
            session = self.journal.session(owner, session_id)
            if (session["state"] != "OPEN" or session["revision"] != revision):
                raise BridgeRefusal("STALE_OR_CLOSED_SESSION")
            if now < session["updated_at_ms"]:
                raise BridgeRefusal("TIME_ROLLBACK")

            attempt = self.db.execute(
                "SELECT user_turn_id,model_key,status,created_at_ms "
                "FROM forest_attempts_b3 "
                "WHERE attempt_id=? AND session_id=? AND owner_key=?",
                (attempt_id, session_id, owner),
            ).fetchone()
            if (attempt is None or attempt[1] != model
                    or attempt[2] != "RESERVED"):
                raise BridgeRefusal("ATTEMPT_NOT_RESERVED")
            if now < attempt[3]:
                raise BridgeRefusal("TIME_ROLLBACK")
            last = self.db.execute(
                "SELECT turn_id,role,ordinal FROM forest_turns "
                "WHERE session_id=? ORDER BY ordinal DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if last is None or last[0] != attempt[0] or last[1] != "user":
                raise BridgeRefusal("USER_TURN_CHANGED")
            ordinal = last[2] + 1
            if ordinal > MAX_MESSAGES_PER_SESSION:
                raise BridgeRefusal("TURN_LIMIT")
            reply_turn_id = "t_" + uuid.uuid4().hex
            self.db.execute(
                "INSERT INTO forest_turns "
                "(turn_id,session_id,ordinal,role,provider_key,model_key,"
                "body,recorded_at_ms) VALUES (?,?,?,'assistant','ollama',?,?,?)",
                (reply_turn_id, session_id, ordinal, model, answer, now),
            )
            self.db.execute(
                "UPDATE forest_sessions SET revision=revision+1, "
                "updated_at_ms=? WHERE session_id=?",
                (now, session_id),
            )
            updated = self.db.execute(
                "UPDATE forest_attempts_b3 "
                "SET status='COMMITTED',reply_turn_id=?,updated_at_ms=? "
                "WHERE attempt_id=? AND status='RESERVED'",
                (reply_turn_id, now, attempt_id),
            ).rowcount
            if updated != 1:
                raise BridgeRefusal("ATTEMPT_NOT_RESERVED")
        return {"event": "COMMITTED", "revision": revision + 1,
                "turn_id": reply_turn_id, "ordinal": ordinal,
                "provider": "ollama", "model": model, "text": answer}

    def _abort(self, attempt_id: str) -> None:
        # A committed turn stays committed; no retry can reuse this user turn.
        with _write(self.db):
            self.db.execute(
                "UPDATE forest_attempts_b3 SET status='ABORTED' "
                "WHERE attempt_id=? AND status='RESERVED'",
                (attempt_id,),
            )

    def exchange(self, *, owner: str, session_id: str,
                 expected_revision: int, model: str,
                 endpoint: str = "http://127.0.0.1:11434",
                 max_predict: int = 256, num_ctx: int = 4096
                 ) -> Iterator[dict[str, object]]:
        """Provisional DELTA events; COMMITTED only after atomic durable write.

        No automatic resend, even if the host loses the completion receipt.
        Explicitly closing this generator aborts the reserved attempt.
        """
        reserved = ""
        completed = False
        transport = None
        try:
            # Validate network and resource policy BEFORE reserving a turn.
            # A malformed request must not consume its one-time attempt.
            _number(max_predict, lower=1, upper=MAX_OUTPUT_TOKENS,
                    code="INVALID_PREDICT_LIMIT")
            _number(num_ctx, lower=MIN_CONTEXT, upper=MAX_CONTEXT,
                    code="INVALID_CONTEXT")
            try:
                _target(endpoint)
            except InventoryFailure as exc:
                raise BridgeRefusal(exc.reason) from exc
            reserved, messages = self._reserve(
                owner, session_id, expected_revision, model)
            yield {"event": "RESERVED", "attempt_id": reserved}
            transport = iter(self.streamer(
                model=model, messages=messages, endpoint=endpoint,
                max_predict=max_predict, num_ctx=num_ctx,
            ))
            state = "INITIAL"
            parts: list[str] = []
            size = 0
            completed_text = None
            for item in transport:
                if type(item) is not dict:
                    raise BridgeRefusal("INVALID_STREAM_EVENT")
                event = item.get("event")
                if event == "STARTED":
                    if (state != "INITIAL" or set(item) !=
                            {"event", "model", "provider"}
                            or item["provider"] != "ollama"
                            or item["model"] != model):
                        raise BridgeRefusal("INVALID_STREAM_EVENT")
                    state = "STREAMING"
                    yield {"event": "STARTED", "provider": "ollama", "model": model}
                elif event == "DELTA":
                    if state != "STREAMING" or set(item) != {"event", "text"}:
                        raise BridgeRefusal("INVALID_STREAM_EVENT")
                    chunk = item["text"]
                    if type(chunk) is not str or not chunk:
                        raise BridgeRefusal("INVALID_STREAM_EVENT")
                    size += len(chunk.encode("utf-8"))
                    if size > MAX_BODY:
                        raise BridgeRefusal("ANSWER_TOO_LARGE")
                    parts.append(chunk)
                    yield {"event": "DELTA", "text": chunk,
                           "provisional": True}
                elif event == "COMPLETE":
                    if (state != "STREAMING" or set(item) !=
                            {"event", "provider", "model", "text"}
                            or item["provider"] != "ollama"
                            or item["model"] != model or not parts
                            or type(item["text"]) is not str
                            or item["text"] != "".join(parts)):
                        raise BridgeRefusal("INVALID_STREAM_COMPLETION")
                    completed_text = item["text"]
                    state = "TERMINAL"
                else:
                    raise BridgeRefusal("INVALID_STREAM_EVENT")
            # No output can follow COMPLETE. Response must end cleanly.
            if state != "TERMINAL" or completed_text is None:
                raise BridgeRefusal("INCOMPLETE_STREAM")
            receipt = self._commit(
                _key(owner), _key(session_id), reserved,
                expected_revision, _model_name(model), completed_text)
            completed = True
            yield receipt
        except (BridgeRefusal, ChatRefusal, JournalRefusal) as exc:
            code = getattr(exc, "code", "INVALID_REQUEST")
            raise BridgeRefusal(code) from exc
        except (sqlite3.Error, UnicodeError, ValueError, TypeError) as exc:
            raise BridgeRefusal("BRIDGE_STORAGE_OR_STREAM_ERROR") from exc
        finally:
            if transport is not None and callable(getattr(transport, "close", None)):
                transport.close()
            if reserved and not completed:
                # Leave a durable no-auto-retry record. If storage is lost here
                # the original RESERVED row also blocks automatic replay.
                try:
                    self._abort(reserved)
                except (sqlite3.Error, JournalRefusal):
                    pass
