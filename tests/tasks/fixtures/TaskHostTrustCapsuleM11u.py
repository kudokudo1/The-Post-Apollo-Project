#!/usr/bin/env python3
"""M11u Linux-only, disposable synthetic script-identity capsule.

This is NOT a production host, not a launch-authority credential, and never
accesses a TASKS store. A caller-supplied hash MUST come from an independent
trusted source. A sealed memfd pins the verified synthetic script bytes
against path replacement after read. It does not authenticate Python itself,
the caller, the operating system, or other live task writers.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
import subprocess

FOLDER = "m11u-host-copy"
NAME = "synthetic-host.py"
MARKER = b"# M11U SYNTHETIC HOST ONLY\n"
EXPECTED_OUTPUT = "M11U_SYNTHETIC_OK\n"
MAX_BYTES = 65536


class TrustRefusal(ValueError):
    """Private, constant-string refusal. Never expose paths or script data."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise TrustRefusal(reason)


def _regular_private(s: os.stat_result) -> bool:
    return (stat.S_ISREG(s.st_mode) and s.st_uid == os.geteuid()
            and s.st_nlink == 1 and stat.S_IMODE(s.st_mode) & 0o077 == 0)


def _private_directory(s: os.stat_result) -> bool:
    return (stat.S_ISDIR(s.st_mode) and s.st_uid == os.geteuid()
            and stat.S_IMODE(s.st_mode) & 0o077 == 0)


@dataclass(frozen=True)
class SyntheticSnapshot:
    script: bytes
    sha256: str


