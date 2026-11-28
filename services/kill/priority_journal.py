"""Local write-ahead custody for KILL priority changes.

Storage primitive only: no CLI, dispatch, auto-restore, permission grant or
startup IO. Caller supplies an already provisioned private state directory.
A pending record is uncertain after restart and cannot be overwritten.
Same-user storage is not a security boundary against that same user.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from priority_control import nice_value, reversible_range

MAX_BYTES = 8192
SCHEMA = "post-apollo-kill-priority-journal-v1"


class JournalRefused(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise JournalRefused(message)


def scope():
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    require(str(uuid.UUID(boot)) == boot, "invalid boot identity")
    return {"boot": boot, "pidNamespace": os.readlink("/proc/self/ns/pid"),
            "userNamespace": os.readlink("/proc/self/ns/user"), "uid": os.geteuid()}


def identity(pid, birth, comm):
    require(type(pid) is int and 1 < pid < 2**31
            and type(birth) is int and 0 < birth < 2**53
            and type(comm) is str and 0 < len(comm.encode("utf-8")) <= 64
            and "\x00" not in comm, "invalid target")
    return {"pid": pid, "startTicks": birth, "comm": comm}


def snapshot(value, owner):
    require(type(value) is dict and set(value) == {"nice", "soft", "hard", "scheduler", "uid"}
            and nice_value(value["nice"])
            and type(value["uid"]) is int and value["uid"] == owner
            and type(value["scheduler"]) is int and value["scheduler"] in (0, 3)
            and type(value["soft"]) is int and 0 <= value["soft"] <= 40
            and type(value["hard"]) is int
            and (value["hard"] == -1 or value["soft"] <= value["hard"] <= 40),
            "invalid captured priority evidence")
    return dict(value)


def encode(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    require(len(raw) <= MAX_BYTES, "oversize journal")
    return raw


def filename(context, target):
    return hashlib.sha256(encode([context, target])).hexdigest() + ".json"


def validate(record, context, target):
    require(type(record) is dict and set(record) == {
        "schema", "scope", "target", "token", "phase", "operation",
        "original", "before", "requested", "after"}
        and record["schema"] == SCHEMA and record["scope"] == context
        and record["target"] == target, "journal identity mismatch")
    token = record["token"]
    require(type(token) is str and str(uuid.UUID(token)) == token, "invalid journal token")
    phase, operation = record["phase"], record["operation"]
    require(phase in ("pending_unknown", "managed", "restored")
            and operation in ("apply", "restore"), "invalid journal phase")
    before = snapshot(record["before"], context["uid"])
    original, requested = record["original"], record["requested"]
    require(reversible_range(original, before["nice"], requested, before["soft"])
            and requested != before["nice"]
            and (operation != "restore" or requested == original), "invalid journal intent")
    if phase == "pending_unknown":
        require(record["after"] is None, "pending record has an outcome")
    else:
        after = snapshot(record["after"], context["uid"])
        require(after == dict(before, nice=requested)
                and phase == ("restored" if requested == original else "managed"),
                "invalid journal readback")
    return record


class PriorityJournal:
    def __init__(self, directory):
        self.directory = Path(directory)
        require(self.directory.is_absolute(), "absolute state directory required")

    @contextlib.contextmanager
    def _locked(self):
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
                    "private owned state directory required")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield fd
        finally:
            os.close(fd)

    @staticmethod
    def _read(fd, context, target):
        name = filename(context, target)
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            return None
        with os.fdopen(handle, "rb") as source:
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == context["uid"]
                    and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600
                    and 0 < info.st_size <= MAX_BYTES, "unsafe journal file")
            raw = source.read(MAX_BYTES + 1)
        require(0 < len(raw) <= MAX_BYTES, "invalid journal size")
        try:
            record = json.loads(raw)
            require(raw == encode(record), "noncanonical journal")
            return validate(record, context, target)
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise JournalRefused("invalid existing journal") from exc

    @staticmethod
    def _write(fd, context, target, record):
        validate(record, context, target)
        raw = encode(record)
        name = filename(context, target)
        temp = ".tmp-" + uuid.uuid4().hex
        handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=fd)
        try:
            with os.fdopen(handle, "wb") as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temp, dir_fd=fd)
            except FileNotFoundError:
                pass

    def read(self, pid, birth, comm):
        """Return exact current-boot custody; never repair or replay."""
        context, target = scope(), identity(pid, birth, comm)
        with self._locked() as fd:
            return self._read(fd, context, target)

    def mark(self, pid, birth, comm, *, operation, original, before, requested):
        """Durably mark one future attempt before any kernel write."""
        context, target = scope(), identity(pid, birth, comm)
        before = snapshot(before, context["uid"])
        with self._locked() as fd:
            prior = self._read(fd, context, target)
            if prior is None or prior["phase"] == "restored":
                require(operation == "apply" and original == before["nice"],
                        "fresh original required")
            else:
                require(prior["phase"] == "managed" and prior["original"] == original
                        and prior["after"] == before, "unresolved or changed ownership")
            record = dict(schema=SCHEMA, scope=context, target=target,
                          token=str(uuid.uuid4()), phase="pending_unknown",
                          operation=operation, original=original, before=before,
                          requested=requested, after=None)
            self._write(fd, context, target, record)
            return record["token"]

    def finish(self, pid, birth, comm, *, token, after):
        """Commit verified readback for the exact marked attempt only."""
        context, target = scope(), identity(pid, birth, comm)
        after = snapshot(after, context["uid"])
        with self._locked() as fd:
            prior = self._read(fd, context, target)
            require(prior is not None and prior["phase"] == "pending_unknown"
                    and prior["token"] == token, "unmatched journal completion")
            require(after == dict(prior["before"], nice=prior["requested"]),
                    "readback does not match marked intent")
            record = dict(prior, after=after, phase="restored"
                          if after["nice"] == prior["original"] else "managed")
            self._write(fd, context, target, record)
            return record
