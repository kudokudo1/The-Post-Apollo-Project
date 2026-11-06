#!/usr/bin/env python3
"""Content-free iPhone MAP/PBAP diagnostics for the existing Social PHONE pane.

Uses the already-installed read-only BlueFerry/BlueZ observation helpers.
Never lists phone messages, conversation keys, contact cards, names, numbers
or addresses. An active Bluetooth profile is not a Social content grant.
Only an explicit --inspect argument triggers the probes.
"""
from __future__ import annotations

import json
import sys
from typing import Callable

from PhoneDeviceObservation import (
    PROFILE, _running_profile, observe,
)

SCHEMA = "post-apollo.phone.content-diagnostic.v0"
EXECUTION = "READ_ONLY_PROVIDER_METADATA"
MAX_CONTACT_COUNT = 100000


def _fallback(state: str = "UNAVAILABLE") -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": EXECUTION,
        "state": state,
        "deviceState": "UNVERIFIED",
        "messages": {"state": "UNVERIFIED"},
        "contacts": {"state": "UNVERIFIED", "cachedCount": None},
        "socialLink": "NOT_AUTHORIZED",
        "trustedPhoneLink": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
    }


def inspect(*, device_reader: Callable[[], object] = observe,
            status_reader: Callable[[], object] = _running_profile
            ) -> dict[str, object]:
    """Return only matched-profile, non-content backend capability observations.

    The device observer already matches BlueFerry's UUIDv4 profile to its
    private configuration and the exact BlueZ paired device. This function
    then independently matches GetStatus to that same profile before using
    its MAP/PBAP booleans or optional count. Neither probe grants anything.
    """
    try:
        device = device_reader()
        if (type(device) is not dict
                or device.get("schema") != "post-apollo.phone.device-observation.v0"
                or device.get("execution") != "READ_ONLY_DEVICE_OBSERVATION"
                or device.get("trustedPhoneLink") != "UNVERIFIED"
                or device.get("contentAccessEnabled") is not False
                or device.get("state") not in (
                    "BLUETOOTH_CONNECTED", "PAIRED_OFFLINE"
                )):
            return _fallback()
        profile = device.get("profileId")
        if type(profile) is not str or PROFILE.fullmatch(profile) is None:
            return _fallback()
        expected_link = ("CONNECTED" if device["state"] == "BLUETOOTH_CONNECTED"
                         else "PAIRED_OFFLINE")
        if device.get("bluetoothLink") != expected_link:
            return _fallback()
        if device["state"] == "PAIRED_OFFLINE":
            result = _fallback("DEVICE_OFFLINE")
            result["deviceState"] = "PAIRED_OFFLINE"
            return result

        status = status_reader()
        if (type(status) is not dict
                or status.get("phone_profile_id") != profile
                or type(status.get("api_version")) is not int
                or status["api_version"] != 2
                or status.get("daemon") is not True
                or type(status.get("map")) is not bool
                or type(status.get("pbap")) is not bool):
            return _fallback()
        count = status.get("contact_card_count")
        if (type(count) is not int or not 0 <= count <= MAX_CONTACT_COUNT):
            # Older BlueFerry may not offer contact-card support. Do not
            # infer that the iPhone has zero contacts.
            count = None
        return {
            "schema": SCHEMA,
            "execution": EXECUTION,
            "state": "BACKEND_REPORTED",
            "deviceState": "BLUETOOTH_CONNECTED",
            "messages": {"state": (
                "MAP_ACTIVE_BACKEND_REPORT" if status["map"]
                else "MAP_INACTIVE_BACKEND_REPORT"
            )},
            "contacts": {
                "state": (
                    "PBAP_ACTIVE_BACKEND_REPORT" if status["pbap"]
                    else "PBAP_INACTIVE_BACKEND_REPORT"
                ),
                "cachedCount": count,
            },
            "socialLink": "NOT_AUTHORIZED",
            "trustedPhoneLink": "UNVERIFIED",
            "routeEligible": False,
            "contentAccessEnabled": False,
        }
    except Exception:
        # Never publish D-Bus failure text or raw GetStatus; metadata can
        # contain a person's phone identifier or other private information.
        return _fallback()


def main(args: list[str] | None = None) -> int:
    argv = sys.argv[1:] if args is None else args
    if argv != ["--inspect"]:
        print(json.dumps(_fallback("EXPLICIT_ACTION_REQUIRED"), sort_keys=True))
        return 2
    print(json.dumps(inspect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
