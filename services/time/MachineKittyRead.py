"""MACHINE M2d3: opt-in, ONE-SHOT read-only Kitty native inventory adapter.

The documented `kitten @ ls` response contains titles, directories,
commands, PIDs and environment data. Accept it only in transient memory,
strictly bound its size, and return only numeric OS window/tab/pane IDs and
counts. These native IDs are ephemeral, NOT Sway con_ids or checkpoint IDs.

No import-time calls, QML activation, socket creation, shell execution,
remote-control configuration, file writes, or restore/move/launch functions.
A socket read requires an explicit target and explicit caller opt-in. No
trusted user-authentication claim is made by the opt-in function argument.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

MAX_RESPONSE_BYTES = 2_000_000
MAX_OS_WINDOWS = 256
MAX_TABS = 2048
MAX_PANES = 8192
READ_TIMEOUT_SECONDS = 3


class KittyInventoryError(ValueError):
    pass


def _positive_id(value):
    if type(value) is not int or not 0 < value < 2 ** 63:
        raise KittyInventoryError("INVALID KITTY IDENTIFIER")
    return value


def _collection(value, maximum):
    if not isinstance(value, list) or len(value) > maximum:
        raise KittyInventoryError("INVALID KITTY COLLECTION")
    return value


def normalize_kitty_ls(payload):
    """Strictly project a real Kitty ls JSON tree, never echo private fields.

    Accepted source can be bytes or text; ignored source keys include
    titles, current working directories, commands, environment and PIDs.
    Nested response shape is validated, with all IDs unique in their own
    scope. Nothing is written or logged.
    """
    if type(payload) is bytes:
        raw = payload
    elif type(payload) is str:
        try:
            raw = payload.encode("utf-8")
        except UnicodeError as exc:
            raise KittyInventoryError("INVALID KITTY RESPONSE") from exc
    else:
        raise KittyInventoryError("INVALID KITTY RESPONSE")
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise KittyInventoryError("OVERSIZED OR EMPTY KITTY RESPONSE")
    try:
        parsed = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise KittyInventoryError("INVALID KITTY RESPONSE") from exc
    tree = _collection(parsed, MAX_OS_WINDOWS)
    result = []
    os_ids = set()
    tab_ids = set()
    pane_ids = set()
    tab_count = 0
    pane_count = 0
    for os_window in tree:
        if not isinstance(os_window, dict):
            raise KittyInventoryError("INVALID KITTY OS WINDOW")
        os_id = _positive_id(os_window.get("id"))
        if os_id in os_ids:
            raise KittyInventoryError("DUPLICATE KITTY OS WINDOW")
        os_ids.add(os_id)
        tabs = _collection(os_window.get("tabs"), MAX_TABS - tab_count)
        clean_tabs = []
        for tab in tabs:
            if not isinstance(tab, dict):
                raise KittyInventoryError("INVALID KITTY TAB")
            tab_id = _positive_id(tab.get("id"))
            if tab_id in tab_ids:
                raise KittyInventoryError("DUPLICATE KITTY TAB")
            tab_ids.add(tab_id)
            tab_count += 1
            panes = _collection(tab.get("windows"), MAX_PANES - pane_count)
            clean_panes = []
            for pane in panes:
                if not isinstance(pane, dict):
                    raise KittyInventoryError("INVALID KITTY PANE")
                pane_id = _positive_id(pane.get("id"))
                if pane_id in pane_ids:
                    raise KittyInventoryError("DUPLICATE KITTY PANE")
                pane_ids.add(pane_id)
                pane_count += 1
                clean_panes.append({"pane_id": pane_id})
            clean_tabs.append({"tab_id": tab_id, "panes": clean_panes,
                               "pane_count": len(clean_panes)})
        result.append({"os_window_id": os_id, "tabs": clean_tabs,
                       "tab_count": len(clean_tabs)})
    return {
        "kind": "machine-kitty-native-inventory-projection",
        "read_only": True,
        "executable": False,
        "input_origin_verified": False,
        "host_window_binding_verified": False,
        "checkpoint_session_match": False,
        "runtime_ids_ephemeral": True,
        "counts": {
            "os_windows": len(result),
            "tabs": tab_count,
            "panes": pane_count,
        },
        "os_windows": result,
        "safe_actions": [],
        "capture_enabled": False,
        "restore_enabled": False,
    }


def _explicit_socket(target, runtime_directory, *, inspector=os.lstat):
    """Reject unscoped, remotely accessible and unsafe socket targets."""
    if not isinstance(target, str) or not target.startswith("unix:"):
        raise KittyInventoryError("EXPLICIT UNIX SOCKET REQUIRED")
    path = target[5:]
    if (not path or len(path) > 240 or "\x00" in path or
            not path.startswith("/") or
            any(part in (".", "..", "") for part in path.split("/")[1:])):
        raise KittyInventoryError("INVALID SOCKET PATH")
    if (not isinstance(runtime_directory, str)
            or not runtime_directory.startswith("/")
            or runtime_directory == "/"):
        raise KittyInventoryError("INVALID RUNTIME DIRECTORY")
    # An absolute runtime root is required; no implicit socket discovery.
    root = os.path.normpath(runtime_directory)
    if root != runtime_directory or path == root or not path.startswith(root + "/"):
        raise KittyInventoryError("SOCKET OUTSIDE APPROVED RUNTIME")
    if len(Path(path).parts) > len(Path(root).parts) + 2:
        raise KittyInventoryError("UNEXPECTED SOCKET DIRECTORY DEPTH")
    try:
        parent = inspector(str(Path(path).parent))
        leaf = inspector(path)
    except OSError as exc:
        raise KittyInventoryError("KITTY SOCKET NOT AVAILABLE") from exc
    for node in (parent, leaf):
        if node.st_uid != os.geteuid() or node.st_mode & 0o077:
            raise KittyInventoryError("UNSAFE SOCKET OWNERSHIP")
    if not stat.S_ISDIR(parent.st_mode) or not stat.S_ISSOCK(leaf.st_mode):
        raise KittyInventoryError("UNSAFE SOCKET FILE TYPE")
    return target


def read_existing_kitty_inventory(*, target, runtime_directory, opt_in,
                                  runner=subprocess.run,
                                  inspector=os.lstat):
    """Opt-in read of an ALREADY enabled, specifically named Kitty socket.

    Never starts Kitty or enables remote control. This entrypoint is NOT
    exposed by QML or CLI and cannot authenticate the caller. Production
    use requires a separately trusted UI grant and socket-owner review.
    """
    if opt_in != "explicit_read_only_kitty_inventory":
        raise KittyInventoryError("KITTY INVENTORY CONSENT REQUIRED")
    endpoint = _explicit_socket(target, runtime_directory, inspector=inspector)
    argv = ["kitten", "@", "--to", endpoint, "ls"]
    try:
        response = runner(argv, check=True, capture_output=True,
                          timeout=READ_TIMEOUT_SECONDS, shell=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise KittyInventoryError("KITTY INVENTORY UNAVAILABLE") from exc
    if getattr(response, "returncode", 1) != 0:
        raise KittyInventoryError("KITTY INVENTORY UNAVAILABLE")
    return normalize_kitty_ls(getattr(response, "stdout", None))
