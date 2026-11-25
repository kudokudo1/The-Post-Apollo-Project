#!/usr/bin/env python3
"""Bounded external Quickshell memory observation; JSONL to stdout only."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from syntagma_quickshell_thread_sampler import find_quickshell, parse_stat_line

FIELDS = ("Rss", "Pss", "Pss_Anon", "Pss_File", "Pss_Shmem",
          "Private_Clean", "Private_Dirty", "Swap", "SwapPss")


def parse_rollup(text):
    values = {}
    for line in text.splitlines():
        key, sep, tail = line.partition(":")
        if not sep or key not in FIELDS:
            continue
        parts = tail.split()
        if (key in values or len(parts) != 2 or parts[1] != "kB"
                or not parts[0].isascii() or not parts[0].isdecimal()):
            raise ValueError("invalid rollup field: " + key)
        values[key] = int(parts[0])
    if any(key not in values for key in FIELDS):
        raise ValueError("incomplete rollup")
    if values["Private_Clean"] + values["Private_Dirty"] > values["Rss"]:
        raise ValueError("private resident exceeds RSS")
    return values


HOST_FIELDS = ("MemTotal", "MemAvailable", "MemFree", "AnonPages",
               "Cached", "Shmem", "SReclaimable", "SUnreclaim",
               "SwapTotal", "SwapFree")


def parse_host_memory(text):
    values = {}
    for line in text.splitlines():
        key, sep, tail = line.partition(":")
        if not sep or key not in HOST_FIELDS:
            continue
        parts = tail.split()
        if (key in values or len(parts) != 2 or parts[1] != "kB"
                or not parts[0].isascii() or not parts[0].isdecimal()):
            raise ValueError("invalid host memory field")
        values[key] = int(parts[0])
    if any(key not in values for key in HOST_FIELDS):
        raise ValueError("incomplete host memory")
    if (values["MemTotal"] <= 0
            or values["MemAvailable"] > values["MemTotal"]
            or values["MemFree"] > values["MemTotal"]
            or values["SwapFree"] > values["SwapTotal"]):
        raise ValueError("inconsistent host memory")
    return values


def host_memory(path):
    # Optional additive evidence; preserve process capture if unavailable.
    # No summation of overlapping kernel counters and no attribution inference.
    try:
        return parse_host_memory(path.read_text())
    except (OSError, ValueError):
        return None


def identity(path, uid):
    if path.stat().st_uid != uid:
        raise ValueError("different owner")
    stat = parse_stat_line((path / "stat").read_text())
    if stat["name"] != "quickshell":
        raise ValueError("not Quickshell")
    return stat


def observe(path, uid, start):
    before = identity(path, uid)
    if before["start"] != start:
        raise ValueError("process replaced")
    host_start = time.monotonic_ns()
    host_before = host_memory(path.parent / "meminfo")
    memory = parse_rollup((path / "smaps_rollup").read_text())
    host_after = host_memory(path.parent / "meminfo")
    host_span = time.monotonic_ns() - host_start
    after = identity(path, uid)
    if after["start"] != start or after["ticks"] < before["ticks"]:
        raise ValueError("process replaced or inconsistent")
    return {
        "event": "memory", "tsMs": round(time.time() * 1000),
        "pid": int(path.name), "startTicks": start,
        "memoryKiB": memory,
        "hostObservation": {
            "beforeKiB": host_before, "afterKiB": host_after,
            "spanMs": round(host_span / 1_000_000, 3),
        },
        # Ordinary private resident pages; excludes separately accounted hugetlb.
        "privateResidentKiB": memory["Private_Clean"] + memory["Private_Dirty"],
        "pssPlusSwapPssKiB": memory["Pss"] + memory["SwapPss"],
        "cpuTicks": after["ticks"],
    }


def emit(record):
    print(json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pid", type=int)
    p.add_argument("--duration", type=int, default=120)
    p.add_argument("--interval", type=int, default=10)
    a = p.parse_args(argv)
    if not 1 <= a.duration <= 1800 or not 5 <= a.interval <= 60:
        p.error("duration 1..1800 seconds; interval 5..60 seconds")
    if a.pid is not None and a.pid <= 0:
        p.error("PID must be positive")
    uid = os.getuid()
    root = Path("/proc")
    pid = a.pid if a.pid is not None else find_quickshell(root, uid)
    if pid is None:
        print("No same-user Quickshell found.", file=sys.stderr)
        return 2
    path = root / str(pid)
    try:
        start = identity(path, uid)["start"]
    except (OSError, ValueError, IndexError):
        print("Quickshell identity unavailable.", file=sys.stderr)
        return 2
    hz = os.sysconf("SC_CLK_TCK")
    deadline = time.monotonic() + a.duration
    previous = None
    previous_time = None
    try:
        while True:
            record = observe(path, uid, start)
            now = time.monotonic()
            record["cpuPct"] = None
            record["sampleIntervalMs"] = None
            if previous is not None:
                elapsed = now - previous_time
                delta = record["cpuTicks"] - previous["cpuTicks"]
                if delta < 0 or elapsed <= 0:
                    raise ValueError("inconsistent CPU counter")
                record["cpuPct"] = round(100 * delta / hz / elapsed, 1)
                record["sampleIntervalMs"] = round(elapsed * 1000)
            emit(record)
            previous, previous_time = record, now
            remaining = deadline - now
            if remaining <= 0:
                break
            time.sleep(min(a.interval, remaining))
    except (OSError, ValueError, IndexError):
        emit({"event": "stopped", "pid": pid, "startTicks": start,
              "reason": "identity-or-observation-unavailable"})
        return 1
    except KeyboardInterrupt:
        emit({"event": "stopped", "pid": pid, "reason": "user-interrupt"})
        return 130
    emit({"event": "complete", "pid": pid, "startTicks": start})
    return 0


if __name__ == "__main__":
    sys.exit(main())
