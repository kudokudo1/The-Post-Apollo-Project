"""R5: explicit disposable public conversation host, never an installed service.

Owns one newly created temporary B1/B3 journal, fixed prompts, fake model,
one explicit operation at a time, and the existing R4b ordered callback.
No paths, arbitrary prompts/models, protected records or network inputs.
The owner supplies synchronous UI2 callbacks and independent view observation.
"""
from __future__ import annotations

import inspect
import secrets
import sqlite3
import tempfile
import threading
from pathlib import Path
from contextlib import contextmanager

from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from turn_bridge_b3 import ForestTurnBridge, bootstrap_attempts_synthetic
from shared_context_b6r1 import TaskContext, BarkAttachment
from context_first_tree_m2 import SessionContextRef
from runtime_events_r3 import RuntimeExchange, OperationRef
from runtime_public_status_r4 import FixtureTreeBinding
from runtime_public_delivery_r4b import (
    PresentationCorrelation, FixtureDeliveryBinding, LocalFixtureDelivery,
    DeliveryResult,
)
from history_public_fixture_m4 import (
    PublicViewRef, HistoryPageRef, history_public_fixture_in_transaction,
)

_OWNER = "r5-public-fixture"
_TURNS = (
    ("What is a Tree?", "Public fixture: a Tree is a Forest agent identity."),
    ("What does its journal preserve?", "Public fixture: committed conversation turns."),
    ("Public STOP demonstration", "Uncommitted public demonstration fragment."),
)


class FixtureHostRefusal(ValueError):
    """Fixed owner-side failure; never a user-facing internal error."""


def _ref(correlation):
    return {"requestId": correlation.request_id, "viewKey": correlation.view_key,
            "generation": correlation.generation}


