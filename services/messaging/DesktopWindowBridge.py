#!/usr/bin/env python3
"""Fail-closed, opt-in Sway docking of an already-open provider desktop window.

Works on the provider's *window*, not its messages, session, or credentials.
Only a uniquely matched real provider process can be docked. A generated Sway
con_id is used so no regex or broad app_id/class selector can affect others.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

EXECUTABLE_NAMES = {
    "signal": frozenset({"signal-desktop", "signal-desktop.AppImage"}),
    "viber": frozenset({"viber", "Viber"}),
    "wechat": frozenset({"wechat", "weixin", "WeChat", "Weixin"}),
}
MARK_PREFIX = "post-apollo-social-desktop-"
SELECTOR_WIDTH = 110
MAX_TREE_SIZE = 8 * 1024 * 1024


def walk(tree):
    if not isinstance(tree, dict):
        return
    yield tree
    for key in ("nodes", "floating_nodes"):
        for child in tree.get(key, []) or []:
            yield from walk(child)


def executable_name(pid: int) -> str:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return ""
    try:
        return Path(os.readlink(f"/proc/{pid}/exe")).name
    except (OSError, ValueError):
        return ""


def candidates(tree: dict, service: str, name_reader=executable_name) -> list[dict]:
    if service not in EXECUTABLE_NAMES:
        raise ValueError("Unsupported service")
    found = []
    for node in walk(tree):
        cid = node.get("id")
        pid = node.get("pid")
        if not isinstance(cid, int) or isinstance(cid, bool) or cid <= 0:
            continue
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            continue
        # Must be a real client view. Do not mistake Sway workspaces/containers
        # or unrelated processes for the messaging application.
        view_id = node.get("app_id") or (node.get("window_properties") or {}).get("class")
        if not isinstance(view_id, str) or not view_id:
            continue
        if name_reader(pid) in EXECUTABLE_NAMES[service]:
            found.append(node)
    return found


def unique_window(tree: dict, service: str, name_reader=executable_name) -> dict | None:
    found = candidates(tree, service, name_reader)
    # No arbitrary largest-window choice; two matching windows is ambiguous.
    return found[0] if len(found) == 1 else None


def social_window(tree: dict) -> dict | None:
    matches = [
        node for node in walk(tree)
        if node.get("name") == "QS_SOCIAL_MENU"
        and isinstance(node.get("rect"), dict)
        and node.get("visible") is True
    ]
    return matches[0] if len(matches) == 1 else None


def read_tree() -> dict:
    result = subprocess.run(
        ["swaymsg", "-r", "-t", "get_tree"], text=True, capture_output=True,
        timeout=4, check=True,
    )
    if len(result.stdout) > MAX_TREE_SIZE:
        raise ValueError("Sway window tree is too large")
    tree = json.loads(result.stdout)
    if not isinstance(tree, dict):
        raise ValueError("Unexpected Sway tree")
    return tree


def dock_rect(social: dict) -> tuple[int, int, int, int]:
    rect = social["rect"]
    width, height = int(rect["width"]), int(rect["height"])
    if width < SELECTOR_WIDTH + 230 or height < 220:
        raise ValueError("Social menu is too small to dock a provider")
    x = int(rect["x"]) + SELECTOR_WIDTH + 1
    y = int(rect["y"]) + 1
    return x, y, width - SELECTOR_WIDTH - 2, height - 2


def sway_command(text: str) -> None:
    response = subprocess.run(["swaymsg", "-r", text],
                              text=True, capture_output=True, timeout=4,
                              check=True)
    data = json.loads(response.stdout)
    if not isinstance(data, list) or not data or not all(
        isinstance(row, dict) and row.get("success") is True for row in data
    ):
        raise ValueError("Sway rejected the window operation")


def operation(action: str, service: str, *, tree: dict | None = None,
              name_reader=executable_name, execute=sway_command) -> dict:
    if service not in EXECUTABLE_NAMES or action not in ("probe", "dock", "hide"):
        raise ValueError("Unsupported provider-window action")
    tree = read_tree() if tree is None else tree
    matches = candidates(tree, service, name_reader)
    window = matches[0] if len(matches) == 1 else None
    mark = MARK_PREFIX + service
    managed = window is not None and mark in (window.get("marks") or [])
    result = {
        "serviceId": service, "action": action,
        "windowAvailable": window is not None,
        "ambiguous": len(matches) > 1, "docked": bool(managed),
        "changed": False,
    }
    if action == "probe":
        result["detail"] = (
            "Multiple provider windows detected; cannot dock safely" if len(matches) > 1
            else "Provider window available for docking" if window
            else "No uniquely identified provider window; leave it separate"
        )
        return result
    if window is None:
        result["detail"] = "Provider window not uniquely identified; nothing changed"
        return result
    cid = int(window["id"])
    criterion = f"[con_id={cid}]"
    if action == "hide":
        if not managed:
            result["detail"] = "Window is not managed by Social; nothing changed"
            return result
        execute(f"{criterion} move scratchpad")
        result["changed"] = True
        result["detail"] = "Managed provider window hidden"
        return result

    social = social_window(tree)
    if social is None:
        result["detail"] = "Post-Apollo Social window not visible; nothing changed"
        return result
    x, y, width, height = dock_rect(social)
    # No provider account data is read, and neither 'kill' nor package setup
    # is ever issued. A mark allows hide to affect only windows we docked.
    commands = [f"{criterion} floating enable",
                f"{criterion} border none"]
    if managed and not window.get("visible", False):
        commands.append(f"{criterion} scratchpad show")
    commands += [
        f"{criterion} resize set width {width} px height {height} px",
        f"{criterion} move absolute position {x} px {y} px",
        f"{criterion} mark --add {mark}",
        f"{criterion} focus",
    ]
    execute("; ".join(commands))
    result["docked"] = True
    result["changed"] = True
    result["detail"] = "Provider desktop window docked; native chat API still unsupported"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicit Post-Apollo desktop window docking")
    parser.add_argument("action", choices=("probe", "dock", "hide"))
    parser.add_argument("service", choices=tuple(EXECUTABLE_NAMES))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(operation(args.action, args.service), separators=(",", ":")))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, OverflowError):
        # Never echo arbitrary Sway window titles or environment/session data.
        print(json.dumps({
            "serviceId": args.service, "action": args.action,
            "windowAvailable": False, "docked": False, "changed": False,
            "detail": "Provider window action unavailable; no safe match confirmed",
        }))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
