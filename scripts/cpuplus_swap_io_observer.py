#!/usr/bin/env python3
"""Explicit bounded read-only host swap traffic, pressure and active zram capture."""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCHEMA = "post-apollo-swap-io-v1"
MAX_SAFE = (1 << 53) - 1
MAX_COUNTER = (1 << 64) - 1
MAX_BYTES = 65536
MAX_SWAP = 32
MAX_ZRAM = 16


def read_text(path, limit):
    with path.open("r", encoding="ascii") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("source exceeds budget")
    return value


def uint(value, cap=MAX_SAFE):
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("invalid unsigned counter")
    number = int(value)
    if number > cap:
        raise ValueError("counter exceeds budget")
    return number


def fields(text, required, unit=None, cap=MAX_SAFE):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0].rstrip(":")
        if key not in required:
            continue
        if key in result or len(parts) != (3 if unit else 2) or (unit and parts[2] != unit):
            raise ValueError("invalid or duplicate field")
        result[key] = uint(parts[1], cap)
    if set(result) != set(required):
        raise ValueError("required field unavailable")
    return result


def parse_meminfo(text):
    f = fields(text, ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"), "kB")
    if not 0 < f["MemTotal"] or f["MemAvailable"] > f["MemTotal"] or f["SwapFree"] > f["SwapTotal"]:
        raise ValueError("invalid memory capacity")
    return [f["MemTotal"], f["MemAvailable"], f["SwapTotal"], f["SwapTotal"] - f["SwapFree"]]


def parse_swaps(text):
    lines = text.splitlines()
    if not lines or lines[0].split() != ["Filename", "Type", "Size", "Used", "Priority"]:
        raise ValueError("invalid active swap list")
    result = {}
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            raise ValueError("unsupported active swap row")
        name, kind, size, used, priority = parts
        if name in result or kind not in ("partition", "file") or len(name) > 4096:
            raise ValueError("invalid swap identity")
        size, used = uint(size), uint(used)
        if not 0 < size or used > size or not re.fullmatch(r"-?[0-9]{1,10}", priority):
            raise ValueError("invalid swap capacity")
        priority = int(priority)
        result[name] = (kind, size, priority)
        if len(result) > MAX_SWAP:
            raise ValueError("active swap budget")
    return result


def parse_pressure(text):
    rows = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] not in ("some", "full"):
            continue
        name = parts[0]
        if name in rows or len(parts) != 5:
            raise ValueError("invalid PSI row")
        values = {}
        for part in parts[1:]:
            key, sep, value = part.partition("=")
            if not sep or key in values:
                raise ValueError("invalid PSI field")
            values[key] = value
        if set(values) != {"avg10", "avg60", "avg300", "total"}:
            raise ValueError("invalid PSI fields")
        for key in ("avg10", "avg60", "avg300"):
            if not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,6})?", values[key]) or not 0 <= float(values[key]) <= 100:
                raise ValueError("invalid PSI average")
        rows[name] = (float(values["avg10"]), uint(values["total"], MAX_COUNTER))
    if set(rows) != {"some", "full"}:
        raise ValueError("missing PSI row")
    return rows


def optional_pressure(proc):
    try:
        return parse_pressure(read_text(proc / "pressure/memory", 4096))
    except (OSError, ValueError):
        return None


def active_zram(active):
    names = sorted(name[5:] for name in active if re.fullmatch(r"/dev/zram(?:0|[1-9][0-9]{0,5})", name))
    if len(names) > MAX_ZRAM:
        raise ValueError("active zram budget")
    return names


def zram_snapshot(block, names):
    result = []
    for name in names:
        try:
            parts = read_text(block / name / "mm_stat", 1024).split()
            if not 3 <= len(parts) <= 16:
                raise ValueError("unsupported zram mm_stat")
            original, compressed, allocated = (uint(v) for v in parts[:3])
            result.append([name, original, compressed, allocated])
        except (OSError, ValueError):
            result.append([name, None, None, None])
    return result


