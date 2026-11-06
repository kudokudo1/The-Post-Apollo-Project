#!/usr/bin/env python3
"""Read-only observation of the configured BlueFerry phone, not Social authorization.

BlueFerry owns pairing and profile IDs. The private config MAC is used *only*
inside this process to match the running daemon profile to a BlueZ Device1.
Neither a MAC, D-Bus object path, configuration value nor phone content is
returned. A physical Bluetooth link does not authorize Social message access.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys
from collections.abc import Mapping
from typing import Callable

SCHEMA = "post-apollo.phone.device-observation.v0"
PROFILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
MAC = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")
OWNER = re.compile(r"^:[0-9]+\.[0-9]+$")
SERVICE = "io.weirdware.BlueFerry"
OBJECT = "/io/weirdware/BlueFerry"
IFACE = SERVICE + ".Messages1"


def _running_profile() -> object:
    """Call only an already-running unique-owner BlueFerry daemon."""
    import dbus  # type: ignore

    bus = dbus.SessionBus(private=True)
    if not bus.name_has_owner(SERVICE):
        return None
    owner = str(bus.get_name_owner(SERVICE))
    if not OWNER.fullmatch(owner):
        return None
    proxy = bus.get_object(owner, OBJECT, introspect=False)
    raw = str(dbus.Interface(proxy, IFACE).GetStatus(timeout=3))
    if len(raw) > 32768:
        return None
    return json.loads(raw)


def _saved_binding() -> tuple[str, str] | None:
    """Read only the two identity fields from BlueFerry's owner-only config."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / "blueferry" / "local.env"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_size > 65536):
                return None
            data = handle.read(65537)
        if len(data) > 65536:
            return None
    except (OSError, UnicodeError, ValueError):
        return None

    keys: dict[str, str] = {}
    for line in data.splitlines():
        key, sep, value = line.partition("=")
        if not sep or key not in ("BLUEFERRY_PROFILE_ID", "BLUEFERRY_MAC"):
            continue
        if key in keys:
            return None
        keys[key] = value.strip().strip('"')
    profile = keys.get("BLUEFERRY_PROFILE_ID", "")
    mac = keys.get("BLUEFERRY_MAC", "").upper()
    if not PROFILE.fullmatch(profile) or not MAC.fullmatch(mac):
        return None
    return profile, mac


def _dbus_flag(value: object) -> bool | None:
    if type(value) is bool:
        return value
    # dbus-python's Boolean is an integer subclass, not a Python bool.
    if type(value).__name__ == "Boolean" and type(value).__module__.startswith("dbus"):
        return bool(value)
    return None


def _bluez_device(mac: str) -> object:
    """Match the exact configured phone address in an already-running BlueZ."""
    import dbus  # type: ignore

    bus = dbus.SystemBus(private=True)
    if not bus.name_has_owner("org.bluez"):
        return None
    proxy = bus.get_object("org.bluez", "/", introspect=False)
    devices = dbus.Interface(
        proxy, "org.freedesktop.DBus.ObjectManager"
    ).GetManagedObjects(timeout=3)
    if not isinstance(devices, Mapping) or len(devices) > 2048:
        return None
    for interfaces in devices.values():
        if not isinstance(interfaces, Mapping):
            continue
        props = interfaces.get("org.bluez.Device1")
        if not isinstance(props, Mapping):
            continue
        if str(props.get("Address", "")).upper() != mac:
            continue
        return {
            "paired": _dbus_flag(props.get("Paired")),
            "connected": _dbus_flag(props.get("Connected")),
            "alias": str(props.get("Alias", "")),
        }
    return None


def _result(state: str = "UNAVAILABLE", *, profile_id: str = "",
            name: str = "", link: str = "UNVERIFIED") -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": state, "profileId": profile_id, "displayName": name,
        "bluetoothLink": link, "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def observe(*, backend: Callable[[], object] = _running_profile,
            binding: Callable[[], object] = _saved_binding,
            bluez: Callable[[str], object] = _bluez_device) -> dict[str, object]:
    try:
        status = backend()
        if (not isinstance(status, dict) or status.get("api_version") != 2
                or status.get("daemon") is not True
                or type(status.get("map")) is not bool
                or type(status.get("pbap")) is not bool):
            return _result()
        profile_id = status.get("phone_profile_id")
        if type(profile_id) is not str or not PROFILE.fullmatch(profile_id):
            return _result()
        saved = binding()
        if (not isinstance(saved, tuple) or len(saved) != 2
                or saved[0] != profile_id or type(saved[1]) is not str
                or not MAC.fullmatch(saved[1])):
            return _result("PROFILE_ONLY", profile_id=profile_id, name="iPhone")
        observed = bluez(saved[1])
        if not isinstance(observed, dict):
            return _result("PROFILE_ONLY", profile_id=profile_id, name="iPhone")
        paired, connected = observed.get("paired"), observed.get("connected")
        if type(paired) is not bool or type(connected) is not bool or not paired:
            return _result("PROFILE_ONLY", profile_id=profile_id, name="iPhone")
        raw_name = observed.get("alias")
        name = raw_name.strip() if type(raw_name) is str else ""
        if not name or len(name) > 56 or not name.isprintable():
            name = "iPhone"
        if connected:
            return _result("BLUETOOTH_CONNECTED", profile_id=profile_id,
                           name=name, link="CONNECTED")
        return _result("PAIRED_OFFLINE", profile_id=profile_id,
                       name=name, link="PAIRED_OFFLINE")
    except Exception:
        return _result()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--inspect"]:
        print(json.dumps(_result(), sort_keys=True))
        return 2
    print(json.dumps(observe(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
