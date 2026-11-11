#!/usr/bin/env python3
"""Read-only, bounded Linux input LED observation.

Reports keyboard LED brightness as a PROXY, never Sway/XKB lock state.
The production CLI uses only /sys/class/leds. Test-only callers can inject
an isolated fixture root. No access to /dev/input, no privileges, no writes.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

PRODUCTION_ROOT = Path("/sys/class/leds")
LED_NAME = re.compile(r"^input[0-9]{1,5}::(numlock|capslock)$")
MAX_ENTRIES = 64
MAX_MATCHES = 24
MAX_READ_BYTES = 16


def read_brightness(file: Path) -> bool | None:
    """Return LED brightness >0, or unknown (never silently assume OFF)."""
    try:
        with file.open("rb") as handle:
            content = handle.read(MAX_READ_BYTES + 1)
        if len(content) > MAX_READ_BYTES:
            return None
        raw = content.strip()
        if not raw or not raw.isdigit():
            return None
        value = int(raw)
        if value > 255:
            return None
        return value > 0
    except (OSError, ValueError):
        return None


def normalize(states: list[bool | None], count: int) -> dict:
    if count == 0:
        return {"status": "absent", "value": None, "count": 0}
    if count > MAX_MATCHES:
        return {"status": "too_many", "value": None, "count": count}
    if any(x is None for x in states):
        return {"status": "unreadable", "value": None, "count": count}
    if len(set(states)) != 1:
        return {"status": "conflict", "value": None, "count": count}
    return {"status": "observed", "value": "on" if states[0] else "off",
            "count": count}


def sample(led_root: Path = PRODUCTION_ROOT) -> dict:
    """Read only matched kernel LED brightness entries, not keystrokes."""
    root = Path(led_root)
    try:
        entries = list(root.iterdir())
    except OSError:
        return {"source": "linux-led-brightness-proxy",
                "status": "unavailable",
                "num": normalize([], 0), "caps": normalize([], 0)}
    if len(entries) > MAX_ENTRIES:
        return {"source": "linux-led-brightness-proxy",
                "status": "too_many_entries",
                "num": normalize([None], 1),
                "caps": normalize([None], 1)}
    values = {"num": [], "caps": []}
    for entry in entries:
        matched = LED_NAME.fullmatch(entry.name)
        if not matched:
            continue
        lock = "num" if matched.group(1) == "numlock" else "caps"
        values[lock].append(read_brightness(entry / "brightness"))
    return {"source": "linux-led-brightness-proxy", "status": "sampled",
            "num": normalize(values["num"], len(values["num"])),
            "caps": normalize(values["caps"], len(values["caps"]))}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["sample"]:
        print(json.dumps({"status": "invalid_action"}, separators=(",", ":")))
        return 2
    print(json.dumps(sample(), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
