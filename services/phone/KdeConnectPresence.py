#!/usr/bin/env python3
"""P1 KDE Connect presence snapshot; no phone messages or permissions requested.

Explicit CLI invocation can activate the user's existing KDE Connect daemon
through D-Bus. This source is inert unless the operator deliberately runs it.
Presence is NOT a proof of network transport, Android OS, SMS, contacts, or calls.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Callable

SCHEMA = "post-apollo.phone.kdeconnect-presence.v0"
CLI_ARGS = ("--list-available", "--id-only")
DEVICE_ID = re.compile(r"^[A-Za-z0-9_.-]{8,128}$")
MAX_DEVICES = 32
MAX_BYTES = 8192
TIMEOUT_SECONDS = 5


def _snapshot(state: str, count: int = 0) -> dict[str, Any]:
    """Deliberately omit device names, IDs, addresses, messages, and contacts."""
    return {
        "schema": SCHEMA,
        "provider": "kdeconnect",
        "execution": "DISCOVERY_ONLY",
        "state": state,
        "pairedReachableCount": count,
        "devicePlatform": "UNVERIFIED",
        "transport": "UNVERIFIED",
        "sms": "NOT_CHECKED",
        "contacts": "NOT_CHECKED",
        "notifications": "NOT_CHECKED",
        "callAudio": "NOT_CHECKED",
        "routeEligible": False,
    }


def summarize(stdout: object, returncode: object) -> dict[str, Any]:
    """Parse the exact --list-available --id-only output, without exposing IDs."""
    if type(returncode) is not int or returncode != 0:
        return _snapshot("CLIENT_ERROR")
    if not isinstance(stdout, str) or len(stdout.encode("utf-8")) > MAX_BYTES:
        return _snapshot("INVALID_RESPONSE")
    if stdout == "":
        return _snapshot("NO_PAIRED_REACHABLE_DEVICES")
    lines = stdout.splitlines()
    if len(lines) > MAX_DEVICES or not lines or any(
        not DEVICE_ID.fullmatch(line) for line in lines
    ) or len(set(lines)) != len(lines):
        return _snapshot("INVALID_RESPONSE")
    return _snapshot("PAIRED_REACHABLE_REPORTED", len(lines))


def probe(
    *,
    find_executable: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Opt-in local inventory request with fixed, nonmutating command arguments.

    May autostart an installed KDE Connect user daemon; never call silently.
    Caller must separately verify protocol, phone OS, permissions, pairing
    identity, connection transport and capability before routing any action.
    """
    path = find_executable("kdeconnect-cli")
    if not path:
        return _snapshot("CLIENT_NOT_INSTALLED")
    try:
        result = runner(
            [path, *CLI_ARGS],
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _snapshot("CLIENT_TIMEOUT")
    except (OSError, UnicodeError, ValueError):
        return _snapshot("CLIENT_ERROR")
    return summarize(getattr(result, "stdout", None),
                     getattr(result, "returncode", None))


def main() -> None:
    print(json.dumps(probe(), separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
