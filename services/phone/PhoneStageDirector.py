#!/usr/bin/env python3
"""PHONE-only Sway stage for an explicitly launched BlueFerry foot wizard.

This is a compositor window placement boundary, not a pairing or phone-content
authority. Never targets a generic terminal, invokes Bluetooth/BlueFerry, or
moves the shared Social window. No shell or broad class/pid kill.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Any

SCHEMA = "post-apollo.phone.stage-director.v0"
STAGE_APP_ID = "post-apollo-social-phone-setup"
SOCIAL_TITLE = "QS_SOCIAL_MENU"
MAX_TREE = 8 * 1024 * 1024
MAX_COORD = 32768
MAX_SIZE = 8192


def _walk(node: object):
    if type(node) is not dict:
        return
    yield node
    for key in ("nodes", "floating_nodes"):
        for child in node.get(key, []) if type(node.get(key)) is list else []:
            yield from _walk(child)


def _exe(pid: int) -> str:
    try:
        return Path(os.readlink(f"/proc/{pid}/exe")).name
    except (OSError, ValueError):
        return ""


def _rect(value: object) -> dict[str, int] | None:
    if type(value) is not dict:
        return None
    if any(type(value.get(k)) is not int for k in ("x", "y", "width", "height")):
        return None
    if value["width"] <= 0 or value["height"] <= 0:
        return None
    return {k: value[k] for k in ("x", "y", "width", "height")}


def _unique(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    return nodes[0] if len(nodes) == 1 else None


def _stage_actor(tree: dict, executable: Callable[[int], str]) -> dict | None:
    matches = []
    for node in _walk(tree):
        if node.get("app_id") != STAGE_APP_ID:
            continue
        pid, con_id = node.get("pid"), node.get("id")
        if (type(pid) is int and pid > 0 and type(con_id) is int
                and con_id > 0 and executable(pid) == "foot"
                and _rect(node.get("rect")) is not None):
            matches.append(node)
    return _unique(matches)


def _social_actor(tree: dict) -> dict | None:
    return _unique([
        node for node in _walk(tree)
        if node.get("name") == SOCIAL_TITLE
        and node.get("visible") is True
        and _rect(node.get("rect")) is not None
    ])


def _read_tree() -> dict:
    p = subprocess.run(["swaymsg", "-r", "-t", "get_tree"],
                       capture_output=True, text=True, timeout=4, check=True)
    if len(p.stdout) > MAX_TREE:
        raise ValueError("Tree too large")
    tree = json.loads(p.stdout)
    if type(tree) is not dict:
        raise ValueError("Malformed Sway tree")
    return tree


def _execute(command: str) -> None:
    p = subprocess.run(["swaymsg", "-r", command],
                       capture_output=True, text=True, timeout=4, check=True)
    parsed = json.loads(p.stdout)
    if (type(parsed) is not list or not parsed
            or not all(type(x) is dict and x.get("success") is True
                       for x in parsed)):
        raise ValueError("Sway operation denied")


def _result(state: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": "STAGE_ONLY",
        "state": state,
        "verifiedHole": False,
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def _actual_content(node: dict) -> dict[str, int] | None:
    outer = _rect(node.get("rect"))
    if outer is None:
        return None
    inner = _rect(node.get("window_rect"))
    if inner is None:
        return outer
    if (inner["x"] < 0 or inner["y"] < 0
            or inner["x"] + inner["width"] > outer["width"] + 1
            or inner["y"] + inner["height"] > outer["height"] + 1):
        return None
    return {
        "x": outer["x"] + inner["x"],
        "y": outer["y"] + inner["y"],
        "width": inner["width"],
        "height": inner["height"],
    }


def operation(action: str, *, local: tuple[int, int, int, int] | None = None,
              tree: dict | None = None,
              executable: Callable[[int], str] = _exe,
              execute: Callable[[str], None] = _execute) -> dict[str, object]:
    """One exact foot actor only. Return a hole ONLY after observed fit."""
    if action not in ("sync", "close"):
        return _result("REFUSED")
    if action == "sync":
        if (type(local) is not tuple or len(local) != 4
                or any(type(v) is not int for v in local)):
            return _result("REFUSED")
        x, y, width, height = local
        if (x < 0 or y < 0 or width < 200 or height < 120
                or max(x, y) > MAX_COORD
                or width > MAX_SIZE or height > MAX_SIZE):
            return _result("REFUSED")

    try:
        observed = _read_tree() if tree is None else tree
        if type(observed) is not dict:
            return _result("UNAVAILABLE")
        stage = _stage_actor(observed, executable)
        if stage is None:
            return _result("ACTOR_NOT_FOUND")
        selector = f'[con_id={stage["id"]}]'
        if action == "close":
            execute(f"{selector} kill")
            return _result("CLOSE_REQUESTED")
        if stage.get("visible") is not True:
            return _result("ACTOR_NOT_FOUND")
        social = _social_actor(observed)
        if social is None:
            return _result("HOST_NOT_FOUND")
        host = _rect(social["rect"])
        assert host is not None
        if x + width > host["width"] or y + height > host["height"]:
            return _result("REFUSED")
        target = {
            "x": host["x"] + x, "y": host["y"] + y,
            "width": width, "height": height,
        }
        actual = _actual_content(stage)
        if (stage.get("visible") is True and actual == target):
            return {**_result("ALIGNED"), "verifiedHole": True}
        # Sway operations target only this verified foot con_id. A successful
        # resize request is not proof of fit; the NEXT observation checks it.
        execute(
            f"{selector} floating enable, border none, "
            f"resize set width {width} px height {height} px, "
            f"move absolute position {target['x']} px {target['y']} px"
        )
        return _result("POSITION_REQUESTED")
    except (OSError, ValueError, subprocess.SubprocessError,
            OverflowError, TypeError, KeyError):
        return _result("UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--close"]:
        result = operation("close")
    elif len(args) == 5 and args[0] == "--sync":
        try:
            local = tuple(int(v) for v in args[1:])
        except ValueError:
            result = _result("REFUSED")
        else:
            result = operation("sync", local=local)
    else:
        result = _result("REFUSED")
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["state"] not in ("REFUSED", "UNAVAILABLE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
