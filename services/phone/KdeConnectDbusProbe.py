#!/usr/bin/env python3
"""Explicit opt-in, read-only KDE Connect user D-Bus metadata diagnostic.

Never performs pairing, plugin changes, contacts sync, SMS retrieval/sending,
or any desktop integration. No D-Bus service auto-activation. Does not establish
identity authorization or any READY capabilities; strictly local evidence.
"""
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Callable

from KdeConnectDbusEvidence import SCHEMA as EVIDENCE_SCHEMA, assess

SCHEMA = "post-apollo.phone.kdeconnect-dbus-probe.v0"
BUS_NAME = "org.kde.kdeconnect"
BUS_OBJECT = "/modules/kdeconnect"
BUS_INTERFACE = "org.kde.kdeconnect.daemon"
DEVICE_INTERFACE = "org.kde.kdeconnect.device"
DBUS_SERVICE = "org.freedesktop.DBus"
DBUS_OBJECT = "/org/freedesktop/DBus"
DEVICE_ID = re.compile(r"^[A-Za-z0-9_]{8,80}$")
MAX_DEVICES = 4
MAX_REPLY_BYTES = 8192
MAX_TOKENS = 128
TIMEOUT_SECONDS = 3

# Fixed flags guarantee D-Bus calls will not activate kdeconnectd. All
# allowed calls are observational. Do not substitute other methods here.
BASE = ("--user", "--auto-start=no",
        "--allow-interactive-authorization=no", "--timeout=2s", "--no-pager")


def _result(state: str, count: int = 0,
            sms: int = 0, contacts: int = 0, telephony: int = 0) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "execution": "DIAGNOSTIC_ONLY",
        "provider": "kdeconnect",
        "state": state,
        "reportedPairedReachableCount": count,
        "localSmsPluginCount": sms,
        "localContactsPluginCount": contacts,
        "localTelephonyPluginCount": telephony,
        "devicePlatform": "UNVERIFIED",
        "transport": "UNVERIFIED",
        "smsPermission": "NOT_CHECKED",
        "contactsPermission": "NOT_CHECKED",
        "callAudio": "NOT_CHECKED",
        "routeEligible": False,
    }


def _tokens(stdout: object) -> list[str]:
    if not isinstance(stdout, str) or len(stdout.encode("utf-8")) > MAX_REPLY_BYTES:
        raise ValueError("malformed bus response")
    try:
        values = shlex.split(stdout, posix=True)
    except ValueError as exc:
        raise ValueError("malformed bus response") from exc
    if not values or len(values) > MAX_TOKENS:
        raise ValueError("malformed bus response")
    return values


def _boolean(stdout: object, *, variant: bool = False) -> bool:
    values = _tokens(stdout)
    expected = ["v", "b"] if variant else ["b"]
    if values[:-1] != expected or values[-1] not in ("true", "false"):
        raise ValueError("unexpected boolean type")
    return values[-1] == "true"


def _string(stdout: object, *, variant: bool = False) -> str:
    values = _tokens(stdout)
    expected = ["v", "s"] if variant else ["s"]
    if values[:len(expected)] != expected or len(values) != len(expected) + 1:
        raise ValueError("unexpected string type")
    return values[-1]


def _strings(stdout: object, *, variant: bool = False,
             maximum: int = 64) -> list[str]:
    values = _tokens(stdout)
    prefix = ["v", "as"] if variant else ["as"]
    if values[:len(prefix)] != prefix or len(values) < len(prefix) + 1:
        raise ValueError("unexpected string array type")
    count_token = values[len(prefix)]
    if not count_token.isascii() or not count_token.isdecimal():
        raise ValueError("invalid array count")
    count = int(count_token)
    if count > maximum or count != len(values) - len(prefix) - 1:
        raise ValueError("unexpected array count")
    return values[len(prefix) + 1:]


def _call(
    path: str,
    argv: list[str],
    runner: Callable[..., Any],
) -> str:
    completed = runner(
        [path, *BASE, "call", *argv],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    if getattr(completed, "returncode", None) != 0:
        raise ValueError("D-Bus metadata unavailable")
    stdout = getattr(completed, "stdout", None)
    _tokens(stdout)
    return stdout


def _get_property(
    busctl: str,
    object_path: str,
    name: str,
    runner: Callable[..., Any],
) -> str:
    # Properties.Get is a getter, not GetAll (which may expose private names,
    # address lists, verification keys, and other unwanted metadata).
    return _call(busctl, [
        BUS_NAME, object_path, "org.freedesktop.DBus.Properties",
        "Get", "ss", DEVICE_INTERFACE, name,
    ], runner)


def probe(*, find_executable: Callable[[str], str | None] = shutil.which,
          runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Opt-in metadata probe, no auto-start and no messages or pairing."""
    busctl = find_executable("busctl")
    if not isinstance(busctl, str) or not busctl.startswith("/"):
        return _result("BUSCTL_NOT_INSTALLED")
    try:
        owned = _boolean(_call(busctl, [
            DBUS_SERVICE, DBUS_OBJECT, DBUS_SERVICE, "NameHasOwner", "s", BUS_NAME,
        ], runner))
        if not owned:
            return _result("SERVICE_NOT_RUNNING")

        device_ids = _strings(_call(busctl, [
            BUS_NAME, BUS_OBJECT, BUS_INTERFACE, "devices", "bb", "true", "true",
        ], runner), maximum=MAX_DEVICES)
        if len(set(device_ids)) != len(device_ids) or any(
            not DEVICE_ID.fullmatch(device_id) for device_id in device_ids
        ):
            raise ValueError("invalid device IDs")
        if not device_ids:
            return _result("NO_PAIRED_REACHABLE_DEVICES")

        summaries = []
        for device_id in device_ids:
            path = "/modules/kdeconnect/devices/" + device_id
            observation = {
                "schema": EVIDENCE_SCHEMA,
                "isPaired": _boolean(
                    _get_property(busctl, path, "isPaired", runner), variant=True),
                "isReachable": _boolean(
                    _get_property(busctl, path, "isReachable", runner), variant=True),
                "deviceType": _string(
                    _get_property(busctl, path, "type", runner), variant=True),
                "supportedPlugins": _strings(
                    _get_property(busctl, path, "supportedPlugins", runner),
                    variant=True),
                "activeProviderNames": _strings(
                    _get_property(busctl, path, "activeProviderNames", runner),
                    variant=True, maximum=8),
                "loadedPlugins": _strings(_call(busctl, [
                    BUS_NAME, path, DEVICE_INTERFACE, "loadedPlugins",
                ], runner)),
            }
            summary = assess(observation)
            if summary["state"] != "PAIRED_REACHABLE_REPORTED":
                raise ValueError("inconsistent metadata")
            summaries.append(summary)
        return _result(
            "METADATA_REPORTED", count=len(summaries),
            sms=sum(x["sms"] == "LOCAL_PLUGIN_LOADED" for x in summaries),
            contacts=sum(x["contacts"] == "LOCAL_PLUGIN_LOADED" for x in summaries),
            telephony=sum(x["telephonyEvents"] == "LOCAL_PLUGIN_LOADED"
                          for x in summaries),
        )
    except subprocess.TimeoutExpired:
        return _result("BUS_TIMEOUT")
    except (OSError, UnicodeError, ValueError, TypeError):
        # Never surface raw device IDs, subprocess stderr, or D-Bus error text.
        return _result("METADATA_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--probe"]:
        print(json.dumps(_result("EXPLICIT_FLAG_REQUIRED"), separators=(",", ":")))
        return 2
    print(json.dumps(probe(), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
