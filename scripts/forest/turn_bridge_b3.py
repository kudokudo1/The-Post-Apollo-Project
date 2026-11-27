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
from dataclasses import dataclass

from ollama_chat_transport import (
    ChatRefusal, _messages, _model_name, _number, stream_chat,
    MIN_CONTEXT, MAX_CONTEXT, MAX_OUTPUT_TOKENS,
)
from ollama_inventory import InventoryFailure, _target
from context_first_tree_m2 import (
    ContextRefusal, SessionContextRef, snapshot_in_transaction,
    first_light_snapshot_in_transaction,
)
from capability_registry_b6r2 import SelectionPlan
from runtime_stop_control_r2 import RuntimeStopControl, StopArbitrationRefusal
from shared_context_b6r1 import ContractRefusal
from local_terminal_outbox_b4f import (
    append_terminal_in_writer_transaction, require_local_outbox,
    OutboxRefusal,
)
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
    outbox_expectation_b4g TEXT CHECK(
        outbox_expectation_b4g IS NULL OR
        outbox_expectation_b4g='OUTBOX_EXPECTED_V1'),
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

OUTBOX_EXPECTATION_B4G = "OUTBOX_EXPECTED_V1"  # Synthetic marker, NOT C5 evidence.


class BridgeRefusal(Exception):
    """Static failure reason; never include prompt, model output, or SQL text."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class SyntheticCommitBinding:
    """Persisted B3 context, not an authenticated security grant.

    Never construct a production authorizer from client-supplied values.
    In particular, a request ID is only a correlation identifier.
    """
    owner_key: str
    tree_key: str
    session_id: str
    user_turn_id: str
    attempt_id: str
    request_id: str
    model_key: str
    expected_revision: int


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
                 streamer: Callable = stream_chat,
                 synthetic_terminal_outbox: bool = False,
                 synthetic_outbox_expectation_b4g: bool = False,
                 first_light_prompt: str | None = None):
        if not isinstance(journal, ForestSessionJournal):
            raise BridgeRefusal("INVALID_JOURNAL")
        if (not callable(clock_ms) or not callable(streamer)
                or type(synthetic_terminal_outbox) is not bool
                or type(synthetic_outbox_expectation_b4g) is not bool):
            raise BridgeRefusal("INVALID_DEPENDENCY")
        if synthetic_outbox_expectation_b4g and not synthetic_terminal_outbox:
            raise BridgeRefusal("OUTBOX_EXPECTATION_REQUIRES_OUTBOX")
        # Owner-side immutable-by-convention input for the explicitly
        # selected disposable First Light bridge, not a caller grant.
        if first_light_prompt is not None:
            _messages([{"role": "user", "content": first_light_prompt}])
            if streamer is stream_chat:
                raise BridgeRefusal("FIRST_LIGHT_TEST_TRANSPORT_REQUIRED")
        self._first_light_prompt = first_light_prompt
        self._synthetic_terminal_outbox = synthetic_terminal_outbox
        self._synthetic_outbox_expectation_b4g = synthetic_outbox_expectation_b4g
        if synthetic_terminal_outbox:
            try:
                require_local_outbox(journal.db)
            except OutboxRefusal as exc:
                raise BridgeRefusal("LOCAL_OUTBOX_UNAVAILABLE") from exc
        if synthetic_outbox_expectation_b4g:
            try:
                cols = {c[1] for c in journal.db.execute(
                    "PRAGMA table_info(forest_attempts_b3)")}
            except sqlite3.Error as exc:
                raise BridgeRefusal("OUTBOX_EXPECTATION_SCHEMA_UNAVAILABLE") from exc
            if "outbox_expectation_b4g" not in cols:
                raise BridgeRefusal("OUTBOX_EXPECTATION_SCHEMA_MISSING")
        self.journal = journal
        self.db = journal.db
        self.clock_ms = clock_ms
        self.streamer = streamer
        if self.db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='forest_attempts_b3'"
        ).fetchone() is None:
            raise BridgeRefusal("ATTEMPT_SCHEMA_MISSING")

    def _preflight_context_attempt(self, owner, session_id, revision, now,
                                   context_ref, current_context_ref,
                                   capability_plan):
        """Reject known local conflicts before M2 reads any message body.

        Only the already scoped context-bound disposable path. Invalid or
        inconsistent references remain subject to M2's normal refusal
        ordering. This is not authentication or a separate reservation.
        Caller holds the same writer transaction as the final unique INSERT.
        """
        if (type(context_ref) is not SessionContextRef
                or type(current_context_ref) is not SessionContextRef
                or context_ref != current_context_ref
                or owner != context_ref.context.principal_key
                or session_id != context_ref.session_id
                or revision != context_ref.expected_revision
                or (capability_plan is not None and (
                    type(capability_plan) is not SelectionPlan
                    or capability_plan.context != context_ref.context))):
            return
        scope = self.db.execute(
            "SELECT state,revision,updated_at_ms FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND session_id=?",
            (owner, context_ref.context.tree_key, session_id),
        ).fetchone()
        if (scope is None or scope[0] != "OPEN" or scope[1] != revision
                or now < scope[2]):
            return
        latest = self.db.execute(
            "SELECT turn_id,ordinal,role FROM forest_turns "
            "WHERE session_id=? ORDER BY ordinal DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if (latest is None or latest[0] != context_ref.user_turn_id
                or latest[2] != "user" or type(latest[1]) is not int
                or not 1 <= latest[1] <= revision):
            return
        # Both existing constraints remain authoritative. No body or title
        # read here; no attempt state is returned to a client.
        conflict = self.db.execute(
            "SELECT 1 FROM forest_attempts_b3 WHERE session_id=? "
            "AND (user_turn_id=? OR status='RESERVED') LIMIT 1",
            (session_id, latest[0]),
        ).fetchone()
        if conflict is not None:
            raise BridgeRefusal("ATTEMPT_ALREADY_EXISTS")

    def _reserve(self, owner: str, session_id: str, revision: int,
                 model: str, *,
                 context_ref: SessionContextRef | None = None,
                 current_context_ref: SessionContextRef | None = None,
                 capability_plan: SelectionPlan | None = None,
                 ) -> tuple[str, list[dict[str, str]]]:
        if type(revision) is not int or revision < 0:
            raise BridgeRefusal("INVALID_REVISION")
        owner, session_id, model = _key(owner), _key(session_id), _model_name(model)
        now = _time(self.clock_ms())
        attempt_id = "a_" + uuid.uuid4().hex

        with _write(self.db):
            if context_ref is not None:
                self._preflight_context_attempt(
                    owner, session_id, revision, now, context_ref,
                    current_context_ref, capability_plan)
                # M2 validates exact owner/Tree/session/revision/latest user
                # and selects a bounded suffix in THIS reservation transaction.
                if self._first_light_prompt is not None:
                    if capability_plan is not None:
                        raise BridgeRefusal("FIRST_LIGHT_CAPABILITY_REFUSED")
                    snapshot = first_light_snapshot_in_transaction(
                        self.journal, context_ref, current=current_context_ref,
                        approved_prompt=self._first_light_prompt)
                else:
                    snapshot = snapshot_in_transaction(
                        self.journal, context_ref, current=current_context_ref,
                        capability_plan=capability_plan)
                updated = self.db.execute(
                    "SELECT updated_at_ms FROM forest_sessions WHERE "
                    "owner_key=? AND tree_key=? AND session_id=?",
                    (owner, context_ref.context.tree_key, session_id),
                ).fetchone()
                if updated is None or now < updated[0]:
                    raise BridgeRefusal("TIME_ROLLBACK")
                messages = snapshot.transport_messages()
                user_turn_id = snapshot.ref.user_turn_id
            else:
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
                # B4g: store the expectation in the SAME INSERT as the
                # original reservation. A missing marker never proves legacy.
                fields = ("attempt_id,session_id,user_turn_id,owner_key,"
                          "expected_revision,model_key,status,reply_turn_id,"
                          "created_at_ms,updated_at_ms")
                values = "?,?,?,?,?,?,'RESERVED',NULL,?,?"
                params = (attempt_id, session_id, user_turn_id, owner,
                          revision, model, now, now)
                if self._synthetic_outbox_expectation_b4g:
                    fields += ",outbox_expectation_b4g"
                    values += ",?"
                    params += (OUTBOX_EXPECTATION_B4G,)
                self.db.execute(
                    "INSERT INTO forest_attempts_b3 (" + fields +
                    ") VALUES (" + values + ")", params,
                )
            except sqlite3.IntegrityError as exc:
                raise BridgeRefusal("ATTEMPT_ALREADY_EXISTS") from exc

        return attempt_id, messages

    def _commit_binding(self, owner: str, session_id: str,
                        attempt_id: str, request_id: str,
                        model: str, revision: int) -> SyntheticCommitBinding:
        """Derive exact attempt, user turn and Tree from B3's durable rows."""
        row = self.db.execute(
            "SELECT a.user_turn_id,a.model_key,a.expected_revision,a.status,"
            "s.tree_key FROM forest_attempts_b3 AS a "
            "JOIN forest_sessions AS s ON s.session_id=a.session_id "
            "WHERE a.attempt_id=? AND a.session_id=? AND a.owner_key=? "
            "AND s.owner_key=?",
            (attempt_id, session_id, owner, owner),
        ).fetchone()
        if row is None or row[3] != "RESERVED":
            raise BridgeRefusal("FENCE_ATTEMPT_UNAVAILABLE")
        if row[1] != model or row[2] != revision:
            raise BridgeRefusal("FENCE_BINDING_MISMATCH")
        if type(request_id) is not str or not request_id or len(request_id) > 96:
            raise BridgeRefusal("INVALID_FENCE_REQUEST")
        return SyntheticCommitBinding(
            owner_key=owner, tree_key=row[4], session_id=session_id,
            user_turn_id=row[0], attempt_id=attempt_id, request_id=request_id,
            model_key=model, expected_revision=revision,
        )

    def _commit_fenced(self, binding: SyntheticCommitBinding,
                       response: str, pre_commit: Callable[[], bool],
                       fence_factory: Callable, *,
                       expected_tree: str | None = None) -> dict[str, object]:
        """B4c test seam: keep injected permit around real SQLite COMMIT.

        The injected permit is a synthetic fixture. A production host must
        independently verify and hold a C5-issued permit, including revocation
        ordering, through actual COMMIT and independently durable terminal ACK.
        """
        wrote_reply = False
        try:
            guard = fence_factory(binding)
            with guard as held:
                # Require an object bound to the exact durable B3 attempt.
                # This equality is a TEST constraint, not cryptographic proof.
                if (held is None or
                        getattr(held, "binding", None) != binding or
                        not callable(getattr(held, "terminal", None))):
                    raise BridgeRefusal("FENCE_BINDING_MISMATCH")
                result = self._commit(
                    binding.owner_key, binding.session_id, binding.attempt_id,
                    binding.expected_revision, binding.model_key, response,
                    pre_commit=pre_commit, expected_tree=expected_tree)
                wrote_reply = True
                # Happens after SQLite transaction has exited. An unavailable
                # terminal receipt must NOT advertise COMMITTED to the client.
                if held.terminal(result) is not True:
                    raise BridgeRefusal("UNKNOWN_HOLD")
            return result
        except BaseException as exc:
            # Even a post-COMMIT exception or lost receipt cannot cause replay.
            # Raising UNKNOWN_HOLD does NOT undo a previously committed reply.
            if wrote_reply:
                raise BridgeRefusal("UNKNOWN_HOLD") from exc
            if isinstance(exc, (BridgeRefusal, KeyboardInterrupt, GeneratorExit,
                                SystemExit)):
                raise
            raise BridgeRefusal("FENCE_UNAVAILABLE") from exc

    def _commit(self, owner: str, session_id: str, attempt_id: str,
                revision: int, model: str, response: str,
                pre_commit: Callable[[], bool] | None = None, *,
                expected_tree: str | None = None) -> dict[str, object]:
        # Never persist an unbounded output even if the model stream allows it.
        answer = _text(response, MAX_BODY)
        now = _time(self.clock_ms())
        with _write(self.db):
            if expected_tree is None:
                session = self.journal.session(owner, session_id)
                state, current_revision, updated = (
                    session["state"], session["revision"], session["updated_at_ms"])
            else:
                scoped = self.db.execute(
                    "SELECT state,revision,updated_at_ms FROM forest_sessions "
                    "WHERE owner_key=? AND tree_key=? AND session_id=?",
                    (owner, expected_tree, session_id),
                ).fetchone()
                if scoped is None:
                    raise BridgeRefusal("SESSION_SCOPE_MISMATCH")
                state, current_revision, updated = scoped
            if state != "OPEN" or current_revision != revision:
                raise BridgeRefusal("STALE_OR_CLOSED_SESSION")
            if now < updated:
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
            # B4b: host-owned authorization must be fresh immediately before
            # the durable INSERT, in the same SQLite transaction. A refusal
            # rolls back all writes; the outer exchange aborts the attempt.
            if pre_commit is not None:
                try:
                    approved = pre_commit()
                except Exception as exc:
                    raise BridgeRefusal("PRE_COMMIT_AUTHORIZATION_DENIED") from exc
                if approved is not True:
                    raise BridgeRefusal("PRE_COMMIT_AUTHORIZATION_DENIED")
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
            # B4f optional *synthetic* outbox: in the SAME transaction
            # as the assistant INSERT, revision and attempt COMMITTED.
            # A failed event INSERT rolls back all those writes.
            if self._synthetic_terminal_outbox:
                try:
                    append_terminal_in_writer_transaction(
                        self.db, attempt_id, "COMMITTED")
                except OutboxRefusal as exc:
                    raise BridgeRefusal("LOCAL_OUTBOX_INTEGRITY_HOLD") from exc
        return {"event": "COMMITTED", "revision": revision + 1,
                "turn_id": reply_turn_id, "ordinal": ordinal,
                "provider": "ollama", "model": model, "text": answer}

    def _abort(self, attempt_id: str) -> None:
        # A committed turn stays committed; no retry can reuse this user turn.
        with _write(self.db):
            if self._synthetic_terminal_outbox:
                now = _time(self.clock_ms())
                updated = self.db.execute(
                    "UPDATE forest_attempts_b3 "
                    "SET status='ABORTED',updated_at_ms=? "
                    "WHERE attempt_id=? AND status='RESERVED' "
                    "AND created_at_ms<=?",
                    (now, attempt_id, now),
                ).rowcount
                if updated == 1:
                    # This local ABORT is a positive durable transition,
                    # not proof that remote C5 acknowledged noncommit.
                    try:
                        append_terminal_in_writer_transaction(
                            self.db, attempt_id, "ABORTED")
                    except OutboxRefusal as exc:
                        raise BridgeRefusal("LOCAL_OUTBOX_INTEGRITY_HOLD") from exc
            else:
                self.db.execute(
                    "UPDATE forest_attempts_b3 SET status='ABORTED' "
                    "WHERE attempt_id=? AND status='RESERVED'",
                    (attempt_id,),
                )

    def exchange(self, *, owner: str, session_id: str,
                 expected_revision: int, model: str,
                 endpoint: str = "http://127.0.0.1:11434",
                 max_predict: int = 256, num_ctx: int = 4096,
                 pre_commit: Callable[[], bool] | None = None,
                 fence_factory: Callable | None = None,
                 fence_request_id: str | None = None,
                 context_ref: SessionContextRef | None = None,
                 current_context_ref: SessionContextRef | None = None,
                 resolve_current_context: Callable[[], SessionContextRef] | None = None,
                 capability_plan: SelectionPlan | None = None,
                 stop_control: RuntimeStopControl | None = None,
                 operation_id: str | None = None,
                 ) -> Iterator[dict[str, object]]:
        """Provisional DELTA events; COMMITTED only after atomic durable write.

        No automatic resend, even if the host loses the completion receipt.
        Explicitly closing this generator aborts the reserved attempt.
        """
        reserved = ""
        completed = False
        transport = None
        control_claimed = False
        bound_attempt = None
        expected_tree = None

        def check_current():
            if context_ref is not None:
                try:
                    current = resolve_current_context()
                except Exception as exc:
                    raise BridgeRefusal("CONTEXT_CURRENTNESS_UNAVAILABLE") from exc
                if type(current) is not SessionContextRef or current != context_ref:
                    raise BridgeRefusal("CONTEXT_CHANGED")
                return current
            return None

        def check_stop():
            if stop_control is not None and stop_control.transport_event.is_set():
                raise BridgeRefusal("OLLAMA_CANCELLED")

        try:
            if self._first_light_prompt is not None and context_ref is None:
                raise BridgeRefusal("CONTEXT_REQUIRED")
            if context_ref is not None or current_context_ref is not None:
                if (type(context_ref) is not SessionContextRef
                        or type(current_context_ref) is not SessionContextRef
                        or context_ref != current_context_ref
                        or owner != context_ref.context.principal_key
                        or session_id != context_ref.session_id
                        or expected_revision != context_ref.expected_revision
                        or not callable(resolve_current_context)):
                    raise BridgeRefusal("CONTEXT_BINDING_MISMATCH")
                expected_tree = context_ref.context.tree_key
            elif any(x is not None for x in (resolve_current_context,
                     capability_plan, stop_control, operation_id)):
                raise BridgeRefusal("CONTEXT_REQUIRED")
            if stop_control is not None or operation_id is not None:
                if (type(stop_control) is not RuntimeStopControl
                        or type(operation_id) is not str):
                    raise BridgeRefusal("INVALID_STOP_CONTROL")
                stop_control.claim_exchange(context_ref.context, operation_id)
                control_claimed = True
                check_stop()
            if pre_commit is not None and not callable(pre_commit):
                raise BridgeRefusal("INVALID_PRE_COMMIT_HOOK")
            if fence_factory is not None:
                if (not callable(fence_factory) or pre_commit is None
                        or type(fence_request_id) is not str
                        or not 16 <= len(fence_request_id) <= 96
                        or not all(ch.isascii() and
                                   (ch.isalnum() or ch in "_-")
                                   for ch in fence_request_id)):
                    raise BridgeRefusal("INVALID_FENCE_DEPENDENCY")
            elif fence_request_id is not None:
                raise BridgeRefusal("INVALID_FENCE_DEPENDENCY")
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
            current = check_current()
            check_stop()
            if context_ref is None:
                reserved, messages = self._reserve(
                    owner, session_id, expected_revision, model)
            else:
                reserved, messages = self._reserve(
                    owner, session_id, expected_revision, model,
                    context_ref=context_ref, current_context_ref=current,
                    capability_plan=capability_plan)
            if stop_control is not None:
                stop_control.bind_reserved_attempt(
                    context_ref.context, operation_id, reserved)
                bound_attempt = reserved
            yield {"event": "RESERVED", "attempt_id": reserved}
            check_current()
            check_stop()
            transport_options = {}
            if stop_control is not None:
                transport_options["cancel_event"] = stop_control.transport_event
            transport = iter(self.streamer(
                model=model, messages=messages, endpoint=endpoint,
                max_predict=max_predict, num_ctx=num_ctx, **transport_options,
            ))
            state = "INITIAL"
            parts: list[str] = []
            size = 0
            completed_text = None
            for item in transport:
                check_stop()
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
            check_current()
            check_stop()
            if stop_control is not None and not stop_control.try_enter_commit(
                    context_ref.context, operation_id, reserved):
                raise BridgeRefusal("OLLAMA_CANCELLED")
            if fence_factory is not None:
                binding = self._commit_binding(
                    _key(owner), _key(session_id), reserved,
                    fence_request_id, _model_name(model), expected_revision)
                receipt = self._commit_fenced(
                    binding, completed_text, pre_commit, fence_factory,
                    expected_tree=expected_tree)
            else:
                # Legacy B3/B4b remains synthetic and NOT production-authorized.
                receipt = self._commit(
                    _key(owner), _key(session_id), reserved,
                    expected_revision, _model_name(model), completed_text,
                    pre_commit=pre_commit, expected_tree=expected_tree)
            completed = True
            yield receipt
        except (ContextRefusal, StopArbitrationRefusal, ContractRefusal) as exc:
            # These existing fixture validators use fixed reason strings.
            raise BridgeRefusal(str(exc)) from exc
        except (BridgeRefusal, ChatRefusal, JournalRefusal) as exc:
            code = getattr(exc, "code", "INVALID_REQUEST")
            raise BridgeRefusal(code) from exc
        except (sqlite3.Error, UnicodeError, ValueError, TypeError) as exc:
            raise BridgeRefusal("BRIDGE_STORAGE_OR_STREAM_ERROR") from exc
        finally:
            try:
                if transport is not None and callable(getattr(transport, "close", None)):
                    transport.close()
            finally:
                try:
                    if reserved and not completed:
                        # Preserve the original durable no-retry reservation
                        # even when abort/outbox evidence cannot be written.
                        try:
                            self._abort(reserved)
                        except (sqlite3.Error, JournalRefusal, BridgeRefusal):
                            pass
                finally:
                    if control_claimed:
                        stop_control.close(context_ref.context, operation_id,
                                           bound_attempt)
