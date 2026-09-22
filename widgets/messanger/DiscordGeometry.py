#!/usr/bin/env python3
"""
Persistent Sway geometry bridge for MessagingW.qml.

Protocol on stdin: newline-delimited JSON.

  {"op":"watch","enabled":true}
  {"op":"sample"}
  {"op":"config","appSelectorWidth":110,"contactListWidth":200,
   "discordGap":0,"discordInset":1,"minimumSharedWidth":311,
   "minimumSharedHeight":260}
  {"op":"mode","discordSelected":true,"discordReady":true}
  {"op":"sync","target":"social|discord","x":0,"y":0,
   "width":100,"height":100,"focus":false,"setup":false}
  {"op":"centerDiscord","x":0,"y":0}
  {"op":"focusDiscord"}

stdout: newline-delimited JSON snapshots:
  {"social":{"rect":...,"focused":...},"discord":{...}}

The helper uses direct Sway IPC sockets. It intentionally does not invoke
swaymsg or jq in the live geometry path.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import deque
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

        # One-time fallback only. The live loop never spawns swaymsg/jq.
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
        if self.sock is not None:
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
                    HEADER.pack(MAGIC, len(encoded), message_type)
                    + encoded
                )

                raw_header = self._recv_exact(HEADER.size)
                magic, length, response_type = HEADER.unpack(raw_header)

                if magic != MAGIC:
                    raise ConnectionError("Invalid Sway IPC response magic")

                raw_payload = self._recv_exact(length)

                # Sway replies with JSON for GET_TREE and RUN_COMMAND.
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
            "width": int(rect.get("width", 0)),
            "height": int(rect.get("height", 0)),
        }
    except (TypeError, ValueError):
        return None


def snapshot_from_tree(tree: dict[str, Any]) -> dict[str, Any]:
    social: dict[str, Any] | None = None
    discord_candidates: list[dict[str, Any]] = []

    for node in walk_tree(tree):
        if not node.get("visible", False):
            continue

        rect = compact_rect(node.get("rect"))
        if rect is None:
            continue

        entry = {
            "rect": rect,
            "focused": bool(node.get("focused", False)),
        }

        if social is None and node.get("name") == "QS_SOCIAL_MENU":
            social = entry

        if node.get("app_id") == "vesktop":
            discord_entry = dict(entry)
            discord_entry["name"] = node.get("name")
            discord_candidates.append(discord_entry)

    discord: dict[str, Any] | None = None

    if discord_candidates:
        discord = max(
            discord_candidates,
            key=lambda item: (
                item["rect"]["width"] * item["rect"]["height"]
            ),
        )

    return {
        "social": social,
        "discord": discord,
    }


def sway_criteria(target: str) -> str:
    if target == "social":
        return '[title="QS_SOCIAL_MENU"]'
    if target == "discord":
        return '[app_id="vesktop"]'
    raise ValueError(f"Unknown sync target: {target}")


def build_sync_command(message: dict[str, Any]) -> str:
    target = str(message["target"])
    criteria = sway_criteria(target)

    x = int(message["x"])
    y = int(message["y"])
    width = max(1, int(message["width"]))
    height = max(1, int(message["height"]))

    commands: list[str] = []

    if bool(message.get("setup", False)):
        commands.append(f"{criteria} floating enable")
        commands.append(f"{criteria} border none")

    commands.append(
        f"{criteria} resize set width {width} px height {height} px"
    )
    commands.append(
        f"{criteria} move absolute position {x} px {y} px"
    )

    if bool(message.get("focus", False)):
        commands.append(f"{criteria} focus")

    return "; ".join(commands)


class Bridge:
    def __init__(self, interval_seconds: float) -> None:
        self.interval = max(0.001, interval_seconds)

        self.poll_ipc = SwayIPC()
        self.command_ipc = SwayIPC()

        self.stop_event = threading.Event()
        self.watch_event = threading.Event()
        self.sample_event = threading.Event()
        self.command_event = threading.Event()

        self.command_lock = threading.Lock()
        self.pending_sync: dict[str, dict[str, Any]] = {}
        self.immediate_commands: deque[str] = deque()

        self.last_snapshot: dict[str, Any] | None = None

        # Shared-geometry constants supplied by MessagingW.qml.
        self.app_selector_width = 110
        self.contact_list_width = 200
        self.discord_gap = 0
        self.discord_inset = 1
        self.minimum_shared_width = 311
        self.minimum_shared_height = 260

        # Fast-follow is active only after the real Discord window is ready.
        self.discord_selected = False
        self.discord_ready = False

    @staticmethod
    def rect_equal(a: dict[str, int] | None, b: dict[str, int] | None) -> bool:
        return bool(a and b) and (
            a["x"] == b["x"]
            and a["y"] == b["y"]
            and a["width"] == b["width"]
            and a["height"] == b["height"]
        )

    def shared_from_discord(self, rect: dict[str, int]) -> dict[str, int]:
        discord_width = max(
            self.contact_list_width + 1,
            int(rect["width"]),
        )

        width = (
            self.app_selector_width
            + self.discord_gap
            + discord_width
            + (self.discord_inset * 2)
        )
        height = max(
            self.minimum_shared_height,
            int(rect["height"]) + (self.discord_inset * 2),
        )

        return {
            "x": (
                int(rect["x"])
                - self.app_selector_width
                - self.discord_gap
                - self.discord_inset
            ),
            "y": int(rect["y"]) - self.discord_inset,
            "width": max(self.minimum_shared_width, width),
            "height": height,
        }

    def discord_from_shared(self, shared: dict[str, int]) -> dict[str, int]:
        return {
            "x": (
                int(shared["x"])
                + self.app_selector_width
                + self.discord_gap
                + self.discord_inset
            ),
            "y": int(shared["y"]) + self.discord_inset,
            "width": max(
                1,
                int(shared["width"])
                - self.app_selector_width
                - self.discord_gap
                - (self.discord_inset * 2),
            ),
            "height": max(
                1,
                int(shared["height"])
                - (self.discord_inset * 2),
            ),
        }

    def fast_follow(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """
        Move the follower directly inside the helper.

        This removes the old:
            Python -> QML -> Python -> Sway
        round trip from live Mod-move/resize operations.

        The focused member is the geometry leader. Commands are still
        coalesced by queue_sync(), so old follower positions cannot build up.
        """
        snapshot["fastLeader"] = None
        snapshot["shared"] = None

        if not (self.discord_selected and self.discord_ready):
            return snapshot

        social = snapshot.get("social")
        discord = snapshot.get("discord")

        if not social or not discord:
            return snapshot

        social_rect = social.get("rect")
        discord_rect = discord.get("rect")

        if not social_rect or not discord_rect:
            return snapshot

        discord_focused = bool(discord.get("focused", False))
        social_focused = bool(social.get("focused", False))

        if discord_focused and not social_focused:
            shared = self.shared_from_discord(discord_rect)

            desired_social = {
                "x": shared["x"],
                "y": shared["y"],
                "width": shared["width"],
                "height": shared["height"],
            }

            snapshot["fastLeader"] = "discord"
            snapshot["shared"] = shared

            if not self.rect_equal(social_rect, desired_social):
                self.queue_sync({
                    "op": "sync",
                    "target": "social",
                    **desired_social,
                    "focus": False,
                    "setup": False,
                })

            return snapshot

        if social_focused and not discord_focused:
            shared = {
                "x": int(social_rect["x"]),
                "y": int(social_rect["y"]),
                "width": max(
                    self.minimum_shared_width,
                    int(social_rect["width"]),
                ),
                "height": max(
                    self.minimum_shared_height,
                    int(social_rect["height"]),
                ),
            }
            desired_discord = self.discord_from_shared(shared)

            snapshot["fastLeader"] = "social"
            snapshot["shared"] = shared

            if not self.rect_equal(discord_rect, desired_discord):
                self.queue_sync({
                    "op": "sync",
                    "target": "discord",
                    **desired_discord,
                    "focus": False,
                    "setup": False,
                })

            return snapshot

        return snapshot

    def queue_sync(self, message: dict[str, Any]) -> None:
        target = str(message.get("target", ""))

        if target not in ("social", "discord"):
            return

        with self.command_lock:
            previous = self.pending_sync.get(target)

            if previous is not None:
                # Never lose a one-shot setup/focus request when stale geometry
                # is replaced by a newer sample.
                message["setup"] = bool(
                    message.get("setup", False)
                    or previous.get("setup", False)
                )
                message["focus"] = bool(
                    message.get("focus", False)
                    or previous.get("focus", False)
                )

            # Latest geometry wins. This is the key to preventing a backlog of
            # stale follower positions while the user drags quickly.
            self.pending_sync[target] = message

        self.command_event.set()

    def queue_command(self, command: str) -> None:
        with self.command_lock:
            self.immediate_commands.append(command)

        self.command_event.set()

    def stdin_loop(self) -> None:
        for raw_line in sys.stdin:
            if self.stop_event.is_set():
                break

            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                message = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                print(
                    f"invalid command JSON: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                continue

            op = message.get("op")

            if op == "watch":
                if bool(message.get("enabled", False)):
                    self.watch_event.set()
                    self.sample_event.set()
                else:
                    self.watch_event.clear()
                continue

            if op == "sample":
                self.sample_event.set()
                continue

            if op == "config":
                self.app_selector_width = int(
                    message.get("appSelectorWidth", self.app_selector_width)
                )
                self.contact_list_width = int(
                    message.get("contactListWidth", self.contact_list_width)
                )
                self.discord_gap = int(
                    message.get("discordGap", self.discord_gap)
                )
                self.discord_inset = int(
                    message.get("discordInset", self.discord_inset)
                )
                self.minimum_shared_width = int(
                    message.get(
                        "minimumSharedWidth",
                        self.minimum_shared_width,
                    )
                )
                self.minimum_shared_height = int(
                    message.get(
                        "minimumSharedHeight",
                        self.minimum_shared_height,
                    )
                )
                continue

            if op == "mode":
                self.discord_selected = bool(
                    message.get("discordSelected", False)
                )
                self.discord_ready = bool(
                    message.get("discordReady", False)
                )
                continue

            if op == "sync":
                self.queue_sync(message)
                continue

            if op == "centerDiscord":
                x = int(message.get("x", 0))
                y = int(message.get("y", 0))
                self.queue_command(
                    '[app_id="vesktop"] border none; '
                    f'[app_id="vesktop"] move absolute position '
                    f'{x} px {y} px'
                )
                continue

            if op == "focusDiscord":
                self.queue_command('[app_id="vesktop"] focus')
                continue

            if op == "stop":
                self.stop_event.set()
                self.watch_event.set()
                self.command_event.set()
                break

    def command_loop(self) -> None:
        while not self.stop_event.is_set():
            self.command_event.wait(0.1)
            self.command_event.clear()

            while not self.stop_event.is_set():
                command: str | None = None

                with self.command_lock:
                    if self.immediate_commands:
                        command = self.immediate_commands.popleft()
                    elif self.pending_sync:
                        # Dict insertion order is stable; either target can be
                        # overwritten repeatedly without building a stale queue.
                        _, message = self.pending_sync.popitem()
                        command = build_sync_command(message)

                if command is None:
                    break

                try:
                    self.command_ipc.request(IPC_COMMAND, command)
                except Exception as exc:
                    print(
                        f"Sway command failed: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                    time.sleep(0.01)

    def emit_snapshot(self, force: bool = False) -> None:
        tree = self.poll_ipc.request(IPC_GET_TREE)
        snapshot = snapshot_from_tree(tree)
        snapshot = self.fast_follow(snapshot)

        if force or snapshot != self.last_snapshot:
            print(
                json.dumps(snapshot, separators=(",", ":")),
                flush=True,
            )
            self.last_snapshot = snapshot

    def poll_loop(self) -> None:
        next_sample = time.monotonic()

        while not self.stop_event.is_set():
            watching = self.watch_event.is_set()
            forced = self.sample_event.is_set()

            if not watching and not forced:
                time.sleep(0.01)
                next_sample = time.monotonic()
                continue

            if forced:
                self.sample_event.clear()

            try:
                self.emit_snapshot(force=True)
            except Exception as exc:
                print(
                    f"Sway geometry read failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(0.02)

            if not watching:
                continue

            next_sample += self.interval
            delay = next_sample - time.monotonic()

            if delay > 0:
                time.sleep(delay)
            else:
                # If one sample ran long, do not accumulate timing debt.
                next_sample = time.monotonic()

    def run(self) -> None:
        stdin_thread = threading.Thread(
            target=self.stdin_loop,
            name="stdin",
            daemon=True,
        )
        command_thread = threading.Thread(
            target=self.command_loop,
            name="commands",
            daemon=True,
        )

        stdin_thread.start()
        command_thread.start()

        try:
            self.poll_loop()
        finally:
            self.stop_event.set()
            self.command_event.set()
            self.poll_ipc.close()
            self.command_ipc.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interval-ms",
        type=float,
        default=8.0,
        help="Geometry sample interval while watch mode is active.",
    )
    args = parser.parse_args()

    bridge = Bridge(max(1.0, args.interval_ms) / 1000.0)

    try:
        bridge.run()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(
            f"fatal: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

