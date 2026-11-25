"""R1: caller-owned notify-only runtime composition, no live registration.

The host must supply an independent source capture and bounded observation
provider, explicitly call actions, and schedule checks. No thread, command,
IPC, Hub call, privileged helper, completion or automatic execution here.
"""
import contextlib
import copy
import threading
import time

from memory_adjustment_queue import QueueError, _int, _source, GIB_KIB
from memory_queue_events import Events
from memory_queue_history import History
from memory_queue_monitor import Monitor


def system_clock_ms():
    return time.time_ns() // 1000000, time.monotonic_ns() // 1000000


class Runtime:
    def __init__(self, queue, capture_source, observe, *, interval_ms,
                 max_age_ms, max_gap_ms, stable_ms, clock=system_clock_ms):
        self.queue = queue
        self.capture_source = capture_source
        self.clock = clock
        self._last_clock = None
        self._lock = threading.Lock()
        self.max_age = _int(max_age_ms, 1)
        self.monitor = Monitor(queue, observe, interval_ms=interval_ms,
                               max_age_ms=max_age_ms, max_gap_ms=max_gap_ms,
                               stable_ms=stable_ms, clock=self._monitor_clock)
        self.events = Events(queue)
        self.history = History(queue)

    @contextlib.contextmanager
    def _serialized(self):
        if not self._lock.acquire(blocking=False):
            raise QueueError("RUNTIME_BUSY")
        try:
            yield
        finally:
            self._lock.release()

    def _now(self):
        wall, mono = self.clock()
        _int(wall)
        _int(mono)
        if self._last_clock is not None:
            previous_wall, previous_mono = self._last_clock
            if wall < previous_wall or mono < previous_mono:
                raise QueueError("CLOCK_ROLLBACK")
        self._last_clock = wall, mono
        return wall, mono

    def _monitor_clock(self):
        wall, mono = self._now()
        return wall // 1000, mono

    def _capture(self, target, expires_at):
        # Only explicit bounded withdrawal requests enter this integration
        # slice. Missing identity is NOT absence of an allocation.
        _int(target, 4, 64)
        _int(expires_at, 1)
        if target % 4:
            raise QueueError("UNSUPPORTED_TARGET")
        before_wall, before_mono = self._now()
        try:
            sample = copy.deepcopy(self.capture_source())
        except Exception as exc:
            raise QueueError("SOURCE_UNAVAILABLE") from exc
        wall, mono = self._now()
        if (type(sample) is not dict or set(sample) != {
                "version", "source", "wall_ms", "monotonic_ms"}
                or type(sample["version"]) is not int or sample["version"] != 1):
            raise QueueError("SOURCE_UNAVAILABLE")
        stamp_wall = _int(sample["wall_ms"])
        stamp_mono = _int(sample["monotonic_ms"])
        if (not before_wall <= stamp_wall <= wall
                or not before_mono <= stamp_mono <= mono
                or wall - stamp_wall > self.max_age or mono - stamp_mono > self.max_age
                or wall - before_wall > self.max_age or mono - before_mono > self.max_age):
            raise QueueError("STALE_SOURCE")
        source = sample["source"]
        total = _source(source)
        if not source["base"] or not source["extension"]:
            raise QueueError("SOURCE_IDENTITY_UNAVAILABLE")
        base = source["base"]["size_kib"]
        extra = source["extension"]["size_kib"]
        extra_nominal = (extra + GIB_KIB - 1) // GIB_KIB
        if (not 0 <= target * GIB_KIB - base <= 1024
                or extra_nominal < 4 or extra_nominal % 4
                or not 0 <= extra_nominal * GIB_KIB - extra <= 1024
                or target + extra_nominal > 64 or total <= base):
            raise QueueError("UNSUPPORTED_TARGET")
        now = wall // 1000
        if expires_at <= now:
            raise QueueError("INVALID_EXPIRY")
        return source, now

    @staticmethod
    def _action_result(request, event=None, error=None):
        return {"version": 1, "request": request, "wake_required": True,
                "notification_candidate": event, "notification_error": error,
                "adjustment_outcome": "UNVERIFIED", "can_execute": False}

    def enqueue(self, *, target_gib, expires_at):
        with self._serialized():
            if self.queue.pending() is not None:
                raise QueueError("PENDING_EXISTS")
            source, now = self._capture(target_gib, expires_at)
            return self._action_result(self.queue.enqueue(
                target_gib=target_gib, source=source, now=now, expires_at=expires_at))

    def replace(self, expected_id, *, target_gib, expires_at):
        with self._serialized():
            pending = self.queue.pending()
            if not pending or pending["id"] != expected_id:
                raise QueueError("STALE_REQUEST")
            source, now = self._capture(target_gib, expires_at)
            return self._action_result(self.queue.replace(
                expected_id, target_gib=target_gib, source=source,
                now=now, expires_at=expires_at))

    def _finish(self, expected_id, *, expire):
        wall, _ = self._now()
        operation = self.queue.expire if expire else self.queue.cancel
        record = operation(expected_id, now=wall // 1000)
        # Intent committed first. An event-store failure is not cancellation
        # failure. Do not silently retry the intent action.
        try:
            event = self.events.stage_terminal(record["id"])
            return self._action_result(record, event=event)
        except QueueError:
            return self._action_result(record, error="EVENT_STAGE_UNAVAILABLE")

    def cancel(self, expected_id):
        with self._serialized():
            return self._finish(expected_id, expire=False)

    def expire(self, expected_id):
        with self._serialized():
            return self._finish(expected_id, expire=True)

    def local_action(self, message):
        """Opt-in durable local correlation; not yet wired to Owner/pipe.

        Never call on startup or retry an interrupted action. Existing
        explicit runtime methods remain unchanged pending joint integration.
        """
        from memory_queue_local_actions import LocalActions, validate
        with self._serialized():
            m = validate(message)
            wall, _ = self._now()
            journal = LocalActions(self.queue)
            journal.prepare(m, now=wall // 1000)
            if m["kind"] in {"QUEUE", "REPLACE"}:
                source, now = self._capture(m["target_gib"], m["expires_at"])
                record = journal.commit(m, now=now, source=source)
                return self._action_result(record)
            wall, _ = self._now()
            record = journal.commit(m, now=wall // 1000)
            try:
                event = self.events.stage_terminal(record["id"])
                return self._action_result(record, event=event)
            except QueueError:
                return self._action_result(record, error="EVENT_STAGE_UNAVAILABLE")

    def detail(self, request_id):
        with self._serialized():
            return self.history.detail(request_id)

    @staticmethod
    def _unavailable(code):
        return {"version": 1, "request_id": None, "target_gib": None,
                "original_actual_kib": None, "expires_at": None,
                "state": "UNKNOWN", "code": code, "can_execute": False,
                "last_checked_at": None, "next_check_monotonic_ms": None,
                "ready_valid_before_monotonic_ms": None, "transition": False}

    def tick(self, *, recheck=False):
        """Return a bounded UI projection and optionally stage a candidate.

        No offer/delivery here. The owner must discard status on a subsequent
        mutation, owner exit or validity deadline. A null next check means
        sleep until explicit wake/reconciliation, never poll an idle runtime.
        """
        with self._serialized():
            status = self.monitor.tick(recheck=recheck)
            event = None
            error = None
            try:
                wall, mono = self._now()
                pending = self.queue.pending()
            except (QueueError, OSError, ValueError, TypeError):
                status = self._unavailable("RUNTIME_UNAVAILABLE")
                return self._projection(status, None, "RUNTIME_UNAVAILABLE")
            if (pending["id"] if pending else None) != status["request_id"]:
                return self._projection(self._unavailable("REQUEST_CHANGED"), None,
                                        "WAKE_REQUIRED")
            if pending is not None and wall // 1000 >= pending["expires_at"]:
                # Stop advisory readiness on expiry without silently changing
                # the durable intent. Explicit expire() reconciles the row.
                status = dict(status, state="WAITING", code="EXPIRY_RECONCILIATION_REQUIRED",
                              next_check_monotonic_ms=None,
                              ready_valid_before_monotonic_ms=None)
            elif status["state"] == "READY_ADVISORY":
                if (status["ready_valid_before_monotonic_ms"] <= mono
                        or not 0 <= wall - status["last_checked_at"] * 1000 < self.max_age):
                    status = dict(status, state="UNKNOWN", code="STALE_OBSERVATION",
                                  ready_valid_before_monotonic_ms=None)
            if pending is not None and status["transition"] and status["last_checked_at"] is not None:
                # Only actual blockers/attention/ready edge events. Ordinary
                # initial stability accumulation is not an actionable alert.
                if status["code"] != "STABILITY_INTERVAL":
                    try:
                        event = self.events.stage(status, now=wall // 1000, monotonic_ms=mono,
                                                  max_age_seconds=max(1, (self.max_age + 999) // 1000))
                    except QueueError:
                        error = "EVENT_STAGE_UNAVAILABLE"
            try:
                current = self.queue.pending()
            except QueueError:
                return self._projection(self._unavailable("QUEUE_UNAVAILABLE"), None,
                                        "WAKE_REQUIRED")
            if current != pending:
                return self._projection(self._unavailable("REQUEST_CHANGED"), None,
                                        "WAKE_REQUIRED")
            return self._projection(status, event, error)

    @staticmethod
    def _projection(status, event, error):
        status = dict(status)
        # Do not label captured-at-request capacity as live telemetry.
        if "actual_kib" in status:
            status["original_actual_kib"] = status.pop("actual_kib")
        return {"version": 1, "status": status, "notification_candidate": event,
                "notification_error": error, "adjustment_outcome": "UNVERIFIED",
                "can_execute": False}
