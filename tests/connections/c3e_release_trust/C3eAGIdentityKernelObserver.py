#!/usr/bin/env python3
"""C3e-AG: real Linux /proc Identity process observer, deny-only CI candidate.

A disposable root GitHub runner can observe real kernel process state and
root-owned script bytes. The optional C4b official Silverblue guest mode must
be explicitly invoked by its owner later; this C3e source does not alter C4b.
Even an accurate observation is NOT a trusted remote witness, signed release
admission, independently protected issuer or user consent. No authorization.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys

SCHEMA = "postapollo.connections.c3eag-identity-kernel-observation.ci-v1"
C4B_UNIT = "post-apollo-identity-silverblue-ci.service"
C4B_EXE = "/run/postapollo-identity-silverblue-ci-only/ci-python3"
C4B_SCRIPT = "/usr/libexec/post-apollo/identity/identity-gateway-ci"
C4B_CGROUP = "/system.slice/" + C4B_UNIT
C4B_SELINUX = "system_u:system_r:postapollo_identity_ci_t:s0"
FIXTURE_UNIT = "c3eag-disposable-fixture"
FIXTURE_PREFIX = "c3eag-ci-"
MAX_PROC = 8192
MAX_SCRIPT = 256 * 1024
MAX_EXE = 16 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
EXPECTED = frozenset((
    "pid", "startTicks", "uid", "gid", "unit", "exePath", "exeSha256",
    "scriptPath", "entrypointSha256", "cgroup", "selinux",
))
NEGATIVE = {
    "independentInstalledHostAttested": False,
    "signedHostOriginAuthenticated": False,
    "operatorReleaseRootEnrolled": False,
    "externallyProtectedChallengeIssuerVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """Fail-closed kernel observation, never an admission grant."""

def _deny(code):
    raise Refused(code)

def _read(path: Path, maximum=MAX_PROC):
    try:
        with path.open("rb") as source:
            value = source.read(maximum + 1)
    except (OSError, ValueError) as exc:
        raise Refused("C3EAG_KERNEL_RECORD_UNAVAILABLE") from exc
    if not value or len(value) > maximum:
        _deny("C3EAG_KERNEL_RECORD_BOUNDS_REFUSED")
    return value

def _start(pid):
    try:
        raw = _read(Path("/proc") / str(pid) / "stat").decode("ascii")
        # Linux /proc/<pid>/stat field 22 is index 19 after the final ') '.
        ticks = raw.rsplit(") ", 1)[1].split()[19]
        if not ticks.isascii() or not ticks.isdecimal() or int(ticks) <= 0:
            _deny("C3EAG_KERNEL_START_INVALID")
        return int(ticks)
    except (UnicodeError, IndexError, ValueError) as exc:
        raise Refused("C3EAG_KERNEL_START_UNAVAILABLE") from exc

def _identity(pid):
    raw = _read(Path(f"/proc/{pid}/status")).decode("ascii")
    records = {}
    for line in raw.splitlines():
        if line.startswith(("Uid:", "Gid:")):
            name, values = line.split(":", 1)
            if name in records:
                _deny("C3EAG_KERNEL_DUPLICATE_IDENTITY")
            parts = values.split()
            if len(parts) != 4 or any(not v.isdecimal() for v in parts):
                _deny("C3EAG_KERNEL_IDENTITY_MALFORMED")
            records[name] = tuple(map(int, parts))
    if set(records) != {"Uid", "Gid"}:
        _deny("C3EAG_KERNEL_IDENTITY_MISSING")
    return records

def _cgroup(pid):
    raw = _read(Path(f"/proc/{pid}/cgroup")).decode("utf-8")
    rows = raw.splitlines()
    if len(rows) != 1 or not rows[0].startswith("0::"):
        _deny("C3EAG_CGROUP_V2_REQUIRED")
    value = rows[0][3:]
    if not value.startswith("/") or "\x00" in value or len(value) > 2048:
        _deny("C3EAG_KERNEL_CGROUP_INVALID")
    return value

def _selinux_or_lsm(pid):
    raw = _read(Path(f"/proc/{pid}/attr/current"), 512)
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if raw.endswith(b"\x00"):
        raw = raw[:-1]
    if not raw or b"\n" in raw or b"\x00" in raw:
        _deny("C3EAG_KERNEL_LSM_INVALID")
    try:
        return raw.decode("ascii")
    except UnicodeError as exc:
        raise Refused("C3EAG_KERNEL_LSM_INVALID") from exc

def _safe_path(path: Path):
    if not path.is_absolute():
        _deny("C3EAG_SCRIPT_PATH_NOT_ABSOLUTE")
    cursor = path.parent
    while True:
        try:
            st = os.lstat(cursor)
        except OSError as exc:
            raise Refused("C3EAG_SCRIPT_PARENT_UNAVAILABLE") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or
                stat.S_IMODE(st.st_mode) & 0o022):
            _deny("C3EAG_SCRIPT_PARENT_UNSAFE")
        if cursor == Path("/"):
            break
        cursor = cursor.parent

def _hash_fd(fd, maximum):
    before = os.fstat(fd)
    if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum):
        _deny("C3EAG_UNSAFE_EXECUTABLE_BYTES")
    digest = hashlib.sha256()
    size = 0
    while True:
        data = os.read(fd, min(65536, maximum + 1 - size))
        if not data:
            break
        size += len(data)
        if size > maximum:
            _deny("C3EAG_EXECUTABLE_TOO_LARGE")
        digest.update(data)
    after = os.fstat(fd)
    if size != before.st_size or (
            before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns):
        _deny("C3EAG_EXECUTABLE_CHANGED_DURING_READ")
    return digest.hexdigest(), before

def _executable(pid, expected):
    fd = None
    try:
        fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
        observed, st = _hash_fd(fd, MAX_EXE)
        pinned = os.stat(expected["exePath"])
        if (st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or
                stat.S_IMODE(st.st_mode) & 0o022):
            _deny("C3EAG_EXECUTABLE_OWNER_OR_MODE_UNSAFE")
        if (st.st_dev, st.st_ino) != (pinned.st_dev, pinned.st_ino):
            _deny("C3EAG_KERNEL_INTERPRETER_INODE_MISMATCH")
        if not hmac.compare_digest(observed, expected["exeSha256"]):
            _deny("C3EAG_KERNEL_INTERPRETER_HASH_MISMATCH")
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
                st.st_ctime_ns)
    except OSError as exc:
        raise Refused("C3EAG_KERNEL_INTERPRETER_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)

def _script(expected):
    path = Path(expected["scriptPath"])
    _safe_path(path)
    fd = None
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        observed, st = _hash_fd(fd, MAX_SCRIPT)
        if (st.st_uid != 0 or st.st_gid != 0 or
                st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o555):
            _deny("C3EAG_SCRIPT_NOT_ROOT_OWNED_IMMUTABLE")
        if not hmac.compare_digest(observed, expected["entrypointSha256"]):
            _deny("C3EAG_SCRIPT_HASH_MISMATCH")
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
                st.st_ctime_ns)
    except OSError as exc:
        raise Refused("C3EAG_SCRIPT_OPEN_REFUSED") from exc
    finally:
        if fd is not None:
            os.close(fd)

def _cmdline(pid, expected):
    raw = _read(Path(f"/proc/{pid}/cmdline"), 4096)
    if not raw.endswith(b"\x00"):
        _deny("C3EAG_CMDLINE_INVALID")
    fields = raw[:-1].split(b"\x00")
    if (len(fields) != 4 or fields[1:3] != [b"-I", b"-B"] or
            os.fsdecode(fields[3]) != expected["scriptPath"] or
            os.path.realpath(os.fsdecode(fields[0])) !=
                os.path.realpath(expected["exePath"])):
        _deny("C3EAG_CMDLINE_WRONG_GATEWAY")
    return raw

def _scope(expected, mode):
    if mode == "fixture":
        p = Path(expected["scriptPath"])
        if (expected["unit"] != FIXTURE_UNIT or
                p.parent.parent != Path("/run") or
                not p.parent.name.startswith(FIXTURE_PREFIX) or
                p.name != "identity-gateway-ci" or
                expected["exePath"] != "/usr/bin/python3"):
            _deny("C3EAG_FIXTURE_SCOPE_REFUSED")
    elif mode == "c4b-guest-candidate":
        if (expected["unit"] != C4B_UNIT or
                expected["scriptPath"] != C4B_SCRIPT or
                expected["exePath"] != C4B_EXE or
                expected["cgroup"] != C4B_CGROUP or
                expected["selinux"] != C4B_SELINUX or
                os.environ.get("POST_APOLLO_C4B_TEST_GUEST") != "1" or
                not Path("/run/ostree-booted").exists() or
                _read(Path("/sys/fs/selinux/enforce"), 8).strip() != b"1"):
            _deny("C3EAG_REAL_C4B_GUEST_SCOPE_REFUSED")
    else:
        _deny("C3EAG_UNKNOWN_OBSERVATION_MODE")

def _main_pid_from_systemd():
    try:
        command = subprocess.run(
            ["systemctl", "show", C4B_UNIT,
             "--property=MainPID", "--property=ActiveState",
             "--property=ControlGroup"],
            capture_output=True, text=True, timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("C3EAG_SYSTEMD_READ_ONLY_STATUS_UNAVAILABLE") from exc
    if command.returncode != 0 or len(command.stdout) > 1024:
        _deny("C3EAG_SYSTEMD_STATUS_REFUSED")
    values = {}
    for line in command.stdout.splitlines():
        if "=" not in line:
            _deny("C3EAG_SYSTEMD_STATUS_REFUSED")
        k, v = line.split("=", 1)
        if k in values:
            _deny("C3EAG_SYSTEMD_DUPLICATE_PROPERTY")
        values[k] = v
    if set(values) != {"MainPID", "ActiveState", "ControlGroup"}:
        _deny("C3EAG_SYSTEMD_REQUIRED_PROPERTIES_MISSING")
    if (not values["MainPID"].isdecimal() or
            values["ActiveState"] != "active" or
            values["ControlGroup"] != C4B_CGROUP):
        _deny("C3EAG_SYSTEMD_WRONG_INSTALLED_SERVICE")
    return int(values["MainPID"])

def observe_ci_only(*, expected: dict, mode="fixture"):
    """Read genuine kernel state but never trust its origin beyond this CI host.

    Every expected value still comes from a caller; actual signed RPM release
    approval and remote trusted-host provenance remain separate dependencies.
    """
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3EAG_DISPOSABLE_ROOT_GITHUB_CI_REQUIRED")
    if type(expected) is not dict or set(expected) != EXPECTED:
        _deny("C3EAG_EXACT_EXPECTED_SNAPSHOT_REQUIRED")
    pins = dict(expected)
    for k in ("pid", "startTicks", "uid", "gid"):
        if type(pins[k]) is not int or not 0 < pins[k] < 2**63:
            _deny("C3EAG_EXPECTED_KERNEL_IDENTITY_INVALID")
    if pins["pid"] <= 1 or pins["uid"] <= 0 or pins["gid"] <= 0:
        _deny("C3EAG_NONROOT_SERVICE_REQUIRED")
    for k in ("unit", "exePath", "scriptPath", "cgroup", "selinux"):
        if type(pins[k]) is not str or not pins[k] or len(pins[k]) > 512:
            _deny("C3EAG_EXPECTED_STRING_INVALID")
    for k in ("exeSha256", "entrypointSha256"):
        if type(pins[k]) is not str or SHA.fullmatch(pins[k]) is None:
            _deny("C3EAG_EXPECTED_DIGEST_INVALID")
    _scope(pins, mode)
    pid = pins["pid"]
    try:
        fd = os.pidfd_open(pid, 0)
    except (AttributeError, OSError) as exc:
        raise Refused("C3EAG_PIDFD_UNAVAILABLE") from exc
    try:
        poll = select.poll()
        poll.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
        if poll.poll(0):
            _deny("C3EAG_PROCESS_ALREADY_EXITED")
        if mode == "c4b-guest-candidate" and _main_pid_from_systemd() != pid:
            _deny("C3EAG_SYSTEMD_MAIN_PID_MISMATCH")
        if _start(pid) != pins["startTicks"]:
            _deny("C3EAG_PROCESS_START_MISMATCH")
        identity = _identity(pid)
        if (identity["Uid"] != (pins["uid"],) * 4 or
                identity["Gid"] != (pins["gid"],) * 4):
            _deny("C3EAG_KERNEL_UID_GID_MISMATCH")
        if _cgroup(pid) != pins["cgroup"]:
            _deny("C3EAG_KERNEL_CGROUP_MISMATCH")
        if _selinux_or_lsm(pid) != pins["selinux"]:
            _deny("C3EAG_KERNEL_LSM_MISMATCH")
        commandline = _cmdline(pid, pins)
        interpreter_inode = _executable(pid, pins)
        script_inode = _script(pins)
        process_exe_stat = os.stat(f"/proc/{pid}/exe")
        script_stat = os.stat(pins["scriptPath"])
        if ((process_exe_stat.st_dev, process_exe_stat.st_ino,
             process_exe_stat.st_size, process_exe_stat.st_mtime_ns,
             process_exe_stat.st_ctime_ns) != interpreter_inode or
                (script_stat.st_dev, script_stat.st_ino, script_stat.st_size,
                 script_stat.st_mtime_ns, script_stat.st_ctime_ns) != script_inode or
                _start(pid) != pins["startTicks"] or
                _identity(pid) != identity or
                _cgroup(pid) != pins["cgroup"] or
                _selinux_or_lsm(pid) != pins["selinux"] or
                _cmdline(pid, pins) != commandline or poll.poll(0)):
            _deny("C3EAG_PROCESS_CHANGED_DURING_OBSERVATION")
        if mode == "c4b-guest-candidate" and _main_pid_from_systemd() != pid:
            _deny("C3EAG_SYSTEMD_MAIN_PID_CHANGED")
    except OSError as exc:
        raise Refused("C3EAG_PROCESS_CHANGED_OR_MISSING") from exc
    finally:
        os.close(fd)
    return {
        "schema": SCHEMA,
        "realLinuxPidAndExecutableObservedInDisposableCI": True,
        "kernelProcessFieldsMatchCallerPinsInCI": True,
        "sourceScriptFileMatchesCallerPinInCI": True,
        "observedC4bGuestCandidateNotAttested": mode == "c4b-guest-candidate",
        **NEGATIVE,
    }
