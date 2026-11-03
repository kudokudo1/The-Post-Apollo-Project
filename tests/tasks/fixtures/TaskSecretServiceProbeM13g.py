#!/usr/bin/env python3
"""M13g read-only Secret Service *presence* probe.

Only asks org.freedesktop.DBus.NameHasOwner for org.freedesktop.secrets.
This cannot auto-activate the target service, list collections, prompt,
unlock, retrieve, store or clear any secret. Its response is intentionally
small and contains no account/environment/secret values.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Callable

OWNER = "org.freedesktop.secrets"
QUERY = [
    "gdbus", "call", "--session",
    "--dest", "org.freedesktop.DBus",
    "--object-path", "/org/freedesktop/DBus",
    "--method", "org.freedesktop.DBus.NameHasOwner",
    OWNER,
]


def probe(
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    availability = {
        "gdbus": which("gdbus") is not None,
        "secret_tool": which("secret-tool") is not None,
        "gnome_keyring_daemon": which("gnome-keyring-daemon") is not None,
    }
    output: dict[str, object] = {
        "status": "NOT_VERIFIED",
        "service_name": OWNER,
        "owner_present": False,
        "tools": availability,
        "safe_read_only": True,
        "authenticated_unlock_verified": False,
        "key_roundtrip_verified": False,
        "production_key_provider_selected": False,
    }
    if not availability["gdbus"]:
        output["status"] = "DBUS_PROBE_TOOL_MISSING"
        return output
    try:
        observed = run(
            QUERY, capture_output=True, text=True, timeout=4, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        output["status"] = "SESSION_BUS_UNAVAILABLE"
        return output
    if observed.returncode != 0:
        output["status"] = "SESSION_BUS_UNAVAILABLE"
        return output
    answer = observed.stdout.strip()
    # gdbus may print '(true,)' or '(false,)' with whitespace.
    if re.fullmatch(r"\(\s*true\s*,?\s*\)", answer):
        output["status"] = "SERVICE_ACQUIRED"
        output["owner_present"] = True
    elif re.fullmatch(r"\(\s*false\s*,?\s*\)", answer):
        output["status"] = "SERVICE_NOT_RUNNING"
    else:
        output["status"] = "UNEXPECTED_DBUS_RESPONSE"
    return output


if __name__ == "__main__":
    print(json.dumps(probe(), sort_keys=True, separators=(",", ":")))
