"""Disposable archive/fence publication experiment; never an installed writer.

Only private marked temporary fixtures; no production paths, deletion, recovery
clearance, authorization, helper invocation or kernel effects. Linux dirfd/flock.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
from contextlib import contextmanager
from reclaim_custody import PIN, plan

LIMIT = 65536
MARKER = b"DISPOSABLE_RECLAIM_CUSTODY_V2\n"
ARCHIVE = "archive.json"
FENCE = "external-fence"
PREPARED = "prepared.json"

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"

def require(condition, message):
    if not condition:
        raise ValueError(message)

def private_dir(fd):
    s = os.fstat(fd)
    require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.geteuid()
            and stat.S_IMODE(s.st_mode) == 0o700, "unsafe fixture directory")

def present(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False

def read(fd, name):
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                   dir_fd=fd)
    try:
        s = os.fstat(item)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == os.geteuid()
                and stat.S_IMODE(s.st_mode) == 0o600 and s.st_nlink == 1
                and 0 < s.st_size <= LIMIT, "unsafe fixture record")
        with os.fdopen(item, "rb", closefd=False) as stream:
            data = stream.read(LIMIT + 1)
        after = os.fstat(item)
        require(len(data) == s.st_size and
                (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                "changed fixture record")
        return data
    finally:
        os.close(item)

def decode(data):
    obj = json.loads(data)
    require(type(obj) is dict and canonical(obj) == data, "noncanonical fixture record")
    return obj

@contextmanager
def locked(root):
    root = Path(root)
    require(root.is_absolute() and root.name.startswith("cpu-memory-reclaim-fixture-"),
            "not a disposable fixture path")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        private_dir(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(read(fd, "fixture-marker") == MARKER, "fixture marker mismatch")
        yield fd
    finally:
        os.close(fd)

def write_once(fd, name, data):
    require(type(data) is bytes and 0 < len(data) <= LIMIT, "record size invalid")
    item = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                   0o600, dir_fd=fd)
    try:
        view = memoryview(data)
        while view:
            n = os.write(item, view)
            require(n > 0, "short write")
            view = view[n:]
        os.fsync(item)
    finally:
        os.close(item)
    os.fsync(fd)
    require(read(fd, name) == data, "publication readback mismatch")

def resync(fd, name, expected):
    require(read(fd, name) == expected, "archive changed")
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                   dir_fd=fd)
    try:
        os.fsync(item)
    finally:
        os.close(item)
    os.fsync(fd)
    require(read(fd, name) == expected, "archive changed after sync")

def archive_digest(bundle):
    return hashlib.sha256(canonical(bundle)[:-1]).hexdigest()

def prepared_for(bundle):
    return {"version": 2, "state": "PREPARED", "archive_digest": archive_digest(bundle),
            "boot_id": bundle["boot_id"], "can_execute": False, "can_clear": False}

def publish(root, helper, facts, boundary=lambda stage: None):
    """Publish a synthetic archive before a simulated external fence.
    The callback is exclusively for fault injection in the disposable tests.
    Any existing archive/fence refuses a second publication, even if partial.
    """
    with locked(root) as fd:
        require(not present(fd, ARCHIVE) and not present(fd, FENCE), "existing custody evidence")
        proposal = plan(helper, **facts)
        require(proposal.get("state") == "ARCHIVE_CUSTODY_PROPOSED"
                and proposal.get("can_execute") is False, "proposal refused")
        bundle = proposal["bundle"]
        require(bundle["candidate_blob"] == PIN and bundle["version"] == 2
                and archive_digest(bundle) == proposal["archive_digest"], "proposal digest mismatch")
        archive = canonical(bundle)
        write_once(fd, ARCHIVE, archive)
        resync(fd, ARCHIVE, archive)
        boundary("ARCHIVE_DURABLE")
        # Re-evaluate synthetic observations; not protected live provenance.
        require(plan(helper, **facts) == proposal, "proposal changed before fence")
        os.mkdir(FENCE, 0o700, dir_fd=fd)
        os.fsync(fd)
        boundary("FENCE_DIRECTORY_DURABLE")
        child = os.open(FENCE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=fd)
        try:
            private_dir(child)
            write_once(child, PREPARED, canonical(prepared_for(bundle)))
        finally:
            os.close(child)
        boundary("PREPARED_DURABLE")
        require(read(fd, ARCHIVE) == archive, "archive changed after fence")
        return {"state": "FIXTURE_PREPARED", "can_execute": False, "can_clear": False}

def inspect(root):
    """Read-only classification; no missing evidence permits recovery effects."""
    blocked = {"state": "RECOVERY_REQUIRED", "can_execute": False, "can_clear": False}
    try:
        with locked(root) as fd:
            archive_exists = present(fd, ARCHIVE)
            fence_exists = present(fd, FENCE)
            if not archive_exists and not fence_exists:
                return dict(blocked, state="EMPTY_FIXTURE", code="NO_EVIDENCE")
            if not archive_exists:
                return dict(blocked, code="ARCHIVE_MISSING")
            bundle = decode(read(fd, ARCHIVE))
            require(bundle.get("version") == 2 and bundle.get("state") == "RECLAIM_ARCHIVE_PROPOSAL"
                    and bundle.get("candidate_blob") == PIN, "archive schema mismatch")
            if not fence_exists:
                return dict(blocked, code="ARCHIVE_ONLY")
            child = os.open(FENCE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=fd)
            try:
                private_dir(child)
                if not present(child, PREPARED):
                    return dict(blocked, code="FENCE_INCOMPLETE")
                marker = decode(read(child, PREPARED))
                require(canonical(marker) == canonical(prepared_for(bundle)), "marker mismatch")
                return dict(blocked, code="PREPARED_REVIEW_REQUIRED")
            finally:
                os.close(child)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return dict(blocked, code="EVIDENCE_UNVERIFIED")
