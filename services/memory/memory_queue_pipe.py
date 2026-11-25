"""R3a: unprivileged, session-owned pipe transport reference.

No executable entry point, provider, command launch, daemon, or Hub delivery.
The shell host must explicitly supply an already constructed Owner and pipes.
A protocol/transport failure terminates the session, never retries an action.
"""
import json
import re
import os
import select
import stat
import time
import uuid

from memory_adjustment_queue import QueueError, _int, _uuid
from memory_queue_owner import MAX_SAFE
from memory_queue_local_actions import validate as validate_local_action
from memory_queue_delivery import Delivery

MAX_FRAME = 16384
INPUT_CHUNK = 4096


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise QueueError("DUPLICATE_WIRE_KEY")
        obj[key] = value
    return obj


def _safe(value, depth=0):
    if depth > 12:
        raise QueueError("WIRE_DEPTH")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        _int(value, 0, MAX_SAFE)
        return
    if type(value) is str:
        if len(value) > 1024:
            raise QueueError("WIRE_STRING")
        return
    if type(value) is list:
        if len(value) > 64:
            raise QueueError("WIRE_LIST")
        for item in value:
            _safe(item, depth + 1)
        return
    if type(value) is dict:
        if len(value) > 64:
            raise QueueError("WIRE_OBJECT")
        for key, item in value.items():
            if type(key) is not str or len(key) > 128:
                raise QueueError("WIRE_KEY")
            _safe(item, depth + 1)
        return
    raise QueueError("WIRE_TYPE")


def decode(line):
    if not line or len(line) >= MAX_FRAME or b"\n" in line or b"\r" in line:
        raise QueueError("WIRE_FRAME")
    try:
        obj = json.loads(line.decode("utf-8"), object_pairs_hook=_pairs)
        _safe(obj)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise QueueError("WIRE_FRAME") from exc
    if (type(obj) is not dict or type(obj.get("version")) is not int
            or obj["version"] != 1):
        raise QueueError("WIRE_VERSION")
    return obj


def encode(obj):
    _safe(obj)
    data = json.dumps(obj, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii") + b"\n"
    if len(data) > MAX_FRAME:
        raise QueueError("WIRE_FRAME")
    return data


def status_for_ui(packet):
    # Keep the strict DOC 2 projector shape, but do not cross the UI pipe
    # with notification candidate data. Actual delivery has its own seam.
    p = dict(packet["projection"], notification_candidate=None)
    result = dict(packet, projection=p)
    _safe(result)
    return result


def detail_for_ui(packet):
    d = packet["detail"]
    r = d["request"]
    request = {k: r[k] for k in ("id", "state", "target_gib", "actual_kib",
                                "requested_at", "expires_at", "changed_at", "replaced_by")}
    request["original_actual_kib"] = request.pop("actual_kib")
    events = [{k: e[k] for k in ("event_id", "kind", "code", "observed_at",
                                 "attempt_reserved_at_ms", "delivery_outcome")}
              for e in d["notification_events"]]
    evidence = d["withdrawal_evidence"]
    # Never expose the nested unsigned helper VERIFIED result or raw IDs.
    detail = {"version": 1, "request": request, "notification_events": events,
              "withdrawal_evidence": None if evidence is None else {
                  "state": "UNBOUND_EVIDENCE", "observed_at": evidence["observed_at"],
                  "kernel_verified_for_request": False, "can_execute": False},
              "adjustment_outcome": "UNVERIFIED", "can_execute": False}
    result = dict(packet, detail=detail)
    _safe(result)
    return result


def _exact(obj, fields):
    if type(obj) is not dict or set(obj) != set(fields.split()):
        raise QueueError("INVALID_REVIEW_WIRE")
    return obj


def _review_digest(value):
    if type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value):
        raise QueueError("INVALID_REVIEW_WIRE")
    return value


