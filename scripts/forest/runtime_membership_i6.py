#!/usr/bin/env python3
"""Forest I6: passive correlation of an existing process and cgroup.

No executable reads/hashes, process search, command-line/environment,
network, model load, process control, privilege or identity attestation.
Only explicit same-effective-UID PIDs. Observed inode and start time are
local references, not release authentication or proof of model ownership.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
import re
import stat
import sys

import cgroup_observation_i5 as group
import process_observation_i4 as proc

SCHEMA = "post-apollo.forest.runtime-membership.i6"
MAX_PIDS = 16
_UUID = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n?\Z")
_FIELDS = ("stat", "cgroup", "status")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class MembershipRefusal(ValueError):
    """Fixed refusal code; no external values in public errors."""


def _pids(values):
    if (type(values) is not tuple or not 1 <= len(values) <= MAX_PIDS
            or any(type(p) is not int or not 1 <= p <= proc.MAX_PID for p in values)
            or len(set(values)) != len(values)):
        raise MembershipRefusal("INVALID_PID_SELECTION")
    return values


def _boot():
    fd = os.open("/proc/sys/kernel/random/boot_id", os.O_RDONLY | os.O_CLOEXEC)
    try:
        raw = group._read_fd(fd, 64)
    finally:
        os.close(fd)
    if not _UUID.fullmatch(raw):
        raise MembershipRefusal("BOOT_REFERENCE_UNAVAILABLE")
    return raw.strip()


def _read(fd, name):
    if name not in _FIELDS:
        raise MembershipRefusal("INVALID_PROC_FIELD")
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        return group._read_fd(item, proc.MAX_PROC_BYTES)
    finally:
        os.close(item)


def _membership(raw):
    """Require one unified-hierarchy entry; no guessed hybrid mapping."""
    lines = raw.splitlines()
    if len(lines) != 1 or not lines[0].startswith(b"0::"):
        raise MembershipRefusal("UNSUPPORTED_CGROUP_MEMBERSHIP")
    try:
        path = lines[0][3:].decode("ascii")
        # root is valid kernel membership, not a valid selected group.
        return () if path == "/" else group._parts(path)
    except (UnicodeError, group.CgroupRefusal):
        raise MembershipRefusal("UNSUPPORTED_CGROUP_MEMBERSHIP") from None


def _uids(raw):
    lines = [line for line in raw.splitlines() if line.startswith(b"Uid:")]
    if len(lines) != 1:
        raise MembershipRefusal("UID_REFERENCE_UNAVAILABLE")
    parts = lines[0][4:].split()
    if len(parts) != 4:
        raise MembershipRefusal("UID_REFERENCE_UNAVAILABLE")
    try:
        return tuple(proc._number(v, 2**32 - 1) for v in parts)
    except proc.ObservationRefusal:
        raise MembershipRefusal("UID_REFERENCE_UNAVAILABLE") from None


def _exe_reference(fd):
    # Follow only the kernel's fixed /proc/PID/exe magic link for metadata.
    # No executable contents, link text or executable paths read.
    info = os.stat("exe", dir_fd=fd, follow_symlinks=True)
    if not stat.S_ISREG(info.st_mode):
        raise MembershipRefusal("EXECUTABLE_REFERENCE_UNAVAILABLE")
    return info.st_dev, info.st_ino


@dataclass(frozen=True, slots=True)
class Member:
    start_ticks: int
    directory_identity: tuple[int, int]
    executable_identity: tuple[int, int]
    uid_reference: tuple[int, ...]
    membership: tuple[str, ...]


def _member(fd, pid, selected, uid):
    before = proc._parse_stat(_read(fd, "stat"), pid)
    ids = _uids(_read(fd, "status"))
    if ids != (uid,) * 4:
        raise MembershipRefusal("PROCESS_OWNER_SCOPE_MISMATCH")
    membership = _membership(_read(fd, "cgroup"))
    if membership[:len(selected)] != selected:
        raise MembershipRefusal("PROCESS_OUTSIDE_SELECTED_GROUP")
    executable = _exe_reference(fd)
    after = proc._parse_stat(_read(fd, "stat"), pid)
    if (after.start_ticks != before.start_ticks
            or after.user_ticks < before.user_ticks
            or after.system_ticks < before.system_ticks
            or _uids(_read(fd, "status")) != ids
            or _membership(_read(fd, "cgroup")) != membership
            or _exe_reference(fd) != executable):
        raise MembershipRefusal("PROCESS_REFERENCE_CHANGED")
    return Member(after.start_ticks, group._identity(fd), executable, ids, membership)


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "EXPLICIT_PROCESS_MEMBERSHIP_DIAGNOSTIC",
        "runtime_release_authenticated": False,
        "provider_runtime_instance_verified": False,
        "model_artifact_verified": False,
        "model_binding_verified": False,
        "complete_group_membership_verified": False,
        "continuous_membership_verified": False,
        "workload_isolation_verified": False,
        "memory_attributed_to_model": False,
        "accelerator_mapping_verified": False,
        "resource_requirements_established": False,
        "resource_reserved": False,
        "generation_requested": False,
        "model_load_requested": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def correlate(path, pids):
    selected = group._parts(path)
    pids = _pids(pids)
    if sys.platform != "linux":
        raise MembershipRefusal("LINUX_REQUIRED")
    uid = os.geteuid()
    try:
        boot = _boot()
        mount = group._mount()
        with ExitStack() as stack:
            group_fd = group._open_group(selected)
            stack.callback(os.close, group_fd)
            original_group = group._identity(group_fd)
            # Confirm selected hierarchy path is readable as a memory group.
            group._scalar(group._read_counter(group_fd, "memory.current", optional=False))
            handles = []
            for pid in pids:
                fd = os.open("/proc/" + str(pid), _DIR_FLAGS)
                stack.callback(os.close, fd)
                handles.append((pid, fd))
            first = tuple(_member(fd, pid, selected, uid) for pid, fd in handles)
            second = tuple(_member(fd, pid, selected, uid) for pid, fd in handles)
            if first != second:
                raise MembershipRefusal("PROCESS_REFERENCE_CHANGED")
            # Reopen the numeric paths and hierarchy at the end; compare
            # observable directory identity against the retained handles.
            for pid, fd in handles:
                check = os.open("/proc/" + str(pid), _DIR_FLAGS)
                try:
                    if group._identity(check) != group._identity(fd):
                        raise MembershipRefusal("PROCESS_REFERENCE_CHANGED")
                finally:
                    os.close(check)
            check = group._open_group(selected)
            try:
                if group._identity(check) != original_group:
                    raise MembershipRefusal("CGROUP_REFERENCE_CHANGED")
            finally:
                os.close(check)
            if _boot() != boot or group._mount() != mount:
                raise MembershipRefusal("HOST_REFERENCE_CHANGED")
            direct = sum(m.membership == selected for m in second)
            distinct = len({m.executable_identity for m in second})
    except (OSError, OverflowError, group.CgroupRefusal, proc.ObservationRefusal):
        raise MembershipRefusal("LOCAL_MEMBERSHIP_UNAVAILABLE") from None
    return {
        **_base(),
        "status": "OBSERVED",
        "selected_process_count": len(pids),
        "direct_member_count": direct,
        "descendant_member_count": len(pids) - direct,
        "distinct_executable_reference_count": distinct,
        "same_owner_references_observed": True,
        "matching_membership_references_observed": True,
        "matching_process_references_observed": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Forest I6: correlate explicit existing same-owner process references")
    parser.add_argument("command", choices=("correlate",))
    parser.add_argument("--cgroup", required=True)
    parser.add_argument("--pid", required=True, action="append", type=int)
    args = parser.parse_args(argv)
    try:
        data, status = correlate(args.cgroup, tuple(args.pid)), 0
    except (MembershipRefusal, group.CgroupRefusal) as exc:
        # Both modules expose fixed refusal codes.
        data, status = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        data, status = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
