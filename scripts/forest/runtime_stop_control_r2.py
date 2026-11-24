"""DOC 2F R2 // In-process STOP/commit-entry arbitration, fixture only.

No journal access, model execution, task registry, permission or egress.
One instance belongs to one host-resolved original operation. It is not
a wire decoder, authenticated identity, resource reservation or receipt.
"""
from __future__ import annotations

import threading
from shared_context_b6r1 import TaskContext, _key


class StopArbitrationRefusal(ValueError):
    """Fixed local reason; no task identifiers in error text."""


class RuntimeStopControl:
    """One-shot local control; caller owns the actual B3 transaction.

    A STOP that wins the lock before commit entry sets the transport event.
    After entry, STOP cannot promise rollback. Actual terminal evidence
    must be reconciled by the existing journal/fence owner.
    """

    def __init__(self, context: TaskContext, operation_id: str):
        if type(context) is not TaskContext:
            raise StopArbitrationRefusal("INVALID_CONTEXT")
        _key(operation_id, "OPERATION_ID")
        self._context = context
        self._operation_id = operation_id
        self._attempt_id = None
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._entered = False
        self._closed = False

    @property
    def transport_event(self) -> threading.Event:
        """For B2 consumption only. Host must never set/clear it directly."""
        return self._event

    def _match(self, context, operation_id, attempt_id):
        if (type(context) is not TaskContext or context != self._context
                or type(operation_id) is not str
                or operation_id != self._operation_id
                or (attempt_id is not None and type(attempt_id) is not str)
                or attempt_id != self._attempt_id):
            raise StopArbitrationRefusal("OPERATION_MISMATCH")

    def bind_reserved_attempt(self, context, operation_id, attempt_id):
        """Only the worker calls this after actual B3 durable reservation.

        A STOP before reservation completion remains latched. Binding is
        allowed so the worker can reconcile that exact reserved attempt.
        """
        _key(attempt_id, "ATTEMPT_ID")
        with self._lock:
            self._match(context, operation_id, None)
            if self._closed or self._entered:
                raise StopArbitrationRefusal("CONTROL_CLOSED")
            self._attempt_id = attempt_id

    def request_stop(self, context, operation_id, attempt_id):
        """Owner-resolved exact request, NOT authorization or terminal ACK."""
        with self._lock:
            self._match(context, operation_id, attempt_id)
            if self._closed:
                return "CONTROL_CLOSED"
            if self._entered:
                return "COMMIT_ENTRY_ALREADY_WON"
            self._event.set()
            return "STOP_LATCHED"

    def try_enter_commit(self, context, operation_id, attempt_id):
        """One-time local arbitration ONLY, not permission to write.

        Caller must retain all existing precommit/fence checks. No lock is
        held during DB or C5 calls. A winning entry does not imply COMMITTED.
        """
        with self._lock:
            self._match(context, operation_id, attempt_id)
            if self._attempt_id is None:
                raise StopArbitrationRefusal("ATTEMPT_REQUIRED")
            if self._closed or self._entered or self._event.is_set():
                return False
            self._entered = True
            return True

    def close(self, context, operation_id, attempt_id):
        """Worker lifecycle closure only, never an outcome or receipt."""
        with self._lock:
            self._match(context, operation_id, attempt_id)
            self._closed = True