def _review_wire(review):
    # Historical rows may be read after their queue state changes. Check
    # exact safe fields, never transmit extra stored/raw source identities.
    _exact(review, "version review_id owner_id action_id snapshot review_digest reviewed_at_ms can_execute startup_unlock")
    _uuid(review["review_id"])
    _uuid(review["owner_id"])
    _uuid(review["action_id"])
    _review_digest(review["review_digest"])
    _int(review["reviewed_at_ms"], 0, MAX_SAFE)
    snapshot = _exact(review["snapshot"], "version record pending_request_id pending_digest adjustment_outcome can_execute startup_unlock")
    if snapshot["pending_request_id"] is not None:
        _uuid(snapshot["pending_request_id"])
    _review_digest(snapshot["pending_digest"])
    row = _exact(snapshot["record"], "version ordinal message state prepared_at result_request_id committed_at adjustment_outcome can_execute")
    m = validate_local_action(row["message"])
    _int(row["ordinal"], 1, MAX_SAFE)
    _int(row["prepared_at"], 0, MAX_SAFE)
    if (m["action_id"] != review["action_id"] or m["owner_id"] == review["owner_id"]
            or (m["expires_at"] is not None and m["expires_at"] <= row["prepared_at"])):
        raise QueueError("INVALID_REVIEW_WIRE")
    if row["state"] == "PREPARED":
        if row["result_request_id"] is not None or row["committed_at"] is not None:
            raise QueueError("INVALID_REVIEW_WIRE")
    elif row["state"] == "COMMITTED":
        _uuid(row["result_request_id"])
        _int(row["committed_at"], row["prepared_at"], MAX_SAFE)
        if ((m["kind"] in {"QUEUE","REPLACE"}) ==
                (row["result_request_id"] == m["expected_request_id"])):
            raise QueueError("INVALID_REVIEW_WIRE")
    else:
        raise QueueError("INVALID_REVIEW_WIRE")
    for obj in (review, snapshot, row):
        if type(obj["version"]) is not int or obj["version"] != 1 or obj["can_execute"] is not False:
            raise QueueError("INVALID_REVIEW_WIRE")
    if (review["startup_unlock"] is not False or snapshot["startup_unlock"] is not False
            or snapshot["adjustment_outcome"] != "UNVERIFIED" or row["adjustment_outcome"] != "UNVERIFIED"):
        raise QueueError("INVALID_REVIEW_WIRE")
    return review


def _receipt_wire(receipt):
    _exact(receipt, "version review acknowledged_at_ms disposition adjustment_outcome can_execute startup_unlock")
    review = _review_wire(receipt["review"])
    _int(receipt["acknowledged_at_ms"], review["reviewed_at_ms"], MAX_SAFE)
    if (type(receipt["version"]) is not int or receipt["version"] != 1
            or receipt["disposition"] != "REVIEW_ACKNOWLEDGED_ONLY"
            or receipt["adjustment_outcome"] != "UNVERIFIED"
            or receipt["can_execute"] is not False or receipt["startup_unlock"] is not False):
        raise QueueError("INVALID_REVIEW_WIRE")
    return receipt