def snapshot(proc, block):
    active = parse_swaps(read_text(proc / "swaps", 65536))
    memory = parse_meminfo(read_text(proc / "meminfo", 65536))
    traffic = fields(read_text(proc / "vmstat", 131072), ("pswpin", "pswpout"), cap=MAX_COUNTER)
    pressure = optional_pressure(proc)
    zram = zram_snapshot(block, active_zram(active))
    if parse_swaps(read_text(proc / "swaps", 65536)) != active:
        raise ValueError("swap topology changed during read")
    return active, memory, traffic, pressure, zram


def delta(before, after, scale=1):
    if after < before or after - before > MAX_SAFE // scale:
        raise ValueError("counter reset or delta exceeds budget")
    return (after - before) * scale


def pressure_delta(before, after):
    if before is None or after is None:
        return None
    some = delta(before["some"][1], after["some"][1])
    full = delta(before["full"][1], after["full"][1])
    return [after["some"][0], after["full"][0], some, full]


def validate(duration, interval, page_size):
    if type(duration) is not int or type(interval) is not int:
        raise ValueError("integer calibration required")
    if not 1 <= duration <= 30 or not 1 <= interval <= min(5, duration):
        raise ValueError("invalid swap calibration")
    if (duration + interval - 1) // interval > 12:
        raise ValueError("swap observation budget")
    if type(page_size) is not int or not 1024 <= page_size <= 1048576 or page_size & (page_size - 1):
        raise ValueError("unsupported system page size")


def capture(duration, interval, proc=Path("/proc"), block=Path("/sys/block"), page_size=None):
    page_size = os.sysconf("SC_PAGE_SIZE") if page_size is None else page_size
    validate(duration, interval, page_size)
    pinned, memory, previous, pressure, _ = snapshot(proc, block)
    capacity = (memory[0], memory[2])
    start = time.monotonic_ns()
    elapsed_previous = 0
    lines, size = [], 0

    def append(row):
        nonlocal size
        line = json.dumps(row, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        size += len(line) + 1
        if size > MAX_BYTES:
            raise ValueError("swap report exceeds budget")
        lines.append(line)

    for scheduled in range(interval, duration + interval, interval):
        scheduled = min(scheduled, duration)
        deadline = start + scheduled * 1000000000
        while time.monotonic_ns() < deadline:
            time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))
        active, mem, counters, psi, zram = snapshot(proc, block)
        elapsed = (time.monotonic_ns() - start) // 1000000
        if active != pinned or (mem[0], mem[2]) != capacity:
            raise ValueError("swap topology or memory capacity changed")
        if not elapsed_previous < elapsed <= 45000:
            raise ValueError("swap observation timing")
        append({"schema": SCHEMA, "event": "swapio", "sequence": len(lines)+1,
                "elapsedMs": elapsed, "intervalMs": elapsed-elapsed_previous,
                "memoryKiB": mem, "swapBytes": [
                    delta(previous["pswpin"], counters["pswpin"], page_size),
                    delta(previous["pswpout"], counters["pswpout"], page_size)],
                "pressure": pressure_delta(pressure, psi), "zram": zram})
        previous, pressure, elapsed_previous = counters, psi, elapsed
        if scheduled == duration:
            break
    append({"schema": SCHEMA, "event": "complete", "samples": len(lines),
            "observedMs": elapsed_previous, "pageSize": page_size,
            "calibration": {"kind": "swapio", "durationSeconds": duration, "intervalMs": interval*1000}})
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--workshop", required=True, action="store_true")
    parser.add_argument("--duration", required=True, type=int)
    parser.add_argument("--interval", required=True, type=int)
    args = parser.parse_args()
    try:
        sys.stdout.write(capture(args.duration, args.interval))
    except (OSError, ValueError, RuntimeError) as exc:
        print("Swap capture unavailable: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
