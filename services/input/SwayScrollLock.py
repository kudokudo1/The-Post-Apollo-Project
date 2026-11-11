#!/usr/bin/env python3
"""Guarded per-device Sway middle-button scroll lock.

The exact device must support on-button scrolling, and the operator must
confirm the active selection in CPU++. Enabling records a recoverable
one-device original snapshot before changing Sway. Restore (or later recovery)
checks that Sway still has the controlled settings before modifying anything.
This file NEVER implements Windows-style inertial autoscroll and never
synthesizes pointer events.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

DEVICE = re.compile(r"^[A-Za-z0-9_.:+-]{1,160}$")
MODES = {"none", "two_finger", "edge", "on_button_down"}
LOCKS = {"enabled", "disabled"}
MIDDLE = 274  # Linux BTN_MIDDLE. Avoid X11 button2 ambiguity in IPC.
HEADER = "post-apollo-sway-scroll-lock-v1"
MAX_REPLY = 262144
MAX_DEVICES = 64


class LockError(Exception):
    pass


def state_file():
    home = Path.home().resolve()
    root = Path(os.environ.get("XDG_STATE_HOME",
                               str(home / ".local" / "state")))
    if not root.is_absolute() or not root.resolve().is_relative_to(home):
        raise LockError("UNSAFE_STATE_DIRECTORY")
    base = root / "post-apollo"
    if base.is_symlink():
        raise LockError("UNSAFE_STATE_DIRECTORY")
    return base / "mouse-scroll-lock-v1.json"


def read_owned(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LockError("UNSAFE_SNAPSHOT") from exc
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid()
                or meta.st_nlink != 1 or meta.st_size > 4096):
            raise LockError("UNSAFE_SNAPSHOT")
        try:
            return json.loads(os.read(fd, 4097))
        except (UnicodeError, ValueError) as exc:
            raise LockError("INVALID_SNAPSHOT") from exc
    finally:
        os.close(fd)


def snapshot_path():
    path = state_file()
    if path.parent.exists() and (not path.parent.is_dir()
                                 or path.parent.is_symlink()):
        raise LockError("UNSAFE_STATE_DIRECTORY")
    return path


def save_snapshot(data):
    path = snapshot_path()
    if path.exists() or path.is_symlink():
        raise LockError("ACTIVE_SNAPSHOT")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise LockError("UNSAFE_STATE_DIRECTORY")
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
    except OSError as exc:
        raise LockError("SNAPSHOT_WRITE_FAILED") from exc


def run_sway(args):
    try:
        run = subprocess.run(["swaymsg", *args], capture_output=True,
                             text=True, check=False, timeout=4)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LockError("SWAY_IPC_UNAVAILABLE") from exc
    if run.returncode != 0 or len(run.stdout) > MAX_REPLY:
        raise LockError("SWAY_COMMAND_FAILED")
    return run.stdout


def read_devices():
    try:
        data = json.loads(run_sway(["-t", "get_inputs"]))
    except ValueError as exc:
        raise LockError("INVALID_SWAY_REPLY") from exc
    if not isinstance(data, list) or len(data) > MAX_DEVICES:
        raise LockError("INVALID_DEVICE_LIST")
    found = []
    for dev in data:
        if not isinstance(dev, dict) or dev.get("type") != "pointer":
            continue
        identifier = dev.get("identifier")
        if not isinstance(identifier, str) or not DEVICE.fullmatch(identifier):
            continue
        # Sway GET_INPUTS places scroll configuration in libinput,
        # not at the device's outer level (unlike scroll_factor).
        lib = dev.get("libinput")
        if not isinstance(lib, dict):
            continue
        mode, lock, button = (lib.get("scroll_method"),
                              lib.get("scroll_button_lock"),
                              lib.get("scroll_button"))
        if (mode not in MODES or lock not in LOCKS
                or not isinstance(button, int) or isinstance(button, bool)
                or button < 0 or button > 767):
            continue
        found.append({"identifier": identifier,
                      "name": str(dev.get("name") or identifier)[:100],
                      "scroll_method": mode, "scroll_button_lock": lock,
                      "scroll_button": button})
    if len(set(x["identifier"] for x in found)) != len(found):
        raise LockError("DUPLICATE_DEVICE")
    return found


def find_device(identifier):
    if not DEVICE.fullmatch(identifier):
        raise LockError("INVALID_DEVICE_ID")
    return next((d for d in read_devices()
                 if d["identifier"] == identifier), None)


def require_command(identifier, key, value):
    try:
        reply = json.loads(run_sway(["input", identifier, key, str(value)]))
    except ValueError as exc:
        raise LockError("INVALID_COMMAND_REPLY") from exc
    if (not isinstance(reply, list) or not reply
            or any(not isinstance(x, dict) or x.get("success") is not True
                   for x in reply)):
        raise LockError("SWAY_REJECTED_SETTING")


def fingerprint(dev):
    return {key: dev[key] for key in
            ("identifier", "scroll_method", "scroll_button_lock",
             "scroll_button")}


def active(dev):
    return (dev["scroll_method"] == "on_button_down"
            and dev["scroll_button_lock"] == "enabled"
            and dev["scroll_button"] == MIDDLE)


def inspect():
    devices = read_devices()
    snapshot = read_owned(snapshot_path())
    if snapshot is not None:
        validate_snapshot(snapshot)
    return {"status": "ok", "devices": devices,
            "active_identifier": snapshot["original"]["identifier"]
            if snapshot else None, "snapshot": snapshot is not None,
            "scope": "live_sway_only"}


def validate_snapshot(snap):
    if (not isinstance(snap, dict) or snap.get("format") != HEADER
            or not isinstance(snap.get("original"), dict)
            or set(snap["original"]) != {"identifier", "scroll_method",
                                         "scroll_button_lock", "scroll_button"}):
        raise LockError("INVALID_SNAPSHOT")
    d = snap["original"]
    if (not isinstance(d["identifier"], str)
            or not DEVICE.fullmatch(d["identifier"])
            or d["scroll_method"] not in MODES
            or d["scroll_button_lock"] not in LOCKS
            or not isinstance(d["scroll_button"], int)
            or not 0 <= d["scroll_button"] <= 767):
        raise LockError("INVALID_SNAPSHOT")


def enable(identifier, expected_method, expected_lock, expected_button):
    dev = find_device(identifier)
    if dev is None:
        raise LockError("DEVICE_UNSUPPORTED")
    if active(dev):
        raise LockError("ALREADY_ACTIVE")
    if dev["scroll_method"] != expected_method or dev["scroll_button_lock"] != expected_lock:
        raise LockError("STALE_DEVICE")
    if str(dev["scroll_button"]) != expected_button:
        raise LockError("STALE_DEVICE")
    snap = {"format": HEADER, "original": fingerprint(dev)}
    save_snapshot(snap)
    try:
        require_command(identifier, "scroll_button", "BTN_MIDDLE")
        require_command(identifier, "scroll_button_lock", "enabled")
        require_command(identifier, "scroll_method", "on_button_down")
        changed = find_device(identifier)
        if changed is None or not active(changed):
            raise LockError("CHANGE_NOT_VERIFIED")
    except LockError:
        # Snapshot remains available so a partial change is recoverable.
        raise
    return {"status": "enabled", "identifier": identifier,
            "scope": "live_sway_only", "snapshot": True}


def restore():
    path = snapshot_path()
    snap = read_owned(path)
    if snap is None:
        raise LockError("NO_SNAPSHOT")
    validate_snapshot(snap)
    old = snap["original"]
    identifier = old["identifier"]
    current = find_device(identifier)
    if current is None:
        raise LockError("DEVICE_MISSING")
    # Allow partial application in the enabling sequence, but not unrelated
    # changes to the device while we were away. No wildcard input commands.
    allowed_mode = {old["scroll_method"], "on_button_down"}
    allowed_lock = {old["scroll_button_lock"], "enabled"}
    allowed_button = {old["scroll_button"], MIDDLE}
    if (current["scroll_method"] not in allowed_mode
            or current["scroll_button_lock"] not in allowed_lock
            or current["scroll_button"] not in allowed_button):
        raise LockError("DEVICE_CHANGED_EXTERNALLY")
    if current["scroll_method"] != old["scroll_method"]:
        require_command(identifier, "scroll_method", old["scroll_method"])
    if current["scroll_button_lock"] != old["scroll_button_lock"]:
        require_command(identifier, "scroll_button_lock",
                        old["scroll_button_lock"])
    if current["scroll_button"] != old["scroll_button"]:
        value = ("disable" if old["scroll_button"] == 0
                 else str(old["scroll_button"]))
        require_command(identifier, "scroll_button", value)
    verify = find_device(identifier)
    if verify is None or fingerprint(verify) != old:
        raise LockError("RESTORE_NOT_VERIFIED")
    path.unlink()
    return {"status": "restored", "identifier": identifier,
            "scope": "live_sway_only"}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["inspect"]:
            result = inspect()
        elif len(args) == 5 and args[0] == "enable":
            result = enable(*args[1:])
        elif args == ["restore"]:
            result = restore()
        else:
            raise LockError("INVALID_ACTION")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except LockError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
