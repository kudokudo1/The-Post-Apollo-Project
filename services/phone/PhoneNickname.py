#!/usr/bin/env python3
"""Optional local PHONE nickname for the exact active BlueFerry profile.

Nickname is presentation metadata, not a trusted identity, contact, phone line,
permission, second paired phone, or Bluetooth configuration. All commands
verify the active observed device again. Only explicit --save or --clear writes
an owner-only file in Post-Apollo's private local state directory.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unicodedata
from typing import Callable

from PhoneDeviceObservation import PROFILE, observe

SCHEMA = "post-apollo.phone.nickname-action.v0"
STORE_SCHEMA = "post-apollo.phone.nicknames.v0"
MAX_FILE = 8192
MAX_PROFILES = 8
MAX_NICKNAME = 40
PAIRED_STATES = frozenset({"BLUETOOTH_CONNECTED", "PAIRED_OFFLINE"})


def _valid_nickname(name: object) -> bool:
    return (
        type(name) is str and 1 <= len(name) <= MAX_NICKNAME
        and name == name.strip() and bool(name)
        and name.isprintable()
        and not any(unicodedata.category(char).startswith("C") for char in name)
    )


def _state_path() -> Path:
    root = os.environ.get("XDG_STATE_HOME")
    directory = Path(root) if root and os.path.isabs(root) else Path.home() / ".local" / "state"
    return directory / "post-apollo" / "social-phone-nicknames.json"


def _current(profile: str, *, observer: Callable[[], object]) -> bool:
    try:
        result = observer()
        return (
            type(profile) is str and PROFILE.fullmatch(profile) is not None
            and type(result) is dict
            and result.get("schema") == "post-apollo.phone.device-observation.v0"
            and result.get("execution") == "READ_ONLY_DEVICE_OBSERVATION"
            and result.get("state") in PAIRED_STATES
            and result.get("profileId") == profile
            and result.get("bluetoothLink") in ("CONNECTED", "PAIRED_OFFLINE")
            and result.get("trustedPhoneLink") == "UNVERIFIED"
            and result.get("contentAccessEnabled") is False
        )
    except Exception:
        return False


def _result(state: str, *, profile: str = "", name: str = "") -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": "LOCAL_DISPLAY_METADATA",
        "state": state, "profileId": profile, "nickname": name,
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }


def _load(path: Path) -> dict[str, str] | None:
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return {}
    except OSError:
        return None
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as reader:
            info = os.fstat(reader.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or (info.st_mode & 0o077) or info.st_size > MAX_FILE):
                return None
            raw = reader.read(MAX_FILE + 1)
        if len(raw.encode("utf-8")) > MAX_FILE:
            return None
        document = json.loads(raw)
        if (type(document) is not dict or set(document) != {"schema", "profiles"}
                or document["schema"] != STORE_SCHEMA or type(document["profiles"]) is not dict):
            return None
        profiles = document["profiles"]
        if len(profiles) > MAX_PROFILES:
            return None
        if any(type(key) is not str or PROFILE.fullmatch(key) is None
               or not _valid_nickname(value) for key, value in profiles.items()):
            return None
        return profiles
    except (UnicodeError, ValueError, OSError):
        return None


def _prepare_private_directory(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = path.parent.lstat()
        return (
            stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
            and (info.st_mode & 0o077) == 0
        )
    except OSError:
        return False


def _write(path: Path, records: dict[str, str]) -> bool:
    payload = (json.dumps({"schema": STORE_SCHEMA, "profiles": records},
                          ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > MAX_FILE:
        return False
    handle = None
    temp_path = None
    try:
        handle, temp_path = tempfile.mkstemp(prefix=".phone-name-", dir=path.parent)
        os.fchmod(handle, 0o600)
        with os.fdopen(handle, "wb") as out:
            handle = None
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_path, path)
        temp_path = None
        return True
    except OSError:
        return False
    finally:
        if handle is not None:
            os.close(handle)
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def action(args: list[str], *,
           observer: Callable[[], object] = observe,
           path: Path | None = None) -> dict[str, object]:
    if (len(args) < 2 or args[0] not in ("--read", "--save", "--clear")
            or (len(args) != 3 if args[0] == "--save" else len(args) != 2)):
        return _result("REFUSED")
    command, profile = args[:2]
    if not _current(profile, observer=observer):
        return _result("DEVICE_UNAVAILABLE")
    if command == "--save" and not _valid_nickname(args[2]):
        return _result("INVALID_NICKNAME", profile=profile)
    location = path if path is not None else _state_path()
    if command == "--read":
        records = _load(location)
        if records is None:
            return _result("STORAGE_UNAVAILABLE", profile=profile)
        name = records.get(profile, "")
        return _result("PRESENT" if name else "EMPTY", profile=profile, name=name)

    # Writes occur only on a human's explicit SAVE LABEL or CLEAR LABEL click.
    if not _prepare_private_directory(location):
        return _result("STORAGE_UNAVAILABLE", profile=profile)
    lock_fd = None
    try:
        flags = (os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
                 | getattr(os, "O_CLOEXEC", 0))
        lock_fd = os.open(str(location) + ".lock", flags, 0o600)
        info = os.fstat(lock_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or (info.st_mode & 0o077)):
            return _result("STORAGE_UNAVAILABLE", profile=profile)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        # Do not write if the active provider profile changed during the lock.
        if not _current(profile, observer=observer):
            return _result("DEVICE_UNAVAILABLE")
        records = _load(location)
        if records is None:
            return _result("STORAGE_UNAVAILABLE", profile=profile)
        if command == "--save":
            if profile not in records and len(records) >= MAX_PROFILES:
                return _result("STORAGE_FULL", profile=profile)
            records[profile] = args[2]
            final = _result("SAVED", profile=profile, name=args[2])
        else:
            if profile not in records:
                return _result("CLEARED", profile=profile)
            del records[profile]
            final = _result("CLEARED", profile=profile)
        if not _write(location, records):
            return _result("STORAGE_UNAVAILABLE", profile=profile)
        return final
    except OSError:
        return _result("STORAGE_UNAVAILABLE", profile=profile)
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    result = action(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in ("PRESENT", "EMPTY", "SAVED", "CLEARED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
