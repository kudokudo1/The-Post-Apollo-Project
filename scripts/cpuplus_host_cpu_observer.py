#!/usr/bin/env python3
"""Explicit bounded host CPU capture; no writes, process scans or child commands."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

SCHEMA = "post-apollo-host-cpu-v1"
MAX_CPUS = 128
MAX_BYTES = 65536
MAX_STAT = 131072


def bounded_text(path, limit):
    with path.open("r", encoding="ascii") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("source exceeds budget")
    return value


def parse_stat(text):
    rows = {}
    for line in text.splitlines():
        fields = line.split()
        if not fields or not re.fullmatch(r"cpu(?:[0-9]+)?", fields[0]):
            continue
        name = fields[0]
        cpu = -1 if name == "cpu" else int(name[3:])
        if cpu in rows or cpu > 1048575 or len(fields) < 9:
            raise ValueError("invalid CPU identity/counters")
        # guest and guest_nice already belong to user and nice.
        values = tuple(int(v) for v in fields[1:9])
        if any(v < 0 for v in values):
            raise ValueError("negative counter")
        rows[cpu] = values
        if len(rows) > MAX_CPUS + 1:
            raise ValueError("CPU coverage exceeds budget")
    if -1 not in rows or len(rows) < 2:
        raise ValueError("missing aggregate or logical CPUs")
    return rows


def delta(before, after):
    values = tuple(b - a for a, b in zip(before, after))
    # Linux iowait may decrease; do not silently clamp a counter reset.
    total = sum(values)
    if any(v < 0 for v in values) or not 0 < total <= 1000000000:
        raise ValueError("non-comparable CPU counters")
    return [total, total - values[3] - values[4], values[4]]


def optional_pressure():
    try:
        line = next(l for l in bounded_text(Path("/proc/pressure/cpu"), 4096).splitlines()
                    if l.startswith("some "))
        value = float(next(v[6:] for v in line.split() if v.startswith("avg10=")))
        return value if 0 <= value <= 100 else None
    except (OSError, ValueError, StopIteration):
        return None


def optional_frequency(cpu):
    try:
        value = int(bounded_text(Path("/sys/devices/system/cpu") / ("cpu%d" % cpu)
                                 / "cpufreq/scaling_cur_freq", 64).strip())
        return value if 0 < value <= 100000000 else None
    except (OSError, ValueError):
        return None


def validate(duration, interval):
    if not 1 <= duration <= 30 or not 1 <= interval <= min(5, duration):
        raise ValueError("invalid CPU calibration")
    if (duration + interval - 1) // interval > 12:
        raise ValueError("CPU observation budget")


def capture(duration, interval, workflow_clock=False):
    validate(duration, interval)
    before = parse_stat(bounded_text(Path("/proc/stat"), MAX_STAT))
    ids = sorted(k for k in before if k >= 0)
    start = time.monotonic_ns()
    previous_ms = 0
    count = 0
    encoded = []
    size = 0

    def append(row):
        nonlocal size
        line = json.dumps(row, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        size += len(line) + 1
        if size > MAX_BYTES:
            raise ValueError("CPU report exceeds budget")
        encoded.append(line)

    for scheduled in range(interval, duration + interval, interval):
        scheduled = min(scheduled, duration)
        deadline = start + scheduled * 1000000000
        while time.monotonic_ns() < deadline:
            time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))
        after = parse_stat(bounded_text(Path("/proc/stat"), MAX_STAT))
        elapsed = (time.monotonic_ns() - start) // 1000000
        if after.keys() != before.keys() or elapsed <= previous_ms or elapsed > 45000:
            raise ValueError("CPU topology or timing changed")
        count += 1
        append({"schema": SCHEMA, "event": "hostcpu", "sequence": count,
                "elapsedMs": elapsed, "intervalMs": elapsed - previous_ms,
                "aggregate": delta(before[-1], after[-1]),
                "cores": [[cpu, *delta(before[cpu], after[cpu]), optional_frequency(cpu)]
                          for cpu in ids],
                "psiSomeAvg10": optional_pressure()})
        before = after
        previous_ms = elapsed
        if scheduled == duration:
            break
    append({"schema": SCHEMA, "event": "complete", "samples": count,
            "observedMs": previous_ms,
            **({"startedMonotonicMs": start // 1000000,
                "monotonicMs": start // 1000000 + previous_ms} if workflow_clock else {}),
            "calibration": {"kind": "hostcpu", "durationSeconds": duration,
                            "intervalMs": interval * 1000}})
    # Publish only a complete bounded capture. Cancellation cannot produce a
    # fabricated terminal receipt; the session owner handles the child exit.
    return "\n".join(encoded) + "\n"


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--workshop", action="store_true", required=True)
    parser.add_argument("--duration", required=True, type=int)
    parser.add_argument("--interval", required=True, type=int)
    parser.add_argument("--workflow-clock", action="store_true")
    args = parser.parse_args()
    try:
        sys.stdout.write(capture(args.duration, args.interval, workflow_clock=args.workflow_clock))
    except (OSError, ValueError) as exc:
        print("CPU capture unavailable: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
