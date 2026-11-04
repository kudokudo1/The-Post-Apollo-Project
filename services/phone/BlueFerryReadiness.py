"""Read-only local readiness for the Social PHONE surface.

No pairing, activation, device discovery, MAC addresses, contacts, messages,
credentials, or phone authorization. A running daemon is not a content grant.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess

SCHEMA = "post-apollo.social.phone-readiness.v0"
SERVICE_STATES = {"active", "inactive", "failed", "activating", "deactivating"}
BLUEFERRY_BUS = "io.weirdware.BlueFerry"
BLUEFERRY_PATH = "/io/weirdware/BlueFerry"
BLUEFERRY_IFACE = "io.weirdware.BlueFerry.Messages1"
# A unique-owner destination cannot D-Bus-activate a stopped backend.
UNIQUE_OWNER = re.compile(r"^:[0-9]+\\.[0-9]+$")


def _read_command(argv: list[str]) -> str:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=3, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _service_state(unit: str, *, user: bool = False) -> str:
    argv = ["systemctl"]
    if user:
        argv.append("--user")
    # is-active returns exit status 3 for an inactive unit, but still prints
    # its state. Do not treat that as a reason to start or restart it.
    argv.extend(["is-active", unit])
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=3, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    state = result.stdout.strip()
    return state if state in SERVICE_STATES else "unknown"



def _backend_profile_observation(
    service_state: str, *, dbus_api: object = None, bus_address: str | None = None
) -> dict[str, object]:
    """Observe an already-running BlueFerry daemon, without activating it.

    GetStatus contains more data than the Social UI is allowed to see. Only
    two strict booleans are projected, and they are *backend self-reports*,
    not permission grants, verified phone identity, or content access.
    """
    unknown = {
        "backendObservation": "NOT_RUNNING" if service_state != "active" else "UNAVAILABLE",
        "mapSessionActive": None,
        "pbapSessionActive": None,
    }
    if service_state != "active":
        return unknown
    if bus_address is None:
        bus_address = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not bus_address:
        return unknown

    try:
        if dbus_api is None:
            import dbus as dbus_api

        bus = dbus_api.SessionBus(private=True)
        if not bus.name_has_owner(BLUEFERRY_BUS):
            return {**unknown, "backendObservation": "NO_OWNER"}
        owner = str(bus.get_name_owner(BLUEFERRY_BUS))
        if UNIQUE_OWNER.fullmatch(owner) is None:
            return unknown
        # Passing the unique name, not the activatable well-known name, is
        # essential. Even if the daemon dies here, it will NOT be launched.
        proxy = bus.get_object(owner, BLUEFERRY_PATH, introspect=False)
        iface = dbus_api.Interface(proxy, BLUEFERRY_IFACE)
        raw = str(iface.GetStatus(timeout=3))
        if len(raw) > 32768:
            return unknown
        status = json.loads(raw)
        if (type(status) is not dict or type(status.get("api_version")) is not int
                or status["api_version"] != 2 or status.get("daemon") is not True
                or type(status.get("map")) is not bool
                or type(status.get("pbap")) is not bool):
            return unknown
        return {
            "backendObservation": "REPORTED",
            "mapSessionActive": status["map"],
            "pbapSessionActive": status["pbap"],
        }
    except Exception:
        # Never log D-Bus errors or provider status. They may contain phone
        # identifiers or metadata; the UI only receives a bounded enum.
        return unknown


def readiness() -> dict[str, object]:
    package = _read_command(["rpm", "-q", "blueferry-backend"])
    bluetooth_state = _service_state("bluetooth.service")
    # bluetoothctl may D-Bus-activate bluetoothd on some hosts. Only inspect
    # the controller if the system service was already active.
    adapter = _read_command(["bluetoothctl", "show"]) if bluetooth_state == "active" else ""
    powered: bool | None = None
    for line in adapter.splitlines():
        if line.strip() == "Powered: yes":
            powered = True
            break
        if line.strip() == "Powered: no":
            powered = False
            break
    backend_state = _service_state("blueferry.service", user=True)
    observation = _backend_profile_observation(backend_state)
    return {
        "schema": SCHEMA,
        "execution": "READ_ONLY",
        "blueferryInstalled": package.startswith("blueferry-backend-"),
        "bluetoothService": bluetooth_state,
        "controllerPowered": powered,
        "configurationPresent": (
            Path(os.path.expanduser("~/.config/blueferry/local.env")).is_file()
        ),
        "backendService": backend_state,
        **observation,
        "phoneLink": "UNVERIFIED",
        "contentAuthorized": False,
    }


def main() -> None:
    print(json.dumps(readiness(), sort_keys=True))


if __name__ == "__main__":
    main()
