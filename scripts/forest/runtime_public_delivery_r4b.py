"""R4b owner-side ordered disposable callback candidate.

No UI consumer, network sender, queue, storage, publicness classifier or
protected authorization. Host resolves original and current public fixture
provenance independently; never construct a binding from Bark input.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import secrets
import threading

from runtime_events_r3 import OperationRef
from runtime_public_status_r4 import (
    FixtureTreeBinding, Observation, PublicRuntimeStatus, SCHEMA,
)
from shared_context_b6r1 import BarkAttachment, _generation

_TOKEN = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_STATUSES = frozenset(("IDLE", "REQUEST_PENDING", "PREPARING", "GENERATING",
    "STOP_REQUESTED", "LOCAL_COMMIT_RECORDED", "UNKNOWN_HOLD"))
_TERMINAL = frozenset(("LOCAL_COMMIT_RECORDED", "UNKNOWN_HOLD"))
_FLAGS = ("sourceAuthenticated", "permissionGranted", "productionAuthority",
          "modelExecutionPermitted")
_FIELDS = frozenset(("schema", "status", "safeActions", *_FLAGS))


class DeliveryResult(Enum):
    # Local owner results, never presentation units or delivery receipts.
    CALLBACK_RETURNED = 1
    NO_UPDATE = 2
    INVALIDATED = 3
    CLOSED = 4


@dataclass(frozen=True, slots=True)
class PresentationCorrelation:
    """Separate host-issued local lifetime; no private identity or authority."""
    request_id: str
    view_key: str
    generation: int

    def __post_init__(self):
        _generation(self.generation)
        if (type(self.request_id) is not str or
                _TOKEN.fullmatch(self.request_id) is None or
                type(self.view_key) is not str or
                _TOKEN.fullmatch(self.view_key) is None or
                self.request_id == self.view_key):
            raise ValueError("INVALID_LOCAL_CORRELATION")

    @classmethod
    def fresh(cls, generation):
        # The host owns one new lifetime and must never reuse it.
        return cls(secrets.token_hex(16), secrets.token_hex(16), generation)


@dataclass(frozen=True, slots=True)
class FixtureDeliveryBinding:
    operation: OperationRef
    attachment: BarkAttachment
    tree_binding: FixtureTreeBinding
    correlation: PresentationCorrelation

    def __post_init__(self):
        if (type(self.operation) is not OperationRef or
                type(self.attachment) is not BarkAttachment or
                not self.attachment.attached or
                type(self.tree_binding) is not FixtureTreeBinding or
                not self.tree_binding.matches(self.operation, self.attachment) or
                type(self.correlation) is not PresentationCorrelation or
                self.correlation.generation != self.attachment.view_generation):
            raise ValueError("INVALID_DELIVERY_BINDING")


def _status_packet(packet):
    """Build fresh allowlisted fields; never serialize an internal event."""
    if (type(packet) is not dict or set(packet) != _FIELDS or
            type(packet["schema"]) is not str or packet["schema"] != SCHEMA or
            type(packet["status"]) is not str or packet["status"] not in _STATUSES or
            any(packet[k] is not False for k in _FLAGS) or
            type(packet["safeActions"]) is not list or packet["safeActions"]):
        raise ValueError("INVALID_STATUS_PACKET")
    return {"schema": SCHEMA, "status": packet["status"],
            **{k: False for k in _FLAGS}, "safeActions": []}


class LocalFixtureDelivery:
    """Single lifetime, synchronous owner-thread callback, no queue.

    resolve_current() returns a freshly owner-resolved FixtureDeliveryBinding
    only while isolated public fixture provenance is established; otherwise
    None. Equality is not authentication. Both callbacks must be synchronous
    and owned by that same host, never supplied by the UI.

    INVALIDATED requires the owner to close/clear only this correlation via
    its independently observed local lifetime state, even if the callback
    threw after painting. Never retry a callback or clear a newer view.
    """

    def __init__(self, original, *, resolve_current, deliver):
        if (type(original) is not FixtureDeliveryBinding or
                not callable(resolve_current) or not callable(deliver)):
            raise ValueError("INVALID_DELIVERY_DEPENDENCY")
        self._original = original
        self._resolve = resolve_current
        self._deliver = deliver
        self._projection = PublicRuntimeStatus(
            original.operation, original.attachment, tree_binding=original.tree_binding)
        self._thread = threading.get_ident()
        self._sequence = 0
        self._closed = False
        self._busy = False
        self._terminal = False

    @property
    def correlation(self):
        """Local owner correlation only, not execution or recipient identity."""
        return self._original.correlation

    def _invalidate(self):
        self._closed = True
        self._projection.withdraw()
        return DeliveryResult.INVALIDATED

    def _current(self):
        current = self._resolve()
        if type(current) is not FixtureDeliveryBinding or current != self._original:
            return None
        return current

    def _run(self, method, *args):
        if threading.get_ident() != self._thread:
            raise ValueError("WRONG_OWNER_THREAD")
        if self._busy:
            return self._invalidate()
        if self._closed:
            return DeliveryResult.CLOSED
        self._busy = True
        try:
            current = self._current()
            if current is None or self._closed:
                return self._invalidate()
            if method == "withdraw":
                packet = None
                kind = "WITHDRAW"
            else:
                if self._terminal and method == "observe":
                    # A late event cannot replace an already displayed terminal
                    # result. Invalidate the lifetime instead of replaying it.
                    return self._invalidate()
                value = getattr(self._projection, method)(
                    *args, current_operation=current.operation,
                    current_attachment=current.attachment,
                    current_tree_binding=current.tree_binding)
                if value is Observation.NO_UPDATE:
                    return DeliveryResult.NO_UPDATE
                if value is None:
                    return self._invalidate()
                packet = _status_packet(value)
                kind = "STATUS"
            # Last owner-side sample immediately before synchronous dispatch.
            # No atomic protected fence or asynchronous queue is claimed.
            if self._current() is None or self._closed:
                return self._invalidate()
            corr = self.correlation
            self._sequence += 1
            unit = {"requestId": corr.request_id, "viewKey": corr.view_key,
                    "generation": corr.generation, "sequence": self._sequence,
                    "kind": kind, "statusPacket": packet}
            # Record terminal/withdrawal before callback. A failing callback
            # cannot re-enter or cause an automatic retransmission.
            if kind == "WITHDRAW":
                self._closed = True
                self._projection.withdraw()
            elif packet["status"] in _TERMINAL:
                self._terminal = True
            self._deliver(unit)
            if self._closed and kind != "WITHDRAW":
                return DeliveryResult.INVALIDATED
            return DeliveryResult.CALLBACK_RETURNED
        except Exception:
            # Do not expose exception text or attempt any retry.
            return self._invalidate()
        finally:
            self._busy = False

    def observe(self, event):
        return self._run("observe", event)

    def observe_stop_ack(self, disposition, attempt_id):
        return self._run("observe_stop_ack", disposition, attempt_id)

    def finish(self):
        return self._run("finish")

    def withdraw(self):
        # Only explicit withdrawal of a still-current local lifetime sends.
        # Lost currentness instead invalidates locally; never retarget.
        return self._run("withdraw")
