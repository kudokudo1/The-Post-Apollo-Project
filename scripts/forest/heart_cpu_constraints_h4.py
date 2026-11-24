#!/usr/bin/env python3
"""Heart H4: passive visible cgroup CPU constraints, not free capacity."""
import argparse
from contextlib import ExitStack
import json
import os
import re
import sys
import time
from fractions import Fraction

import cgroup_observation_i5 as I5

SCHEMA = "post-apollo.forest.heart-cpu-constraints.h4"
MAX_WINDOW_NS = 1_000_000_000
MAX_CPU_INDEX = 1_048_575
MAX_CPUS = 65536
_RANGE = re.compile(rb"([0-9]{1,7})(?:-([0-9]{1,7}))?")


def _read(fd, name, cap):
    if name not in ("cpu.max", "cpuset.cpus.effective"):
        raise I5.CgroupRefusal("INVALID_CPU_COUNTER")
    source = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                     dir_fd=fd)
    try:
        return I5._read_fd(source, cap)
    finally:
        os.close(source)


def _quota(raw):
    fields = raw.strip().split()
    if len(fields) != 2:
        raise I5.CgroupRefusal("INVALID_CPU_QUOTA")
    period = I5._number(fields[1])
    if not 1 <= period <= 1_000_000:
        raise I5.CgroupRefusal("INVALID_CPU_PERIOD")
    quota = None if fields[0] == b"max" else I5._number(fields[0])
    if quota == 0:
        raise I5.CgroupRefusal("INVALID_CPU_QUOTA")
    return quota, period


def _cpuset(raw):
    """Canonical interval list; no large set expansion."""
    value = raw.strip()
    if not value:
        raise I5.CgroupRefusal("CPUSET_UNAVAILABLE")
    intervals = []
    count = 0
    for item in value.split(b","):
        m = _RANGE.fullmatch(item)
        if not m:
            raise I5.CgroupRefusal("INVALID_CPUSET")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) is not None else start
        if not start <= end <= MAX_CPU_INDEX or (intervals and start <= intervals[-1][1]):
            raise I5.CgroupRefusal("INVALID_CPUSET")
        count += end - start + 1
        if count > MAX_CPUS:
            raise I5.CgroupRefusal("CPUSET_TOO_LARGE")
        if intervals and start == intervals[-1][1] + 1:
            intervals[-1] = (intervals[-1][0], end)
        else:
            intervals.append((start, end))
    return tuple(intervals)


def _sample(fds):
    return (tuple(_quota(_read(fd, "cpu.max", 64)) for fd in fds),
            _cpuset(_read(fds[-1], "cpuset.cpus.effective", 32768)))


def _summary(first, second):
    if first != second:
        raise I5.CgroupRefusal("CPU_CONSTRAINT_CHANGED")
    quotas, cpus = first
    count = sum(end - start + 1 for start, end in cpus)
    finite = [Fraction(quota, period) for quota, period in quotas if quota is not None]
    minimum = min(finite) if finite else None
    ceiling = min(Fraction(count), minimum) if minimum is not None else Fraction(count)
    return {
        "visible_nonroot_levels_sampled": len(quotas),
        "effective_cpuset_cpu_count": count,
        "finite_quota_levels": len(finite),
        "visible_quota_millicpu_floor": int(minimum * 1000) if minimum is not None else None,
        "visible_cpu_time_ceiling_millicpu_floor": int(ceiling * 1000),
    }


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "VISIBLE_CGROUP_CPU_CONSTRAINTS",
        "runtime_identity_verified": False,
        "complete_host_hierarchy_verified": False,
        "atomic_snapshot": False,
        "idle_cpu_capacity_established": False,
        "runtime_thread_limit_enforced": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(path):
    parts = I5._parts(path)
    if sys.platform != "linux":
        raise I5.CgroupRefusal("LINUX_REQUIRED")
    try:
        started = time.monotonic_ns()
        mount = I5._mount()
        with ExitStack() as stack:
            fds = []
            for i in range(1, len(parts) + 1):
                fd = I5._open_group(parts[:i])
                stack.callback(os.close, fd)
                fds.append(fd)
            identities = tuple(I5._identity(fd) for fd in fds)
            first = _sample(fds)
            second = _sample(fds)
            for i, original in enumerate(identities, 1):
                check = I5._open_group(parts[:i])
                try:
                    if I5._identity(check) != original:
                        raise I5.CgroupRefusal("CGROUP_SCOPE_CHANGED")
                finally:
                    os.close(check)
            if I5._mount() != mount:
                raise I5.CgroupRefusal("CGROUP_SCOPE_CHANGED")
            elapsed = time.monotonic_ns() - started
            if not 0 < elapsed <= MAX_WINDOW_NS:
                raise I5.CgroupRefusal("OBSERVATION_WINDOW_EXCEEDED")
            result = _summary(first, second)
    except (OSError, OverflowError):
        raise I5.CgroupRefusal("CPU_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", "elapsed_ns": elapsed, **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Heart H4: visible CPU constraints")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cgroup", required=True)
    args = parser.parse_args(argv)
    try:
        result, code = observe(args.cgroup), 0
    except I5.CgroupRefusal as exc:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