class Session:
    def __init__(self, owner, emit, *, review_max_age_ms=None, notification_max_age_ms=None):
        if review_max_age_ms is not None:
            if owner.staged_max_age_ms is None:
                raise QueueError("STAGED_ACTION_MODE_REQUIRED")
            _int(review_max_age_ms, 1, 60000)
        if notification_max_age_ms is not None:
            _int(notification_max_age_ms,1,60000)
            if notification_max_age_ms > owner.runtime.max_age:
                raise QueueError("INVALID_NOTIFICATION_AGE")
        self.notification_max_age_ms = notification_max_age_ms
        self.delivery = Delivery(owner.runtime.events) if notification_max_age_ms is not None else None
        self.review_max_age_ms = review_max_age_ms
        self.review = None
        self.review_deadline = None
        self.owner, self.emit = owner, emit
        self.deadline = None
        self.started = False
        self.closed = False
        self.prepared = None
        self.prepare_deadline = None

    def close(self):
        """Terminal teardown; never preserve an admission across sessions."""
        if self.closed:
            return
        self.prepared = None
        self.review = None
        self.review_deadline = None
        self.prepare_deadline = self.deadline = None
        self.owner.close()
        self.closed = True

    def _control(self, kind):
        return {"version": 1, "kind": kind, "owner_id": self.owner.owner_id,
                "can_execute": False}

    def _notify(self, packet, terminal_reply):
        # Single session thread, no extra observation, no client-triggered
        # delivery, no recovery backlog scan. Reservation is durable before
        # emission; a lost frame is never retransmitted.
        if self.delivery is None:
            return
        status = packet["projection"]["status"]
        candidate = packet["projection"]["notification_candidate"]
        try:
            event = None
            if candidate and candidate["created"]:
                event = candidate["event"]
            if terminal_reply and terminal_reply.get("disposition")=="REPORTED":
                request = (terminal_reply.get("result") or {}).get("request")
                if request and request["state"] in {"CANCELLED","EXPIRED"}:
                    matches = [x for x in self.owner.runtime.events.for_request(request["id"])
                               if x["kind"]==request["state"]]
                    if len(matches)==1:
                        event = matches[0]
            if event is None:
                return
            def current():
                publication = self.owner.status()
                if publication is None or publication["sequence"]!=packet["sequence"]:
                    raise QueueError("NOTIFICATION_PUBLICATION_CHANGED")
                return publication["projection"]["status"]
            emit_failed = []
            def offer(notice):
                # Terminal notifications also require the same live
                # publication. Never let a queued packet become an outbox.
                current()
                try:
                    self.emit(dict(self._control("NOTIFICATION"),
                                   status_sequence=packet["sequence"],notice=notice))
                except Exception as exc:
                    emit_failed.append(exc)
                    raise
                return "OFFER_OUTCOME_UNKNOWN"
            self.delivery.attempt(event["event_id"],read_status=current,
                        clock=self.owner.runtime._now,max_age_ms=self.notification_max_age_ms,offer=offer)
        except (QueueError,OSError,ValueError,TypeError):
            return
        if emit_failed:
            raise QueueError("NOTIFICATION_PIPE_WRITE_FAILED") from emit_failed[0]

    def publish(self, terminal_reply=None):
        # Invalidate before potentially slow collection, not after it.
        self.deadline = None
        self.owner.invalidate()
        self.emit(self._control("INVALIDATE"))
        packet = self.owner.publish()
        status = packet["projection"]["status"]
        due = status["next_check_monotonic_ms"]
        if due is not None:
            wall, mono = self.owner.runtime._now()
            expiry = status["expires_at"]
            if expiry is None:
                raise QueueError("INVALID_SCHEDULE")
            # Owner's clock domain only. Never export a UI wall-clock timer.
            due = min(due, mono + max(0, expiry * 1000 - wall))
            if due <= mono:
                raise QueueError("SCHEDULE_ELAPSED")
            self.deadline = due
        self.emit(status_for_ui(packet))
        self._notify(packet,terminal_reply)

    def start(self):
        if self.closed or self.started:
            raise QueueError("SESSION_ALREADY_STARTED")
        self.started = True
        self.emit(self._control("HELLO"))
        self.publish()

    def wait_seconds(self):
        if self.closed:
            raise QueueError("SESSION_CLOSED")
        if self.prepare_deadline is not None:
            return max(0, self.prepare_deadline - time.monotonic())
        waits = []
        if self.review_deadline is not None:
            waits.append(max(0, self.review_deadline - time.monotonic()))
        if self.deadline is not None:
            _, mono = self.owner.runtime._now()
            waits.append(max(0, self.deadline - mono) / 1000)
        return min(waits) if waits else None

    def due(self):
        if self.review_deadline is not None and time.monotonic() >= self.review_deadline:
            self.close()
            raise QueueError("RECOVERY_PIPE_EXPIRED")
        if self.prepare_deadline is not None and self.wait_seconds() == 0:
            self.close()
            raise QueueError("STAGED_PIPE_EXPIRED")
        if self.deadline is not None:
            _, mono = self.owner.runtime._now()
            if mono >= self.deadline:
                self.publish()

    def receive(self, line):
        if not self.started or self.closed:
            raise QueueError("SESSION_NOT_STARTED")
        try:
            self._receive(line)
        except BaseException:
            # Staged mode is terminal on any malformed/unexpected command,
            # emission failure or lost continuation, even in direct fixtures.
            # Existing legacy direct Session fixtures retain their contract.
            if self.owner.staged_max_age_ms is not None:
                self.close()
            raise

    def _receive(self, line):
        obj = decode(line)
        mode = self.owner.staged_max_age_ms
        if self.prepared is not None:
            if time.monotonic() >= self.prepare_deadline:
                raise QueueError("STAGED_PIPE_EXPIRED")
            message, sequence, challenge = self.prepared
            if (set(obj) != {"version","kind","message","prepared_sequence","challenge"}
                    or obj["kind"] != "COMMIT_ACTION"
                    or type(obj["prepared_sequence"]) is not int
                    or obj["prepared_sequence"] != sequence
                    or obj["challenge"] != challenge
                    or validate_local_action(obj["message"]) != message):
                raise QueueError("STAGED_PIPE_MISMATCH")
            # Consume the receipt before the synchronous owner dispatch. A
            # lost commit reply cannot be retried, even in this generation.
            self.prepared = None
            self.prepare_deadline = None
            reply = self.owner.commit_action(message)
            self.emit(reply)
            self.publish(terminal_reply=reply)
            return
        if self.review is not None:
            if time.monotonic() >= self.review_deadline:
                raise QueueError("RECOVERY_PIPE_EXPIRED")
            review_id, digest, sequence = self.review
            if (set(obj) != {"version","kind","owner_id","review_id","review_digest","review_sequence"}
                    or obj["kind"] != "RECOVERY_ACK"
                    or obj["owner_id"] != self.owner.owner_id
                    or obj["review_id"] != review_id or obj["review_digest"] != digest
                    or type(obj["review_sequence"]) is not int or obj["review_sequence"] != sequence):
                raise QueueError("RECOVERY_PIPE_MISMATCH")
            self.review = None
            self.review_deadline = None
            packet = self.owner.acknowledge_recovery_review(review_id=review_id, review_digest=digest)
            _receipt_wire(packet["receipt"])
            self.emit(packet)
            return
        if obj.get("kind") == "RECOVERY_REVIEW":
            if self.review_max_age_ms is None or set(obj) != {"version","kind","owner_id","action_id"}:
                raise QueueError("RECOVERY_PIPE_MODE_REQUIRED")
            if obj["owner_id"] != self.owner.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            self.review_deadline = time.monotonic() + self.review_max_age_ms / 1000
            packet = self.owner.begin_recovery_review(_uuid(obj["action_id"]), max_age_ms=self.review_max_age_ms)
            review = _review_wire(packet["review"])
            if time.monotonic() >= self.review_deadline:
                raise QueueError("RECOVERY_PIPE_EXPIRED")
            self.review = (review["review_id"],review["review_digest"],packet["sequence"])
            self.emit(packet)
            return
        if obj.get("kind") == "RECOVERY_ACK":
            raise QueueError("RECOVERY_PIPE_NOT_LIVE")
        if obj.get("kind") == "RECOVERY_REVIEW_HISTORY":
            if self.review_max_age_ms is None or set(obj) != {"version","kind","owner_id","review_id"}:
                raise QueueError("RECOVERY_PIPE_MODE_REQUIRED")
            if obj["owner_id"] != self.owner.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            packet = self.owner.recovery_review_history(_uuid(obj["review_id"]))
            if packet["receipt"] is not None:
                _receipt_wire(packet["receipt"])
            self.emit(packet)
            return
        if obj.get("kind") == "PREPARE_ACTION":
            if mode is None or set(obj) != {"version","kind","message"}:
                raise QueueError("STAGED_PIPE_MODE_REQUIRED")
            # Stop advisory publication while waiting for the exact receipt
            # response. The owner separately checks both clocks under lock.
            self.deadline = None
            self.prepare_deadline = time.monotonic() + mode / 1000
            packet = self.owner.prepare_action(obj["message"])
            if time.monotonic() >= self.prepare_deadline:
                raise QueueError("STAGED_PIPE_EXPIRED")
            challenge = str(uuid.uuid4())
            self.prepared = (packet["record"]["message"],packet["sequence"],challenge)
            self.emit(dict(packet,challenge=challenge))
            return
        if obj.get("kind") == "COMMIT_ACTION":
            raise QueueError("STAGED_PIPE_NOT_PREPARED")
        if obj.get("kind") == "ACTION" and set(obj) == {"version", "kind", "message"}:
            # ACTION reply precedes the new STATUS. Client clears the old
            # projection on submit. Unknown response must never be replayed.
            self.deadline = None
            reply = self.owner.action(obj["message"])
            self.emit(reply)
            self.publish(terminal_reply=reply)
        elif obj.get("kind") == "HISTORY" and set(obj) == {
                "version", "kind", "owner_id", "request_id"}:
            if obj["owner_id"] != self.owner.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            self.emit(detail_for_ui(self.owner.detail(_uuid(obj["request_id"]))))
        elif obj.get("kind") == "INVENTORY" and set(obj) == {
                "version", "kind", "owner_id", "limit"}:
            if obj["owner_id"] != self.owner.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            self.emit(self.owner.inventory(limit=_int(obj["limit"], 1, 16)))
        elif obj.get("kind") == "LOCAL_ACTION" and set(obj) == {
                "version", "kind", "owner_id", "action_id"}:
            if obj["owner_id"] != self.owner.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            self.emit(self.owner.lookup_action(_uuid(obj["action_id"])))
        else:
            # No UI-triggered STATUS, publish, shell, path, or raw receipt.
            raise QueueError("WIRE_COMMAND")


