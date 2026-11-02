#!/usr/bin/env python3
"""Opt-in, read-only Linux iPhone Bluetooth prerequisite inventory (P2).

Run ONLY with --inspect. This never scans/pairs/disconnects a Bluetooth
device, activates BlueFerry, requests phone data, reads Bluetooth addresses,
queries session/system D-Bus, installs packages or changes the desktop.

Information is a local tool/sysfs snapshot, NOT Bluetooth/iPhone readiness.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Any

SCHEMA = "post-apollo.phone.iphone-bluetooth-prerequisites.v0"
_TIMEOUT = 3
_MAX_VERSION_BYTES = 256
_MAX_SYSFS_ENTRIES = 32
_MAX_ADAPTERS = 8
_VERSION = re.compile(r"(?:bluetoothctl(?::|\s)\s*)?(\d{1,3})\.(\d{1,3})(?:\.\d{1,3})?\s*\Z", re.ASCII)
_HCI = re.compile(r"hci(?:0|[1-9][0-9]{0,2})\Z", re.ASCII)


def _snapshot(
    state: str,
    *,
    bluez_version: str | None = None,
    adapter_count: int | None = None,
    blueferry_available: bool = False,
) -> dict[str, Any]:
    # Never return command paths, device names/addresses, paired phone IDs,
    # iPhone model, Linux username, environment, D-Bus data or subprocess text.
    version_tuple = tuple(map(int, bluez_version.split("."))) if bluez_version else None
    return {
        "schema": SCHEMA,
        "execution": "OPT_IN_LOCAL_METADATA_ONLY",
        "state": state,
        "bluezVersion": bluez_version,
        "adapterCount": adapter_count,
        "blueferryExecutableFound": blueferry_available,
        "mapPbapVersionMinimum": (
            "DOCUMENTED_VERSION_MET" if version_tuple is not None and version_tuple >= (5, 72)
            else "BELOW_DOCUMENTED_VERSION" if version_tuple is not None
            else "NOT_CHECKED"
        ),
        "ancsVersionMinimum": (
            "DOCUMENTED_VERSION_MET" if version_tuple is not None and version_tuple >= (5, 86)
            else "BELOW_DOCUMENTED_VERSION" if version_tuple is not None
            else "NOT_CHECKED"
        ),
        "controllerClassicLeSupport": "NOT_CHECKED",
        "iphonePairing": "NOT_CHECKED",
        "iphonePermissions": "NOT_CHECKED",
        "blueferryDaemon": "NOT_CHECKED",
        "networkRoute": "NOT_CHECKED",
        "messaging": "NOT_VERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
    }


def _binary_path(which: Callable[[str], str | None], name: str) -> str | None:
    value = which(name)
    if value is None:
        return None
    if (type(value) is not str or not value.startswith("/")
            or len(value) > 4096 or any(ord(ch) < 32 for ch in value)):
        raise ValueError("invalid executable path")
    return value


def parse_version(stdout: object, returncode: object) -> str | None:
    """Read only exact BlueZ major.minor version, never error text."""
    if type(returncode) is not int or returncode != 0 or type(stdout) is not str:
        return None
    try:
        if len(stdout.encode("utf-8")) > _MAX_VERSION_BYTES:
            return None
    except UnicodeError:
        return None
    match = _VERSION.fullmatch(stdout.strip())
    if not match:
        return None
    return f"{int(match.group(1))}.{int(match.group(2))}"


def _adapter_count(listdir: Callable[[str], list[str]]) -> int:
    entries = listdir("/sys/class/bluetooth")
    if type(entries) not in (list, tuple) or len(entries) > _MAX_SYSFS_ENTRIES:
        raise ValueError("invalid sysfs listing")
    if any(type(name) is not str for name in entries):
        raise ValueError("invalid sysfs entry")
    adapters = [name for name in entries if _HCI.fullmatch(name)]
    if len(adapters) > _MAX_ADAPTERS or len(set(adapters)) != len(adapters):
        raise ValueError("invalid adapter count")
    return len(adapters)


def inspect(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = subprocess.run,
    listdir: Callable[[str], list[str]] = os.listdir,
    platform: str = sys.platform,
) -> dict[str, Any]:
    """One fixed --version command and one sysfs directory listing, no bus."""
    if platform != "linux":
        return _snapshot("UNSUPPORTED_PLATFORM")
    try:
        blueferry = _binary_path(which, "blueferry") is not None
        ctl = _binary_path(which, "bluetoothctl")
        try:
            count = _adapter_count(listdir)
        except (OSError, UnicodeError, ValueError, TypeError):
            count = None

        if ctl is None:
            return _snapshot(
                "BLUEZ_CLI_MISSING", adapter_count=count,
                blueferry_available=blueferry,
            )
        reply = runner(
            [ctl, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        version = parse_version(getattr(reply, "stdout", None),
                                getattr(reply, "returncode", None))
        if version is None:
            return _snapshot(
                "BLUEZ_VERSION_UNAVAILABLE", adapter_count=count,
                blueferry_available=blueferry,
            )
        return _snapshot(
            "LOCAL_METADATA_OBSERVED" if count is not None
            else "SYSFS_UNAVAILABLE",
            bluez_version=version, adapter_count=count,
            blueferry_available=blueferry,
        )
    except subprocess.TimeoutExpired:
        return _snapshot("VERSION_QUERY_TIMEOUT")
    except (OSError, UnicodeError, ValueError, TypeError):
        return _snapshot("INVENTORY_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--inspect"]:
        print(json.dumps(_snapshot("EXPLICIT_FLAG_REQUIRED"), sort_keys=True))
        return 2
    print(json.dumps(inspect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
