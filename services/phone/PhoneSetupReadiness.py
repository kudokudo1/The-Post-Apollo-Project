#!/usr/bin/env python3
"""Explicit Social PHONE setup check, NOT phone pairing or authorization.

One user action reads the already-defined BlueFerry and KDE Connect local
diagnostics, then uses the fail-closed provider projector. Never connects,
pairs, starts services, requests permissions, or reads private phone data.
"""
from __future__ import annotations

import json
import sys
from typing import Callable

from BlueFerryReadiness import readiness
from KdeConnectDbusProbe import probe
from PhoneProviderObservation import project

SCHEMA = "post-apollo.phone.setup-check.v0"


def check(
    *,
    blueferry_reader: Callable[[], object] = readiness,
    kdeconnect_reader: Callable[[], object] = probe,
) -> dict[str, object]:
    """Invoke separate read-only probes; keep each source fail-closed."""
    try:
        blueferry = blueferry_reader()
    except Exception:
        blueferry = None
    try:
        kdeconnect = kdeconnect_reader()
    except Exception:
        kdeconnect = None
    projected = project(blueferry, kdeconnect)
    providers = projected["providers"]
    # "BRIDGE_REPORTED" intentionally does NOT mean a phone is connected.
    observed = (
        providers["BLUEFERRY"]["state"] == "REPORTED"
        or providers["KDECONNECT"]["state"] == "METADATA_REPORTED"
    )
    return {
        "schema": SCHEMA,
        "execution": "READ_ONLY_CHECK",
        "status": "BRIDGE_REPORTED" if observed else "NO_BRIDGE_REPORTED",
        "trustedPhoneLink": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
        "providers": providers,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--check"]:
        # No probe is run without an explicit setup action.
        print(json.dumps({
            "schema": SCHEMA,
            "execution": "READ_ONLY_CHECK",
            "status": "EXPLICIT_ACTION_REQUIRED",
            "trustedPhoneLink": "UNVERIFIED",
            "routeEligible": False,
            "contentAccessEnabled": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(check(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
