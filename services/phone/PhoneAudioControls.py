#!/usr/bin/env python3
"""Explicit, per-BlueFerry-phone media/calls controls for Social PHONE.

No persistent Post-Apollo device store. The provider owns saved preferences.
Status reads the already-running daemon by its unique D-Bus owner. Changing
a route requires a deliberate in-menu click and a fixed CLI argument list.
No installs, pairing, service restart, arbitrary command, phone content or
unrestricted device selection.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

from BlueFerryReadiness import (
    BLUEFERRY_BUS, BLUEFERRY_PATH, BLUEFERRY_IFACE,
    UNIQUE_OWNER, _service_state,
)

SCHEMA = "post-apollo.phone.audio-controls.v0"
PREFS = frozenset({"pc", "phone", "auto"})
CALL_STATES = frozenset({
    "disabled", "unavailable", "searching", "connecting", "ready",
    "bluez_conflict",
})
MEDIA_CHOICES = {"phone": "phone", "pc": "pc", "auto": "auto"}
CALL_CHOICES = {"enable": True, "disable": False}


def _config_exists() -> bool:
    try:
        return Path(os.path.expanduser("~/.config/blueferry/local.env")).is_file()
    except (OSError, ValueError):
        return False


def _status_from_running_daemon() -> object:
    """GetStatus never addresses the activatable well-known bus name."""
    import dbus  # type: ignore

    bus = dbus.SessionBus(private=True)
    if not bus.name_has_owner(BLUEFERRY_BUS):
        return None
    owner = str(bus.get_name_owner(BLUEFERRY_BUS))
    if UNIQUE_OWNER.fullmatch(owner) is None:
        return None
    proxy = bus.get_object(owner, BLUEFERRY_PATH, introspect=False)
    interface = dbus.Interface(proxy, BLUEFERRY_IFACE)
    payload = str(interface.GetStatus(timeout=3))
    if len(payload) > 32768:
        return None
    return json.loads(payload)


def _ofono_active() -> bool:
    return _service_state("ofono.service") == "active"


def _output(result: str, observed: dict | None = None,
            *, can_adjust: bool = False, ofono: bool = False,
            execution: str = "READ_ONLY") -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": execution, "result": result,
        "mediaPreference": observed["preference"] if observed else "UNKNOWN",
        "mediaRoute": observed["route"] if observed else "UNKNOWN",
        "callsEnabled": observed["calls_enabled"] if observed else None,
        "callsState": observed["calls_state"] if observed else "UNKNOWN",
        "canAdjust": can_adjust, "ofonoActive": ofono,
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }


def _project(value: object) -> dict | None:
    if (type(value) is not dict
            or type(value.get("api_version")) is not int
            or value.get("api_version") != 2
            or value.get("daemon") is not True):
        return None
    raw_pref = value.get("phone_audio_preference")
    raw_route = value.get("phone_audio_route")
    raw_calls = value.get("calls_enabled")
    raw_state = value.get("calls_state")
    return {
        "preference": raw_pref.upper() if type(raw_pref) is str and raw_pref in PREFS else "UNKNOWN",
        "route": raw_route.upper() if type(raw_route) is str and raw_route in ("pc", "phone") else "UNKNOWN",
        "calls_enabled": raw_calls if type(raw_calls) is bool else None,
        "calls_state": raw_state.upper() if type(raw_state) is str and raw_state in CALL_STATES else "UNKNOWN",
    }


def inspect(
    *, config: Callable[[], bool] = _config_exists,
    service: Callable[[], str] = lambda: _service_state("blueferry.service", user=True),
    status: Callable[[], object] = _status_from_running_daemon,
    ofono: Callable[[], bool] = _ofono_active,
) -> dict[str, object]:
    try:
        if config() is not True or service() != "active":
            return _output("BRIDGE_UNAVAILABLE")
        view = _project(status())
        if view is None:
            return _output("BRIDGE_UNAVAILABLE")
        try:
            ofono_ready = ofono() is True
        except Exception:
            ofono_ready = False
        return _output("OBSERVED", view, can_adjust=True, ofono=ofono_ready)
    except Exception:
        return _output("BRIDGE_UNAVAILABLE")


def apply(
    family: str, selection: str,
    *, probe: Callable[[], dict[str, object]] = inspect,
    find: Callable[[str], str | None] = shutil.which,
    run: Callable[..., object] = subprocess.run,
) -> dict[str, object]:
    if family == "media":
        if type(selection) is not str or selection not in MEDIA_CHOICES:
            return _output("REFUSED", execution="USER_ACTION")
        args = ["audio", selection]
    elif family == "calls":
        if type(selection) is not str or selection not in CALL_CHOICES:
            return _output("REFUSED", execution="USER_ACTION")
        args = ["calls", selection]
    else:
        return _output("REFUSED", execution="USER_ACTION")

    before = probe()
    if (type(before) is not dict or before.get("schema") != SCHEMA
            or before.get("execution") != "READ_ONLY"
            or before.get("result") != "OBSERVED"
            or before.get("canAdjust") is not True
            or before.get("trustedPhoneLink") != "UNVERIFIED"
            or before.get("contentAccessEnabled") is not False):
        return _output("BRIDGE_UNAVAILABLE", execution="USER_ACTION")
    if family == "calls" and selection == "enable" and before.get("ofonoActive") is not True:
        return _output(
            "CALLS_PREREQUISITES_MISSING",
            observed=_safe_before(before), can_adjust=True,
            ofono=False, execution="USER_ACTION",
        )
    # No arbitrary paths or command arguments may arrive from provider data.
    try:
        executable = find("blueferry")
        if type(executable) is not str or not os.path.isabs(executable):
            return _output("CLIENT_UNAVAILABLE", execution="USER_ACTION")
        completed = run(
            [executable, *args],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if getattr(completed, "returncode", 1) != 0:
            return _output("CHANGE_FAILED", execution="USER_ACTION")
    except Exception:
        return _output("CHANGE_FAILED", execution="USER_ACTION")
    # The upstream CLI's exit code only means a request was submitted.
    # Require an independent status reread before claiming a saved preference.
    after = probe()
    match = (
        type(after) is dict
        and after.get("result") == "OBSERVED"
        and after.get("canAdjust") is True
        and (
            after.get("mediaPreference") == selection.upper()
            if family == "media"
            else after.get("callsEnabled") is CALL_CHOICES[selection]
        )
    )
    if not match:
        return _output("NOT_CONFIRMED", execution="USER_ACTION")
    return _output(
        "PREFERENCE_SAVED", observed=_safe_before(after),
        can_adjust=True, ofono=after.get("ofonoActive") is True,
        execution="USER_ACTION",
    )


def _safe_before(view: dict[str, object]) -> dict:
    # Convert ONLY typed, bounded local state already returned by inspect.
    return {
        "preference": view["mediaPreference"] if view.get("mediaPreference") in ("PHONE", "PC", "AUTO") else "UNKNOWN",
        "route": view["mediaRoute"] if view.get("mediaRoute") in ("PHONE", "PC") else "UNKNOWN",
        "calls_enabled": view["callsEnabled"] if type(view.get("callsEnabled")) is bool else None,
        "calls_state": view["callsState"] if view.get("callsState") in (
            "DISABLED", "UNAVAILABLE", "SEARCHING", "CONNECTING",
            "READY", "BLUEZ_CONFLICT"
        ) else "UNKNOWN",
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--status"]:
        value = inspect()
    elif len(args) == 3 and args[0] == "--set":
        value = apply(args[1], args[2])
    else:
        value = _output("REFUSED")
    print(json.dumps(value, sort_keys=True))
    return 0 if value["result"] in ("OBSERVED", "PREFERENCE_SAVED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
