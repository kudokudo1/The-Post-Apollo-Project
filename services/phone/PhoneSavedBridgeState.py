#!/usr/bin/env python3
"""Read the local BlueFerry setup and service lifecycle without phone content.

One click only. No phone identifiers, MAC addresses, private config values,
messages, contacts, reconnects, service activation or writes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Callable

from BlueFerryReadiness import readiness

SCHEMA = "post-apollo.phone.saved-bridge-state.v0"
STARTUP = frozenset({
    "enabled", "enabled-runtime", "disabled", "static", "indirect",
    "masked", "masked-runtime", "generated", "linked", "linked-runtime",
    "transient", "alias",
})
BACKEND = frozenset({
    "active", "inactive", "failed", "activating", "deactivating", "unknown",
})
PROFILE = frozenset({
    "REPORTED", "NOT_RUNNING", "NO_OWNER", "UNAVAILABLE",
})


def startup_state(*, runner: Callable[..., object] = subprocess.run) -> str:
    try:
        p = runner(
            ["systemctl", "--user", "is-enabled", "blueferry.service"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        value = str(getattr(p, "stdout", "")).strip()
        return value if value in STARTUP else "unknown"
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return "unknown"


def inspect(
    *,
    probe: Callable[[], object] = readiness,
    startup: Callable[[], str] = startup_state,
) -> dict[str, object]:
    try:
        observation = probe()
    except Exception:
        observation = None
    valid = (
        type(observation) is dict
        and observation.get("schema") == "post-apollo.social.phone-readiness.v0"
        and observation.get("execution") == "READ_ONLY"
        and observation.get("phoneLink") == "UNVERIFIED"
        and observation.get("contentAuthorized") is False
        and type(observation.get("configurationPresent")) is bool
        and observation.get("backendService") in BACKEND
        and observation.get("backendObservation") in PROFILE
        and (
            (observation.get("backendObservation") == "REPORTED"
             and type(observation.get("mapSessionActive")) is bool
             and type(observation.get("pbapSessionActive")) is bool
             and observation.get("backendService") == "active")
            or (observation.get("backendObservation") != "REPORTED"
                and observation.get("mapSessionActive") is None
                and observation.get("pbapSessionActive") is None)
        )
    )
    if not valid:
        return {
            "schema": SCHEMA, "execution": "READ_ONLY_LOCAL_LIFECYCLE",
            "state": "UNAVAILABLE", "configurationPresent": None,
            "backendService": "unknown", "startup": "unknown",
            "messageProfile": "UNVERIFIED", "contactsProfile": "UNVERIFIED",
            "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
        }
    try:
        value = startup()
    except Exception:
        value = "unknown"
    startup_value = value if type(value) is str and value in STARTUP else "unknown"
    configured = observation["configurationPresent"]
    backend = observation["backendService"]
    status = observation["backendObservation"]
    if not configured:
        state = "NO_LOCAL_CONFIGURATION"
    elif backend != "active":
        state = "CONFIGURATION_PRESENT_BACKEND_INACTIVE"
    elif status == "REPORTED":
        state = "BACKEND_REPORTED"
    else:
        state = "CONFIGURATION_PRESENT_BACKEND_UNVERIFIED"
    return {
        "schema": SCHEMA, "execution": "READ_ONLY_LOCAL_LIFECYCLE",
        "state": state, "configurationPresent": configured,
        "backendService": backend, "startup": startup_value,
        "messageProfile": ("ACTIVE_BACKEND_REPORT"
                           if status == "REPORTED" and observation["mapSessionActive"]
                           else "INACTIVE_BACKEND_REPORT"
                           if status == "REPORTED" else "UNVERIFIED"),
        "contactsProfile": ("ACTIVE_BACKEND_REPORT"
                            if status == "REPORTED" and observation["pbapSessionActive"]
                            else "INACTIVE_BACKEND_REPORT"
                            if status == "REPORTED" else "UNVERIFIED"),
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--inspect"]:
        print(json.dumps({
            "schema": SCHEMA, "execution": "READ_ONLY_LOCAL_LIFECYCLE",
            "state": "EXPLICIT_ACTION_REQUIRED", "trustedPhoneLink": "UNVERIFIED",
            "contentAccessEnabled": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(inspect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