class PublicConversationHost:
    """One explicit owner-thread trial, no scheduler or UI authority.

    open_lifetime(ref) explicitly mounts the local correlation and returns
    True only when the existing consumer opens. current_view() independently
    observes the host's current eligible lifetime, returning an exact
    PresentationCorrelation or None. receive_unit(unit) calls the actual UI2
    void method synchronously; a refusal or failure must raise locally.
    invalidate_lifetime(ref) clears only the matching old lifetime.
    The owner must independently clear on detach even without a callback.
    """

    def __init__(self, *, open_lifetime, current_view, receive_unit, invalidate_lifetime):
        callbacks = (open_lifetime, current_view, receive_unit, invalidate_lifetime)
        if any(not callable(f) or inspect.iscoroutinefunction(f) for f in callbacks):
            raise FixtureHostRefusal("INVALID_OWNER_CALLBACK")
        self._open, self._view, self._receive, self._invalidate = callbacks
        self._thread = threading.get_ident()
        self._busy = False
        self._closed = False
        self._blocked = False
        self._clock = 1
        self._index = 0
        self._binding = None
        self._delivery = None
        self._runtime = None
        self._stream = None
        self._attempt = None
        self._terminal = False
        self._presentation_lost = True
        self._tmp = tempfile.TemporaryDirectory(prefix="forest-r5-public-")
        self._path = Path(self._tmp.name) / "conversation.sqlite"
        try:
            self._db = sqlite3.connect(self._path)
            bootstrap_synthetic(self._db)
            bootstrap_attempts_synthetic(self._db)
            self._journal = ForestSessionJournal(self._db)
            self._session = self._journal.create_session(
                _OWNER, "cherry", "Disposable public conversation",
                now_ms=self._tick())["session_id"]
        except BaseException:
            if hasattr(self, "_db"):
                self._db.close()
            self._tmp.cleanup()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @contextmanager
    def _action(self):
        if threading.get_ident() != self._thread or self._busy or self._closed:
            raise FixtureHostRefusal("OWNER_ACTION_UNAVAILABLE")
        self._busy = True
        try:
            yield
        finally:
            self._busy = False

    def _tick(self):
        self._clock += 1
        return self._clock

    def _current(self):
        if self._presentation_lost or self._binding is None:
            return None
        try:
            current = self._view()
            if inspect.iscoroutine(current):
                current.close()
                return None
            if type(current) is PresentationCorrelation and current == self._binding.correlation:
                return self._binding
        except Exception:
            pass
        return None

    def _clear(self, correlation):
        # Do not send withdrawal to a replacement view. A failure to clear
        # remains a local hold; no retry or acknowledgement is synthesized.
        self._presentation_lost = True
        try:
            returned = self._invalidate(_ref(correlation))
            if inspect.iscoroutine(returned):
                returned.close()
        except Exception:
            pass

    def _apply(self, method, *args):
        if self._delivery is None or self._presentation_lost:
            return
        result = getattr(self._delivery, method)(*args)
        if result is DeliveryResult.INVALIDATED:
            self._clear(self._delivery.correlation)

    def _callback(self, unit):
        original = self._current()
        if original is None:
            raise FixtureHostRefusal("VIEW_UNAVAILABLE")
        returned = self._receive(unit)
        if inspect.iscoroutine(returned):
            returned.close()
        # Even a successful void callback can have switched the view.
        if returned is not None or self._current() != original:
            raise FixtureHostRefusal("VIEW_CHANGED_DURING_CALLBACK")

    def _resolve_context(self):
        # Resolve from durable owner-scoped state, not from the captured UI.
        ctx = self._binding.operation.context_ref.context
        session = self._db.execute(
            "SELECT state,revision FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND session_id=?",
            (_OWNER, "cherry", self._session)).fetchone()
        latest = self._db.execute(
            "SELECT turn_id,role FROM forest_turns WHERE session_id=? "
            "ORDER BY ordinal DESC LIMIT 1", (self._session,)).fetchone()
        if session is None or session[0] != "OPEN" or latest is None or latest[1] != "user":
            raise FixtureHostRefusal("DURABLE_CONTEXT_UNAVAILABLE")
        return SessionContextRef(ctx, self._session, session[1], latest[0])

    def _fake_stream(self, index, **kwargs):
        # Test that actual M2 selection carries previous committed turns.
        expected = []
        for question, answer in _TURNS[:index]:
            expected.extend(({"role": "user", "content": question},
                             {"role": "assistant", "content": answer}))
        expected.append({"role": "user", "content": _TURNS[index][0]})
        if kwargs["messages"] != expected:
            raise FixtureHostRefusal("FIXTURE_CONTEXT_MISMATCH")
        answer = _TURNS[index][1]
        yield {"event": "STARTED", "provider": "ollama", "model": "fixture-model"}
        yield {"event": "DELTA", "text": answer}
        yield {"event": "COMPLETE", "provider": "ollama", "model": "fixture-model",
               "text": answer}

    def start_next(self):
        """Explicit new fixed fixture turn. Never replay an attempt."""
        with self._action():
            if self._blocked or self._stream is not None or self._index >= len(_TURNS):
                raise FixtureHostRefusal("TURN_UNAVAILABLE")
            if self._delivery is not None:
                self._apply("withdraw")
            self._presentation_lost = True
            index = self._index
            c = PresentationCorrelation.fresh(index + 1)
            try:
                opened = self._open(_ref(c))
                if inspect.iscoroutine(opened):
                    opened.close()
                observed = self._view()
                if inspect.iscoroutine(observed):
                    observed.close()
                if opened is not True or type(observed) is not PresentationCorrelation or observed != c:
                    raise FixtureHostRefusal("VIEW_OPEN_UNAVAILABLE")
                revision = self._journal.session(_OWNER, self._session)["revision"]
                row = self._journal.append_turn(_OWNER, self._session,
                    expected_revision=revision, role="user", body=_TURNS[index][0],
                    now_ms=self._tick())
                ctx = TaskContext(_OWNER, "cherry", None, "task-" + str(index + 1),
                    "exec-" + str(index + 1), index + 1, "INTERACTIVE")
                context = SessionContextRef(ctx, self._session, row["revision"], row["turn_id"])
                op = OperationRef(context, "r5-operation-" + secrets.token_hex(16))
                att = BarkAttachment(ctx, "fixture-bark", "fixture-requester",
                    "fixture-release", "fixture-seat", "fixture-recipient",
                    "CHERRY", c.generation)
                self._binding = FixtureDeliveryBinding(op, att,
                    FixtureTreeBinding("cherry", "CHERRY"), c)
                self._presentation_lost = False
                self._delivery = LocalFixtureDelivery(self._binding,
                    resolve_current=self._current, deliver=self._callback)
                bridge = ForestTurnBridge(self._journal, clock_ms=self._tick,
                    streamer=lambda **kw: self._fake_stream(index, **kw))
                self._runtime = RuntimeExchange(bridge, op,
                    resolve_current_context=self._resolve_context, model="fixture-model")
                self._stream = self._runtime.run()
                self._attempt = None
                self._terminal = False
                self._index += 1
                return _ref(c)
            except Exception:
                # A user turn might already be durable. No retry or new turn
                # on an uncertain setup outcome, even if the UI is closed.
                self._blocked = True
                self._clear(c)
                raise FixtureHostRefusal("TURN_SETUP_HOLD") from None

    def advance(self):
        """Advance one explicit fake transport event; never expose raw R3."""
        with self._action():
            if self._stream is None:
                raise FixtureHostRefusal("NO_ACTIVE_TURN")
            try:
                frame = next(self._stream)
                self._attempt = frame.attempt_id
                self._apply("observe", frame)
                if frame.payload.get("event") in ("COMMITTED", "UNKNOWN_HOLD"):
                    self._terminal = True
                    # R3 already exhausted B3 before yielding terminal receipt.
                    self._stream.close()
                    self._stream = None
                    self._apply("finish")
                    if frame.payload["event"] != "COMMITTED":
                        self._blocked = True
                    return "TERMINAL"
                return "ACTIVE"
            except Exception:
                self._blocked = True
                self._stream.close()
                self._stream = None
                self._apply("finish")
                return "UNKNOWN_HOLD"

    def stop(self, correlation):
        """Explicit owner STOP for exactly the currently bound operation."""
        with self._action():
            current = self._current()
            if (self._stream is None or current is None
                    or type(correlation) is not PresentationCorrelation
                    or correlation != current.correlation):
                raise FixtureHostRefusal("STOP_SCOPE_UNAVAILABLE")
            ack = self._runtime.request_stop(current.operation, self._attempt)
            self._apply("observe_stop_ack", ack, self._attempt)
            # No cancellation or resource-release receipt.
            return "STOP_OBSERVED"

    def observe_view(self):
        """Owner calls on lifecycle change independently of delivery."""
        with self._action():
            if self._binding is not None and self._current() is None:
                self._apply("withdraw")
                self._presentation_lost = True

    def reopen_journal(self):
        """Explicit idle fixture connection reopen; not process-crash recovery.

        Retain only this host-created path/session, never accept one from UI.
        Close the old presentation before closing SQLite; the next explicit
        turn owns a fresh task and view. No automatic replay or new bootstrap.
        """
        with self._action():
            if (self._blocked or self._stream is not None or not self._terminal
                    or self._binding is None or self._attempt is None):
                raise FixtureHostRefusal("REOPEN_UNAVAILABLE")
            old = self._binding
            attempt = self._attempt
            self._apply("withdraw")
            self._clear(old.correlation)
            self._binding = self._delivery = self._runtime = self._attempt = None
            self._terminal = False
            try:
                self._db.close()
                # mode=rw refuses a missing database instead of creating one.
                self._db = sqlite3.connect(self._path.as_uri() + "?mode=rw", uri=True)
                self._journal = ForestSessionJournal(self._db)
                session = self._db.execute(
                    "SELECT state,revision FROM forest_sessions "
                    "WHERE owner_key=? AND tree_key=? AND session_id=?",
                    (_OWNER, "cherry", self._session)).fetchone()
                terminal = self._db.execute(
                    "SELECT status,reply_turn_id FROM forest_attempts_b3 "
                    "WHERE owner_key=? AND session_id=? AND attempt_id=? "
                    "AND user_turn_id=? AND expected_revision=?",
                    (_OWNER, self._session, attempt, old.operation.context_ref.user_turn_id,
                     old.operation.context_ref.expected_revision)).fetchone()
                if (session != ("OPEN", old.operation.context_ref.expected_revision + 1)
                        or terminal is None or terminal[0] != "COMMITTED"
                        or type(terminal[1]) is not str):
                    raise FixtureHostRefusal("REOPEN_EVIDENCE_UNAVAILABLE")
                reply = self._db.execute(
                    "SELECT ordinal,role FROM forest_turns "
                    "WHERE session_id=? AND turn_id=?", (self._session, terminal[1])).fetchone()
                if reply != (session[1], "assistant"):
                    raise FixtureHostRefusal("REOPEN_EVIDENCE_UNAVAILABLE")
            except Exception:
                self._blocked = True
                raise FixtureHostRefusal("REOPEN_HOLD") from None
            return "JOURNAL_REOPENED"

    def history_page(self, *, after=0, limit=16, expected_revision=None,
                     expected_view=None):
        """Explicit M4 read; continuation pins the original revision/view.

        The fixture owner retains the first page revision and independently
        observed PresentationCorrelation. A continuation may not silently
        use the newest revision or a replacement attachment.
        """
        with self._action():
            current = self._current()
            if current is None:
                raise FixtureHostRefusal("HISTORY_VIEW_UNAVAILABLE")
            if type(after) is not int or after < 0:
                raise FixtureHostRefusal("HISTORY_CURSOR_UNAVAILABLE")
            pinned = expected_revision is not None or expected_view is not None
            if after > 0 or pinned:
                if (type(expected_revision) is not int or expected_revision < 0
                        or type(expected_view) is not PresentationCorrelation
                        or expected_view != current.correlation):
                    raise FixtureHostRefusal("HISTORY_CONTINUATION_UNAVAILABLE")
            self._db.execute("BEGIN")
            try:
                row = self._db.execute(
                    "SELECT state,revision FROM forest_sessions "
                    "WHERE owner_key=? AND tree_key=? AND session_id=?",
                    (_OWNER, "cherry", self._session)).fetchone()
                if row is None or row[0] != "OPEN":
                    raise FixtureHostRefusal("HISTORY_VIEW_UNAVAILABLE")
                revision = row[1]
                if pinned and revision != expected_revision:
                    raise FixtureHostRefusal("HISTORY_CONTINUATION_UNAVAILABLE")
                rid = secrets.token_hex(16)
                req = HistoryPageRef(PublicViewRef(current.attachment, rid),
                    self._session, revision, after, limit)
                observed = self._current()
                if observed != current:
                    raise FixtureHostRefusal("HISTORY_VIEW_UNAVAILABLE")
                independent = HistoryPageRef(PublicViewRef(observed.attachment, rid),
                    self._session, revision, after, limit)
                frame = history_public_fixture_in_transaction(self._journal, req,
                    current=independent)
            finally:
                self._db.rollback()
            if self._current() != current:
                raise FixtureHostRefusal("HISTORY_VIEW_UNAVAILABLE")
            return frame

    def close(self):
        if self._closed:
            return
        with self._action():
            try:
                if self._stream is not None:
                    self._stream.close()
                    self._stream = None
                if self._binding is not None:
                    self._apply("withdraw")
                    self._clear(self._binding.correlation)
            finally:
                self._closed = True
                self._db.close()
                self._tmp.cleanup()
