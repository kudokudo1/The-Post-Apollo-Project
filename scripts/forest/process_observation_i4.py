#!/usr/bin/env python3
"""I4 // bounded passive Linux process diagnostics.

Explicit numeric PID only; no process discovery, launch, signal, inference,
network, file writes, privileged access or protected data. Pin a proc
directory descriptor throughout the observation. RSS is approximate and
per process, not total model memory. Sampled maxima are not true peaks.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass

SCHEMA = "post-apollo.forest.process-observation.i4"
MAX_PROC_BYTES = 16384
MAX_NUMBER = 2**63 - 1
MAX_SAMPLES = 20
MIN_INTERVAL_MS = 100
MAX_INTERVAL_MS = 500
MAX_PID = 2**31 - 1
_UINT = re.compile(rb"[0-9]{1,19}\Z")
_FIELDS = (b"VmRSS", b"VmHWM", b"RssAnon", b"RssFile", b"RssShmem", b"VmSwap")


class ObservationRefusal(ValueError):
    """Fixed public refusal code, no raw process data or filesystem paths."""


def _number(value, maximum=MAX_NUMBER):
    if type(value) is not bytes or not _UINT.fullmatch(value):
        raise ObservationRefusal("INVALID_COUNTER")
    n = int(value)
    if n > maximum:
        raise ObservationRefusal("INVALID_COUNTER")
    return n


def _bounded_int(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ObservationRefusal("INVALID_ARGUMENT")


@dataclass(frozen=True, slots=True)
class ProcessStat:
    start_ticks: int
    user_ticks: int
    system_ticks: int
    threads: int


def _parse_stat(raw, pid):
    # comm can contain spaces, closing parentheses, and newlines.
    if type(raw) is not bytes or len(raw) > MAX_PROC_BYTES:
        raise ObservationRefusal("INVALID_STAT")
    prefix = str(pid).encode("ascii") + b" ("
    end = raw.rfind(b")")
    if not raw.startswith(prefix) or end < len(prefix) or raw[end+1:end+2] != b" ":
        raise ObservationRefusal("INVALID_STAT")
    fields = raw[end+2:].split()
    if len(fields) < 20 or fields[0] not in (
            b"R", b"S", b"D", b"T", b"t", b"I", b"P", b"W"):
        # Reject exited/zombie or unrecognized states, not zero usage.
        raise ObservationRefusal("PROCESS_NOT_LIVE")
    start = _number(fields[19])
    threads = _number(fields[17], 65536)
    if threads == 0:
        raise ObservationRefusal("INVALID_COUNTER")
    return ProcessStat(start, _number(fields[11]), _number(fields[12]), threads)


def _parse_status(raw):
    if type(raw) is not bytes or len(raw) > MAX_PROC_BYTES:
        raise ObservationRefusal("INVALID_STATUS")
    values = {}
    for line in raw.split(b"\n"):
        key, sep, rest = line.partition(b":")
        if not sep or key not in _FIELDS:
            continue
        if key in values:
            raise ObservationRefusal("DUPLICATE_COUNTER")
        parts = rest.split()
        if len(parts) != 2 or parts[1] != b"kB":
            raise ObservationRefusal("INVALID_COUNTER_UNIT")
        values[key] = _number(parts[0], MAX_NUMBER // 1024) * 1024
    return tuple(values.get(key) for key in _FIELDS)


def _read_proc(directory, name):
    # Only these two fixed numeric diagnostic files are reachable.
    if name not in ("stat", "status"):
        raise ObservationRefusal("INVALID_PROC_FIELD")
    fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                 dir_fd=directory)
    try:
        chunks = bytearray()
        while len(chunks) <= MAX_PROC_BYTES:
            chunk = os.read(fd, min(4096, MAX_PROC_BYTES + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > MAX_PROC_BYTES:
            raise ObservationRefusal("PROC_FIELD_TOO_LARGE")
        return bytes(chunks)
    finally:
        os.close(fd)


@dataclass(frozen=True, slots=True)
class Sample:
    time_ns: int
    stat: ProcessStat
    memory: tuple[int | None, ...]


def _sample(directory, pid):
    before = _parse_stat(_read_proc(directory, "stat"), pid)
    memory = _parse_status(_read_proc(directory, "status"))
    after = _parse_stat(_read_proc(directory, "stat"), pid)
    if before.start_ticks != after.start_ticks:
        raise ObservationRefusal("PROCESS_INSTANCE_CHANGED")
    if before.user_ticks > after.user_ticks or before.system_ticks > after.system_ticks:
        raise ObservationRefusal("CPU_COUNTER_REGRESSED")
    return Sample(time.monotonic_ns(), after, memory)


def _summarize(samples, ticks_per_second):
    first, last = samples[0], samples[-1]
    for a, b in zip(samples, samples[1:]):
        if a.stat.start_ticks != b.stat.start_ticks:
            raise ObservationRefusal("PROCESS_INSTANCE_CHANGED")
        if (b.time_ns <= a.time_ns or b.stat.user_ticks < a.stat.user_ticks
                or b.stat.system_ticks < a.stat.system_ticks):
            raise ObservationRefusal("COUNTER_REGRESSED")
    def maximum(index):
        vals = tuple(s.memory[index] for s in samples)
        return None if any(v is None for v in vals) else max(vals)
    rss_max = maximum(0)
    baseline = first.memory[0]
    # Baseline belongs to the same sample window. This is a sampled delta,
    # NOT an attributable workload allocation or calibrated requirement.
    increase = None if rss_max is None or baseline is None else rss_max - baseline
    return {
        "sample_count": len(samples),
        "elapsed_ns": last.time_ns - first.time_ns,
        "clock_ticks_per_second": ticks_per_second,
        "rss_first_bytes": baseline,
        "rss_last_bytes": last.memory[0],
        "rss_sampled_max_bytes": rss_max,
        "rss_sampled_increase_bytes": increase,
        "rss_lifetime_high_water_bytes_reported": last.memory[1],
        "rss_anon_last_bytes": last.memory[2],
        "rss_file_last_bytes": last.memory[3],
        "rss_shmem_last_bytes": last.memory[4],
        "swap_last_bytes_reported": last.memory[5],
        "user_cpu_ticks_delta": last.stat.user_ticks - first.stat.user_ticks,
        "system_cpu_ticks_delta": last.stat.system_ticks - first.stat.system_ticks,
        "threads_last_observed": last.stat.threads,
    }


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "SINGLE_PROCESS_SAMPLED_DIAGNOSTIC",
        "process_instance_authenticated": False,
        "executable_identity_verified": False,
        "model_binding_verified": False,
        "workload_isolation_verified": False,
        "measurement_coverage_complete": False,
        "accelerator_mapping_verified": False,
        "runtime_requirements_established": False,
        "resource_availability_established": False,
        "resource_reserved": False,
        "generation_requested": False,
        "model_load_requested": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(pid, *, samples=5, interval_ms=250):
    """Observe one existing PID for at most 20 samples / 9.5s sleep.

    No PID or comm/command-line, path, task, model or identity in report.
    Proc fd pins the directory, start ticks checked within/across samples.
    This is not executable attestation, nor proof of no exec/namespace
    change or attribution to a particular model. On any interrupted or
    inconsistent sample discard aggregate rather than publish partial max.
    """
    _bounded_int(pid, 1, MAX_PID)
    _bounded_int(samples, 2, MAX_SAMPLES)
    _bounded_int(interval_ms, MIN_INTERVAL_MS, MAX_INTERVAL_MS)
    if sys.platform != "linux":
        raise ObservationRefusal("LINUX_REQUIRED")
    try:
        ticks = os.sysconf("SC_CLK_TCK")
        _bounded_int(ticks, 1, 1000000)
        directory = os.open("/proc/" + str(pid),
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            result = []
            for i in range(samples):
                if i:
                    time.sleep(interval_ms / 1000)
                result.append(_sample(directory, pid))
            metrics = _summarize(tuple(result), ticks)
        finally:
            os.close(directory)
    except (OSError, OverflowError):
        raise ObservationRefusal("PROCESS_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", **metrics}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Forest I4: bounded passive Linux process sample")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval-ms", type=int, default=250)
    args = parser.parse_args(argv)
    try:
        output = observe(args.pid, samples=args.samples, interval_ms=args.interval_ms)
        status = 0
    except ObservationRefusal as exc:
        output, status = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        output, status = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(output, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
