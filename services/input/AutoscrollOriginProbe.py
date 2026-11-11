#!/usr/bin/env python3
"""Read-only capability inventory for universal autoscroll on Wayland/Sway.

This does NOT discover the global pointer position. It never creates a Wayland
surface, grabs a mouse, opens an evdev device, generates virtual input, or
installs compositor keybindings. A matching protocol advertisement is only
evidence of availability, not authority to inject input.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

CAPABILITIES = ("zwlr_layer_shell_v1", "zwlr_virtual_pointer_manager_v1")
OUTPUT = re.compile(r"^[A-Za-z0-9_.:+-]{1,120}$")
MAX_REPLY = 524288


class ProbeError(Exception):
    pass


def run_readonly(cmd, timeout=2.5):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True,
                                check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("READ_ONLY_COMMAND_UNAVAILABLE") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_REPLY:
        raise ProbeError("READ_ONLY_COMMAND_FAILED")
    return result.stdout


def parse_outputs(raw):
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProbeError("INVALID_OUTPUT_REPLY") from exc
    if not isinstance(data, list) or len(data) > 16:
        raise ProbeError("INVALID_OUTPUT_REPLY")
    result = []
    for output in data:
        if not isinstance(output, dict):
            raise ProbeError("INVALID_OUTPUT_ITEM")
        if output.get("active") is not True:
            continue
        name, rect, scale = (output.get("name"), output.get("rect"),
                             output.get("scale"))
        if not isinstance(name, str) or not OUTPUT.fullmatch(name):
            raise ProbeError("INVALID_OUTPUT_NAME")
        if not isinstance(rect, dict) or not all(
            isinstance(rect.get(key), int) and not isinstance(rect.get(key), bool)
            for key in ("x", "y", "width", "height")
        ):
            raise ProbeError("INVALID_OUTPUT_RECT")
        if (not -100000 <= rect["x"] <= 100000
                or not -100000 <= rect["y"] <= 100000
                or not 1 <= rect["width"] <= 16384
                or not 1 <= rect["height"] <= 16384):
            raise ProbeError("INVALID_OUTPUT_RECT")
        if (isinstance(scale, bool) or not isinstance(scale, (int, float))
                or not math.isfinite(scale) or not 0.5 <= scale <= 6):
            raise ProbeError("INVALID_OUTPUT_SCALE")
        result.append({"name": name, "x": rect["x"], "y": rect["y"],
                       "width": rect["width"], "height": rect["height"],
                       "scale": scale})
    if not result or len({x["name"] for x in result}) != len(result):
        raise ProbeError("MISSING_OR_DUPLICATE_OUTPUT")
    return result


def parse_seats(raw):
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProbeError("INVALID_SEAT_REPLY") from exc
    if not isinstance(data, list) or len(data) != 1:
        return False
    seat = data[0]
    return (isinstance(seat, dict)
            and isinstance(seat.get("name"), str)
            and len(seat["name"]) > 0)


def parse_protocols(text):
    # wayland-info is an *inventory* utility: no app protocol is bound here.
    if not isinstance(text, str) or len(text) > MAX_REPLY:
        raise ProbeError("INVALID_WAYLAND_INFO")
    return {name: name in text for name in CAPABILITIES}


def stop_socket_available():
    from AutoscrollStopChannel import inspect_socket, socket_path
    try:
        return inspect_socket(socket_path()) is not None
    except Exception:
        return False


def inspect():
    env = {
        "sway_socket": bool(os.environ.get("SWAYSOCK")),
        "wayland_display": bool(os.environ.get("WAYLAND_DISPLAY")),
        "uinput_writable": os.access("/dev/uinput", os.W_OK),
        "python_evdev": importlib.util.find_spec("evdev") is not None,
        "stop_endpoint_present": stop_socket_available()
    }
    if not env["sway_socket"]:
        return {"status": "no_sway_socket", "environment": env,
                "pointer_origin_verified": False, "runtime_enabled": False}
    outputs = parse_outputs(run_readonly(["swaymsg", "-t", "get_outputs"]))
    single_seat = parse_seats(run_readonly(["swaymsg", "-t", "get_seats"]))
    try:
        protocols = parse_protocols(run_readonly(["wayland-info"], timeout=3))
        inventory = "available"
    except ProbeError:
        protocols = {name: False for name in CAPABILITIES}
        inventory = "unavailable"
    return {
        "status": "inventory_only",
        "environment": env,
        "outputs": outputs,
        "single_seat": single_seat,
        "wayland_info": inventory,
        "protocols": protocols,
        "pointer_origin_verified": False,
        "pointer_target_verified": False,
        "escape_binding_verified": False,
        "runtime_enabled": False,
        "overlay_allowed": False,
        "note": "PROTOCOL_DISCOVERY_IS_NOT_POINTER_LOCATION_AUTHORITY"
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args != ["--inspect"]:
            raise ProbeError("INVALID_ACTION")
        result = inspect()
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except ProbeError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc),
                          "pointer_origin_verified": False,
                          "runtime_enabled": False}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
