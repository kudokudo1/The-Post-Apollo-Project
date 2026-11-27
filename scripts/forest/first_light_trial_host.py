"""First Light FL3: single-use owner-side public trial host.

Development-only integration seam. No default transport, executable entry
point, installed host, native admission, UI sender or protected authority.
The explicit injected transport is for disposable verification only.
Never connect this candidate to a real provider or unqualified recipient.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid

from context_first_tree_m2 import SessionContextRef
from runtime_events_r3 import OperationRef, RuntimeExchange
from session_journal_v0 import ForestSessionJournal, MAX_BODY, bootstrap_synthetic
from shared_context_b6r1 import TaskContext
from turn_bridge_b3 import ForestTurnBridge, bootstrap_attempts_synthetic

# Candidate public trial values, NOT selected/qualified native settings.
PROMPT = "Reply with READY."
MODEL = "granite3.3:2b"
ENDPOINT = "http://127.0.0.1:11434"
NUM_CTX = 2048
MAX_PREDICT = 32
OWNER = "first-light-public"
TREE = "cherry"


class FirstLightRefusal(ValueError):
    """Fixed local reason, no input/output or provider diagnostics."""


class _OwnerStream:
    """Checked iterator, not a transferable Python generator.

    Keep the generator pinned in the original host until explicit owner
    closure/exhaustion. A foreign caller cannot resume or inject close.
    This is thread-lifetime hygiene, not process or security isolation.
    """

    def __init__(self, host, generator):
        self._host = host
        self._generator = generator
        self._closed = False
        self._busy = False

    def __iter__(self):
        return self

    def _check(self):
        if threading.current_thread() is not self._host._owner_thread or self._busy:
            raise FirstLightRefusal("OWNER_ACTION_UNAVAILABLE")

    def _retire(self):
        self._closed = True
        self._generator = None
        self._host._active_stream = None
        self._host._running = False
        if self._host._phase == "RUNNING":
            self._host._phase = "UNKNOWN_HOLD"

    def __next__(self):
        self._check()
        if self._closed:
            raise StopIteration
        self._busy = True
        try:
            return next(self._generator)
        except BaseException:
            # Generator has terminated; never allow another original run.
            self._retire()
            raise
        finally:
            self._busy = False

    def close(self):
        self._check()
        if self._closed:
            return
        self._busy = True
        try:
            self._generator.close()
        finally:
            # Also handles a never-started generator: its finally block
            # has not executed, but this original stream is still spent.
            self._retire()
            self._busy = False


class FirstLightTrialHost:
    """One fresh journal and one original operation per disposable host.

    Construct, submit, consume and close on the same owner worker thread.
    STOP is the existing independently resolved original R3 control and
    may be called by an owner-side control thread. No raw event may be
    forwarded to UI; actual current recipient/output admission is missing.
    In-memory storage is not crash-resistant original effect custody.
    """

    def __init__(self, *, test_transport):
        if not callable(test_transport):
            raise FirstLightRefusal("TRANSPORT_REQUIRED")
        self._owner_thread = threading.current_thread()
        self._transport = test_transport
        self._db = None
        self._runtime = None
        self._operation = None
        self._attempt = None
        self._phase = "IDLE"
        self._running = False
        self._active_stream = None
        self._closed = False
        self._local = "UNKNOWN_HOLD"
        self._committed_bytes = None
        self._clock = 0

    @property
    def phase(self):
        return self._phase

    def _owner(self):
        if threading.current_thread() is not self._owner_thread or self._closed:
            raise FirstLightRefusal("OWNER_ACTION_UNAVAILABLE")

    def _tick(self):
        self._clock += 1
        return self._clock

    def submit(self, prompt):
        """Prepare exactly the fixed public input; not dispatch or authority."""
        self._owner()
        if self._phase != "IDLE":
            raise FirstLightRefusal("TRIAL_ALREADY_USED")
        if type(prompt) is not str or prompt != PROMPT:
            raise FirstLightRefusal("PUBLIC_INPUT_MISMATCH")
        # No caller-supplied path, reopen, ATTACH or private store.
        self._phase = "UNKNOWN_HOLD"
        try:
            self._db = sqlite3.connect(":memory:")
            bootstrap_synthetic(self._db)
            bootstrap_attempts_synthetic(self._db)
            journal = ForestSessionJournal(self._db)
            session = journal.create_session(
                OWNER, TREE, "First Light public trial", now_ms=self._tick())
            turn = journal.append_turn(
                OWNER, session["session_id"], expected_revision=0,
                role="user", body=PROMPT, now_ms=self._tick())
            nonce = uuid.uuid4().hex
            context = TaskContext(OWNER, TREE, None, "task-" + nonce,
                                  "execution-" + nonce, 1, "INTERACTIVE")
            ref = SessionContextRef(context, session["session_id"],
                                    turn["revision"], turn["turn_id"])
            self._operation = OperationRef(ref, "first-light-" + nonce)
            self._resolve_context()
            bridge = ForestTurnBridge(journal, clock_ms=self._tick,
                                      streamer=self._exact_stream,
                                      first_light_prompt=PROMPT)
            self._runtime = RuntimeExchange(
                bridge, self._operation,
                resolve_current_context=self._resolve_context,
                model=MODEL, num_ctx=NUM_CTX, max_predict=MAX_PREDICT,
                endpoint=ENDPOINT)
        except Exception:
            raise FirstLightRefusal("TRIAL_SETUP_HOLD") from None
        self._phase = "PREPARED"
        return self._operation

    def _resolve_context(self):
        # Read only metadata; M2 still owns full context validation. Check
        # the whole tiny exclusive journal, not just a matching latest row.
        ref = self._operation.context_ref
        sessions = self._db.execute(
            "SELECT session_id,owner_key,tree_key,state,revision "
            "FROM forest_sessions LIMIT 2").fetchall()
        turns = self._db.execute(
            "SELECT turn_id,session_id,ordinal,role FROM forest_turns "
            "LIMIT 2").fetchall()
        if (sessions != [(ref.session_id, OWNER, TREE, "OPEN", 1)]
                or turns != [(ref.user_turn_id, ref.session_id, 1, "user")]
                or ref.expected_revision != 1):
            raise FirstLightRefusal("TRIAL_CONTEXT_CHANGED")
        return ref

    def _exact_stream(self, **options):
        # B3 now uses Mind's canonical exact-input helper inside the
        # reservation transaction. This separate check binds the actual
        # transport parameters to the original fixed public trial.
        if (set(options) != {"model", "messages", "endpoint", "num_ctx",
                             "max_predict", "cancel_event"}
                or options["model"] != MODEL or options["endpoint"] != ENDPOINT
                or options["num_ctx"] != NUM_CTX
                or options["max_predict"] != MAX_PREDICT
                or options["messages"] != [{"role": "user", "content": PROMPT}]
                or type(options["cancel_event"]) is not threading.Event):
            raise FirstLightRefusal("TRIAL_INPUT_CHANGED")
        self._resolve_context()
        yield from self._transport(**options)

    def run_internal(self):
        """One R3 stream for the owner worker ONLY; never a UI envelope."""
        self._owner()
        if self._phase != "PREPARED" or self._running:
            raise FirstLightRefusal("TRIAL_ALREADY_USED")
        self._running = True
        self._phase = "RUNNING"
        self._active_stream = _OwnerStream(self, self._run_frames())
        return self._active_stream

    def _run_frames(self):
        stream = self._runtime.run()
        try:
            for frame in stream:
                self._attempt = frame.attempt_id
                event = frame.payload["event"]
                if event == "COMMITTED":
                    body = frame.payload.get("text")
                    if type(body) is not str:
                        raise FirstLightRefusal("TERMINAL_BODY_INVALID")
                    encoded = body.encode("utf-8")
                    if not 0 < len(encoded) <= MAX_BODY:
                        raise FirstLightRefusal("TERMINAL_BODY_INVALID")
                    self._committed_bytes = encoded
                    self._phase = "LOCAL_COMMITTED"
                elif event == "UNKNOWN_HOLD":
                    self._phase = "UNKNOWN_HOLD"
                yield frame
        finally:
            stream.close()

    def request_stop(self, operation, attempt):
        """Owner resolves exact original references; no inferred terminal."""
        if self._closed or self._runtime is None:
            raise FirstLightRefusal("STOP_UNAVAILABLE")
        return self._runtime.request_stop(operation, attempt)

    def local_outcome(self):
        """Exact local journal evidence only; never provider settlement."""
        self._owner()
        if self._running:
            raise FirstLightRefusal("ORIGINAL_ACTIVE")
        if self._db is None or self._attempt is None:
            return "UNKNOWN_HOLD"
        ref = self._operation.context_ref
        row = self._db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 "
            "WHERE attempt_id=? AND session_id=? AND user_turn_id=? "
            "AND owner_key=? AND expected_revision=1 AND model_key=?",
            (self._attempt, ref.session_id, ref.user_turn_id, OWNER, MODEL),
        ).fetchone()
        session = self._db.execute(
            "SELECT session_id,owner_key,tree_key,state,revision "
            "FROM forest_sessions LIMIT 2").fetchall()
        turns = self._db.execute(
            "SELECT turn_id,session_id,ordinal,role,provider_key,model_key "
            "FROM forest_turns ORDER BY ordinal LIMIT 3").fetchall()
        user = (ref.user_turn_id, ref.session_id, 1, "user", "", "")
        if (row == ("ABORTED", None)
                and session == [(ref.session_id, OWNER, TREE, "OPEN", 1)]
                and turns == [user]):
            return "ABORTED_LOCAL"
        if (row is not None and row[0] == "COMMITTED" and row[1] is not None
                and session == [(ref.session_id, OWNER, TREE, "OPEN", 2)]
                and turns == [user, (row[1], ref.session_id, 2, "assistant",
                                     "ollama", MODEL)]):
            # Only after exact original metadata linkage and worker
            # retirement: independently compare bounded persisted bytes.
            # Do not return/read a body from a foreign or aborted row.
            expected = self._committed_bytes
            if expected is None:
                return "UNKNOWN_HOLD"
            body = self._db.execute(
                "SELECT CASE WHEN typeof(body)='text' "
                "AND length(CAST(body AS BLOB)) BETWEEN 1 AND ? "
                "THEN CAST(body AS BLOB) ELSE NULL END "
                "FROM forest_turns WHERE turn_id=? AND session_id=? "
                "AND ordinal=2 AND role='assistant' "
                "AND provider_key='ollama' AND model_key=?",
                (MAX_BODY, row[1], ref.session_id, MODEL),
            ).fetchone()
            if body == (expected,):
                return "COMMITTED_LOCAL"
        return "UNKNOWN_HOLD"

    def close(self):
        """Dispose offline journal; no claim of erasure or physical release."""
        self._owner()
        if self._running:
            raise FirstLightRefusal("ORIGINAL_ACTIVE")
        # Retain the original phase and local result in this owner object.
        # Unknown cannot be converted into a new dispatch by disposal.
        self._local = self.local_outcome()
        if self._db is not None:
            self._db.close()
            self._db = None
        self._committed_bytes = None
        self._closed = True
        return self._local