def serve(owner, read_fd, write_fd, *, io_timeout_ms, review_max_age_ms=None, notification_max_age_ms=None):
    """Single session loop; caller owns descriptors and must close them.

    Blocking sleep when idle; a pending request arms just one timeout.
    No timers/threads/children created. Bounded frame and write/partial-read
    lifetime; provider itself must enforce a separate observation deadline.
    Close the owner on EOF or any failure. Never respawn/replay here.
    """
    _int(io_timeout_ms, 1, 60000)
    if (read_fd == write_fd or not stat.S_ISFIFO(os.fstat(read_fd).st_mode)
            or not stat.S_ISFIFO(os.fstat(write_fd).st_mode)):
        raise QueueError("PIPE_REQUIRED")
    before_read, before_write = os.get_blocking(read_fd), os.get_blocking(write_fd)
    def emit(obj):
        data = memoryview(encode(obj))
        deadline = time.monotonic() + io_timeout_ms / 1000
        while data:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [write_fd], [], remaining)[1]:
                raise QueueError("PIPE_WRITE_TIMEOUT")
            try:
                count = os.write(write_fd, data)
            except BlockingIOError:
                continue
            if count <= 0:
                raise QueueError("PIPE_WRITE_FAILED")
            data = data[count:]
    session = Session(owner, emit, review_max_age_ms=review_max_age_ms,
                      notification_max_age_ms=notification_max_age_ms)
    buffer = bytearray()
    partial_deadline = None
    try:
        os.set_blocking(read_fd, False)
        os.set_blocking(write_fd, False)
        session.start()
        while True:
            wait = session.wait_seconds()
            if partial_deadline is not None:
                left = partial_deadline - time.monotonic()
                if left <= 0:
                    raise QueueError("PIPE_READ_TIMEOUT")
                wait = left if wait is None else min(left, wait)
            ready = select.select([read_fd], [], [], wait)[0]
            if ready:
                try:
                    chunk = os.read(read_fd, INPUT_CHUNK)
                except BlockingIOError:
                    continue
                if not chunk:
                    if buffer:
                        raise QueueError("TRUNCATED_FRAME")
                    return
                if not buffer:
                    partial_deadline = time.monotonic() + io_timeout_ms / 1000
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, _, tail = buffer.partition(b"\n")
                    buffer = bytearray(tail)
                    session.receive(bytes(line))
                    partial_deadline = (time.monotonic() + io_timeout_ms / 1000
                                        if buffer else None)
                if len(buffer) >= MAX_FRAME:
                    raise QueueError("WIRE_FRAME")
            session.due()
    finally:
        try:
            session.close()
        finally:
            os.set_blocking(read_fd, before_read)
            os.set_blocking(write_fd, before_write)
