#!/usr/bin/env python3
"""Heart H3: read-only Linux hierarchy memory headroom observations.

Not an admission measurement: selected cgroup is not verified Ollama;
memory.current and MemAvailable are sampled estimates, not reservations.
"""
import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
import re
import sys
import time

import cgroup_observation_i5 as I5
from performance_snapshot_p0 import _host_memory_available_mib

SCHEMA = "post-apollo.forest.heart-memory-headroom.h3"
MAX_WINDOW_NS = 1_000_000_000
_MIB = 1024 * 1024
_COUNTERS = ("memory.current", "memory.max", "memory.high")


@dataclass(frozen=True, slots=True)
class Level:
    charged: int
    hard: int | str
    high: int | str


def _read_level(fd):
    values = []
    for name in _COUNTERS:
        counter = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
        try:
            values.append(I5._scalar(I5._read_fd(counter, 64), limit=name != "memory.current"))
        finally:
            os.close(counter)
    return Level(*values)


def _summarize(first, second, host_first, host_second):
    if not first or len(first) != len(second):
        raise I5.CgroupRefusal("INCOMPLETE_HIERARCHY")
    if any((a.hard, a.high) != (b.hard, b.high) for a, b in zip(first, second)):
        raise I5.CgroupRefusal("MEMORY_LIMIT_CHANGED")
    if any(type(x) is not int or not 0 <= x <= I5.MAX_NUMBER // _MIB
           for x in (host_first, host_second)):
        raise I5.CgroupRefusal("HOST_MEMORY_UNAVAILABLE")
    hard, high = [], []
    for a, b in zip(first, second):
        used = max(a.charged, b.charged)
        if type(a.hard) is int:
            hard.append(max(0, a.hard - used))
        if type(a.high) is int:
            high.append(max(0, a.high - used))
    host = min(host_first, host_second)
    hard_min = min(hard) if hard else None
    high_min = min(high) if high else None
    # Round DOWN before comparing against available MiB. high is a
    # throttling threshold, not a hard limit; use it conservatively.
    ceiling = min([host] + [x // _MIB for x in (hard_min, high_min) if x is not None])
    return {
        "visible_nonroot_levels_sampled": len(first),
        "host_available_mib_sampled_min": host,
        "visible_hard_limit_headroom_mib": None if hard_min is None else hard_min // _MIB,
        "visible_high_threshold_headroom_mib": None if high_min is None else high_min // _MIB,
        "finite_hard_limit_levels": len(hard),
        "finite_high_threshold_levels": len(high),
        "sampled_memory_headroom_hint_mib": ceiling,
    }


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "EXPLICIT_VISIBLE_CGROUP_HIERARCHY_AND_HOST",
        "runtime_identity_verified": False,
        "complete_host_hierarchy_verified": False,
        "atomic_snapshot": False,
        "allocatable_memory_established": False,
        "resource_requirements_established": False,
        "accelerator_availability_established": False,
        "cpu_availability_established": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


# H10: optional leaf-scope pressure observation, using the existing held fd.
_PSI_ROW = re.compile(rb"(some|full) avg10=([0-9]{1,3}\.[0-9]{2}) avg60=([0-9]{1,3}\.[0-9]{2}) avg300=([0-9]{1,3}\.[0-9]{2}) total=([0-9]{1,20})")
_EVENT_ROW = re.compile(rb"([a-z][a-z0-9_]{0,63}) ([0-9]{1,20})")
_EVENT_KEYS = ("low", "high", "max", "oom", "oom_kill")


def _pressure(raw):
    result = {}
    for line in raw.splitlines():
        match = _PSI_ROW.fullmatch(line)
        if not match or match[1] in result:
            raise I5.CgroupRefusal("INVALID_MEMORY_PRESSURE")
        averages = tuple(int(v.replace(b".", b"")) for v in match.groups()[1:4])
        if any(v > 10000 for v in averages):
            raise I5.CgroupRefusal("INVALID_MEMORY_PRESSURE")
        result[match[1]] = (*averages, I5._number(match[5]))
    if set(result) != {b"some", b"full"}:
        raise I5.CgroupRefusal("INVALID_MEMORY_PRESSURE")
    return result


def _events(raw):
    result = {}
    for line in raw.splitlines():
        match = _EVENT_ROW.fullmatch(line)
        if not match or match[1] in result:
            raise I5.CgroupRefusal("INVALID_MEMORY_EVENTS")
        result[match[1]] = I5._number(match[2])
    if not all(k.encode("ascii") in result for k in _EVENT_KEYS):
        raise I5.CgroupRefusal("INVALID_MEMORY_EVENTS")
    return result


def _read_pressure(fd):
    values = []
    for name in ("memory.pressure", "memory.events"):
        counter = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
        try:
            values.append(I5._read_fd(counter, 4096))
        finally:
            os.close(counter)
    return _pressure(values[0]), _events(values[1])


def _pressure_summary(first, second):
    a, events_a = first
    b, events_b = second
    if (events_a.keys() != events_b.keys()
            or any(events_b[k] < v for k, v in events_a.items())
            or any(b[k][3] < a[k][3] for k in (b"some", b"full"))):
        raise I5.CgroupRefusal("MEMORY_COUNTER_CONTINUITY_LOST")
    keys = _EVENT_KEYS + ("oom_group_kill",)
    return {
        "scope": "SELECTED_CGROUP_LEAF_HIERARCHICAL_EVENTS",
        "psi": {k.decode("ascii"): {
            "avg10_hundredths_percent": b[k][0],
            "avg60_hundredths_percent": b[k][1],
            "avg300_hundredths_percent": b[k][2],
            "total_us": b[k][3],
            "observed_delta_us": b[k][3] - a[k][3],
        } for k in (b"some", b"full")},
        "events_total": {k: events_b.get(k.encode("ascii")) for k in keys},
        "events_observed_delta": {
            k: (events_b[k.encode("ascii")] - events_a[k.encode("ascii")]
                if k.encode("ascii") in events_b else None) for k in keys},
        "pressure_free_established": False,
    }


def observe(path, *, pressure=False):
    if type(pressure) is not bool:
        raise I5.CgroupRefusal("INVALID_PRESSURE_OPTION")
    parts = I5._parts(path)
    if sys.platform != "linux":
        raise I5.CgroupRefusal("LINUX_REQUIRED")
    try:
        started = time.monotonic_ns()
        mount = I5._mount()
        # Hold every non-root ancestor fd open through both observations.
        # cgroup-v2 root has no memory.max/high; host availability is
        # separately sampled, not a claim that hidden ancestors are absent.
        with ExitStack() as stack:
            fds = []
            for i in range(1, len(parts) + 1):
                fd = I5._open_group(parts[:i])
                stack.callback(os.close, fd)
                fds.append(fd)
            identities = tuple(I5._identity(fd) for fd in fds)
            pressure_first = _read_pressure(fds[-1]) if pressure else None
            host_first = _host_memory_available_mib()
            first = tuple(_read_level(fd) for fd in fds)
            second = tuple(_read_level(fd) for fd in reversed(fds))[::-1]
            host_second = _host_memory_available_mib()
            pressure_second = _read_pressure(fds[-1]) if pressure else None
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
            result = _summarize(first, second, host_first, host_second)
            if pressure:
                result["selected_cgroup_pressure"] = _pressure_summary(pressure_first, pressure_second)
    except (OSError, OverflowError):
        raise I5.CgroupRefusal("HIERARCHY_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", "elapsed_ns": elapsed, **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Heart H3: read-only visible memory headroom")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cgroup", required=True)
    parser.add_argument("--pressure", action="store_true", help="also read selected cgroup PSI and memory.events")
    args = parser.parse_args(argv)
    try:
        result, code = observe(args.cgroup, pressure=args.pressure), 0
    except I5.CgroupRefusal as exc:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
