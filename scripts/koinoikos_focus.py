#!/usr/bin/env python3
"""Koinoikos widget-only spatial Focus Mode router.

Used only by the opt-in Sway binding mode. Native application focus stays
owned by Sway: this router never moves native windows or falls back to Sway.
No service, injected keyboard daemon, persistent writes or extra dependency.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from typing import Any


DIRECTIONS = ("left", "right", "up", "down")


def command(*args: str, timeout: float = 2.0) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def qs(method: str, *args: str) -> tuple[int, str]:
    return command("qs", "ipc", "call", "relationshipFocus", method, *args)


def snapshot() -> dict[str, Any] | None:
    code, output = qs("snapshot")
    if code != 0:
        return None
    try:
        # The IPC method returns a JSON string, without framing.
        data = json.loads(output)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("surfaces"), list):
        return None
    return data


def menu_windows(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if data is None:
        return []
    out: list[dict[str, Any]] = []
    for row in data["surfaces"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        if not all(isinstance(row.get(k), (int, float))
                   for k in ("x", "y", "w", "h")):
            continue
        if row["w"] <= 0 or row["h"] <= 0:
            continue
        out.append(dict(row, kind="menu"))
    return out


def center(item: dict[str, Any]) -> tuple[float, float]:
    return item["x"] + item["w"] / 2, item["y"] + item["h"] / 2


def nearest(items: list[dict[str, Any]],
            current: dict[str, Any], direction: str) -> dict[str, Any] | None:
    """Spatial half-plane navigation with lateral offset penalty."""
    cx, cy = center(current)
    best = None
    score = float("inf")
    for candidate in items:
        if candidate["id"] == current["id"]:
            continue
        tx, ty = center(candidate)
        dx, dy = tx - cx, ty - cy
        major, minor = ((dx, dy) if direction == "right" else
                        (-dx, dy) if direction == "left" else
                        (dy, dx) if direction == "down" else (-dy, dx))
        if major <= 0.5:
            continue
        # Prefer nearby surfaces straight ahead; allow diagonals when needed.
        value = math.hypot(major, minor) + abs(minor) * 1.5
        if value < score:
            score, best = value, candidate
    return best


def focus_target(target: dict[str, Any]) -> bool:
    """Select only registered Quickshell widgets, never a Sway container."""
    code, result = qs("select", target["id"])
    return code == 0 and result.strip().lower() == "true"


def move(direction: str) -> bool:
    data = snapshot()
    # The held Sway chord activates the temporary widget session only when
    # a directional key is actually pressed. Super+grave alone never selects
    # or cycles widgets. No fallback to Sway application focus.
    if data is None:
        return False
    if not data.get("active"):
        code, result = qs("begin")
        if code != 0 or result.strip().lower() != "true":
            return False
        data = snapshot()
        if data is None or not data.get("active"):
            return False

    items = menu_windows(data)
    if not items:
        return False
    owner = data.get("owner", "")
    current = next((item for item in items if item["id"] == owner), None)
    if current is None:
        # The first direction must itself move focus where possible, not
        # require a second arrow just to choose a starting widget.
        current = min(items, key=lambda item: (item["x"], item["y"], item["id"]))
        target = nearest(items, current, direction)
        return focus_target(target or current)

    target = nearest(items, current, direction)
    # At the edge, stay put. Never drift into the ordinary Sway layer.
    return bool(target and focus_target(target))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("move", "exit", "snapshot"))
    parser.add_argument("direction", nargs="?", choices=DIRECTIONS)
    args = parser.parse_args(argv)
    if args.action == "exit":
        # This is invoked automatically on release of grave or Super.
        # The compositor binding mode returns to default independently.
        qs("end")
        return 0
    if args.action == "snapshot":
        print(json.dumps({"qs": snapshot()}))
        return 0
    if not args.direction:
        parser.error("move requires direction")
    return 0 if move(args.direction) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
