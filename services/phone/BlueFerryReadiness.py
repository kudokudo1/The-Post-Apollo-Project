"""Read-only local readiness for the Social PHONE surface.

No pairing, activation, device discovery, MAC addresses, contacts, messages,
credentials, or phone authorization. A running daemon is not a content grant.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

SCHEMA = "post-apollo.social.phone-readiness.v0"
SERVICE_STATES = {"active", "inactive", "failed", "activating", "deactivating"}


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


def readiness() -> dict[str, object]:
    package = _read_command(["rpm", "-q", "blueferry-backend"])
    adapter = _read_command(["bluetoothctl", "show"])
    powered: bool | None = None
    for line in adapter.splitlines():
        if line.strip() == "Powered: yes":
            powered = True
            break
        if line.strip() == "Powered: no":
            powered = False
            break
    return {
        "schema": SCHEMA,
        "execution": "READ_ONLY",
        "blueferryInstalled": package.startswith("blueferry-backend-"),
        "bluetoothService": _service_state("bluetooth.service"),
        "controllerPowered": powered,
        "configurationPresent": (
            Path(os.path.expanduser("~/.config/blueferry/local.env")).is_file()
        ),
        "backendService": _service_state("blueferry.service", user=True),
        "phoneLink": "UNVERIFIED",
        "contentAuthorized": False,
    }


def main() -> None:
    print(json.dumps(readiness(), sort_keys=True))


if __name__ == "__main__":
    main()
