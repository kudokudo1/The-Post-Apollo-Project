#!/usr/bin/env python3
"""Bounded, explicit read-only observation of Linux whole block-device counters.

No benchmarks, partition aggregation, device commands, file-content scans,
privileges or resident polling. Sector counters use Linux's 512-byte units.
"""
import argparse
import itertools
import json
import re
import sys
import time
from pathlib import Path

SCHEMA = "post-apollo-disk-io-v1"
MAX_DEVICES = 32
MAX_BYTES = 65536
MAX_SAFE = (1 << 53) - 1
MAX_COUNTER = (1 << 64) - 1
NAME = re.compile(r"[A-Za-z0-9_.!+\-]{1,64}")
# Linux block stat fields: reads, read merges, read sectors, read ms,
# writes, write merges, write sectors, write ms, inflight, io ms,
# weighted io ms. Discard and flush fields are not included in this version.
DELTA_FIELDS = (0, 2, 3, 4, 6, 7, 9, 10)


def bounded_text(path, limit=1024):
    with path.open("r", encoding="ascii") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("block source exceeds budget")
    return value.strip()


def unsigned(value, maximum=MAX_COUNTER):
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("invalid block counter")
    number = int(value)
    if number > maximum:
        raise ValueError("block counter exceeds budget")
    return number


def discover(block, devices_root):
    result = {}
    entries = list(itertools.islice(block.iterdir(), 257))
    if len(entries) > 256:
        raise ValueError("block enumeration budget")
    for entry in sorted(entries):
        # /sys/block contains whole block devices, not their partitions.
        # Exclude loop, dm, zram and other purely virtual block objects.
        if not (entry / "device").is_symlink():
            continue
        path = entry.resolve(strict=True)
        relative = path.relative_to(devices_root)
        if not relative.parts or relative.parts[0] == "virtual":
            continue
        if not NAME.fullmatch(entry.name):
            raise ValueError("unsupported block name")
        if (path / "partition").exists():
            raise ValueError("unexpected partition in whole-device scope")
        device_id = bounded_text(path / "dev", 32).split(":")
        if len(device_id) != 2:
            raise ValueError("invalid block device number")
        major, minor = (unsigned(v, 1048575) for v in device_id)
        try:
            diskseq = unsigned(bounded_text(path / "diskseq", 32), MAX_SAFE)
        except FileNotFoundError:
            diskseq = None
        info = path.stat()
        result[entry.name] = (path, major, minor, diskseq, info.st_dev, info.st_ino)
        if len(result) > MAX_DEVICES:
            raise ValueError("block device coverage exceeds budget")
    if not result:
        raise ValueError("no device-backed whole block devices")
    if len({row[1:3] for row in result.values()}) != len(result):
        raise ValueError("ambiguous block identity")
    return result


def parse_stat(text):
    fields = text.split()
    if not 11 <= len(fields) <= 32:
        raise ValueError("invalid block stat shape")
    values = tuple(unsigned(v) for v in fields[:11])
    if values[8] > MAX_SAFE:
        raise ValueError("in-flight count exceeds budget")
    return values


def snapshot(block, devices_root):
    pinned = discover(block, devices_root)
    values = {name: parse_stat(bounded_text(identity[0] / "stat"))
              for name, identity in pinned.items()}
    if discover(block, devices_root) != pinned:
        raise ValueError("block identity changed during observation")
    return pinned, values


def delta(before, after):
    # Also check the merge counters for resets, even though they are not
    # projected. In-flight is a point reading and may decrease normally.
    if any(after[i] < before[i] for i in range(11) if i != 8):
        raise ValueError("block counter reset")
    values = [after[i] - before[i] for i in DELTA_FIELDS]
    if any(v > MAX_SAFE for v in values):
        raise ValueError("block delta exceeds budget")
    if values[1] > MAX_SAFE // 512 or values[4] > MAX_SAFE // 512:
        raise ValueError("block byte delta exceeds budget")
    values[1] *= 512
    values[4] *= 512
    return values + [after[8]]


def validate(duration, interval):
    if type(duration) is not int or type(interval) is not int:
        raise ValueError("integer disk calibration required")
    if not 1 <= duration <= 30 or not 1 <= interval <= min(5, duration):
        raise ValueError("invalid disk calibration")
    if (duration + interval - 1) // interval > 12:
        raise ValueError("disk observation budget")


def capture(duration, interval, block=Path("/sys/block"),
            devices_root=Path("/sys/devices")):
    validate(duration, interval)
    devices_root = devices_root.resolve(strict=True)
    pinned, before = snapshot(block, devices_root)
    start = time.monotonic_ns()
    previous = 0
    lines = []
    size = 0

    def append(row):
        nonlocal size
        line = json.dumps(row, ensure_ascii=True, allow_nan=False,
                          separators=(",", ":"))
        size += len(line) + 1
        if size > MAX_BYTES:
            raise ValueError("disk report exceeds budget")
        lines.append(line)

    for scheduled in range(interval, duration + interval, interval):
        scheduled = min(scheduled, duration)
        deadline = start + scheduled * 1000000000
        while time.monotonic_ns() < deadline:
            time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))
        current, after = snapshot(block, devices_root)
        elapsed = (time.monotonic_ns() - start) // 1000000
        if current != pinned or after.keys() != before.keys():
            raise ValueError("block topology or identity changed")
        if not previous < elapsed <= 45000:
            raise ValueError("disk observation timing")
        append({"schema": SCHEMA, "event": "diskio",
                "sequence": len(lines) + 1, "elapsedMs": elapsed,
                "intervalMs": elapsed - previous,
                "devices": [[name, *pinned[name][1:4],
                             *delta(before[name], after[name])]
                            for name in sorted(pinned)]})
        before = after
        previous = elapsed
        if scheduled == duration:
            break
    append({"schema": SCHEMA, "event": "complete", "samples": len(lines),
            "observedMs": previous,
            "calibration": {"kind": "diskio", "durationSeconds": duration,
                            "intervalMs": interval * 1000}})
    # Complete capture only; failures and cancellation publish no receipt.
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--workshop", action="store_true", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--interval", type=int, required=True)
    args = parser.parse_args()
    try:
        sys.stdout.write(capture(args.duration, args.interval))
    except (OSError, ValueError, RuntimeError) as exc:
        print("Disk capture unavailable: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
