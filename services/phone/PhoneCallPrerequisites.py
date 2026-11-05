#!/usr/bin/env python3
"""Read-only oFono prerequisite diagnosis for Social PHONE's existing Calls button.

A real hands-free call requires more than an active service. This helper checks
only local package/unit and D-Bus *presence*, not Bluetooth identity, messages,
microphone capture, WirePlumber configuration or private phone data.

It NEVER installs, enables, starts or restarts a service.
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Callable

SCHEMA = "post-apollo.phone.calls-prerequisites.v0"
PACKAGE = frozenset({"INSTALLED", "NOT_INSTALLED", "UNKNOWN"})
LOAD = frozenset({"loaded", "not-found", "masked", "error", "stub", "unknown"})
ACTIVE = frozenset({
    "active", "inactive", "failed", "activating", "deactivating", "reloading",
    "unknown",
})
BUS = frozenset({"OWNER_PRESENT", "NO_OWNER", "UNKNOWN"})
STATES = frozenset({
    "PACKAGE_NOT_INSTALLED", "SERVICE_UNIT_MISSING", "SERVICE_MASKED",
    "SERVICE_FAILED", "SERVICE_STOPPED", "SERVICE_STARTING",
    "DBUS_NAME_MISSING", "AUDIO_PATH_UNVERIFIED", "INSPECTION_UNAVAILABLE",
})


def package_state(*, runner: Callable[..., object] = subprocess.run) -> str:
    """Never copy rpm output into the UI."""
    try:
        result = runner(
            ["rpm", "-q", "--qf", "%{NAME}", "ofono"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if getattr(result, "returncode", None) == 0:
            return ("INSTALLED" if getattr(result, "stdout", "").strip() == "ofono"
                    else "UNKNOWN")
        if getattr(result, "returncode", None) == 1:
            return "NOT_INSTALLED"
    except Exception:
        pass
    return "UNKNOWN"


def service_state(*, runner: Callable[..., object] = subprocess.run) -> tuple[str, str]:
    """System service status only. No systemctl action can alter its state."""
    try:
        result = runner(
            ["systemctl", "show", "ofono.service", "--no-pager",
             "--property=LoadState", "--property=ActiveState"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        output = getattr(result, "stdout", "")
        if type(output) is not str or len(output) > 2048:
            return "unknown", "unknown"
        fields: dict[str, str] = {}
        for line in output.splitlines():
            if line.count("=") != 1:
                continue
            key, value = line.split("=", 1)
            if key in ("LoadState", "ActiveState"):
                fields[key] = value
        raw_load = fields.get("LoadState", "unknown")
        raw_active = fields.get("ActiveState", "unknown")
        return (
            raw_load if raw_load in LOAD else "unknown",
            raw_active if raw_active in ACTIVE else "unknown",
        )
    except Exception:
        return "unknown", "unknown"


def bus_state() -> str:
    """Only has_name_owner; never invoke methods on or activate org.ofono."""
    try:
        import dbus  # type: ignore
        bus = dbus.SystemBus(private=True)
        return "OWNER_PRESENT" if bus.name_has_owner("org.ofono") else "NO_OWNER"
    except Exception:
        return "UNKNOWN"


def diagnose(
    *,
    package: Callable[[], str] = package_state,
    service: Callable[[], tuple[str, str]] = service_state,
    bus: Callable[[], str] = bus_state,
) -> dict[str, object]:
    try:
        p = package()
    except Exception:
        p = "UNKNOWN"
    if type(p) is not str or p not in PACKAGE:
        p = "UNKNOWN"

    try:
        data = service()
        load, active = data if type(data) is tuple and len(data) == 2 else ("unknown", "unknown")
    except Exception:
        load, active = "unknown", "unknown"
    if type(load) is not str or load not in LOAD:
        load = "unknown"
    if type(active) is not str or active not in ACTIVE:
        active = "unknown"

    owner = "UNKNOWN"
    if active == "active":
        try:
            value = bus()
            if type(value) is str and value in BUS:
                owner = value
        except Exception:
            pass

    if load == "not-found":
        state = "PACKAGE_NOT_INSTALLED" if p == "NOT_INSTALLED" else "SERVICE_UNIT_MISSING"
    elif load == "masked":
        state = "SERVICE_MASKED"
    elif active == "failed":
        state = "SERVICE_FAILED"
    elif active == "inactive":
        state = "SERVICE_STOPPED"
    elif active in ("activating", "deactivating", "reloading"):
        state = "SERVICE_STARTING"
    elif active == "active":
        state = ("DBUS_NAME_MISSING" if owner == "NO_OWNER"
                 else "AUDIO_PATH_UNVERIFIED")
    else:
        state = "INSPECTION_UNAVAILABLE"

    return {
        "schema": SCHEMA,
        "execution": "READ_ONLY_CALL_DIAGNOSIS",
        "state": state,
        "package": p,
        "serviceLoad": load,
        "serviceActive": active,
        "systemBus": owner,
        "hfpReady": False,
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--check"]:
        print(json.dumps({
            "schema": SCHEMA, "execution": "READ_ONLY_CALL_DIAGNOSIS",
            "state": "EXPLICIT_ACTION_REQUIRED",
            "hfpReady": False,
            "trustedPhoneLink": "UNVERIFIED",
            "contentAccessEnabled": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(diagnose(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
