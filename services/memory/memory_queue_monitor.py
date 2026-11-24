"""Caller-driven M1c.3c.1 monitor. No timer, process, DB writes or authority."""
import copy
import threading
import time
import uuid

from memory_adjustment_queue import QueueError, _int
from memory_queue_advisory import evaluate


def system_clock():
    return time.time_ns() // 1000000000, time.monotonic_ns() // 1000000


class Monitor:
    def __init__(self, queue, observe, *, interval_ms, max_age_ms,
                 max_gap_ms, stable_ms, clock=system_clock):
        self.interval = _int(interval_ms, 1)
        self.max_age = _int(max_age_ms, self.interval)
        self.max_gap = _int(max_gap_ms, self.interval, self.max_age)
        self.stable = _int(stable_ms, self.interval)
        self.queue, self.observe, self.clock = queue, observe, clock
        self._lock = threading.Lock()
        self._last_clock = None
        self._signature = None
        self._status = None
        self._set_record(None)

    def _reset_sequence(self):
        self._previous = None
        self._first = None
        self._valid_until = None

    def _set_record(self, record):
        self._record = copy.deepcopy(record)
        self._observer = str(uuid.uuid4())
        self._reset_sequence()
        self._checked = None
        self._due = None

    def _read_clock(self):
        wall, mono = self.clock()
        _int(wall)
        _int(mono)
        if self._last_clock is not None:
            last_wall, last_mono = self._last_clock
            if wall < last_wall or mono < last_mono:
                raise QueueError("CLOCK_ROLLBACK")
        self._last_clock = wall, mono
        return wall, mono

    def _publish(self, state, code):
        r = self._record
        request_id = r["id"] if r else None
        signature = (request_id, state, code)
        changed = signature != self._signature
        self._signature = signature
        self._status = state, code
        return {"version": 1, "request_id": request_id,
                "target_gib": r["target_gib"] if r else None,
                "actual_kib": r["actual_kib"] if r else None,
                "expires_at": r["expires_at"] if r else None,
                "state": state, "code": code, "can_execute": False,
                "last_checked_at": self._checked,
                "next_check_monotonic_ms": self._due,
                "ready_valid_before_monotonic_ms": self._valid_until if state == "READY_ADVISORY" else None,
                "transition": changed}

    def _stop(self, state, code):
        self._reset_sequence()
        self._due = None
        return self._publish(state, code)

    def _storage_error(self):
        self._set_record(None)
        return self._stop("UNKNOWN", "QUEUE_UNAVAILABLE")

    def _poll(self):
        try:
            record = self.queue.pending()
        except QueueError:
            return self._storage_error()
        if record != self._record:
            self._set_record(record)
        if record is None:
            return self._stop("IDLE", "NO_PENDING_REQUEST")
        try:
            wall, mono = self._read_clock()
        except (QueueError, TypeError, ValueError, OSError):
            return self._stop("UNKNOWN", "CLOCK_UNAVAILABLE_OR_ROLLBACK")
        if wall < record["requested_at"]:
            return self._stop("UNKNOWN", "CLOCK_ROLLBACK")
        if wall >= record["expires_at"]:
            return self._stop("WAITING", "EXPIRY_RECONCILIATION_REQUIRED")
        if self._due is not None and mono < self._due:
            return self._publish(*self._status)

        # Exactly one attempt, then re-read the pending intent. The provider
        # owns bounded collection, source identity and operation-state witness.
        try:
            sample = copy.deepcopy(self.observe(copy.deepcopy(record), self._observer))
        except Exception:
            sample = None
        try:
            current = self.queue.pending()
        except QueueError:
            return self._storage_error()
        try:
            wall, mono = self._read_clock()
        except (QueueError, TypeError, ValueError, OSError):
            return self._stop("UNKNOWN", "CLOCK_UNAVAILABLE_OR_ROLLBACK")
        if current != record:
            self._set_record(current)
            if current is None:
                return self._stop("IDLE", "NO_PENDING_REQUEST")
            self._due = mono + self.interval
            return self._publish("WAITING", "REQUEST_CHANGED")
        self._checked = wall
        self._due = mono + self.interval
        if wall >= record["expires_at"]:
            return self._stop("WAITING", "EXPIRY_RECONCILIATION_REQUIRED")
        if type(sample) is not dict or sample.get("observer_id") != self._observer:
            self._reset_sequence()
            return self._publish("UNKNOWN", "OBSERVATION_UNAVAILABLE")

        # This code means the current sample is valid, fresh and idle, but
        # cannot yet meet the continuity requirement.
        single = evaluate(record, sample, now=wall, monotonic_ms=mono,
                          max_age_ms=self.max_age)
        if single["code"] != "CONTINUITY_REQUIRED":
            self._reset_sequence()
            return self._publish(single["state"], single["code"])
        stamp = sample["monotonic_ms"]
        if self._previous is None:
            self._first = stamp
        else:
            gap = stamp - self._previous["monotonic_ms"]
            if gap <= 0 or sample["wall_time"] < self._previous["wall_time"]:
                self._reset_sequence()
                return self._publish("UNKNOWN", "OBSERVATION_ORDER_INVALID")
            if gap > self.max_gap:
                self._reset_sequence()
                self._first = stamp
            else:
                pair = evaluate(record, sample, now=wall, monotonic_ms=mono,
                                max_age_ms=self.max_age, previous=self._previous)
                if pair["state"] != "READY_ADVISORY":
                    self._reset_sequence()
                    return self._publish(pair["state"], pair["code"])
        self._previous = sample
        if stamp - self._first < self.stable:
            return self._publish("WAITING", "STABILITY_INTERVAL")

        self._valid_until = min(self._due, stamp + self.max_age,
                                mono + (record["expires_at"] - wall) * 1000)
        if self._valid_until <= mono:
            self._reset_sequence()
            return self._publish("UNKNOWN", "STALE_OBSERVATION")
        # A cached READY cannot be returned beyond its next-check deadline.
        self._due = self._valid_until
        return self._publish("READY_ADVISORY", "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED")

    def tick(self):
        """Serialized caller; a concurrent call never returns cached readiness."""
        if not self._lock.acquire(blocking=False):
            raise QueueError("MONITOR_BUSY")
        try:
            return self._poll()
        finally:
            self._lock.release()
