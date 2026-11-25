"""R6d isolated retention library; never grants startup or execution authority.

Single cooperating writer; never run the legacy writer concurrently. The caller
must obtain a verified exact receipt from the trusted current backend channel.
A receipt-shaped dictionary alone is not an authentication mechanism.
"""
import contextlib
import fcntl
import hashlib
import json
import os

from memory_adjustment_queue import QueueError
from memory_queue_host_checkpoint import HostCheckpoint, SLOTS, MAX_BYTES, _json, validate_record
from memory_queue_local_actions import MAX_SAFE
from memory_queue_pipe import _receipt_wire

# Bounded development policy, not an installed retention setting.
MAX_GENERATIONS = 32
SEAL = "dismissed-v2.json"
COMMITTED_SEAL = "committed-v1.json"
SEALS = {SEAL, COMMITTED_SEAL}


class CheckpointGenerations:
    def __init__(self, directory):
        self.root = HostCheckpoint(directory)

    @contextlib.contextmanager
    def _locked(self):
        with self.root._directory() as fd:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield fd

    def _store(self, number):
        return self.root if number == 0 else HostCheckpoint(
            self.root.directory / ("generation-%04d" % number))

    @staticmethod
    def _action(snapshot):
        for key in ("action", "acknowledgment", "dismissal"):
            record = snapshot.get(key)
            if record is not None:
                return (record["message"] if key == "action" else
                        record["review"]["snapshot"]["record"]["message"])["action_id"]
        return None

    @staticmethod
    def _seal_name(receipt):
        return COMMITTED_SEAL if type(receipt) is dict and receipt.get("version") == 1 else SEAL

    @staticmethod
    def _seal_bytes(snapshot, receipt):
        if CheckpointGenerations._seal_name(receipt) == COMMITTED_SEAL:
            ack = snapshot.get("acknowledgment")
            if (ack is None or snapshot.get("dismissal") is not None
                    or ack["review"]["snapshot"]["record"]["state"] != "COMMITTED"):
                raise QueueError("CHECKPOINT_EXACT_COMMITTED_REVIEW_REQUIRED")
            _receipt_wire(receipt)
            if (_json(receipt["review"]) != _json(ack["review"])
                    or not 0 <= receipt["acknowledged_at_ms"] - ack["review"]["reviewed_at_ms"] < 60000):
                raise QueueError("CHECKPOINT_EXACT_COMMITTED_REVIEW_REQUIRED")
            return CheckpointGenerations._encode_seal(snapshot, receipt)
        dismissal = snapshot.get("dismissal")
        if (dismissal is None or type(receipt) is not dict
                or set(receipt) != {"version", "review", "dismissed_at_ms",
                                    "disposition", "adjustment_outcome",
                                    "can_execute", "startup_unlock"}
                or type(receipt["version"]) is not int or receipt["version"] != 2
                or _json(receipt["review"]) != _json(dismissal["review"])
                or receipt["disposition"] != "LOCAL_PREPARATION_DISMISSED"
                or receipt["adjustment_outcome"] != "UNVERIFIED"
                or receipt["can_execute"] is not False
                or receipt["startup_unlock"] is not False
                or type(receipt["dismissed_at_ms"]) is not int
                or not 0 <= receipt["dismissed_at_ms"] <= MAX_SAFE
                or not 0 <= receipt["dismissed_at_ms"] - dismissal["review"]["reviewed_at_ms"] < 60000):
            raise QueueError("CHECKPOINT_EXACT_DISMISSAL_REQUIRED")
        return CheckpointGenerations._encode_seal(snapshot, receipt)

    @staticmethod
    def _encode_seal(snapshot, receipt):
        data = _json({"version": 1, "receipt": receipt,
                      "snapshot_sha256": hashlib.sha256(_json(snapshot)).hexdigest()}) + b"\n"
        if len(data) > MAX_BYTES:
            raise QueueError("HOST_CHECKPOINT_TOO_LARGE")
        return data

    def _read_seal(self, fd, snapshot):
        present = SEALS.intersection(os.listdir(fd))
        if not present:
            return None
        if len(present) != 1:
            raise QueueError("INVALID_CHECKPOINT_GENERATION_SEAL")
        name = next(iter(present))
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=fd)
        try:
            before = os.fstat(handle)
            HostCheckpoint._private(before)
            data = bytearray()
            while len(data) <= MAX_BYTES:
                part = os.read(handle, min(4096, MAX_BYTES + 1 - len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(handle)
            current = os.stat(name, dir_fd=fd, follow_symlinks=False)
            for info in (after, current):
                HostCheckpoint._private(info)
            stamp = lambda i: (i.st_dev, i.st_ino, i.st_size, i.st_mtime_ns, i.st_ctime_ns)
            if stamp(before) != stamp(after) or stamp(after) != stamp(current):
                raise QueueError("HOST_CHECKPOINT_CHANGED")
            try:
                if len(data) > MAX_BYTES:
                    raise ValueError("oversize seal")
                value = json.loads(data.decode("ascii"))
                receipt = value["receipt"]
                if self._seal_name(receipt) != name or self._seal_bytes(snapshot, receipt) != data:
                    raise ValueError("noncanonical seal")
                return receipt
            except (ValueError, KeyError, TypeError, RecursionError) as exc:
                raise QueueError("INVALID_CHECKPOINT_GENERATION_SEAL") from exc
        finally:
            os.close(handle)

    def _scan(self, root_fd):
        allowed = set(SLOTS.values()) | SEALS
        names = set(os.listdir(root_fd)) - allowed
        expected = {"generation-%04d" % i for i in range(1, len(names) + 1)}
        if len(names) >= MAX_GENERATIONS or names != expected:
            raise QueueError("INVALID_CHECKPOINT_GENERATIONS")
        entries = []
        seen = set()
        for number in range(len(names) + 1):
            store = self._store(number)
            with store._directory() as fd:
                if number and set(os.listdir(fd)) - allowed:
                    raise QueueError("INVALID_CHECKPOINT_GENERATIONS")
                snapshot = store.load()
                receipt = self._read_seal(fd, snapshot)
            action_id = self._action(snapshot)
            if action_id is not None:
                if action_id in seen:
                    raise QueueError("CHECKPOINT_ACTION_ALREADY_RETAINED")
                seen.add(action_id)
            if number < len(names) and receipt is None:
                raise QueueError("CHECKPOINT_GENERATION_UNSEALED")
            entries.append((snapshot, receipt))
        return entries, seen

    def load(self):
        with self._locked() as fd:
            entries, _ = self._scan(fd)
            snapshot, receipt = entries[-1]
            return {"generation": len(entries)-1, "checkpoint": snapshot,
                    "sealed": receipt is not None, "receipt": receipt,
                    "startup_unlock": False, "can_execute": False}

    def save(self, generation, record):
        with self._locked() as fd:
            validate_record(record)
            entries, seen = self._scan(fd)
            # A prior mkdir may have survived a failed root fsync. Make its
            # directory entry durable before allowing a new checkpoint save.
            os.fsync(fd)
            snapshot, receipt = entries[-1]
            if type(generation) is not int or generation != len(entries)-1 or receipt is not None:
                raise QueueError("CHECKPOINT_GENERATION_NOT_WRITABLE")
            if record.get("kind") == "ACTION" and record.get("message", {}).get("action_id") in seen:
                raise QueueError("CHECKPOINT_ACTION_ALREADY_RETAINED")
            # Review-only checkpoints must not reuse an older generation's UUID.
            prior = seen - {self._action(snapshot)}
            if record.get("kind") in {"REVIEW_ACK", "REVIEW_DISMISS"} and record.get("review", {}).get("action_id") in prior:
                raise QueueError("CHECKPOINT_ACTION_ALREADY_RETAINED")
            return self._store(generation).save(record)

    def advance(self, generation, receipt):
        """Explicit retention transition only. Never send or authorize an action."""
        with self._locked() as root_fd:
            entries, _ = self._scan(root_fd)
            if type(generation) is not int or generation != len(entries)-1:
                raise QueueError("CHECKPOINT_GENERATION_NOT_CURRENT")
            if len(entries) >= MAX_GENERATIONS:
                raise QueueError("CHECKPOINT_GENERATION_LIMIT")
            snapshot, previous = entries[-1]
            data = self._seal_bytes(snapshot, receipt)
            seal_name = self._seal_name(receipt)
            store = self._store(generation)
            with store._directory() as fd:
                if previous is None:
                    handle = os.open(seal_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
                    try:
                        remaining = memoryview(data)
                        while remaining:
                            count = os.write(handle, remaining)
                            if count <= 0:
                                raise QueueError("HOST_CHECKPOINT_STORAGE_ERROR")
                            remaining = remaining[count:]
                        os.fsync(handle)
                    finally:
                        os.close(handle)
                elif previous != receipt:
                    raise QueueError("CHECKPOINT_EXACT_DISMISSAL_REQUIRED")
                # A prior failed fsync may have left a complete seal. Re-sync
                # it before advancing; never replace a partial/corrupt seal.
                if self._read_seal(fd, snapshot) != receipt:
                    raise QueueError("INVALID_CHECKPOINT_GENERATION_SEAL")
                handle = os.open(seal_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    os.fsync(handle)
                finally:
                    os.close(handle)
                os.fsync(fd)
            self.root._check_dir(root_fd)
            name = "generation-%04d" % (generation+1)
            os.mkdir(name, 0o700, dir_fd=root_fd)
            os.fsync(root_fd)
            entries, _ = self._scan(root_fd)
            if len(entries) != generation+2 or entries[-1][1] is not None:
                raise QueueError("INVALID_CHECKPOINT_GENERATIONS")
            return generation+1
