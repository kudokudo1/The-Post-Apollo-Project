#!/usr/bin/env python3
"""C3e-P: CI-only read-only Linux observation of a LIVE Python-script process.

C3e-O validates the existing C3d signed RPM's Python host bytes. C3e-P
measures the corresponding script FILE while a real process is running,
checks that process's kernel PID/start/UID/GID/interpreter and exact cmdline,
and compares script bytes to a separately pinned signed-payload SHA-256.

IMPORTANT: /proc/PID/cmdline is mutable process memory. A matching script
file is not proof of which Python code is loaded, of package installation
or of a secure guest-to-verifier attestation. Output is *observed CI evidence*
with every grant/authentication flag FALSE. This code never installs or writes.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "postapollo.connections.c3ep-running-script-observation.v1"
SIGNED_SCRIPT_PATH = Path("/usr/libexec/post-apollo/connections-status-host")
CI_PREFIX = "c3ep-ci-"
SHA = re.compile(r"[0-9a-f]{64}")
MAX_SCRIPT = 128 * 1024
MAX_CMDLINE = 4096
ARG = b"--read-only"


class Refused(Exception):
    pass


def deny(reason: str):
    raise Refused(reason)


def _proc_start(pid: int) -> str:
    if type(pid) is not int or pid <= 1:
        deny("INVALID_PROCESS_PID")
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        # Field 22 lies at index 19 after the parenthesized comm field.
        ticks = text.rsplit(") ", 1)[1].split()[19]
        if not ticks.isdecimal() or int(ticks) <= 0:
            deny("PROCESS_START_UNAVAILABLE")
        return ticks
    except (OSError, IndexError, ValueError):
        deny("PROCESS_START_UNAVAILABLE")


def _host_path(path: Path):
    if not path.is_absolute():
        deny("SCRIPT_PATH_NOT_ABSOLUTE")
    if path == SIGNED_SCRIPT_PATH:
        if (os.environ.get("GITHUB_ACTIONS") != "true" or
                os.environ.get("POST_APOLLO_C4B_TEST_GUEST") != "1" or
                not Path("/run/ostree-booted").exists()):
            deny("GUEST_ONLY_SCRIPT_SCOPE")
    elif (path.parent.parent != Path("/run") or
          not path.parent.name.startswith(CI_PREFIX) or
          path.name != "status-host"):
        deny("SCRIPT_SCOPE_REFUSED")
    # Check all ancestors, without accepting symlinks in path resolution.
    current = path.parent
    while True:
        try:
            st = os.lstat(current)
        except OSError:
            deny("SCRIPT_PARENT_MISSING")
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or
                stat.S_IMODE(st.st_mode) & 0o022):
            deny("SCRIPT_PARENT_UNSAFE")
        if current == Path("/"):
            break
        current = current.parent


def _process_identity(pid: int, uid: int, gid: int):
    try:
        lines = Path(f"/proc/{pid}/status").read_text().splitlines()
        props = {}
        for line in lines:
            if line.startswith(("Uid:", "Gid:")):
                name, values = line.split(":", 1)
                props[name] = [int(v) for v in values.split()]
        if (len(props.get("Uid", [])) != 4 or
                len(props.get("Gid", [])) != 4):
            deny("PROCESS_OS_IDENTITY_UNAVAILABLE")
        if (props["Uid"] != [uid] * 4 or props["Gid"] != [gid] * 4):
            deny("PROCESS_OS_IDENTITY_MISMATCH")
    except (OSError, ValueError):
        deny("PROCESS_OS_IDENTITY_UNAVAILABLE")


def _script_hash(path: Path, expected_sha256: str):
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        deny("RUNNING_SCRIPT_OPEN_REFUSED")
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
                st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o555 or
                not 1 <= st.st_size <= MAX_SCRIPT):
            deny("RUNNING_SCRIPT_FILE_UNSAFE")
        sha = hashlib.sha256()
        size = 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            size += len(block)
            if size > MAX_SCRIPT:
                deny("RUNNING_SCRIPT_FILE_UNSAFE")
            sha.update(block)
        if size != st.st_size:
            deny("RUNNING_SCRIPT_CHANGED_DURING_READ")
        after = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns):
            deny("RUNNING_SCRIPT_CHANGED_DURING_READ")
        if sha.hexdigest() != expected_sha256:
            deny("RUNNING_SCRIPT_SIGNED_PAYLOAD_MISMATCH")
        return st.st_dev, st.st_ino
    finally:
        os.close(fd)


def observe(*, pid: int, expected_start: str, expected_uid: int,
            expected_gid: int, expected_script_path: str,
            expected_interpreter_path: str,
            expected_signed_script_sha256: str):
    """A scoped CI observation, never a runtime authorization decision."""
    if (not sys.platform.startswith("linux") or
            os.environ.get("GITHUB_ACTIONS") != "true" or
            os.geteuid() != 0):
        deny("CI_ONLY_ROOT_OBSERVER_REQUIRED")
    if (type(expected_uid) is not int or expected_uid <= 0 or
            type(expected_gid) is not int or expected_gid < 0 or
            type(expected_start) is not str or
            type(expected_signed_script_sha256) is not str or
            SHA.fullmatch(expected_signed_script_sha256) is None):
        deny("INVALID_EXPECTED_MEASUREMENT")
    path = Path(expected_script_path)
    interpreter = Path(expected_interpreter_path)
    if not interpreter.is_absolute():
        deny("INTERPRETER_PATH_NOT_ABSOLUTE")
    _host_path(path)
    if _proc_start(pid) != expected_start:
        deny("PROCESS_START_MISMATCH")
    _process_identity(pid, expected_uid, expected_gid)
    try:
        process_exe = os.stat(f"/proc/{pid}/exe")
        expected_exe = os.stat(interpreter)
    except OSError:
        deny("PROCESS_INTERPRETER_UNAVAILABLE")
    if (process_exe.st_dev, process_exe.st_ino) != (
            expected_exe.st_dev, expected_exe.st_ino):
        deny("PROCESS_INTERPRETER_MISMATCH")
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        deny("PROCESS_COMMANDLINE_UNAVAILABLE")
    if (not raw or len(raw) > MAX_CMDLINE or not raw.endswith(b"\0")):
        deny("PROCESS_COMMANDLINE_INVALID")
    parts = raw[:-1].split(b"\0")
    # C4b's signed 0555 entrypoint has a Python shebang and is invoked as
    # ExecStart=.../connections-status-host --read-only with NO shell.
    if (len(parts) != 3 or os.fsdecode(parts[1]) != str(path) or
            parts[2] != ARG or
            os.path.realpath(os.fsdecode(parts[0])) !=
                os.path.realpath(str(interpreter))):
        deny("PROCESS_COMMANDLINE_NOT_INSTALLED_ENTRYPOINT")
    device, inode = _script_hash(path, expected_signed_script_sha256)
    try:
        refreshed = os.stat(path)
    except OSError:
        deny("RUNNING_SCRIPT_CHANGED_AFTER_READ")
    if (refreshed.st_dev, refreshed.st_ino) != (device, inode):
        deny("RUNNING_SCRIPT_CHANGED_AFTER_READ")
    if (_proc_start(pid) != expected_start or
            Path(f"/proc/{pid}/cmdline").read_bytes() != raw):
        deny("PROCESS_CHANGED_AFTER_MEASUREMENT")
    return {
        "schema": SCHEMA,
        "observed_pid": pid,
        "observed_start_ticks": expected_start,
        "observed_uid": expected_uid,
        "running_script_sha256": expected_signed_script_sha256,
        "script_file_matches_supplied_signed_payload": True,
        "kernel_interpreter_inode_matches_expected": True,
        "commandline_matches_installed_entrypoint": True,
        "installedGuestMeasured": path == SIGNED_SCRIPT_PATH,
        "evidenceCryptographicallyAttested": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }
