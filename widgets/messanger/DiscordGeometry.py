#!/usr/bin/env python3
"""
Persistent Sway geometry bridge for MessagingW.qml.

Protocol on stdin: newline-delimited JSON.

  {"op":"watch","enabled":true}
  {"op":"sample"}
  {"op":"config","appSelectorWidth":110,"contactListWidth":200,
   "discordGap":0,"discordInset":1,"minimumSharedWidth":311,
   "minimumSharedHeight":260}
  {"op":"mode","discordSelected":true,"discordReady":true,"discordDocked":true}
  {"op":"sync","target":"social|discord","x":0,"y":0,
   "width":100,"height":100,"focus":false,"setup":false}
  {"op":"centerDiscord","x":0,"y":0}
  {"op":"showDiscord","focus":true}
  {"op":"hideDiscord"}
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
import re
import socket
import struct
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


BROWSER_SITES = ("x", "instagram", "facebook", "reddit", "threads", "pinterest",
                 "truthsocial", "bluesky", "tumblr", "tiktok", "snapchat",
                 "linkedin", "mastodon", "nextdoor", "steamchat", "element",
                 "groupme", "lemon8", "quora", "pixelfed", "zalo",
                 "whatsappweb", "messengerweb", "linechrome")

# Keep exactly the same stable identity shape as XBrowser.py. Do not use the
# display name or a substring match for a Sway window's XWayland class.
BROWSER_IDENTITY_ID = re.compile(r"^identity-[1-9][0-9]{0,8}$")


def validate_browser_identity(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not BROWSER_IDENTITY_ID.fullmatch(value):
        raise ValueError("Invalid Post-Apollo browser identity ID")
    return value


def browser_window_class(site: str, identity_id: str | None = None) -> str:
    if site not in BROWSER_SITES:
        raise ValueError("Unsupported Social browser site")
    identity = validate_browser_identity(identity_id)
    return f"post-apollo-{site}" + (f"-{identity}" if identity is not None else "")

VESKTOP_WAYLAND_IDS = {"vesktop", "dev.vencord.vesktop"}
VESKTOP_X11_CLASSES = {"vesktop"}

# Upstream Vesktop's splash BrowserWindow is exactly 300x350 and has no
# document title in splash.html. The real Discord window may legitimately be
# restored very small, so size alone is never enough to call something splash.
VESKTOP_SPLASH_WIDTH = 300
VESKTOP_SPLASH_HEIGHT = 350
VESKTOP_SPLASH_TOLERANCE = 80
VESKTOP_SPLASH_GENERIC_TITLES = {"", "vesktop", "electron", "loading vesktop..."}


def normalized_identity(value: Any) -> str:
    return str(value or "").strip().lower()


def is_vesktop_node(node: dict[str, Any]) -> bool:
    app_id = normalized_identity(node.get("app_id"))
    sandbox_app_id = normalized_identity(node.get("sandbox_app_id"))
    props = node.get("window_properties") or {}
    window_class = normalized_identity(props.get("class"))
    instance = normalized_identity(props.get("instance"))
    return (
        app_id in VESKTOP_WAYLAND_IDS
        or sandbox_app_id == "dev.vencord.vesktop"
        or window_class in VESKTOP_X11_CLASSES
        or instance in VESKTOP_X11_CLASSES
    )


def vesktop_window_kind(rect: dict[str, int], name: Any) -> str:
    width = int(rect["width"])
    height = int(rect["height"])
    title = normalized_identity(name)

    splash_sized = (
        abs(width - VESKTOP_SPLASH_WIDTH) <= VESKTOP_SPLASH_TOLERANCE
        and abs(height - VESKTOP_SPLASH_HEIGHT) <= VESKTOP_SPLASH_TOLERANCE
    )
    splash_named = title in VESKTOP_SPLASH_GENERIC_TITLES

    return "splash" if splash_sized and splash_named else "main"


def snapshot_from_tree(
    tree: dict[str, Any], browser_identity_id: str | None = None,
) -> dict[str, Any]:
    # Pass None to preserve the exact existing legacy window discovery.
    scoped_identity = validate_browser_identity(browser_identity_id)
    social: dict[str, Any] | None = None
    discord_candidates: list[dict[str, Any]] = []
    browser_candidates: dict[str, list[dict[str, Any]]] = {site: [] for site in BROWSER_SITES}

    for node in walk_tree(tree):
        rect = compact_rect(node.get("rect"))
        if rect is None:
            continue

        visible = bool(node.get("visible", False))
        entry = {
            "rect": rect,
            "focused": bool(node.get("focused", False)),
            "visible": visible,
        }

        # Vesktop may be a native Wayland client or an XWayland client, and a
        # scratchpad window is not necessarily visible. Discover it before the
        # visible-only filtering and carry its exact Sway container id.
        if is_vesktop_node(node):
            discord_entry = dict(entry)
            discord_entry["name"] = node.get("name")
            discord_entry["conId"] = int(node.get("id", 0))
            discord_entry["appId"] = node.get("app_id")
            discord_entry["sandboxAppId"] = node.get("sandbox_app_id")
            discord_entry["shell"] = node.get("shell")
            discord_entry["kind"] = vesktop_window_kind(
                rect,
                discord_entry["name"],
            )
            discord_entry["windowClass"] = (
                (node.get("window_properties") or {}).get("class")
            )
            discord_candidates.append(discord_entry)

        if visible and social is None and node.get("name") == "QS_SOCIAL_MENU":
            social = entry

        # Legacy browser discovery stays visible-only. In the scoped mode,
        # hidden scratchpad windows are discovered with their exact con_id so
        # they cannot be mistaken for a different identity's visible window.
        if not visible and scoped_identity is None:
            continue
        window_class = (node.get("window_properties") or {}).get("class")
        for site in BROWSER_SITES:
            if window_class != browser_window_class(site, scoped_identity):
                continue
            if scoped_identity is None:
                browser_candidates[site].append(entry)
            else:
                con_id = node.get("id")
                if type(con_id) is not int or con_id <= 0:
                    continue
                scoped_entry = dict(entry)
                scoped_entry["conId"] = con_id
                scoped_entry["windowClass"] = window_class
                scoped_entry["browserIdentityId"] = scoped_identity
                browser_candidates[site].append(scoped_entry)

    discord: dict[str, Any] | None = None

    if discord_candidates:
        discord = max(
            discord_candidates,
            key=lambda item: (
                bool(item.get("visible", False)),
                item.get("kind") == "main",
                item["rect"]["width"] * item["rect"]["height"],
                bool(item.get("focused", False)),
            ),
        )

    browser_windows = {
        site: (
            max(browser_candidates[site],
                key=lambda item: item["rect"]["width"] * item["rect"]["height"],
                default=None)
            if scoped_identity is None else
            # More than one window with the *same* identity class is ambiguous.
            # Fail closed rather than choosing whichever happens to be bigger.
            (browser_candidates[site][0]
             if len(browser_candidates[site]) == 1 else None)
        )
        for site in BROWSER_SITES
    }

    return {
        "social": social,
        "discord": discord,
        **browser_windows,
    }


def sway_criteria(
    target: str, con_id: int | None = None,
    browser_identity_id: str | None = None,
) -> str:
    scoped_identity = validate_browser_identity(browser_identity_id)
    if target == "social":
        if scoped_identity is not None:
            # A scoped browser identity cannot establish Social leadership
            # by constructing an arbitrary host-window command.
            raise ValueError("Scoped browser geometry requires verified host state")
        return '[title="QS_SOCIAL_MENU"]'
    if target == "discord":
        if scoped_identity is not None:
            raise ValueError("Browser identity cannot target Vesktop")
        if con_id is None or int(con_id) <= 0:
            raise ValueError("Discord commands require a discovered Sway con_id")
        return f'[con_id="{int(con_id)}"]'
    if target in BROWSER_SITES:
        if scoped_identity is not None:
            if type(con_id) is not int or con_id <= 0:
                raise ValueError("Identity browser commands require a verified Sway con_id")
            return f'[con_id="{con_id}"]'
        return f'[class="post-apollo-{target}"]'
    raise ValueError(f"Unknown sync target: {target}")


def build_sync_command(message: dict[str, Any]) -> str:
    target = str(message["target"])
    identity = validate_browser_identity(message.get("browserIdentityId"))
    if identity is not None:
        if target not in BROWSER_SITES:
            raise ValueError("Scoped browser sync cannot target Social or Vesktop")
        if message.get("windowClass") != browser_window_class(target, identity):
            raise ValueError("Stale or mismatched browser window class")
    criteria = sway_criteria(target, message.get("conId"), identity)

    x = int(message["x"])
    y = int(message["y"])
    width = max(1, int(message["width"]))
    height = max(1, int(message["height"]))

    commands: list[str] = []

    # Discord's Sway titlebar can survive a completed/reused setup request:
    # do not treat "discordConfigured" in QML as compositor acknowledgment.
    # These operations are idempotent, and remain scoped to Vesktop. In
    # particular, a routine fast-follow with setup=False must remove the
    # titlebar and keep the client floating inside the Social slot.
    if target == "discord" or bool(message.get("setup", False)):
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
        # Social confirms Vesktop's initial dock before it can lead moves.
        self.discord_docked = False
        self.x_selected = False
        self.x_ready = False
        # Browser windows may lead only after Social verified their Sway
        # placement; a transient splash/scratchpad rectangle cannot lead.
        self.x_docked = False
        self.browser_site = "x"
        # Scoped identity discovery is passive until a separate operator-
        # approved host integration can coordinate the saved identity and
        # exact browser process. Never infer it from an account nickname.
        self.browser_identity_id: str | None = None
        self.scoped_browser_con_id: int | None = None

        # Discord's runtime identity is learned from Sway. Never assume one
        # app_id spelling: current Vesktop may be native Wayland or XWayland.
        self.discord_con_id: int | None = None
        self.discord_visible = False
        self.discord_kind = ""
        self.discord_show_requested = False
        self.discord_show_focus = True
        # A main BrowserWindow that Electron has never shown must not be
        # treated as a Social-managed hidden/scratchpad window. During cold
        # startup Vesktop creates the main window hidden before appLoaded.
        self.discord_main_seen_visible: set[int] = set()
        self.discord_reveal_attempted_con_id: int | None = None

    def select_browser_scope(
        self, site: str, identity_id: str | None,
    ) -> None:
        """Select one exact browser namespace, with no provider actuation."""
        identity = validate_browser_identity(identity_id)
        if identity is not None and site not in BROWSER_SITES:
            raise ValueError("Invalid scoped browser site")
        selected_site = site if site in BROWSER_SITES else "x"
        if (self.browser_identity_id != identity
                or (identity is not None and self.browser_site != selected_site)):
            # Never carry old dock/readiness or a browser/Social follower
            # command into another identity. Discord's commands are owned by
            # the separate Vesktop path and must be retained.
            self.x_ready = False
            self.x_docked = False
            self.scoped_browser_con_id = None
            with self.command_lock:
                for target in (*BROWSER_SITES, "social"):
                    self.pending_sync.pop(target, None)
                self.immediate_commands = deque(
                    c for c in self.immediate_commands
                    if not c.startswith('[class="post-apollo-')
                )
            self.last_snapshot = None
        self.browser_site = selected_site
        self.browser_identity_id = identity

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

        # Only one external app is selected at a time. Keep the Vesktop
        # path unchanged while allowing the same fast-follow for X.
        guest_id = (
            "discord" if self.discord_selected and self.discord_ready and self.discord_docked else
            self.browser_site if self.x_selected and self.x_ready and self.x_docked else ""
        )
        if not guest_id:
            return snapshot

        # Passive scoped discovery is safe. Geometry leadership is NOT:
        # the live host still launches the legacy classes and cannot yet
        # certify an identity-scoped provider as the selected account.
        if self.x_selected and self.browser_identity_id is not None:
            return snapshot

        social = snapshot.get("social")
        discord = snapshot.get(guest_id)

        if not social or not discord:
            return snapshot

        # Hidden scratchpad clients are discoverable for exact con_id control,
        # but they are not allowed to lead shared geometry until shown.
        if guest_id == "discord" and not bool(discord.get("visible", False)):
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

            snapshot["fastLeader"] = guest_id
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
                    "target": guest_id,
                    **desired_discord,
                    "focus": False,
                    "setup": False,
                })

            return snapshot

        return snapshot

    def queue_sync(self, message: dict[str, Any]) -> None:
        target = str(message.get("target", ""))

        if target not in ("social", "discord", *BROWSER_SITES):
            return

        # No scoped browser actuation until the exact host and provider are
        # bound in one subsequent transition. Refuse both the browser target
        # and its old Social fast-follow command.
        if (message.get("browserIdentityId") is not None
                or (self.browser_identity_id is not None
                    and self.x_selected
                    and target in ("social", *BROWSER_SITES))):
            return

        if target == "discord":
            if not self.discord_con_id:
                return
            message = dict(message)
            message["conId"] = self.discord_con_id

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
                try:
                    # Reject the entire mode message on malformed identity
                    # rather than silently falling back to the legacy lane.
                    scope_id = validate_browser_identity(
                        message.get("browserIdentityId"))
                    candidate = str(message.get("browserSite", "x"))
                    if scope_id is not None and candidate not in BROWSER_SITES:
                        raise ValueError("Invalid scoped browser site")
                except ValueError:
                    print("invalid scoped browser mode", file=sys.stderr, flush=True)
                    continue
                self.select_browser_scope(candidate, scope_id)
                self.discord_selected = bool(
                    message.get("discordSelected", False)
                )
                self.discord_ready = bool(
                    message.get("discordReady", False)
                )
                self.discord_docked = bool(
                    message.get("discordDocked", False)
                ) and self.discord_selected and self.discord_ready
                self.x_selected = bool(message.get("xSelected", False))
                self.x_ready = bool(message.get("xReady", False))
                self.x_docked = (
                    bool(message.get("xDocked", False))
                    and self.x_selected and self.x_ready
                )
                continue

            if op == "sync":
                self.queue_sync(message)
                continue

            if op == "centerDiscord":
                if not self.discord_con_id:
                    self.sample_event.set()
                    continue
                x = int(message.get("x", 0))
                y = int(message.get("y", 0))
                width = max(1, int(message.get("width", 300)))
                height = max(1, int(message.get("height", 350)))
                criteria = sway_criteria("discord", self.discord_con_id)
                self.queue_command(
                    f'{criteria} floating enable; '
                    f'{criteria} border none; '
                    f'{criteria} resize set width {width} px height {height} px; '
                    f'{criteria} move absolute position {x} px {y} px'
                )
                continue

            if op == "showDiscord":
                self.discord_show_requested = True
                self.discord_show_focus = bool(message.get("focus", True))
                self.discord_reveal_attempted_con_id = None
                self.sample_event.set()
                continue

            if op == "hideDiscord":
                self.discord_show_requested = False
                self.discord_reveal_attempted_con_id = None
                if not self.discord_con_id:
                    self.sample_event.set()
                    continue
                if self.discord_visible:
                    criteria = sway_criteria("discord", self.discord_con_id)
                    self.queue_command(f'{criteria} move scratchpad')
                continue

            if op == "focusDiscord":
                if not self.discord_con_id:
                    self.sample_event.set()
                    continue
                criteria = sway_criteria("discord", self.discord_con_id)
                self.queue_command(
                    f'{criteria} floating enable; '
                    f'{criteria} border none; '
                    f'{criteria} focus'
                )
                continue

            if op == "focusX":
                # The legacy lane retains original one-class focus. For a
                # selected browser identity, even a confirmed con_id is not
                # permission for a focus transition until the host owns it.
                if self.browser_identity_id is not None:
                    self.sample_event.set()
                    continue
                self.queue_command(f'[class="post-apollo-{self.browser_site}"] focus')
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
        snapshot = (
            snapshot_from_tree(tree, self.browser_identity_id)
            if self.browser_identity_id is not None else
            snapshot_from_tree(tree)
        )

        if self.browser_identity_id is not None:
            active = snapshot.get(self.browser_site)
            current_con_id = (
                active.get("conId")
                if active and active.get("browserIdentityId")
                == self.browser_identity_id
                and active.get("windowClass")
                == browser_window_class(self.browser_site, self.browser_identity_id)
                else None
            )
            if current_con_id != self.scoped_browser_con_id:
                self.scoped_browser_con_id = current_con_id
                self.x_ready = False
                self.x_docked = False
                with self.command_lock:
                    for target in (*BROWSER_SITES, "social"):
                        self.pending_sync.pop(target, None)

        discord = snapshot.get("discord")
        if discord and int(discord.get("conId", 0)) > 0:
            new_con_id = int(discord["conId"])
            new_visible = bool(discord.get("visible", False))
            new_kind = str(discord.get("kind", ""))

            # A splash->main replacement is a new geometry authority. Never
            # carry ready/docked state across container identity changes.
            if self.discord_con_id != new_con_id:
                self.discord_con_id = new_con_id
                self.discord_ready = False
                self.discord_docked = False
                with self.command_lock:
                    self.pending_sync.pop("discord", None)

            self.discord_visible = new_visible
            self.discord_kind = new_kind

            if new_kind == "main" and new_visible:
                self.discord_main_seen_visible.add(self.discord_con_id)

            if self.discord_show_requested:
                criteria = sway_criteria("discord", self.discord_con_id)

                if new_kind == "splash":
                    # Never force a hidden startup surface visible. Vesktop owns
                    # its own splash->main transition; QML only centers a splash
                    # after Sway reports it visible.
                    pass
                elif new_visible:
                    # First attachment is helper-owned, not a QML round trip.
                    # Derive the exact external-app slot from the live Social
                    # rectangle and snap this exact Vesktop con_id immediately.
                    # QML will only verify that the compositor reached it before
                    # arming bidirectional geometry leadership.
                    social = snapshot.get("social")
                    social_rect = social.get("rect") if social else None

                    if social_rect:
                        desired = self.discord_from_shared(social_rect)
                        self.queue_sync({
                            "op": "sync",
                            "target": "discord",
                            **desired,
                            "focus": self.discord_show_focus,
                            "setup": True,
                        })
                        self.discord_show_requested = False
                        self.discord_reveal_attempted_con_id = None
                    else:
                        # Social has not mapped yet. Keep the request armed and
                        # let the next sampled tree perform the real attachment.
                        self.sample_event.set()
                elif self.discord_con_id in self.discord_main_seen_visible:
                    # This exact main window was visible before and is now a
                    # Social-managed scratchpad window. Reveal it once, then
                    # wait for a visible snapshot before consuming the request.
                    if self.discord_reveal_attempted_con_id != self.discord_con_id:
                        self.queue_command(f'{criteria} scratchpad show')
                        self.discord_reveal_attempted_con_id = self.discord_con_id
                else:
                    # Never launch or restore the provider from the geometry
                    # helper. MessagingW issues the single-instance Vesktop
                    # invocation on every Discord activation. A never-visible
                    # hidden main simply waits for Electron to map it.
                    pass
        else:
            if self.discord_con_id is not None:
                self.discord_ready = False
                self.discord_docked = False
                with self.command_lock:
                    self.pending_sync.pop("discord", None)
            self.discord_con_id = None
            self.discord_visible = False
            self.discord_kind = ""
            self.discord_reveal_attempted_con_id = None

            # No provider launch happens here. The QML activation path owns
            # start/restore; this helper only waits for and manages Sway nodes.

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

