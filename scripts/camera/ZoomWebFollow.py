#!/usr/bin/env python3
"""Continuous Camera/Zoom Web actor follower using Social's Sway IPC bridge.

The Camera QML frame is the sole geometry leader. Unlike the old one-shot
ZoomWebHost.enter(), this process stays alive while Zoom mode is active,
observes the real Sway client rectangle, and coalesces updates to the latest
Camera viewport. No credentials, window titles or browser contents are read.

stdin NDJSON: {"op":"target","revision":1,"output":"DP-5",
               "x":123,"y":123,"width":734,"height":540}
stdout NDJSON: {"kind":"zoom-web-follow","revision":1,
                "state":"ALIGNED|MISALIGNED|MISSING|UNVERIFIED|FAILED",
                "aligned":true|false}
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import select
import sys
import time


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("FOLLOWER_MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[2]
host = _load("_camera_zoom_web_host", Path(__file__).with_name("ZoomWebHost.py"))
social = _load("_camera_social_geometry", ROOT / "widgets/messanger/DiscordGeometry.py")

POLL_SECONDS = 0.12
COMMAND_COOLDOWN_SECONDS = 0.25
MAX_COMMANDS_PER_TARGET = 120


def _target_from_outputs(outputs, message):
    output_name = message.get("output")
    if not isinstance(output_name, str) or not host.re.fullmatch(
            r"[A-Za-z0-9_.-]{1,48}", output_name):
        raise ValueError("INVALID_OUTPUT")
    selected = [item for item in outputs if isinstance(item, dict)
                and item.get("name") == output_name
                and item.get("active") is True]
    if len(selected) != 1:
        raise ValueError("OUTPUT_NOT_FOUND")
    output = selected[0].get("rect") or {}
    fields = ("x", "y", "width", "height")
    if any(type(output.get(field)) is not int for field in fields):
        raise ValueError("OUTPUT_GEOMETRY_UNAVAILABLE")
    if any(type(message.get(field)) is not int for field in fields):
        raise ValueError("INVALID_VIEWPORT")
    x, y, width, height = (message[field] for field in fields)
    if not (480 <= width <= 4000 and 300 <= height <= 2500
            and x >= 0 and y >= 0
            and x + width <= output["width"]
            and y + height <= output["height"]):
        raise ValueError("INVALID_VIEWPORT")
    return ((output["x"] + x, output["y"] + y, width, height), output)


def _sync_command(node, geometry, output_rect, setup):
    """Bounded, numeric con_id only. No generic title/class Sway criteria."""
    if type(node.get("id")) is not int or node["id"] <= 0:
        raise ValueError("INVALID_ACTOR")
    left, top, right, bottom = host._client_insets(node)
    x, y, width, height = geometry
    outer_x, outer_y = x - left, y - top
    outer_w, outer_h = width + left + right, height + top + bottom
    if (outer_x < output_rect["x"] or outer_y < output_rect["y"]
            or outer_x + outer_w > output_rect["x"] + output_rect["width"]
            or outer_y + outer_h > output_rect["y"] + output_rect["height"]):
        raise ValueError("CLIENT_FRAME_OUTSIDE_OUTPUT")
    criterion = "[con_id=%d]" % node["id"]
    commands = []
    if setup:
        commands += [f"{criterion} floating enable", f"{criterion} border none"]
    commands += [
        f"{criterion} resize set width {outer_w} px height {outer_h} px",
        f"{criterion} move absolute position {outer_x} px {outer_y} px"
    ]
    return "; ".join(commands)


class ZoomFollower:
    def __init__(self, profile, ipc, clock=time.monotonic):
        self.profile = profile
        self.ipc = ipc
        self.clock = clock
        self.message = None
        self.revision = -1
        self.latest_state = None
        self.last_command_time = -1e6
        self.commands_for_target = 0
        self.actor_id = None

    def emit(self, state, aligned=False):
        key = (self.revision, state, aligned)
        if key == self.latest_state:
            return
        self.latest_state = key
        print(json.dumps({"kind": "zoom-web-follow",
                          "revision": self.revision,
                          "state": state, "aligned": aligned},
                         separators=(",", ":")), flush=True)

    def set_target(self, message):
        if message.get("op") != "target":
            raise ValueError("INVALID_FOLLOW_ACTION")
        revision = message.get("revision")
        if type(revision) is not int or not 0 <= revision <= 1_000_000_000:
            raise ValueError("INVALID_FOLLOW_REVISION")
        if revision <= self.revision:
            return
        self.message = {key: message.get(key) for key in (
            "output", "x", "y", "width", "height")}
        self.revision = revision
        self.latest_state = None
        self.commands_for_target = 0
        self.last_command_time = -1e6
        self.emit("CHECKING")

    def tick(self):
        if self.message is None:
            return
        try:
            outputs = self.ipc.request(3)
            geometry, output = _target_from_outputs(outputs, self.message)
            tree = self.ipc.request(4)
            actor, error = host._unique_actor(self.profile, tree=tree)
            if actor is None:
                self.actor_id = None
                self.emit("MISSING" if error == "ACTOR_MISSING" else "UNVERIFIED")
                return
            if actor.get("visible") is not True:
                self.emit("UNVERIFIED")
                return
            if host._near(actor, geometry):
                self.actor_id = actor["id"]
                self.emit("ALIGNED", True)
                return
            self.emit("MISALIGNED")
            if self.commands_for_target >= MAX_COMMANDS_PER_TARGET:
                self.emit("FAILED")
                return
            now = self.clock()
            if now - self.last_command_time < COMMAND_COOLDOWN_SECONDS:
                return
            command = _sync_command(actor, geometry, output,
                                    setup=self.actor_id != actor["id"])
            result = self.ipc.request(0, command)
            if not isinstance(result, list) or not result or not all(
                    isinstance(v, dict) and v.get("success") is True
                    for v in result):
                self.emit("FAILED")
                return
            self.actor_id = actor["id"]
            self.last_command_time = now
            self.commands_for_target += 1
            # Next compositor observation, not an optimistic command return,
            # is the only event allowed to mark the input hole as aligned.
        except (OSError, ValueError, RuntimeError, TypeError,
                ConnectionError, AttributeError):
            self.emit("FAILED")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", required=True)
    args = parser.parse_args(argv)
    if not host.IDENTITY_PATTERN.fullmatch(args.identity):
        return 2
    try:
        prefix = host._social_browser_prefix()
        profile = host._private_profile(prefix, args.identity)
        ipc = social.SwayIPC()
        # Require an existing Sway IPC socket, never use a fallback shell.
        if not (os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK")):
            raise RuntimeError("SWAY_IPC_UNAVAILABLE")
        follower = ZoomFollower(profile, ipc)
        while True:
            readable, _, _ = select.select([sys.stdin], [], [], POLL_SECONDS)
            if readable:
                line = sys.stdin.readline()
                if not line:
                    break
                if len(line) > 2048:
                    follower.emit("FAILED")
                    continue
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError("INVALID_FOLLOW_MESSAGE")
                    if message.get("op") == "stop":
                        break
                    follower.set_target(message)
                except (ValueError, TypeError):
                    follower.emit("FAILED")
                    continue
            follower.tick()
    except (OSError, RuntimeError, ValueError):
        print(json.dumps({"kind":"zoom-web-follow", "revision":-1,
                          "state":"FAILED", "aligned":False}), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
