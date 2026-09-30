#!/usr/bin/env python3
"""
Generic persistent Sway window-assembly tracker for Post-Apollo.

A scene owns one canonical rectangle. Each member is defined by an affine
transform from that scene rectangle:

    member.x      = scene.x + xRel * scene.width  + xPx
    member.y      = scene.y + yRel * scene.height + yPx
    member.width  =           wRel * scene.width  + wPx
    member.height =           hRel * scene.height + hPx

When a focusable/canLead member is actively moved or resized, the bridge
inverts that transform to recover the scene rectangle, then directly moves
all follower windows through persistent Sway IPC. Latest geometry wins, so
fast drags do not build a stale command backlog.

Protocol: newline-delimited JSON on stdin/stdout.

Commands:
  {"op":"define","scene":"tv","rect":{...},"members":[...]}
  {"op":"scene","scene":"tv","rect":{...},"sync":true}
  {"op":"watch","scene":"tv","enabled":true}
  {"op":"sample","scene":"tv"}
  {"op":"sync","scene":"tv","member":"screen","rect":{...}}
  {"op":"remove","scene":"tv"}
  {"op":"quit"}

Member example:
  {
    "id":"screen",
    "match":{"appId":"post-apollo-terminal"},
    "canLead":true,
    "setup":true,
    "transform":{
      "xRel":0.0, "xPx":34,
      "yRel":0.0, "yPx":28,
      "wRel":1.0, "wPx":-250,
      "hRel":1.0, "hPx":-220
    }
  }

The bridge is intentionally UI-agnostic. QML owns scene semantics and visual
state; this helper only owns fast geometry observation/correlation/mutation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

MAGIC = b"i3-ipc"
HEADER = struct.Struct("=6sII")

IPC_COMMAND = 0
IPC_GET_TREE = 4


class SwayIPC:
    def __init__(self) -> None:
        self.sock: socket.socket | None = None

    @staticmethod
    def socket_path() -> str:
        path = os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK")
        if path:
            return path

        return subprocess.check_output(
            ["sway", "--get-socketpath"],
            text=True,
        ).strip()

    def connect(self) -> None:
        self.close()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path())
        self.sock = sock

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.sock.close()
        except OSError:
            pass
        self.sock = None

    def _recv_exact(self, count: int) -> bytes:
        if self.sock is None:
            raise ConnectionError("Sway IPC socket is not connected")

        chunks: list[bytes] = []
        remaining = count

        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise ConnectionError("Sway IPC socket closed")
            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)

    def request(self, message_type: int, payload: str = "") -> Any:
        encoded = payload.encode("utf-8")

        for attempt in range(2):
            try:
                if self.sock is None:
                    self.connect()

                assert self.sock is not None
                self.sock.sendall(
                    HEADER.pack(MAGIC, len(encoded), message_type) + encoded
                )

                raw_header = self._recv_exact(HEADER.size)
                magic, length, _response_type = HEADER.unpack(raw_header)

                if magic != MAGIC:
                    raise ConnectionError("Invalid Sway IPC response magic")

                raw_payload = self._recv_exact(length)
                return json.loads(raw_payload.decode("utf-8"))

            except (OSError, ConnectionError, json.JSONDecodeError):
                self.close()
                if attempt == 1:
                    raise
                time.sleep(0.002)

        raise RuntimeError("unreachable")


def walk_tree(node: dict[str, Any]):
    yield node
    for key in ("nodes", "floating_nodes"):
        for child in node.get(key, []) or []:
            yield from walk_tree(child)


def compact_rect(rect: Any) -> dict[str, int] | None:
    if not isinstance(rect, dict):
        return None

    try:
        return {
            "x": int(rect.get("x", 0)),
            "y": int(rect.get("y", 0)),
            "width": max(1, int(rect.get("width", 1))),
            "height": max(1, int(rect.get("height", 1))),
        }
    except (TypeError, ValueError):
        return None


def normalize_rect(rect: Any) -> dict[str, int]:
    compact = compact_rect(rect)
    if compact is None:
        raise ValueError("rect must contain x/y/width/height")
    return compact


def rect_equal(a: dict[str, int] | None, b: dict[str, int], tolerance: int = 0) -> bool:
    if a is None:
        return False

    return (
        abs(a["x"] - b["x"]) <= tolerance
        and abs(a["y"] - b["y"]) <= tolerance
        and abs(a["width"] - b["width"]) <= tolerance
        and abs(a["height"] - b["height"]) <= tolerance
    )


def exact_regex(value: str) -> str:
    return "^" + re.escape(value) + "$"


def sway_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclass
class Transform:
    x_rel: float = 0.0
    x_px: float = 0.0
    y_rel: float = 0.0
    y_px: float = 0.0
    w_rel: float = 1.0
    w_px: float = 0.0
    h_rel: float = 1.0
    h_px: float = 0.0

    @classmethod
    def from_json(cls, raw: Any) -> "Transform":
        raw = raw if isinstance(raw, dict) else {}
        return cls(
            x_rel=float(raw.get("xRel", 0.0)),
            x_px=float(raw.get("xPx", 0.0)),
            y_rel=float(raw.get("yRel", 0.0)),
            y_px=float(raw.get("yPx", 0.0)),
            w_rel=float(raw.get("wRel", 1.0)),
            w_px=float(raw.get("wPx", 0.0)),
            h_rel=float(raw.get("hRel", 1.0)),
            h_px=float(raw.get("hPx", 0.0)),
        )

    def forward(self, scene: dict[str, int]) -> dict[str, int]:
        sw = float(scene["width"])
        sh = float(scene["height"])

        return {
            "x": round(scene["x"] + self.x_rel * sw + self.x_px),
            "y": round(scene["y"] + self.y_rel * sh + self.y_px),
            "width": max(1, round(self.w_rel * sw + self.w_px)),
            "height": max(1, round(self.h_rel * sh + self.h_px)),
        }

    def invert(
        self,
        member: dict[str, int],
        previous_scene: dict[str, int],
        minimum_width: int,
        minimum_height: int,
    ) -> dict[str, int]:
        # If a member dimension depends on scene size, that dimension gives us
        # a direct inverse. Fixed-width/fixed-height members preserve the last
        # known scene size and still remain valid position leaders.
        if abs(self.w_rel) > 1e-9:
            scene_width = (member["width"] - self.w_px) / self.w_rel
        else:
            scene_width = previous_scene["width"]

        if abs(self.h_rel) > 1e-9:
            scene_height = (member["height"] - self.h_px) / self.h_rel
        else:
            scene_height = previous_scene["height"]

        scene_width = max(float(minimum_width), scene_width)
        scene_height = max(float(minimum_height), scene_height)

        scene_x = member["x"] - self.x_rel * scene_width - self.x_px
        scene_y = member["y"] - self.y_rel * scene_height - self.y_px

        return {
            "x": round(scene_x),
            "y": round(scene_y),
            "width": max(1, round(scene_width)),
            "height": max(1, round(scene_height)),
        }


@dataclass
class Member:
    member_id: str
    match: dict[str, str]
    transform: Transform
    can_lead: bool = True
    enabled: bool = True
    setup: bool = True
    focus_after_sync: bool = False
    tolerance: int = 0

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "Member":
        member_id = str(raw.get("id", "")).strip()
        if not member_id:
            raise ValueError("member requires non-empty id")

        match = raw.get("match")
        if not isinstance(match, dict):
            raise ValueError(f"member {member_id}: match must be an object")

        normalized_match: dict[str, str] = {}
        for key in ("appId", "title", "rawCriteria"):
            value = match.get(key)
            if value is not None and str(value) != "":
                normalized_match[key] = str(value)

        if not normalized_match:
            raise ValueError(f"member {member_id}: match is empty")

        return cls(
            member_id=member_id,
            match=normalized_match,
            transform=Transform.from_json(raw.get("transform")),
            can_lead=bool(raw.get("canLead", True)),
            enabled=bool(raw.get("enabled", True)),
            setup=bool(raw.get("setup", True)),
            focus_after_sync=bool(raw.get("focusAfterSync", False)),
            tolerance=max(0, int(raw.get("tolerance", 0))),
        )

    def matches_node(self, node: dict[str, Any]) -> bool:
        app_id = self.match.get("appId")
        if app_id is not None and str(node.get("app_id") or "") != app_id:
            return False

        title = self.match.get("title")
        if title is not None and str(node.get("name") or "") != title:
            return False

        # rawCriteria cannot be safely evaluated against a tree locally, so it
        # is command-only. Require at least one concrete selector for tracking.
        return app_id is not None or title is not None

    def criteria(self) -> str:
        raw = self.match.get("rawCriteria")
        if raw:
            return raw

        clauses: list[str] = []

        app_id = self.match.get("appId")
        if app_id is not None:
            clauses.append(f'app_id="{sway_quote(exact_regex(app_id))}"')

        title = self.match.get("title")
        if title is not None:
            clauses.append(f'title="{sway_quote(exact_regex(title))}"')

        if not clauses:
            raise ValueError(f"member {self.member_id}: no command criteria")

        return "[" + " ".join(clauses) + "]"


@dataclass
class Scene:
    scene_id: str
    rect: dict[str, int]
    members: dict[str, Member]
    minimum_width: int = 1
    minimum_height: int = 1
    watch: bool = False
    last_leader: str | None = None


@dataclass
class PendingSync:
    criteria: str
    rect: dict[str, int]
    setup: bool
    focus: bool


class Bridge:
    def __init__(self, interval_seconds: float) -> None:
        self.interval = max(0.001, interval_seconds)

        self.poll_ipc = SwayIPC()
        self.command_ipc = SwayIPC()

        self.scenes: dict[str, Scene] = {}
        self.state_lock = threading.RLock()

        self.pending_sync: dict[tuple[str, str], PendingSync] = {}
        self.pending_lock = threading.Lock()
        self.immediate_commands: deque[str] = deque()
        self.command_event = threading.Event()

        self.stop_event = threading.Event()
        self.sample_event = threading.Event()

        self.command_thread = threading.Thread(
            target=self.command_loop,
            name="window-assembly-command",
            daemon=True,
        )
        self.poll_thread = threading.Thread(
            target=self.poll_loop,
            name="window-assembly-poll",
            daemon=True,
        )

    def start(self) -> None:
        self.command_thread.start()
        self.poll_thread.start()
        self.stdin_loop()

    def emit(self, payload: dict[str, Any]) -> None:
        print(json.dumps(payload, separators=(",", ":")), flush=True)

    def scene_snapshot_from_tree(
        self,
        scene: Scene,
        tree: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        found: dict[str, Any] = {}
        focused_leader: str | None = None

        nodes = list(walk_tree(tree))

        for member_id, member in scene.members.items():
            if not member.enabled:
                continue

            candidates: list[dict[str, Any]] = []
            for node in nodes:
                if not member.matches_node(node):
                    continue

                rect = compact_rect(node.get("rect"))
                if rect is None:
                    continue

                candidates.append({
                    "rect": rect,
                    "focused": bool(node.get("focused", False)),
                    "visible": bool(node.get("visible", False)),
                    "name": node.get("name"),
                    "appId": node.get("app_id"),
                })

            if not candidates:
                continue

            # Prefer the focused instance, then visible/largest. This handles
            # splash/secondary windows without hard-coding any application.
            entry = max(
                candidates,
                key=lambda item: (
                    1 if item["focused"] else 0,
                    1 if item["visible"] else 0,
                    item["rect"]["width"] * item["rect"]["height"],
                ),
            )

            found[member_id] = entry

            if entry["focused"] and member.can_lead:
                focused_leader = member_id

        return found, focused_leader

    def queue_sync(
        self,
        scene_id: str,
        member: Member,
        rect: dict[str, int],
        *,
        focus: bool | None = None,
        setup: bool | None = None,
    ) -> None:
        pending = PendingSync(
            criteria=member.criteria(),
            rect=normalize_rect(rect),
            setup=member.setup if setup is None else bool(setup),
            focus=member.focus_after_sync if focus is None else bool(focus),
        )

        key = (scene_id, member.member_id)

        with self.pending_lock:
            previous = self.pending_sync.get(key)
            if previous is not None:
                pending.setup = pending.setup or previous.setup
                pending.focus = pending.focus or previous.focus

            # Latest geometry wins.
            self.pending_sync[key] = pending

        self.command_event.set()

    def sync_scene(
        self,
        scene: Scene,
        observed: dict[str, Any] | None = None,
        skip_member: str | None = None,
    ) -> None:
        observed = observed or {}

        for member_id, member in scene.members.items():
            if not member.enabled or member_id == skip_member:
                continue

            desired = member.transform.forward(scene.rect)
            actual = observed.get(member_id, {}).get("rect")

            if rect_equal(actual, desired, member.tolerance):
                continue

            self.queue_sync(scene.scene_id, member, desired)

    def process_scene(self, scene: Scene, tree: dict[str, Any]) -> None:
        observed, leader_id = self.scene_snapshot_from_tree(scene, tree)

        if leader_id is not None:
            leader_entry = observed.get(leader_id)
            leader = scene.members.get(leader_id)

            if leader_entry is not None and leader is not None:
                scene.rect = leader.transform.invert(
                    leader_entry["rect"],
                    scene.rect,
                    scene.minimum_width,
                    scene.minimum_height,
                )
                scene.last_leader = leader_id

                # Hot path: the helper itself moves followers. No
                # compositor -> QML -> helper round trip.
                self.sync_scene(scene, observed, skip_member=leader_id)
        else:
            scene.last_leader = None
            self.sync_scene(scene, observed)

        self.emit({
            "op": "snapshot",
            "scene": scene.scene_id,
            "rect": scene.rect,
            "leader": scene.last_leader,
            "members": observed,
        })

    def sample(self, scene_filter: str | None = None) -> None:
        try:
            tree = self.poll_ipc.request(IPC_GET_TREE)
        except Exception as exc:
            self.emit({"op": "error", "message": f"Sway tree read failed: {exc}"})
            return

        with self.state_lock:
            scenes = list(self.scenes.values())

            for scene in scenes:
                if scene_filter is not None and scene.scene_id != scene_filter:
                    continue
                if not scene.watch and scene_filter is None:
                    continue

                self.process_scene(scene, tree)

    def poll_loop(self) -> None:
        while not self.stop_event.is_set():
            watched = False

            with self.state_lock:
                watched = any(scene.watch for scene in self.scenes.values())

            if watched:
                self.sample()
                self.sample_event.wait(self.interval)
                self.sample_event.clear()
            else:
                self.sample_event.wait()
                self.sample_event.clear()

    def build_sync_command(self, pending: PendingSync) -> str:
        rect = pending.rect
        criteria = pending.criteria

        commands: list[str] = []

        if pending.setup:
            commands.append(f"{criteria} floating enable")
            commands.append(f"{criteria} border none")

        commands.append(
            f"{criteria} resize set width {rect['width']} px "
            f"height {rect['height']} px"
        )
        commands.append(
            f"{criteria} move absolute position {rect['x']} px {rect['y']} px"
        )

        if pending.focus:
            commands.append(f"{criteria} focus")

        return "; ".join(commands)

    def command_loop(self) -> None:
        while not self.stop_event.is_set():
            self.command_event.wait()
            self.command_event.clear()

            while not self.stop_event.is_set():
                command: str | None = None

                with self.pending_lock:
                    if self.immediate_commands:
                        command = self.immediate_commands.popleft()
                    elif self.pending_sync:
                        _key, pending = self.pending_sync.popitem()
                        command = self.build_sync_command(pending)

                if command is None:
                    break

                try:
                    self.command_ipc.request(IPC_COMMAND, command)
                except Exception as exc:
                    self.emit({
                        "op": "error",
                        "message": f"Sway command failed: {exc}",
                        "command": command,
                    })

    def define_scene(self, message: dict[str, Any]) -> None:
        scene_id = str(message.get("scene", "")).strip()
        if not scene_id:
            raise ValueError("define requires scene")

        raw_members = message.get("members")
        if not isinstance(raw_members, list) or not raw_members:
            raise ValueError("define requires non-empty members array")

        members: dict[str, Member] = {}
        for raw_member in raw_members:
            if not isinstance(raw_member, dict):
                raise ValueError("member must be an object")
            member = Member.from_json(raw_member)
            members[member.member_id] = member

        rect = normalize_rect(message.get("rect"))
        minimum_width = max(1, int(message.get("minimumWidth", 1)))
        minimum_height = max(1, int(message.get("minimumHeight", 1)))

        rect["width"] = max(minimum_width, rect["width"])
        rect["height"] = max(minimum_height, rect["height"])

        scene = Scene(
            scene_id=scene_id,
            rect=rect,
            members=members,
            minimum_width=minimum_width,
            minimum_height=minimum_height,
            watch=bool(message.get("watch", False)),
        )

        with self.state_lock:
            self.scenes[scene_id] = scene

        self.emit({
            "op": "defined",
            "scene": scene_id,
            "rect": rect,
            "members": list(members.keys()),
        })

        if bool(message.get("sync", True)):
            with self.state_lock:
                self.sync_scene(scene)

        if scene.watch:
            self.sample_event.set()

    def update_scene_rect(self, message: dict[str, Any]) -> None:
        scene_id = str(message.get("scene", "")).strip()

        with self.state_lock:
            scene = self.scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"unknown scene: {scene_id}")

            rect = normalize_rect(message.get("rect"))
            rect["width"] = max(scene.minimum_width, rect["width"])
            rect["height"] = max(scene.minimum_height, rect["height"])
            scene.rect = rect

            if bool(message.get("sync", True)):
                self.sync_scene(scene)

        self.sample_event.set()

    def update_watch(self, message: dict[str, Any]) -> None:
        scene_id = str(message.get("scene", "")).strip()

        with self.state_lock:
            scene = self.scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"unknown scene: {scene_id}")
            scene.watch = bool(message.get("enabled", False))

        self.sample_event.set()

    def sync_member(self, message: dict[str, Any]) -> None:
        scene_id = str(message.get("scene", "")).strip()
        member_id = str(message.get("member", "")).strip()

        with self.state_lock:
            scene = self.scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"unknown scene: {scene_id}")

            member = scene.members.get(member_id)
            if member is None:
                raise ValueError(f"unknown member {member_id} in scene {scene_id}")

            self.queue_sync(
                scene_id,
                member,
                normalize_rect(message.get("rect")),
                focus=bool(message.get("focus", False)),
                setup=bool(message.get("setup", member.setup)),
            )

    def remove_scene(self, message: dict[str, Any]) -> None:
        scene_id = str(message.get("scene", "")).strip()

        with self.state_lock:
            self.scenes.pop(scene_id, None)

        with self.pending_lock:
            for key in list(self.pending_sync):
                if key[0] == scene_id:
                    self.pending_sync.pop(key, None)

        self.emit({"op": "removed", "scene": scene_id})

    def stdin_loop(self) -> None:
        try:
            for raw_line in sys.stdin:
                if self.stop_event.is_set():
                    break

                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    message = json.loads(raw_line)
                    if not isinstance(message, dict):
                        raise ValueError("command must be a JSON object")

                    op = str(message.get("op", ""))

                    if op == "define":
                        self.define_scene(message)
                    elif op == "scene":
                        self.update_scene_rect(message)
                    elif op == "watch":
                        self.update_watch(message)
                    elif op == "sample":
                        scene_id = str(message.get("scene", "")).strip() or None
                        self.sample(scene_id)
                    elif op == "sync":
                        self.sync_member(message)
                    elif op == "remove":
                        self.remove_scene(message)
                    elif op == "quit":
                        break
                    else:
                        raise ValueError(f"unknown op: {op}")

                except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    self.emit({"op": "error", "message": str(exc)})

        finally:
            self.stop_event.set()
            self.sample_event.set()
            self.command_event.set()
            self.poll_ipc.close()
            self.command_ipc.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-ms", type=float, default=8.0)
    args = parser.parse_args()

    bridge = Bridge(max(1.0, args.interval_ms) / 1000.0)
    bridge.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
