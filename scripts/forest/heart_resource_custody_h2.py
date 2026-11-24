"""H2: local, disposable single-slot resource custody accounting.

Not an Ollama admission gate, physical reservation, durable recovery,
trusted terminal verifier or permission mechanism. One instance per
disposable host, never recreate it to clear an ambiguous active attempt.
"""
from dataclasses import dataclass
import threading

from heart_dispatch_reference_h1 import (
    DispatchSnapshot, DispatchRefusal, compare_dispatch, _key, _time,
)
from shared_context_b6r1 import TaskContext
from resource_governor_p1 import ResourceAvailability

MAX_OPERATIONS = 256
SCHEMA = "post-apollo.forest.heart-custody.h2"


class CustodyRefusal(ValueError):
    """Fixed reason; never include input identities."""


@dataclass(frozen=True, slots=True)
class AttemptRef:
    context: TaskContext
    turn_id: str
    operation_id: str
    attempt_id: str

    def __post_init__(self):
        if type(self.context) is not TaskContext:
            raise CustodyRefusal("INVALID_CONTEXT")
        try:
            for value in (self.turn_id, self.operation_id, self.attempt_id):
                _key(value)
        except DispatchRefusal:
            raise CustodyRefusal("INVALID_ATTEMPT_REFERENCE") from None


@dataclass(frozen=True, slots=True)
class ReleaseReference:
    """Separate fixture observation, not proof of released physical memory.

    A resident idle model can still consume memory. availability must
    describe capacity *after* the retained residency and other charges.
    """
    attempt: AttemptRef
    clock_domain: str
    observed_ns: int
    availability: ResourceAvailability
    active_workload: bool | None

    def __post_init__(self):
        if (type(self.attempt) is not AttemptRef
                or type(self.availability) is not ResourceAvailability
                or (self.active_workload is not None
                    and type(self.active_workload) is not bool)):
            raise CustodyRefusal("INVALID_RELEASE_REFERENCE")
        try:
            _key(self.clock_domain)
            _time(self.observed_ns)
        except DispatchRefusal:
            raise CustodyRefusal("INVALID_RELEASE_REFERENCE") from None


class ResourceCustody:
    """One serialized fixture slot; no automatic expiry or reuse.

    H1 must be recomputed inside the claim lock. Local accounting does
    not protect against another process, a second instance, or actual
    changing native resources. Unknown outcome is sticky for this instance.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._active = None
        self._clock_domain = None
        self._last_ns = None
        self._terminal_ns = None
        self._availability_source = None
        self._operations = set()
        self._attempts = set()
        self._turns = set()
        self._state = "IDLE"

    def claim_reference(self, original, current, *, now_ns):
        with self._lock:
            if self._active is not None:
                return "SLOT_OCCUPIED"
            if len(self._operations) >= MAX_OPERATIONS:
                return "HISTORY_LIMIT_HOLD"
            decision = compare_dispatch(original, current, now_ns=now_ns)
            if not decision["dispatch_reference_matched"]:
                return "DISPATCH_REFERENCE_HOLD"
            scope = current.binding.recommendation.original.scope
            attempt = AttemptRef(scope.context, scope.turn_id,
                                 current.operation_id, current.attempt_id)
            turn = (attempt.context, attempt.turn_id)
            if (attempt.operation_id in self._operations
                    or attempt.attempt_id in self._attempts
                    or turn in self._turns):
                return "REPLAY_HOLD"
            if self._clock_domain is not None and (
                    current.clock_domain != self._clock_domain
                    or original.captured_ns <= self._last_ns):
                return "CUSTODY_CLOCK_HOLD"
            self._operations.add(attempt.operation_id)
            self._attempts.add(attempt.attempt_id)
            self._turns.add(turn)
            self._active = attempt
            self._clock_domain = current.clock_domain
            self._last_ns = now_ns
            self._availability_source = current.availability.source
            self._state = "REFERENCE_HELD"
            return "REFERENCE_HELD"

    def _match(self, attempt):
        if type(attempt) is not AttemptRef or attempt != self._active:
            raise CustodyRefusal("ATTEMPT_MISMATCH")

    def observe_terminal_reference(self, attempt, *, outcome, observed_ns):
        """Fixture terminal report; STOP/EOF/COMMIT entry are not outcomes."""
        if type(outcome) is not str or outcome not in (
                "NOT_DISPATCHED", "COMMITTED", "CANCELLED", "FAILED", "UNKNOWN"):
            raise CustodyRefusal("INVALID_TERMINAL_REFERENCE")
        try:
            _time(observed_ns)
        except DispatchRefusal:
            raise CustodyRefusal("INVALID_CLOCK_REFERENCE") from None
        with self._lock:
            self._match(attempt)
            if self._state == "UNKNOWN_HOLD":
                return "UNKNOWN_HOLD"
            if observed_ns < self._last_ns:
                return "TERMINAL_CLOCK_HOLD"
            if self._state != "REFERENCE_HELD":
                # Contradictory or repeated terminal evidence cannot clear custody.
                self._state = "UNKNOWN_HOLD"
                return "UNKNOWN_HOLD"
            self._last_ns = observed_ns
            self._terminal_ns = observed_ns
            self._state = ("UNKNOWN_HOLD" if outcome == "UNKNOWN"
                           else "TERMINAL_REFERENCE_HELD")
            return self._state

    def account_release_reference(self, observation, *, now_ns):
        if type(observation) is not ReleaseReference:
            raise CustodyRefusal("INVALID_RELEASE_REFERENCE")
        try:
            _time(now_ns)
        except DispatchRefusal:
            raise CustodyRefusal("INVALID_CLOCK_REFERENCE") from None
        with self._lock:
            self._match(observation.attempt)
            if self._state != "TERMINAL_REFERENCE_HELD":
                return "TERMINAL_REQUIRED_HOLD"
            from heart_dispatch_reference_h1 import MAX_AGE_NS
            if (observation.clock_domain != self._clock_domain
                    or not self._terminal_ns < observation.observed_ns <= now_ns
                    or now_ns - observation.observed_ns > MAX_AGE_NS):
                return "RELEASE_CLOCK_HOLD"
            a = observation.availability
            if (observation.active_workload is not False
                    or a.source != self._availability_source
                    or any(v is None for v in
                           (a.memory_mib, a.accelerator_memory_mib, a.cpu_threads))):
                return "RESOURCE_ACCOUNTING_HOLD"
            self._active = None
            self._last_ns = now_ns
            self._terminal_ns = None
            self._availability_source = None
            self._state = "IDLE"
            return "REFERENCE_RELEASED"

    def status(self):
        with self._lock:
            return {
                "schema": SCHEMA, "status": self._state,
                "fixture_slot_occupied": self._active is not None,
                "physical_resources_reserved": False,
                "physical_resources_released": False,
                "source_authenticated": False,
                "terminal_verified": False,
                "durable_recovery": False,
                "safe_to_start_inference": False,
                "permission_granted": False,
                "production_authority": False,
                "safe_actions": [],
            }
