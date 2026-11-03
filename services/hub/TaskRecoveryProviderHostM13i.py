#!/usr/bin/env python3
"""M13i: read-only provider-status host for the unactivated TASKS QML seam.

There is no keyring API here. The only command requests a *name-owner bit*
from the session D-Bus daemon. The requested name is NOT activated, and
collections, labels, items and unlock credentials are never read.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from typing import Callable

QUERY = [
    "gdbus", "call", "--session",
    "--dest", "org.freedesktop.DBus",
    "--object-path", "/org/freedesktop/DBus",
    "--method", "org.freedesktop.DBus.NameHasOwner",
    "org.freedesktop.secrets",
]
STATUSES = (
    "SERVICE_ACQUIRED",
    "SERVICE_NOT_RUNNING",
    "PROBE_TOOL_MISSING",
    "SESSION_BUS_UNAVAILABLE",
    "UNEXPECTED_RESPONSE",
)
DENIED = {
    "protocol": 1, "kind": "M13I_PROVIDER_STATUS",
    "status": "REFUSED_NO_ACTION", "providerPresent": False,
    "keyringUnlocked": False, "recoveryEnabled": False,
    "writeAuthorized": False, "persistAuthorized": False,
    "decryptAuthorized": False, "productionActivation": False,
}


def probe(
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    status = "PROBE_TOOL_MISSING"
    if which("gdbus") is not None:
        try:
            completed = run(
                QUERY, capture_output=True, text=True, check=False, timeout=4
            )
            if completed.returncode == 0:
                output = completed.stdout.strip()
                if re.fullmatch(r"\(\s*true\s*,?\s*\)", output):
                    status = "SERVICE_ACQUIRED"
                elif re.fullmatch(r"\(\s*false\s*,?\s*\)", output):
                    status = "SERVICE_NOT_RUNNING"
                else:
                    status = "UNEXPECTED_RESPONSE"
            else:
                status = "SESSION_BUS_UNAVAILABLE"
        except (OSError, subprocess.TimeoutExpired):
            status = "SESSION_BUS_UNAVAILABLE"
    return {
        "protocol": 1, "kind": "M13I_PROVIDER_STATUS",
        "status": status,
        "providerPresent": status == "SERVICE_ACQUIRED",
        "keyringUnlocked": False,
        "recoveryEnabled": False,
        "writeAuthorized": False,
        "persistAuthorized": False,
        "decryptAuthorized": False,
        "productionActivation": False,
    }


if __name__ == "__main__":
    result = probe() if sys.argv[1:] == ["--probe"] else DENIED
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