def capture_synthetic_script(folder: Path, independent_sha256: str) -> SyntheticSnapshot:
    """Read one exact private synthetic source using directory-relative nofollow.

    The digest is supplied by the trusted caller, never read from the fixture.
    Rejects symlinked directory/leaf, hardlink, loose permissions, missing
    source, changing file identity and unexpectedly large content.
    """
    require(isinstance(folder, Path) and folder.is_absolute()
            and folder.name == FOLDER and ".." not in folder.parts,
            "SYNTHETIC_DIRECTORY_REQUIRED")
    require(type(independent_sha256) is str
            and re.fullmatch(r"[0-9a-f]{64}", independent_sha256) is not None,
            "PINNED_DIGEST_REQUIRED")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    require(bool(nofollow), "NOFOLLOW_UNAVAILABLE")
    directory_fd = -1
    source_fd = -1
    try:
        directory_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | nofollow)
        directory_stat = os.fstat(directory_fd)
        require(_private_directory(directory_stat), "PRIVATE_DIRECTORY_REQUIRED")
        source_before = os.stat(NAME, dir_fd=directory_fd, follow_symlinks=False)
        require(_regular_private(source_before)
                and 0 < source_before.st_size <= MAX_BYTES,
                "PRIVATE_SYNTHETIC_FILE_REQUIRED")
        source_fd = os.open(NAME, os.O_RDONLY | nofollow, dir_fd=directory_fd)
        stat_fd = os.fstat(source_fd)
        require(_regular_private(stat_fd)
                and (stat_fd.st_dev, stat_fd.st_ino)
                == (source_before.st_dev, source_before.st_ino),
                "SOURCE_IDENTITY_CHANGED")
        raw = bytearray()
        while len(raw) <= MAX_BYTES:
            chunk = os.read(source_fd, MAX_BYTES + 1 - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
        stat_after_fd = os.fstat(source_fd)
        stat_after_path = os.stat(NAME, dir_fd=directory_fd, follow_symlinks=False)
        require((stat_fd.st_dev, stat_fd.st_ino, stat_fd.st_size,
                 stat_fd.st_mtime_ns, stat_fd.st_ctime_ns)
                == (stat_after_fd.st_dev, stat_after_fd.st_ino,
                    stat_after_fd.st_size, stat_after_fd.st_mtime_ns,
                    stat_after_fd.st_ctime_ns),
                "SOURCE_CHANGED_WHILE_READING")
        require((stat_fd.st_dev, stat_fd.st_ino)
                == (stat_after_path.st_dev, stat_after_path.st_ino)
                and _regular_private(stat_after_path)
                and len(raw) == stat_fd.st_size and len(raw) <= MAX_BYTES,
                "SOURCE_PATH_CHANGED")
        data = bytes(raw)
        require(data.startswith(MARKER), "NOT_A_SYNTHETIC_SCRIPT")
        actual_sha = hashlib.sha256(data).hexdigest()
        require(hmac.compare_digest(actual_sha, independent_sha256),
                "PINNED_CONTENT_MISMATCH")
        return SyntheticSnapshot(script=data, sha256=actual_sha)
    except (OSError, ValueError) as exc:
        if isinstance(exc, TrustRefusal):
            raise
        raise TrustRefusal("SYNTHETIC_SOURCE_UNAVAILABLE") from None
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if directory_fd >= 0:
            os.close(directory_fd)


def run_sealed_synthetic(snapshot: SyntheticSnapshot) -> str:
    """Run verified bytes from a sealed, inherited Linux memfd; not source path.

    Only a tightly scoped synthetic marker is accepted as a successful reply.
    The fixed root-owned system Python is an explicitly UNATTESTED dependency.
    """
    require(isinstance(snapshot, SyntheticSnapshot)
            and type(snapshot.script) is bytes
            and type(snapshot.sha256) is str
            and len(snapshot.script) <= MAX_BYTES
            and snapshot.script.startswith(MARKER)
            and hmac.compare_digest(
                hashlib.sha256(snapshot.script).hexdigest(), snapshot.sha256),
            "INVALID_PINNED_SNAPSHOT")
    require(hasattr(os, "memfd_create")
            and hasattr(os, "MFD_ALLOW_SEALING")
            and hasattr(fcntl, "F_ADD_SEALS")
            and hasattr(fcntl, "F_SEAL_WRITE"),
            "SEALED_LINUX_MEMFD_REQUIRED")
    # A test-runner toolcache interpreter may be writable by that user.
    # Never weaken the refusal: use a fixed system path, not PATH or
    # sys.executable. This is still NOT interpreter binary attestation.
    try:
        interpreter = Path("/usr/bin/python3").resolve(strict=True)
        istat = interpreter.stat()
    except OSError:
        raise TrustRefusal("INTERPRETER_UNAVAILABLE") from None
    require(interpreter.is_absolute() and interpreter.is_file()
            and interpreter.parent == Path("/usr/bin")
            and stat.S_ISREG(istat.st_mode)
            and istat.st_uid == 0
            and stat.S_IMODE(istat.st_mode) & 0o022 == 0,
            "UNTRUSTED_SYSTEM_INTERPRETER")
    fd = -1
    try:
        fd = os.memfd_create("m11u-synthetic-capsule",
                             os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        pos = 0
        while pos < len(snapshot.script):
            wrote = os.write(fd, snapshot.script[pos:])
            require(wrote > 0, "CAPSULE_WRITE_FAILED")
            pos += wrote
        os.lseek(fd, 0, os.SEEK_SET)
        seals = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_SHRINK
                 | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SEAL)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        require(fcntl.fcntl(fd, fcntl.F_GET_SEALS) & seals == seals,
                "CAPSULE_NOT_SEALED")
        proc = subprocess.run(
            [str(interpreter), "-I", "-S", "-B", "/proc/self/fd/" + str(fd)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=5, pass_fds=(fd,),
            env={"PATH": "/usr/bin:/bin", "LANG": "C",
                 "PYTHONNOUSERSITE": "1"}, check=False)
        require(proc.returncode == 0 and proc.stdout == EXPECTED_OUTPUT
                and proc.stderr == "", "SYNTHETIC_HOST_REFUSED")
        return "SYNTHETIC_CAPSULE_OK"
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        if isinstance(exc, TrustRefusal):
            raise
        raise TrustRefusal("SYNTHETIC_LAUNCH_UNAVAILABLE") from None
    finally:
        if fd >= 0:
            os.close(fd)
