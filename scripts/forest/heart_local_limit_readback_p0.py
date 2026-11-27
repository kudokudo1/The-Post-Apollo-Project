#!/usr/bin/env python3
"""Heart P0: passive cgroup-v2 disposable-provider limit readback.

Checks visible finite constraints, not effective host isolation, installed
model identity, permission, memory demand, free capacity, or runtime admission.
No cgroup writes, provider launch, network, device or workstation operations.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
import sys
import time

import cgroup_observation_i5 as I5
from heart_cpu_constraints_h4 import _quota

SCHEMA = "post-apollo.forest.heart-local-limit-readback.p0"
MAX_WINDOW_NS = 1_000_000_000
_FILES = ("memory.max", "memory.swap.max", "memory.current",
          "cpu.max", "pids.max", "pids.current")


@dataclass(frozen=True, slots=True)
class Level:
    memory_max: int | str
    swap_max: int | str
    memory_current: int
    cpu_quota: int | None
    cpu_period: int
    pids_max: int | str
    pids_current: int


def _read(fd, name):
    if name not in _FILES:
        raise I5.CgroupRefusal("INVALID_LIMIT_COUNTER")
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        return I5._read_fd(item, 64)
    finally:
        os.close(item)


def _level(fd):
    memory = I5._scalar(_read(fd, "memory.max"), limit=True)
    swap = I5._scalar(_read(fd, "memory.swap.max"), limit=True)
    quota, period = _quota(_read(fd, "cpu.max"))
    return Level(memory, swap,
                 I5._scalar(_read(fd, "memory.current")),
                 quota, period,
                 I5._scalar(_read(fd, "pids.max"), limit=True),
                 I5._scalar(_read(fd, "pids.current")))


def _summary(first, second):
    if not first or len(first) != len(second):
        raise I5.CgroupRefusal("INCOMPLETE_LIMIT_HIERARCHY")
    stable = lambda x: (x.memory_max, x.swap_max, x.cpu_quota,
                        x.cpu_period, x.pids_max)
    if any(stable(a) != stable(b) for a, b in zip(first, second)):
        raise I5.CgroupRefusal("LIMITS_CHANGED")
    leaf = second[-1]
    if (type(leaf.memory_max) is not int or leaf.memory_max <= 0
            or type(leaf.pids_max) is not int or leaf.pids_max <= 0
            or type(leaf.cpu_quota) is not int or leaf.cpu_quota <= 0
            or leaf.swap_max != 0):
        raise I5.CgroupRefusal("LEAF_NOT_FINITE_SWAP_FREE")
    finite_memory = [x.memory_max for x in second if type(x.memory_max) is int]
    finite_pids = [x.pids_max for x in second if type(x.pids_max) is int]
    # H4's CPU quota is a time allocation, NOT actual free cores or a
    # thread count. Return only a visible ancestor quota ceiling.
    finite_cpu = [1000 * x.cpu_quota // x.cpu_period for x in second
                  if x.cpu_quota is not None]
    if not finite_cpu or min(finite_cpu) <= 0:
        raise I5.CgroupRefusal("CPU_QUOTA_UNAVAILABLE")
    if (any(x.memory_current < 0 or x.pids_current < 0 for x in second)
            or any(x.memory_current > x.memory_max for x in second
                   if type(x.memory_max) is int)
            or any(x.pids_current > x.pids_max for x in second
                   if type(x.pids_max) is int)):
        raise I5.CgroupRefusal("LIMIT_COUNTER_INCONSISTENT")
    return {
        "visible_nonroot_levels": len(second),
        "leaf_memory_limit_bytes": leaf.memory_max,
        "leaf_swap_limit_bytes": 0,
        "leaf_pids_limit": leaf.pids_max,
        "visible_min_memory_limit_bytes": min(finite_memory),
        "visible_min_pids_limit": min(finite_pids),
        "visible_cpu_quota_millicpu_floor": min(finite_cpu),
        "leaf_memory_used_bytes_sampled_max": max(first[-1].memory_current,
                                                  second[-1].memory_current),
        "leaf_pids_used_sampled_max": max(first[-1].pids_current,
                                          second[-1].pids_current),
    }


def _base():
    return {
        "schema": SCHEMA,
        "scope": "EXPLICIT_VISIBLE_NONROOT_CGROUP_V2",
        "runtime_process_identity_verified": False,
        "provider_and_descendants_contained": False,
        "host_ancestor_coverage_verified": False,
        "filesystem_and_network_isolation_verified": False,
        "accelerator_exclusion_verified": False,
        "available_memory_or_model_demand_established": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(path):
    if sys.platform != "linux":
        raise I5.CgroupRefusal("LINUX_REQUIRED")
    parts = I5._parts(path)
    try:
        start = time.monotonic_ns()
        mount = I5._mount()
        with ExitStack() as stack:
            fds = []
            for depth in range(1, len(parts) + 1):
                fd = I5._open_group(parts[:depth])
                stack.callback(os.close, fd)
                fds.append(fd)
            identities = tuple(I5._identity(fd) for fd in fds)
            first = tuple(_level(fd) for fd in fds)
            second = tuple(_level(fd) for fd in fds)
            for depth, identity in enumerate(identities, 1):
                check = I5._open_group(parts[:depth])
                try:
                    if I5._identity(check) != identity:
                        raise I5.CgroupRefusal("CGROUP_SCOPE_CHANGED")
                finally:
                    os.close(check)
            if I5._mount() != mount:
                raise I5.CgroupRefusal("CGROUP_SCOPE_CHANGED")
            elapsed = time.monotonic_ns() - start
            if not 0 < elapsed <= MAX_WINDOW_NS:
                raise I5.CgroupRefusal("OBSERVATION_WINDOW_EXCEEDED")
            report = _summary(first, second)
    except (OSError, OverflowError):
        raise I5.CgroupRefusal("LIMIT_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", "elapsed_ns": elapsed, **report}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only finite local model cgroup envelope")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cgroup", required=True)
    args = parser.parse_args(argv)
    try:
        result, code = observe(args.cgroup), 0
    except I5.CgroupRefusal as exc:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
