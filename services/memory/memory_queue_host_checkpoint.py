"""R3q host pre-send recovery evidence, not an operation journal or authority.

Explicit caller-owned private directory. Write-once action/ack/dismiss slots, no removal or
overwrite. Before sending a PREPARE or ACK the future host wrapper must
persist the corresponding exact checkpoint and wait for successful fsync.
A crash leaving a partial file blocks recovery; absence is not proof of
noncommit. This is a library, not a service or installed launcher.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat

from memory_adjustment_queue import QueueError
from memory_queue_local_actions import validate
from memory_queue_pipe import _review_wire

MAX_BYTES = 8192
SLOTS = {"ACTION": "action-v1.json", "REVIEW_ACK": "review-ack-v1.json",
         "REVIEW_DISMISS": "review-dismiss-v1.json"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def validate_record(record):
    if (type(record) is not dict or type(record.get("version")) is not int
            or record["version"] != 1 or type(record.get("kind")) is not str):
        raise QueueError("INVALID_HOST_CHECKPOINT")
    kind = record["kind"]
    if kind == "ACTION" and set(record) == {"version","kind","message"}:
        validate(record["message"])
    elif kind in {"REVIEW_ACK","REVIEW_DISMISS"} and set(record) == {"version","kind","review"}:
        review = _review_wire(record["review"])
        if kind=="REVIEW_DISMISS" and review["snapshot"]["record"]["state"]!="PREPARED":
            raise QueueError("INVALID_HOST_CHECKPOINT")
        if hashlib.sha256(_json(review["snapshot"])).hexdigest() != review["review_digest"]:
            raise QueueError("INVALID_HOST_CHECKPOINT_DIGEST")
    else:
        raise QueueError("INVALID_HOST_CHECKPOINT")
    return record


def _encode(record):
    payload = _json(validate_record(record))
    data = _json({"record":record,"sha256":hashlib.sha256(payload).hexdigest()}) + b"\n"
    if len(data) > MAX_BYTES:
        raise QueueError("HOST_CHECKPOINT_TOO_LARGE")
    return data


def _decode(data, kind):
    try:
        value = json.loads(data.decode("ascii"))
        if type(value) is not dict or set(value) != {"record","sha256"}:
            raise QueueError("INVALID_HOST_CHECKPOINT")
        record = value["record"]
        if _encode(record) != data or record["kind"] != kind:
            raise QueueError("INVALID_HOST_CHECKPOINT")
        return record
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise QueueError("INVALID_HOST_CHECKPOINT") from exc


class HostCheckpoint:
    def __init__(self, directory):
        self.directory = Path(directory).absolute()

    @staticmethod
    def _private(info, *, directory=False):
        if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                or info.st_uid != os.getuid() or info.st_mode & 0o077
                or (not directory and info.st_nlink != 1)):
            raise QueueError("UNSAFE_HOST_CHECKPOINT")

    def _check_dir(self, fd):
        if self.directory.resolve() != self.directory:
            raise QueueError("UNSAFE_HOST_CHECKPOINT")
        actual = self.directory.lstat()
        held = os.fstat(fd)
        self._private(actual,directory=True)
        self._private(held,directory=True)
        if (actual.st_dev,actual.st_ino) != (held.st_dev,held.st_ino):
            raise QueueError("HOST_CHECKPOINT_DIRECTORY_REPLACED")

    @contextlib.contextmanager
    def _directory(self):
        try:
            fd = os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:
                self._check_dir(fd)
                yield fd
                self._check_dir(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise QueueError("HOST_CHECKPOINT_STORAGE_ERROR") from exc

    def _read(self, directory_fd, kind):
        name = SLOTS[kind]
        try:
            fd = os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,
                         dir_fd=directory_fd)
        except FileNotFoundError:
            return None
        try:
            before = os.fstat(fd)
            self._private(before)
            data = bytearray()
            while len(data) <= MAX_BYTES:
                part = os.read(fd,min(4096,MAX_BYTES+1-len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(fd)
            current = os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
            self._private(after)
            self._private(current)
            def stamp(info):
                return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
            if stamp(before)!=stamp(after) or stamp(after)!=stamp(current):
                raise QueueError("HOST_CHECKPOINT_CHANGED")
            if not data or len(data)>MAX_BYTES:
                raise QueueError("INVALID_HOST_CHECKPOINT")
            return _decode(bytes(data),kind)
        finally:
            os.close(fd)

    @staticmethod
    def _linked(action, acknowledgment):
        if (action is not None and acknowledgment is not None
                and action["message"] != acknowledgment["review"]["snapshot"]["record"]["message"]):
            raise QueueError("HOST_CHECKPOINT_ACTION_MISMATCH")

    @classmethod
    def _linked_all(cls,action,acknowledgment,dismissal):
        cls._linked(action,acknowledgment)
        cls._linked(action,dismissal)
        if acknowledgment is not None and dismissal is not None:
            if acknowledgment["review"]["snapshot"]["record"]["message"] != dismissal["review"]["snapshot"]["record"]["message"]:
                raise QueueError("HOST_CHECKPOINT_ACTION_MISMATCH")

    def load(self):
        with self._directory() as fd:
            action = self._read(fd,"ACTION")
            acknowledgment = self._read(fd,"REVIEW_ACK")
            dismissal = self._read(fd,"REVIEW_DISMISS")
            self._linked_all(action,acknowledgment,dismissal)
            result={"version":1,"action":action,"acknowledgment":acknowledgment,
                    "startup_unlock":False,"can_execute":False}
            if dismissal is not None:
                result.update(version=2,dismissal=dismissal)
            return result

    def save(self, record):
        data = _encode(record)
        kind = record["kind"]
        with self._directory() as directory_fd:
            # This bounded prototype admits a single action and a single
            # acknowledgment. No replacement, cleanup or reset API.
            action = self._read(directory_fd,"ACTION")
            acknowledgment = self._read(directory_fd,"REVIEW_ACK")
            dismissal = self._read(directory_fd,"REVIEW_DISMISS")
            self._linked_all(action,acknowledgment,dismissal)
            if kind == "ACTION":
                if action is not None or acknowledgment is not None or dismissal is not None:
                    raise QueueError("HOST_CHECKPOINT_OCCUPIED")
            elif kind == "REVIEW_ACK":
                if acknowledgment is not None or dismissal is not None:
                    raise QueueError("HOST_CHECKPOINT_OCCUPIED")
                self._linked_all(action,record,dismissal)
            else:
                if dismissal is not None:
                    raise QueueError("HOST_CHECKPOINT_OCCUPIED")
                self._linked_all(action,acknowledgment,record)
            try:
                fd = os.open(SLOTS[kind],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,
                             0o600,dir_fd=directory_fd)
            except FileExistsError as exc:
                raise QueueError("HOST_CHECKPOINT_OCCUPIED") from exc
            try:
                self._private(os.fstat(fd))
                remaining = memoryview(data)
                while remaining:
                    count = os.write(fd,remaining)
                    if count <= 0:
                        raise QueueError("HOST_CHECKPOINT_STORAGE_ERROR")
                    remaining = remaining[count:]
                os.fsync(fd)
                self._private(os.fstat(fd))
            finally:
                os.close(fd)
            os.fsync(directory_fd)
            self._check_dir(directory_fd)
            if self._read(directory_fd,kind) != record:
                raise QueueError("HOST_CHECKPOINT_CHANGED")
            self._linked_all(self._read(directory_fd,"ACTION"),self._read(directory_fd,"REVIEW_ACK"),
                             self._read(directory_fd,"REVIEW_DISMISS"))
        # Return only after data and directory entry have been synced.
        # Any failure leaves evidence in place; caller MUST NOT send.
        return record
