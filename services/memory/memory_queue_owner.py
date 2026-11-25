"""R2a: cooperating local runtime owner and in-process transport contract.

No socket, service, timer, Hub calls or privilege. Host chooses the transport.
The Linux flock is a coordination guard, not a security boundary or SQLite lock.
"""
import contextlib
import copy
import fcntl
import os
import stat
import threading
import uuid

from memory_adjustment_queue import QueueError, _int, _uuid

MAX_SAFE = 2**53 - 1


class Owner:
    def __init__(self, queue, runtime_factory, *, durable_actions=False,
                 staged_max_age_ms=None):
        if type(durable_actions) is not bool:
            raise QueueError("INVALID_ACTION_MODE")
        if staged_max_age_ms is not None:
            if not durable_actions:
                raise QueueError("DURABLE_ACTION_MODE_REQUIRED")
            _int(staged_max_age_ms, 1, 60000)
        self._staged_max_age_ms = staged_max_age_ms
        self._staged_message = None
        self.queue = queue
        self._durable_actions = durable_actions
        self._journal = None
        self.pid = os.getpid()
        self.owner_id = str(uuid.uuid4())
        self._sequence = 0
        self._next_action = 1
        self._gate = threading.Lock()
        self._fd = None
        self._published = None
        try:
            identity = queue._check_file()
            fd = os.open(queue.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            self._fd = fd
            self._identity = identity
            self._check()
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise QueueError("OWNER_BUSY") from exc
            self._check()
            # Select one action path under the existing owner flock. Do not
            # downgrade a journal-enabled database to legacy owner dispatch.
            if self._durable_actions:
                from memory_queue_local_actions import LocalActions
                self._journal = LocalActions(queue)
            else:
                self._legacy_fence()
            self.runtime = runtime_factory(queue)
            if self.runtime.queue is not queue:
                raise QueueError("OWNER_QUEUE_MISMATCH")
            self._check()
        except BaseException:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            raise

    def _legacy_fence(self):
        with self.queue._transaction() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name=?",
                          ("memory_queue_local_actions_v1",)).fetchone():
                raise QueueError("DURABLE_ACTION_MODE_REQUIRED")

    def _check(self):
        if os.getpid() != self.pid or self._fd is None:
            raise QueueError("OWNER_LOST")
        info = os.fstat(self._fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1
                or (info.st_dev, info.st_ino) != self._identity
                or self.queue._check_file() != self._identity):
            raise QueueError("OWNER_LOST")

    @contextlib.contextmanager
    def _call(self):
        # Refuse inherited objects in forked children before taking a lock.
        if os.getpid() != self.pid:
            raise QueueError("OWNER_LOST")
        if not self._gate.acquire(blocking=False):
            raise QueueError("OWNER_BUSY")
        try:
            self._check()
            yield
            self._check()
        finally:
            self._gate.release()

    def close(self):
        if os.getpid() != self.pid:
            raise QueueError("OWNER_LOST")
        if not self._gate.acquire(blocking=False):
            raise QueueError("OWNER_BUSY")
        try:
            if self._fd is not None:
                # Closing releases the flock, unless an inherited descriptor
                # remains open. Do not fork with a live Owner.
                os.close(self._fd)
                self._fd = None
        finally:
            self._gate.release()

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *_):
        self.close()

    def _envelope(self, kind, **payload):
        self._sequence = _int(self._sequence + 1, 1, MAX_SAFE)
        return dict(version=1, owner_id=self.owner_id, sequence=self._sequence,
                    next_action_sequence=self._next_action, kind=kind,
                    can_execute=False, **payload)

    def publish(self):
        """Owner scheduler/wake only. May observe and stage events."""
        with self._call():
            self._published = None
            packet = self._envelope("STATUS", projection=self.runtime.tick())
            self._published = copy.deepcopy(packet)
            return packet

    def status(self):
        """Passive read of the last publication; no tick or event staging.

        None means no valid publication; the host must invalidate the client.
        Never synthesize a new sequence for a cached packet.
        """
        with self._call():
            if self._published is None:
                return None
            s = self._published["projection"]["status"]
            try:
                wall, mono = self.runtime._now()
                due = s["next_check_monotonic_ms"]
                expiry = s["expires_at"]
                # At a due boundary the scheduler, not the reader, must
                # publish a new observation. Do not retain expired READY.
                # A freshly published expiry-reconciliation status is
                # deliberately terminal for scheduling, not a readiness claim.
                # Keep it readable so the operator can explicitly expire the
                # exact pending intent. All pre-expiry publications still lapse.
                expired_report = (s["state"] == "WAITING"
                                  and s["code"] == "EXPIRY_RECONCILIATION_REQUIRED"
                                  and due is None
                                  and s["ready_valid_before_monotonic_ms"] is None)
                if ((due is not None and mono >= due)
                        or (expiry is not None and wall // 1000 >= expiry
                            and not expired_report)):
                    self._published = None
            except (QueueError, OSError, ValueError, TypeError):
                self._published = None
            return copy.deepcopy(self._published)

    def invalidate(self):
        """Host-owned observer loss/deadline/disconnect invalidation."""
        with self._call():
            self._published = None

    @staticmethod
    def _action_summary(result):
        # Do not send source device/inode values or ephemeral Hub packets to
        # the JS consumer. The durable candidate stays in the event ledger.
        summary = {"version": 1, "can_execute": False,
                   "adjustment_outcome": "UNVERIFIED"}
        if "request" in result:
            r = result["request"]
            summary["request"] = {k: r[k] for k in
                                  ("id", "state", "target_gib", "expires_at")}
            summary["wake_required"] = True
            summary["notification_error"] = result["notification_error"]
        return summary

    def action(self, message):
        """One strictly ordered local action per owner epoch; never replay.

        A lost reply is not a refusal or success. Reconcile via status/history,
        never repeat an action automatically, including after owner restart.
        """
        with self._call():
            if (type(message) is not dict or set(message) != {
                    "version", "owner_id", "action_id", "action_sequence",
                    "kind", "expected_request_id", "target_gib", "expires_at"}
                    or type(message["version"]) is not int or message["version"] != 1
                    or message["owner_id"] != self.owner_id):
                raise QueueError("STALE_OR_INVALID_OWNER")
            action_id = _uuid(message["action_id"])
            seq = _int(message["action_sequence"], 1, MAX_SAFE - 1)
            if seq != self._next_action:
                raise QueueError("STALE_ACTION_SEQUENCE")
            kind = message["kind"]
            if type(kind) is not str or kind not in {
                    "QUEUE", "REPLACE", "CANCEL", "EXPIRE", "RECHECK"}:
                raise QueueError("INVALID_ACTION")
            expected = message["expected_request_id"]
            if kind == "QUEUE":
                if expected is not None:
                    raise QueueError("INVALID_EXPECTED_REQUEST")
            else:
                _uuid(expected)
            target, expires = message["target_gib"], message["expires_at"]
            if kind in {"QUEUE", "REPLACE"}:
                _int(target, 4, 64)
                _int(expires, 1, MAX_SAFE)
                if target % 4:
                    raise QueueError("INVALID_TARGET")
            elif target is not None or expires is not None:
                raise QueueError("INVALID_ACTION_FIELDS")

            if self._staged_max_age_ms is not None:
                if kind != "RECHECK":
                    raise QueueError("STAGED_ACTION_REQUIRED")
                if self._staged_message is not None:
                    raise QueueError("STAGED_ACTION_PENDING")
            if not self._durable_actions:
                self._legacy_fence()
            # Consume sequence before dispatch. It is not authorization and
            # does not survive owner restart. Never retry a lost response.
            self._next_action += 1
            self._published = None
            if kind != "QUEUE":
                current = self.queue.pending()
                if current is None or current["id"] != expected:
                    return self._envelope("ACTION", action_id=action_id,
                                          action_sequence=seq,
                                          disposition="REFUSED",
                                          code="STALE_REQUEST", result=None,
                                          invalidate=True)
            try:
                if self._durable_actions and kind != "RECHECK":
                    # No legacy fallback, including on journal/capture error.
                    result = self.runtime.local_action(message)
                elif kind == "QUEUE":
                    result = self.runtime.enqueue(target_gib=target, expires_at=expires)
                elif kind == "REPLACE":
                    result = self.runtime.replace(expected, target_gib=target, expires_at=expires)
                elif kind == "CANCEL":
                    result = self.runtime.cancel(expected)
                elif kind == "EXPIRE":
                    result = self.runtime.expire(expected)
                else:
                    result = self.runtime.tick(recheck=True)
            except (QueueError, OSError, ValueError, TypeError):
                # An exception after a durable mutation is not proof it failed.
                return self._envelope("ACTION", action_id=action_id,
                                      action_sequence=seq, disposition="UNKNOWN",
                                      code="RECONCILE_REQUIRED", result=None,
                                      invalidate=True)
            return self._envelope("ACTION", action_id=action_id,
                                  action_sequence=seq, disposition="REPORTED",
                                  code="READ_STATUS_REQUIRED", result=self._action_summary(result),
                                  invalidate=True)

    def prepare_action(self, message):
        """Opt-in staged local admission; not an execution permission.

        Future transport must await this correlated durable receipt before
        sending a commit. Any disconnect discards live continuation.
        """
        from memory_queue_local_actions import validate
        with self._call():
            if self._staged_max_age_ms is None:
                raise QueueError("STAGED_ACTION_MODE_REQUIRED")
            if self._staged_message is not None:
                raise QueueError("STAGED_ACTION_PENDING")
            m = validate(message)
            if m["owner_id"] != self.owner_id:
                raise QueueError("STALE_OR_INVALID_OWNER")
            if m["action_sequence"] != self._next_action:
                raise QueueError("STALE_ACTION_SEQUENCE")
            self._next_action += 1
            self._published = None
            record = self.runtime.prepare_staged_action(
                m, max_age_ms=self._staged_max_age_ms)
            self._staged_message = m
            return self._envelope("PREPARED_ACTION", record=record)

    def commit_action(self, message):
        """Consume exact live continuation; exceptions leave durable evidence."""
        from memory_queue_local_actions import validate
        with self._call():
            if self._staged_max_age_ms is None:
                raise QueueError("STAGED_ACTION_MODE_REQUIRED")
            expected, self._staged_message = self._staged_message, None
            if expected is None:
                raise QueueError("STAGED_ACTION_NOT_LIVE")
            m = validate(message)
            if m != expected or m["owner_id"] != self.owner_id:
                # No matching retry after an invalid continuation.
                raise QueueError("STAGED_ACTION_MISMATCH")
            self._published = None
            try:
                result = self.runtime.commit_staged_action(m)
            except (QueueError, OSError, ValueError, TypeError):
                return self._envelope("ACTION", action_id=m["action_id"],
                                      action_sequence=m["action_sequence"],
                                      disposition="UNKNOWN", code="RECONCILE_REQUIRED",
                                      result=None, invalidate=True)
            return self._envelope("ACTION", action_id=m["action_id"],
                                  action_sequence=m["action_sequence"],
                                  disposition="REPORTED", code="READ_STATUS_REQUIRED",
                                  result=self._action_summary(result), invalidate=True)

    def inventory(self, *, limit):
        """Bounded owner-bound read; never an unlock or fresh observation."""
        with self._call():
            if self._journal is None:
                raise QueueError("DURABLE_ACTION_MODE_REQUIRED")
            return self._envelope("INVENTORY", inventory=self._journal.inventory(limit=limit))

    def lookup_action(self, action_id):
        """Exact local action read; missing evidence is not noncommit proof."""
        with self._call():
            if self._journal is None:
                raise QueueError("DURABLE_ACTION_MODE_REQUIRED")
            return self._envelope("LOCAL_ACTION", action_id=_uuid(action_id),
                                  record=self._journal.lookup(action_id))

    def detail(self, request_id):
        """Developer-only history payload; transport encoding not selected."""
        with self._call():
            return self._envelope("DETAIL", detail=self.runtime.detail(request_id))
