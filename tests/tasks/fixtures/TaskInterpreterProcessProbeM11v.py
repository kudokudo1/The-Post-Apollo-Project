#!/usr/bin/env python3
"""M11v Linux-only synthetic interpreter and child-process provenance probe.

NOT a production TASKS host. This accepts only M11u's explicit, synthetic
script snapshot and an independently supplied interpreter SHA-256 pin.
The observed PID/executable and one request/reply are correlations, NOT
authorization against an attacker controlling the launching Python process.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess

HERE = Path(__file__).resolve().parent
CAPSULE_FILE = HERE / "TaskHostTrustCapsuleM11u.py"
_spec = importlib.util.spec_from_file_location("m11v_m11u_capsule", CAPSULE_FILE)
capsule = importlib.util.module_from_spec(_spec)
import sys
sys.modules[_spec.name] = capsule
_spec.loader.exec_module(capsule)

INTERPRETER = Path("/usr/bin/python3")
MAX_INTERPRETER = 32 * 1024 * 1024
MAX_REPLY = 4096
SYNTHETIC_EPOCH = 7
CMD = "M11V_SYNTHETIC_PING"


class ProcessRefusal(ValueError):
    """A redacted, fixed error that does not expose user paths or content."""


def require(ok, reason):
    if not ok:
        raise ProcessRefusal(reason)


@dataclass(frozen=True)
class InterpreterPin:
    path: str
    digest: str
    device: int
    inode: int


def _system_path() -> Path:
    """Check root-controlled path ancestry and resolved binary metadata."""
    try:
        root = INTERPRETER.resolve(strict=True)
        require(root.is_absolute() and root.parent == Path("/usr/bin"),
                "SYSTEM_INTERPRETER_REQUIRED")
        for ancestor in (Path("/"), Path("/usr"), Path("/usr/bin")):
            st = ancestor.lstat()
            require(stat.S_ISDIR(st.st_mode) and st.st_uid == 0
                    and stat.S_IMODE(st.st_mode) & 0o022 == 0,
                    "WRITABLE_INTERPRETER_ANCESTOR")
        st = root.lstat()
        require(stat.S_ISREG(st.st_mode) and st.st_uid == 0
                and stat.S_IMODE(st.st_mode) & 0o022 == 0
                and st.st_nlink >= 1 and 0 < st.st_size <= MAX_INTERPRETER,
                "UNTRUSTED_SYSTEM_INTERPRETER")
        return root
    except OSError:
        raise ProcessRefusal("SYSTEM_INTERPRETER_UNAVAILABLE") from None


def pinned_interpreter(expected_sha256: str) -> InterpreterPin:
    """Capture system-interpreter hash via descriptor; pin is EXTERNAL input.

    Caller must obtain expected digest from a separately trusted source,
    not by hashing the same untrusted deployment at decision time.
    """
    require(type(expected_sha256) is str
            and re.fullmatch("[0-9a-f]{64}", expected_sha256) is not None,
            "INTERPRETER_PIN_REQUIRED")
    path = _system_path()
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 0
                and stat.S_IMODE(before.st_mode) & 0o022 == 0
                and 0 < before.st_size <= MAX_INTERPRETER,
                "INTERPRETER_METADATA_CHANGED")
        h = hashlib.sha256()
        count = 0
        while count <= MAX_INTERPRETER:
            chunk = os.read(fd, min(131072, MAX_INTERPRETER + 1 - count))
            if not chunk:
                break
            h.update(chunk)
            count += len(chunk)
        after = os.fstat(fd)
        now = path.lstat()
        required = lambda s: (s.st_dev, s.st_ino, s.st_size,
                              s.st_mtime_ns, s.st_ctime_ns)
        require(count == before.st_size and count <= MAX_INTERPRETER
                and required(before) == required(after)
                and required(before) == required(now),
                "INTERPRETER_CHANGED_DURING_PIN")
        require(hmac.compare_digest(h.hexdigest(), expected_sha256),
                "INTERPRETER_DIGEST_MISMATCH")
        return InterpreterPin(str(path), expected_sha256,
                              before.st_dev, before.st_ino)
    except OSError:
        raise ProcessRefusal("INTERPRETER_READ_UNAVAILABLE") from None
    finally:
        if fd >= 0:
            os.close(fd)


def _observed_executable_identity(pid: int):
    """Read kernel /proc executable inode; not child-supplied PID assertions."""
    st = os.stat("/proc/" + str(pid) + "/exe")
    return st.st_dev, st.st_ino


def _start_ticks(pid: int) -> int:
    # /proc/pid/stat field 22; fields 3.. start AFTER the last ')' of comm.
    data = Path("/proc/" + str(pid) + "/stat").read_text()
    stop = data.rfind(")")
    require(stop > 0, "MALFORMED_PROC_STAT")
    fields = data[stop + 2:].split()
    require(len(fields) >= 20, "MALFORMED_PROC_STAT")
    return int(fields[19])


def run_bound_synthetic(snapshot: capsule.SyntheticSnapshot,
                        interpreter: InterpreterPin,
                        *, expected_epoch=SYNTHETIC_EPOCH) -> dict:
    """Observe one Linux child, then allow exactly one synthetic exchange.

    A stable PIDFD and exact /proc executable inode bind the observed process.
    Session nonce only correlates messages to the request; it is not proof
    against child-process impersonation or a compromised parent.
    """
    require(isinstance(snapshot, capsule.SyntheticSnapshot)
            and type(snapshot.script) is bytes
            and snapshot.script.startswith(capsule.MARKER)
            and len(snapshot.script) <= capsule.MAX_BYTES
            and hmac.compare_digest(
                hashlib.sha256(snapshot.script).hexdigest(), snapshot.sha256),
            "INVALID_SYNTHETIC_SNAPSHOT")
    require(isinstance(interpreter, InterpreterPin)
            and type(expected_epoch) is int and expected_epoch == SYNTHETIC_EPOCH,
            "INVALID_SYNTHETIC_OWNER_EPOCH")
    require(hasattr(os, "pidfd_open") and hasattr(os, "memfd_create"),
            "LINUX_PROC_FEATURES_REQUIRED")
    # A preceding pin is not perpetual trust: verify it anew before spawn.
    refreshed = pinned_interpreter(interpreter.digest)
    require(refreshed == interpreter, "STALE_INTERPRETER_PIN")
    memfd = -1
    pidfd = -1
    proc = None
    try:
        memfd = os.memfd_create("m11v-synthetic-code",
              os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        wrote = 0
        while wrote < len(snapshot.script):
            n = os.write(memfd, snapshot.script[wrote:])
            require(n > 0, "SYNTHETIC_MEMFD_WRITE_FAILURE")
            wrote += n
        import fcntl
        seals = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW
                 | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        fcntl.fcntl(memfd, fcntl.F_ADD_SEALS, seals)
        require(fcntl.fcntl(memfd, fcntl.F_GET_SEALS) & seals == seals,
                "SYNTHETIC_MEMFD_UNSEALED")
        proc = subprocess.Popen(
            [interpreter.path, "-I", "-S", "-B", "/proc/self/fd/" + str(memfd)],
            pass_fds=(memfd,), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env={"PATH": "/usr/bin:/bin", "LANG": "C",
                            "PYTHONNOUSERSITE": "1"})
        pidfd = os.pidfd_open(proc.pid, 0)
        require(proc.poll() is None, "SYNTHETIC_CHILD_EXITED")
        uid = os.stat("/proc/" + str(proc.pid)).st_uid
        begin_ticks = _start_ticks(proc.pid)
        require(uid == os.geteuid()
                and _observed_executable_identity(proc.pid)
                == (interpreter.device, interpreter.inode),
                "SYNTHETIC_CHILD_EXECUTABLE_MISMATCH")
        # The challenge is generated by the observing parent, not stdout.
        challenge = secrets.token_hex(24)
        request = {"protocol": 1, "kind": "ping", "requestId": 1,
                   "epoch": expected_epoch, "challenge": challenge}
        stdout, stderr = proc.communicate(json.dumps(request) + "\n",
                                          timeout=4)
        require(proc.returncode == 0 and not stderr
                and len(stdout.encode("utf-8")) <= MAX_REPLY,
                "SYNTHETIC_CHILD_OUTPUT_REFUSED")
        lines = stdout.splitlines()
        require(len(lines) == 2, "SYNTHETIC_REPLY_FRAMING_REFUSED")
        def no_duplicates(pairs):
            result = {}
            for k, v in pairs:
                require(k not in result, "DUPLICATE_SYNTHETIC_REPLY_KEY")
                result[k] = v
            return result
        hello, reply = (json.loads(line, object_pairs_hook=no_duplicates)
                        for line in lines)
        require(type(hello) is dict and type(reply) is dict
                and set(hello) == {"protocol","kind","sessionId"}
                and hello["protocol"] == 1 and hello["kind"] == "hello"
                and type(hello["sessionId"]) is str
                and re.fullmatch("[0-9a-f]{48}",hello["sessionId"]),
                "SYNTHETIC_SESSION_HELLO_REFUSED")
        require(set(reply) == {"protocol","kind","sessionId",
                               "requestId","epoch","challenge","status"}
                and reply["protocol"] == 1 and reply["kind"] == "reply"
                and type(reply["requestId"]) is int and reply["requestId"] == 1
                and type(reply["epoch"]) is int and reply["epoch"] == expected_epoch
                and reply["status"] == CMD
                and type(reply["sessionId"]) is str
                and hmac.compare_digest(reply["sessionId"],hello["sessionId"])
                and type(reply["challenge"]) is str
                and hmac.compare_digest(reply["challenge"],challenge),
                "SYNTHETIC_SESSION_REPLY_REFUSED")
        # PIDFD was acquired before exchange; this start time came from the
        # same pre-exchange process. No claimed post-exit /proc observation.
        require(begin_ticks > 0, "SYNTHETIC_CHILD_START_UNKNOWN")
        return {"status":"SYNTHETIC_PROCESS_BOUND",
                "syntheticOnly":True,"realTaskWriterAuthorized":False,
                "interpreterPinMatches":True,
                "kernelExecutableMatches":True,
                "pidfdWasOpened":True,
                "sessionRequestMatched":True}
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        if isinstance(exc, ProcessRefusal):
            raise
        raise ProcessRefusal("SYNTHETIC_PROCESS_UNAVAILABLE") from None
    finally:
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        if pidfd >= 0:
            os.close(pidfd)
        if memfd >= 0:
            os.close(memfd)
