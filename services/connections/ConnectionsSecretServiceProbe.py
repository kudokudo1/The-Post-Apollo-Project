#!/usr/bin/env python3
"""C2a safe read-only Secret Service availability, never an unlock or lookup.

Only addresses the session D-Bus daemon using NameHasOwner. A failed probe
returns bounded coarse JSON. Does not touch the credential service itself.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Callable

QUERY = (
    "gdbus", "call", "--session",
    "--dest", "org.freedesktop.DBus",
    "--object-path", "/org/freedesktop/DBus",
    "--method", "org.freedesktop.DBus.NameHasOwner",
    "org.freedesktop.secrets",
)


def probe(
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "UNVERIFIED", "serviceAcquired": False,
        "keyringUnlocked": False, "credentialPresent": False,
        "providerAuthenticated": False, "permissionGranted": False,
    }
    if which("gdbus") is None:
        result["status"] = "DBUS_PROBE_TOOL_MISSING"
        return result
    try:
        observed = run(
            QUERY, capture_output=True, text=True, timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result["status"] = "SESSION_BUS_UNAVAILABLE"
        return result
    if observed.returncode != 0:
        result["status"] = "SESSION_BUS_UNAVAILABLE"
        return result
    text = observed.stdout.strip()
    if re.fullmatch(r"\(\s*true\s*,?\s*\)", text):
        result["status"] = "SERVICE_ACQUIRED"
        result["serviceAcquired"] = True
    elif re.fullmatch(r"\(\s*false\s*,?\s*\)", text):
        result["status"] = "SERVICE_NOT_RUNNING"
    else:
        result["status"] = "UNEXPECTED_DBUS_RESPONSE"
    return result


if __name__ == "__main__":
    print(json.dumps(probe(), separators=(",", ":"), sort_keys=True))
