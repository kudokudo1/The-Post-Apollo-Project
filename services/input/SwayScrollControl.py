#!/usr/bin/env python3
"""Sway per-device scroll-factor controller.

Read actual input devices from Sway IPC. A change requires a specific,
known identifier, a bounded factor, and a matching previously observed value.
Never run a shell, load a compositor config, touch keystrokes, or modify files.
These changes are LIVE SESSION ONLY and may be reset by Sway restart/reload.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from typing import Any

DEVICE_ID = re.compile(r"^[A-Za-z0-9_.:+-]{1,160}$")
MAX_DEVICES = 64
MAX_RESPONSE = 262144
MIN_FACTOR = 0.25
MAX_FACTOR = 6.0
EPSILON = 0.001


class ScrollControlError(Exception):
    pass


def run_sway(arguments: list[str]) -> str:
    try:
        response = subprocess.run(
            ["swaymsg", *arguments], capture_output=True,
            text=True, timeout=4, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScrollControlError("SWAY_IPC_UNAVAILABLE") from exc
    if response.returncode != 0 or len(response.stdout) > MAX_RESPONSE:
        raise ScrollControlError("SWAY_COMMAND_FAILED")
    return response.stdout


def parse_factor(raw: Any, *, user_choice: bool) -> float:
    if isinstance(raw, bool):
        raise ScrollControlError("INVALID_FACTOR")
    try:
        value = float(raw)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ScrollControlError("INVALID_FACTOR") from exc
    if not math.isfinite(value) or value < MIN_FACTOR or value > MAX_FACTOR:
        raise ScrollControlError("FACTOR_OUT_OF_RANGE")
    # The UI exposes presets, but restoring an observed custom factor must
    # preserve its numeric value instead of rounding to a different preset.
    return value


def list_devices() -> list[dict[str, Any]]:
    raw = run_sway(["-t", "get_inputs"])
    try:
        devices = json.loads(raw)
    except ValueError as exc:
        raise ScrollControlError("INVALID_SWAY_REPLY") from exc
    if not isinstance(devices, list) or len(devices) > MAX_DEVICES:
        raise ScrollControlError("INVALID_DEVICE_LIST")
    result = []
    for device in devices:
        if not isinstance(device, dict) or device.get("type") != "pointer":
            continue
        identifier = device.get("identifier")
        if not isinstance(identifier, str) or not DEVICE_ID.fullmatch(identifier):
            continue
        try:
            factor = parse_factor(device.get("scroll_factor"),
                                  user_choice=False)
        except ScrollControlError:
            # An unavailable or unbounded factor cannot be safely restored.
            continue
        name = str(device.get("name") or identifier)[:100]
        result.append({
            "identifier": identifier,
            "name": name,
            "factor": factor,
            "kind": "touchpad" if "touchpad" in name.casefold()
                    else "pointer"
        })
    if len(result) != len(set(x["identifier"] for x in result)):
        raise ScrollControlError("DUPLICATE_DEVICE")
    return result


def inspect() -> dict[str, Any]:
    return {"status": "ok", "scope": "live_sway_only",
            "devices": list_devices()}


def apply(identifier: str, new_factor: str, expected: str) -> dict[str, Any]:
    if not DEVICE_ID.fullmatch(identifier):
        raise ScrollControlError("INVALID_DEVICE_ID")
    desired = parse_factor(new_factor, user_choice=True)
    previous = parse_factor(expected, user_choice=False)
    devices = list_devices()
    existing = next((x for x in devices if x["identifier"] == identifier),
                    None)
    if existing is None:
        raise ScrollControlError("DEVICE_NOT_FOUND")
    if abs(existing["factor"] - previous) > EPSILON:
        raise ScrollControlError("STALE_DEVICE_FACTOR")
    if abs(previous - desired) <= EPSILON:
        return {"status": "unchanged", "identifier": identifier,
                "before": previous, "factor": previous,
                "scope": "live_sway_only"}
    raw = run_sway(["input", identifier, "scroll_factor", f"{desired:.6f}"])
    try:
        outcome = json.loads(raw)
    except ValueError as exc:
        raise ScrollControlError("INVALID_APPLY_REPLY") from exc
    if not isinstance(outcome, list) or not outcome or any(
        not isinstance(x, dict) or x.get("success") is not True
        for x in outcome
    ):
        raise ScrollControlError("SWAY_REJECTED_CHANGE")
    updated = next(
        (x for x in list_devices() if x["identifier"] == identifier), None
    )
    if updated is None or abs(updated["factor"] - desired) > EPSILON:
        raise ScrollControlError("CHANGE_NOT_VERIFIED")
    return {"status": "applied", "identifier": identifier,
            "before": previous, "factor": updated["factor"],
            "scope": "live_sway_only"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["list"]:
            response = inspect()
        elif len(args) == 4 and args[0] == "apply":
            response = apply(args[1], args[2], args[3])
        else:
            raise ScrollControlError("INVALID_ACTION")
        print(json.dumps(response, separators=(",", ":")))
        return 0
    except ScrollControlError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
