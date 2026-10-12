#!/usr/bin/env python3
"""Koinoikos spatial Focus Mode router.

Used only by the opt-in Sway binding mode. Default Sway keys remain intact.
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


def sway_tree() -> dict[str, Any] | None:
    code, raw = command("swaymsg", "-r", "-t", "get_tree")
    if code:
        return None
    try:
        tree = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return tree if isinstance(tree, dict) else None


def native_windows(tree: dict[str, Any] | None) -> tuple[list[dict[str, Any]], Any]:
    """Only real, visible client leaves on visible workspaces.

    Do not include layer shells, inactive workspace clients, containers,
    scratchpad contents, floating parent shells or invisible placeholders.
    """
    windows: list[dict[str, Any]] = []
    current_id = None

    def visit(node: dict[str, Any], visible: bool) -> None:
        nonlocal current_id
        typ = node.get("type")
        if typ == "workspace":
            visible = bool(node.get("visible"))
        rect = node.get("rect") or {}
        has_client = bool(node.get("app_id")) or node.get("window") is not None
        if (visible and has_client and isinstance(node.get("id"), int)
                and all(isinstance(rect.get(k), (int, float))
                        for k in ("x", "y", "width", "height"))
                and rect["width"] > 0 and rect["height"] > 0):
            item = {"id": "native:" + str(node["id"]),
                    "kind": "native", "con_id": node["id"],
                    "x": rect["x"], "y": rect["y"],
                    "w": rect["width"], "h": rect["height"]}
            windows.append(item)
            if node.get("focused"):
                current_id = item["id"]
        for kind in ("nodes", "floating_nodes"):
            for child in node.get(kind, []):
                if isinstance(child, dict):
                    visit(child, visible)

    if tree:
        visit(tree, False)
    return windows, current_id


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
    if target["kind"] == "menu":
        code, result = qs("select", target["id"])
        return code == 0 and result.strip().lower() == "true"
    # First release exclusive layer-shell keyboard ownership, then ask
    # Sway to focus a real container using its original compositor semantics.
    qs("select", "native")
    code, _ = command("swaymsg", f'[con_id={int(target["con_id"])}] focus')
    return code == 0


def move(direction: str) -> bool:
    data = snapshot()
    if data is None or not data.get("active"):
        # Native-only fallback: Sway navigation stays useful even if QS
        # cannot connect; do not strand the operator in the binding mode.
        code, _ = command("swaymsg", "focus", direction)
        return code == 0
    native, focused_id = native_windows(sway_tree())
    items = native + menu_windows(data)
    owner = data.get("owner", "native")
    wanted_id = focused_id if owner == "native" else owner
    current = next((v for v in items if v["id"] == wanted_id), None)
    if current is None:
        current = next((v for v in items if v["id"] == focused_id), None)
    if current is None:
        return False
    target = nearest(items, current, direction)
    return bool(target and focus_target(target))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enter", "move", "exit", "snapshot"))
    parser.add_argument("direction", nargs="?", choices=DIRECTIONS)
    args = parser.parse_args(argv)
    if args.action == "enter":
        # For this initial bridge, shell.qml still remembers the active
        # Git/Hospital keyboard owner. The IPC bridge checks availability.
        _, output = qs("begin")
        return 0 if output.lower() == "true" else 1
    if args.action == "exit":
        qs("end")
        return 0
    if args.action == "snapshot":
        print(json.dumps({"qs": snapshot(), "native": native_windows(sway_tree())[0]}))
        return 0
    if not args.direction:
        parser.error("move requires direction")
    return 0 if move(args.direction) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
