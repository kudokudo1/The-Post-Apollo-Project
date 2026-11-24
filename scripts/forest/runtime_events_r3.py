"""R3: owner-side correlated B3 events for disposable fixture composition.

No UI sender, native listener, permission, database opener, task registry,
or admission service. Frames may carry private text in principle: NEVER
serialize or forward them to Bark. Host must own synthetic fixture scope.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping, Callable, Iterator

from shared_context_b6r1 import _key
from context_first_tree_m2 import SessionContextRef
from runtime_stop_control_r2 import RuntimeStopControl
from turn_bridge_b3 import ForestTurnBridge


class RuntimeEventRefusal(ValueError):
    """Fixed local failure reason."""


@dataclass(frozen=True, slots=True)
class OperationRef:
    context_ref: SessionContextRef
    operation_id: str

    def __post_init__(self):
        if type(self.context_ref) is not SessionContextRef:
            raise RuntimeEventRefusal("INVALID_CONTEXT")
        _key(self.operation_id, "OPERATION_ID")


@dataclass(frozen=True, slots=True)
class InternalEvent:
    operation: OperationRef
    attempt_id: str | None
    ordinal: int
    payload: Mapping[str, object]


class RuntimeExchange:
    """One operation, one B3 generator, one STOP control.

    Construct only in the owner-side disposable host. Model settings and
    current-context resolution are host inputs, not a UI request decoder.
    No execution or resource authority follows from constructing this object.
    """

    def __init__(self, bridge: ForestTurnBridge, operation: OperationRef, *,
                 resolve_current_context: Callable[[], SessionContextRef],
                 model: str, max_predict: int = 256, num_ctx: int = 4096,
                 endpoint: str = "http://127.0.0.1:11434"):
        if (type(bridge) is not ForestTurnBridge
                or type(operation) is not OperationRef
                or not callable(resolve_current_context)):
            raise RuntimeEventRefusal("INVALID_RUNTIME_DEPENDENCY")
        self._bridge = bridge
        self._operation = operation
        self._resolve = resolve_current_context
        self._settings = dict(model=model, max_predict=max_predict,
                              num_ctx=num_ctx, endpoint=endpoint)
        self._control = RuntimeStopControl(
            operation.context_ref.context, operation.operation_id)
        self._lock = threading.Lock()
        self._used = False
        self._closed = False

    def request_stop(self, operation: OperationRef, attempt_id: str | None):
        """Owner resolves operation and exact active attempt, not Bark.

        A stale pre-reservation reference racing reservation is refused.
        STOP acknowledgement does not prove cancellation or resource release.
        """
        if type(operation) is not OperationRef or operation != self._operation:
            raise RuntimeEventRefusal("OPERATION_MISMATCH")
        with self._lock:
            if self._closed:
                return "CONTROL_CLOSED"
            return self._control.request_stop(operation.context_ref.context,
                                              operation.operation_id,
                                              attempt_id)

    def run(self) -> Iterator[InternalEvent]:
        with self._lock:
            if self._used:
                raise RuntimeEventRefusal("OPERATION_ALREADY_USED")
            self._used = True

        attempt = None
        ordinal = 0
        stream = None
        receipt = None
        failed = False

        def frame(payload):
            nonlocal ordinal
            ordinal += 1
            return InternalEvent(self._operation, attempt, ordinal,
                                 MappingProxyType(dict(payload)))

        try:
            yield frame({"event": "REQUESTED"})
            ref = self._operation.context_ref
            try:
                current = self._resolve()
                stream = self._bridge.exchange(
                    owner=ref.context.principal_key, session_id=ref.session_id,
                    expected_revision=ref.expected_revision, context_ref=ref,
                    current_context_ref=current,
                    resolve_current_context=self._resolve,
                    operation_id=self._operation.operation_id,
                    stop_control=self._control, **self._settings)
                for event in stream:
                    if event["event"] == "RESERVED":
                        attempt = event["attempt_id"]
                    if event["event"] == "COMMITTED":
                        # Do not advertise success before B3 exhausts/cleans up.
                        receipt = dict(event)
                    else:
                        yield frame(event)
            except Exception:
                # Even a failure before RESERVED is observed is not proof
                # of no durable effect. No raw exception or auto-replay.
                failed = True
            finally:
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        failed = True
                with self._lock:
                    self._closed = True
            if failed or receipt is None or attempt is None:
                yield frame({"event": "UNKNOWN_HOLD"})
            else:
                yield frame(receipt)
        finally:
            with self._lock:
                self._closed = True
