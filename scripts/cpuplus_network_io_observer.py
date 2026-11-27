#!/usr/bin/env python3
"""Bounded on-demand network-interface counter observation, no test traffic."""
import argparse
import itertools
import json
import re
import sys
import time
from pathlib import Path

SCHEMA = "post-apollo-network-io-v1"
MAX_INTERFACES = 32
MAX_BYTES = 65536
MAX_SAFE = (1 << 53) - 1
MAX_COUNTER = (1 << 64) - 1
NAME = re.compile(r"[A-Za-z0-9_.+@-]{1,15}")
# /proc/net/dev folds some error/drop fields. Preserve these as kernel
# interface counters, not end-to-end packet loss.
FIELDS = (0, 1, 2, 3, 8, 9, 10, 11)
STATES = {"unknown", "notpresent", "down", "lowerlayerdown", "testing", "dormant", "up"}


def bounded_text(path, limit):
    with path.open("r", encoding="ascii") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("network source exceeds budget")
    return value.strip()


def unsigned(value, cap=MAX_COUNTER):
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("invalid network counter")
    number = int(value)
    if number > cap:
        raise ValueError("network counter exceeds budget")
    return number


def parse_dev(text):
    lines = text.splitlines()
    if len(lines) < 2 or "Receive" not in lines[0] or "Transmit" not in lines[0] or "bytes" not in lines[1]:
        raise ValueError("invalid network counter header")
    result = {}
    for line in lines[2:]:
        name, sep, rest = line.strip().partition(":")
        if not sep or not NAME.fullmatch(name) or name in result:
            raise ValueError("unsupported or duplicate interface")
        parts = rest.split()
        if len(parts) != 16:
            raise ValueError("invalid interface counters")
        counters = tuple(unsigned(v) for v in parts)
        result[name] = counters
        if len(result) > MAX_INTERFACES:
            raise ValueError("interface coverage exceeds budget")
    if not result:
        raise ValueError("no visible interfaces")
    return result


def identities(net, devices_root):
    result = {}
    entries = list(itertools.islice(net.iterdir(), MAX_INTERFACES + 1))
    if len(entries) > MAX_INTERFACES:
        raise ValueError("interface enumeration budget")
    for entry in sorted(entries):
        if not NAME.fullmatch(entry.name):
            raise ValueError("unsupported interface name")
        path = entry.resolve(strict=True)
        relative = path.relative_to(devices_root)
        if not relative.parts:
            raise ValueError("invalid interface path")
        index = unsigned(bounded_text(path / "ifindex", 32), 2147483647)
        link = unsigned(bounded_text(path / "iflink", 32), 2147483647)
        kind = unsigned(bounded_text(path / "type", 32), 65535)
        if index == 0 or link == 0:
            raise ValueError("invalid interface identity")
        info = path.stat()
        # Include loopback and virtual interfaces independently. Never sum
        # stacked devices, bridges, VPNs or loopback into a host total.
        result[entry.name] = (path, index, link, kind, info.st_dev, info.st_ino)
    if len({x[1] for x in result.values()}) != len(result):
        raise ValueError("duplicate interface index")
    return result


def optional_state(path):
    try:
        state = bounded_text(path / "operstate", 32)
        return state if state in STATES else None
    except (OSError, ValueError):
        return None


def snapshot(procdev, net, devices_root):
    pinned = identities(net, devices_root)
    counters = parse_dev(bounded_text(procdev, 65536))
    if counters.keys() != pinned.keys():
        raise ValueError("proc/sysfs interface coverage mismatch")
    states = {name: optional_state(row[0]) for name, row in pinned.items()}
    if identities(net, devices_root) != pinned:
        raise ValueError("interface identity changed during read")
    return pinned, counters, states


def delta(before, after):
    if any(b < a for a, b in zip(before, after)):
        raise ValueError("interface counter reset")
    values = [after[i] - before[i] for i in FIELDS]
    if any(v > MAX_SAFE for v in values):
        raise ValueError("network delta exceeds budget")
    return values


def validate(duration, interval):
    if type(duration) is not int or type(interval) is not int:
        raise ValueError("integer calibration required")
    if not 1 <= duration <= 30 or not 1 <= interval <= min(5, duration):
        raise ValueError("invalid network calibration")
    if (duration + interval - 1) // interval > 12:
        raise ValueError("network observation budget")


def capture(duration, interval, procdev=Path("/proc/net/dev"),
            net=Path("/sys/class/net"), devices_root=Path("/sys/devices")):
    validate(duration, interval)
    devices_root = devices_root.resolve(strict=True)
    pinned, before, _ = snapshot(procdev, net, devices_root)
    start = time.monotonic_ns()
    previous = 0
    lines = []
    size = 0

    def append(row):
        nonlocal size
        line = json.dumps(row, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        size += len(line) + 1
        if size > MAX_BYTES:
            raise ValueError("network report exceeds budget")
        lines.append(line)

    for scheduled in range(interval, duration + interval, interval):
        scheduled = min(scheduled, duration)
        deadline = start + scheduled * 1000000000
        while time.monotonic_ns() < deadline:
            time.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9))
        active, after, states = snapshot(procdev, net, devices_root)
        elapsed = (time.monotonic_ns() - start) // 1000000
        if active != pinned or after.keys() != before.keys():
            raise ValueError("interface topology or identity changed")
        if not previous < elapsed <= 45000:
            raise ValueError("network observation timing")
        append({"schema": SCHEMA, "event": "netio", "sequence": len(lines) + 1,
                "elapsedMs": elapsed, "intervalMs": elapsed - previous,
                "interfaces": [[name, *pinned[name][1:4], states[name],
                                *delta(before[name], after[name])]
                               for name in sorted(pinned)]})
        before, previous = after, elapsed
        if scheduled == duration:
            break
    append({"schema": SCHEMA, "event": "complete", "samples": len(lines),
            "observedMs": previous, "calibration": {"kind": "netio",
                "durationSeconds": duration, "intervalMs": interval * 1000}})
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
        print("Network capture unavailable: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
