#!/usr/bin/env python3
"""Bounded read-only DRM GPU observation. No vendor commands or host writes."""
import argparse
import itertools
import json
import re
import sys
import time
from pathlib import Path

SCHEMA = "post-apollo-gpu-observation-v1"
MAX_DEVICES = 8
MAX_BYTES = 65536
MAX_NUMBER = (1 << 53) - 1


def entries(path, limit):
    items = list(itertools.islice(path.iterdir(), limit + 1))
    if len(items) > limit:
        raise ValueError("enumeration budget")
    return items


def read_int(path, minimum, maximum):
    try:
        with path.open("r", encoding="ascii") as stream:
            value = stream.read(65)
        if len(value) > 64 or not re.fullmatch(r"-?[0-9]+", value.strip()):
            return None
        number = int(value)
        return number if minimum <= number <= maximum else None
    except (OSError, ValueError):
        return None


def discover(drm, devices_root):
    rows = {}
    for card in sorted(entries(drm, 256)):
        if not re.fullmatch(r"card(?:0|[1-9][0-9]{0,5})", card.name):
            continue
        # A DRM card without a device link is not a hardware device.
        link = card / "device"
        if not link.is_symlink():
            continue
        device = link.resolve(strict=True)
        identity = device.relative_to(devices_root).as_posix()
        if len(identity) > 256 or not re.fullmatch(r"[A-Za-z0-9_./:+-]+", identity):
            raise ValueError("unsupported device identity")
        st = device.stat()
        rows[card.name] = (device, identity, st.st_dev, st.st_ino)
        if len(rows) > MAX_DEVICES:
            raise ValueError("GPU coverage exceeds budget")
    if not rows:
        raise ValueError("no hardware DRM cards")
    if len({row[1] for row in rows.values()}) != len(rows):
        raise ValueError("ambiguous DRM device identity")
    return rows


def metrics(device):
    busy = read_int(device / "gpu_busy_percent", 0, 100)
    used = read_int(device / "mem_info_vram_used", 0, MAX_NUMBER)
    total = read_int(device / "mem_info_vram_total", 1, MAX_NUMBER)
    if used is None or total is None or used > total:
        used = total = None
    # Read only a uniquely associated hwmon temp1; not necessarily junction
    # temperature. No global sensor scan and no arbitrary sensor selection.
    temp = None
    try:
        sensors = [p for p in entries(device / "hwmon", 16)
                   if re.fullmatch(r"hwmon[0-9]+", p.name)]
        if len(sensors) == 1:
            temp = read_int(sensors[0] / "temp1_input", -40000, 200000)
    except (OSError, ValueError):
        pass
    return [busy, used, total, temp]


def validate(duration, interval):
    if not 1 <= duration <= 30 or not 1 <= interval <= min(5, duration):
        raise ValueError("invalid GPU calibration")
    if (duration + interval - 1) // interval > 12:
        raise ValueError("GPU observation budget")


def capture(duration, interval, drm=Path("/sys/class/drm"),
            devices_root=Path("/sys/devices"), workflow_clock=False):
    validate(duration, interval)
    pinned = discover(drm, devices_root)
    start = time.monotonic_ns()
    previous = 0
    rows = []
    has_data = False
    for scheduled in range(interval, duration + interval, interval):
        scheduled = min(scheduled, duration)
        deadline = start + scheduled * 1000000000
        while time.monotonic_ns() < deadline:
            time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))
        if discover(drm, devices_root) != pinned:
            raise ValueError("GPU identity or topology changed")
        devices = [[card, info[1], *metrics(info[0])]
                   for card, info in pinned.items()]
        if discover(drm, devices_root) != pinned:
            raise ValueError("GPU identity changed during observation")
        elapsed = (time.monotonic_ns() - start) // 1000000
        if elapsed <= previous or elapsed > 45000:
            raise ValueError("GPU observation timing")
        has_data = has_data or any(any(v is not None for v in d[2:]) for d in devices)
        rows.append({"schema": SCHEMA, "event": "gpu", "sequence": len(rows)+1,
                     "elapsedMs": elapsed, "intervalMs": elapsed-previous, "devices": devices})
        previous = elapsed
        if scheduled == duration:
            break
    if not has_data:
        raise ValueError("no supported GPU measurements")
    rows.append({"schema": SCHEMA, "event": "complete", "samples": len(rows),
                 "observedMs": previous,
            **({"startedMonotonicMs": start // 1000000,
                "monotonicMs": start // 1000000 + previous} if workflow_clock else {}), "calibration": {"kind": "gpu",
                 "durationSeconds": duration, "intervalMs": interval*1000}})
    output = "\n".join(json.dumps(r, ensure_ascii=True, allow_nan=False,
                                  separators=(",", ":")) for r in rows) + "\n"
    if len(output) > MAX_BYTES:
        raise ValueError("GPU report exceeds budget")
    return output


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--workshop", action="store_true", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--interval", type=int, required=True)
    parser.add_argument("--workflow-clock", action="store_true")
    args = parser.parse_args()
    try:
        sys.stdout.write(capture(args.duration, args.interval, workflow_clock=args.workflow_clock))
    except (OSError, ValueError, RuntimeError) as exc:
        print("GPU capture unavailable: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
