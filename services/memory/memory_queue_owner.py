"""R2a: cooperating local runtime owner and in-process transport contract.

No socket, service, timer, Hub calls or privilege. Host chooses the transport.
The Linux flock is a coordination guard, not a security boundary or SQLite lock.
"""
import contextlib
import fcntl
import os
import stat
import threading
import uuid

from memory_adjustment_queue import QueueError, _int, _uuid

MAX_SAFE = 2**53 - 1


class Owner:
    def __init__(self, queue, runtime_factory):
        self.queue = queue
        self.pid = os.getpid()
        self.owner_id = str(uuid.uuid4())
        self._sequence = 0
        self._next_action = 1
        self._gate = threading.Lock()
        self._fd = None
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
            self.runtime = runtime_factory(queue)
            if self.runtime.queue is not queue:
                raise QueueError("OWNER_QUEUE_MISMATCH")
            self._check()
        except BaseException:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            raise

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

    def status(self):
        """Explicit read/wake. R1 projection is unchanged inside the envelope."""
        with self._call():
            return self._envelope("STATUS", projection=self.runtime.tick())

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

            # Consume sequence before dispatch. It is not authorization and
            # does not survive owner restart. Never retry a lost response.
            self._next_action += 1
            if kind != "QUEUE":
                current = self.queue.pending()
                if current is None or current["id"] != expected:
                    return self._envelope("ACTION", action_id=action_id,
                                          action_sequence=seq,
                                          disposition="REFUSED",
                                          code="STALE_REQUEST", result=None,
                                          invalidate=True)
            try:
                if kind == "QUEUE":
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
                                  code="READ_STATUS_REQUIRED", result=result,
                                  invalidate=True)

    def detail(self, request_id):
        """Developer-only history payload; transport encoding not selected."""
        with self._call():
            return self._envelope("DETAIL", detail=self.runtime.detail(request_id))
