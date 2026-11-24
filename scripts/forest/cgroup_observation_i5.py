#!/usr/bin/env python3
"""I5: passive cgroup-v2 observation, no runtime attribution or authority.

Select an existing non-root cgroup explicitly. Kernel memory charges
include descendants; they are not a sum of per-process RSS, and are not
unique physical memory, exact model memory or a reservation.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import sys
import time
from dataclasses import dataclass

SCHEMA = "post-apollo.forest.cgroup-observation.i5"
ROOT = "/sys/fs/cgroup"
MAX_BYTES = 32768
MAX_MOUNT_BYTES = 262144
MAX_NUMBER = 2**63 - 1
MAX_SAMPLES = 10
_SEGMENT = re.compile(r"[A-Za-z0-9_@.-]{1,128}\Z", re.ASCII)
_NUMBER = re.compile(rb"[0-9]{1,19}\Z")
_SCALARS = ("memory.current", "memory.peak", "memory.swap.current",
            "memory.max", "pids.current")
_TABLES = {"memory.stat": (b"anon", b"file", b"shmem"),
           "cpu.stat": (b"usage_usec", b"user_usec", b"system_usec")}
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_OPTIONAL_ERRORS = (errno.ENOENT, errno.EACCES, errno.EPERM)


class CgroupRefusal(ValueError):
    """Static public refusal, never echo raw paths or counters."""


def _parts(path):
    if type(path) is not str or not 2 <= len(path) <= 512 or not path.startswith("/"):
        raise CgroupRefusal("INVALID_CGROUP_SELECTION")
    parts = path[1:].split("/")
    if len(parts) > 16 or any(p in (".", "..") or not _SEGMENT.fullmatch(p)
                              for p in parts):
        raise CgroupRefusal("INVALID_CGROUP_SELECTION")
    return tuple(parts)


def _read_fd(fd, cap):
    result = bytearray()
    while len(result) <= cap:
        chunk = os.read(fd, min(4096, cap + 1 - len(result)))
        if not chunk:
            return bytes(result)
        result.extend(chunk)
    raise CgroupRefusal("OBSERVATION_TOO_LARGE")


def _mount_reference(raw):
    # Conservative layout: one exact cgroup2 mount at ROOT with root /.
    # Namespace-relative roots or alternate layouts are deliberately refused.
    matches = []
    for line in raw.splitlines():
        before, sep, after = line.partition(b" - ")
        fields, tail = before.split(), after.split()
        if len(fields) >= 6 and fields[4] == ROOT.encode("ascii"):
            if (not sep or len(tail) < 3 or tail[0] != b"cgroup2"
                    or fields[3] != b"/"):
                raise CgroupRefusal("UNSUPPORTED_CGROUP_MOUNT")
            matches.append((fields[0], fields[2]))
    if len(matches) != 1:
        raise CgroupRefusal("UNSUPPORTED_CGROUP_MOUNT")
    return matches[0]


def _mount():
    fd = os.open("/proc/self/mountinfo", os.O_RDONLY | os.O_CLOEXEC)
    try:
        return _mount_reference(_read_fd(fd, MAX_MOUNT_BYTES))
    finally:
        os.close(fd)


def _identity(fd):
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def _open_group(parts):
    fd = os.open(ROOT, _DIR_FLAGS)
    try:
        device = _identity(fd)[0]
        for part in parts:
            child = os.open(part, _DIR_FLAGS, dir_fd=fd)
            try:
                if _identity(child)[0] != device:
                    raise CgroupRefusal("CGROUP_DEVICE_CHANGED")
            except BaseException:
                os.close(child)
                raise
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_counter(directory, name, *, optional=True):
    if name not in _SCALARS and name not in _TABLES:
        raise CgroupRefusal("INVALID_COUNTER_NAME")
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                     dir_fd=directory)
    except OSError as exc:
        if optional and exc.errno in _OPTIONAL_ERRORS:
            return None
        raise
    try:
        return _read_fd(fd, MAX_BYTES)
    finally:
        os.close(fd)


def _number(raw):
    if type(raw) is not bytes or not _NUMBER.fullmatch(raw):
        raise CgroupRefusal("INVALID_COUNTER")
    value = int(raw)
    if value > MAX_NUMBER:
        raise CgroupRefusal("INVALID_COUNTER")
    return value


def _scalar(raw, *, limit=False):
    if raw is None:
        return None
    value = raw.strip()
    if limit and value == b"max":
        return "unlimited"
    return _number(value)


def _table(raw, keys):
    if raw is None:
        return tuple(None for _ in keys)
    values = {}
    for line in raw.splitlines():
        fields = line.split()
        if not fields or fields[0] not in keys:
            continue
        if len(fields) != 2 or fields[0] in values:
            raise CgroupRefusal("INVALID_COUNTER_TABLE")
        values[fields[0]] = _number(fields[1])
    return tuple(values.get(k) for k in keys)


@dataclass(frozen=True, slots=True)
class Sample:
    timestamp_ns: int
    current: int
    peak: int | None
    swap: int | None
    local_limit: int | str | None
    tasks: int | None
    memory: tuple[int | None, ...]
    cpu: tuple[int | None, ...]


def _sample(fd):
    current = _scalar(_read_counter(fd, "memory.current", optional=False))
    if current is None:
        raise CgroupRefusal("MEMORY_CURRENT_UNAVAILABLE")
    peak = _scalar(_read_counter(fd, "memory.peak"))
    swap = _scalar(_read_counter(fd, "memory.swap.current"))
    limit = _scalar(_read_counter(fd, "memory.max"), limit=True)
    tasks = _scalar(_read_counter(fd, "pids.current"))
    memory = _table(_read_counter(fd, "memory.stat"), _TABLES["memory.stat"])
    cpu = _table(_read_counter(fd, "cpu.stat"), _TABLES["cpu.stat"])
    return Sample(time.monotonic_ns(), current, peak, swap, limit, tasks, memory, cpu)


def _summary(samples):
    first, last = samples[0], samples[-1]
    for a, b in zip(samples, samples[1:]):
        if b.timestamp_ns <= a.timestamp_ns:
            raise CgroupRefusal("CLOCK_REGRESSED")
        if b.local_limit != a.local_limit:
            raise CgroupRefusal("LOCAL_LIMIT_CHANGED")
        for x, y in zip(a.cpu, b.cpu):
            if x is not None and y is not None and y < x:
                raise CgroupRefusal("CPU_COUNTER_REGRESSED")
    def delta(index):
        values = tuple(s.cpu[index] for s in samples)
        if any(v is None for v in values):
            return None
        return values[-1] - values[0]
    peak = max(s.current for s in samples)
    return {
        "sample_count": len(samples),
        "elapsed_ns": last.timestamp_ns - first.timestamp_ns,
        "charged_memory_first_bytes": first.current,
        "charged_memory_last_bytes": last.current,
        "charged_memory_sampled_max_bytes": peak,
        "charged_memory_sampled_increase_bytes": peak - first.current,
        "kernel_memory_peak_last_bytes_reported": last.peak,
        "swap_last_bytes_reported": last.swap,
        "local_memory_max_bytes": last.local_limit if type(last.local_limit) is int else None,
        "local_memory_max_status": (
            "UNLIMITED" if last.local_limit == "unlimited" else
            "FINITE" if type(last.local_limit) is int else "UNKNOWN"),
        "anon_last_bytes_reported": last.memory[0],
        "file_last_bytes_reported": last.memory[1],
        "shmem_last_bytes_reported": last.memory[2],
        "cpu_usage_usec_delta": delta(0),
        "cpu_user_usec_delta": delta(1),
        "cpu_system_usec_delta": delta(2),
        "tasks_last_reported": last.tasks,
    }


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "CGROUP_V2_CHARGED_MEMORY_DIAGNOSTIC",
        "descendants_included_by_kernel": True,
        "runtime_identity_verified": False,
        "model_binding_verified": False,
        "membership_stability_verified": False,
        "workload_isolation_verified": False,
        "measurement_coverage_complete": False,
        "physical_memory_deduplicated_verified": False,
        "accelerator_mapping_verified": False,
        "effective_memory_limit_established": False,
        "resource_availability_established": False,
        "runtime_requirements_established": False,
        "resource_reserved": False,
        "generation_requested": False,
        "model_load_requested": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(path, *, samples=5, interval_ms=250):
    parts = _parts(path)
    if (type(samples) is not int or not 2 <= samples <= MAX_SAMPLES
            or type(interval_ms) is not int or not 100 <= interval_ms <= 500):
        raise CgroupRefusal("INVALID_SAMPLE_BOUNDS")
    if sys.platform != "linux":
        raise CgroupRefusal("LINUX_REQUIRED")
    try:
        mount = _mount()
        fd = _open_group(parts)
        try:
            original = _identity(fd)
            observations = []
            for i in range(samples):
                if i:
                    time.sleep(interval_ms / 1000)
                observations.append(_sample(fd))
            # Detect observable replacement; no claim of uninterrupted
            # membership, mount/namespace/identity or ABA resistance.
            check = _open_group(parts)
            try:
                if _identity(check) != original or _mount() != mount:
                    raise CgroupRefusal("CGROUP_SCOPE_CHANGED")
            finally:
                os.close(check)
            result = _summary(tuple(observations))
        finally:
            os.close(fd)
    except (OSError, OverflowError):
        raise CgroupRefusal("CGROUP_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Forest I5: passive selected cgroup-v2 counters")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cgroup", required=True, help="non-root hierarchy path, e.g. /system.slice/ollama.service")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval-ms", type=int, default=250)
    args = parser.parse_args(argv)
    try:
        data, status = observe(args.cgroup, samples=args.samples, interval_ms=args.interval_ms), 0
    except CgroupRefusal as exc:
        data, status = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        data, status = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
