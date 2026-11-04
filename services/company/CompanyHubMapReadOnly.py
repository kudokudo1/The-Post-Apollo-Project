#!/usr/bin/env python3
"""Explicit owner-local, read-only Company hub MAP projection.

No organization permissions are invented here. A same-UID operator process
must deliberately invoke --owner-local-view. This is a limited opt-in gate,
NOT an authenticated company/tenant/role grant. Do not expose this endpoint
to a network or treat it as multiuser authorization.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import CompanyHubDirectory as Source

SCHEMA = "post-apollo.company-map.owner-local-v1"
MAX_ACTIVE = 150
ALLOWED_COMMAND = "--owner-local-view"


def projection(doc: Any) -> dict:
    """Allowlist public-facing *fields*, never a raw directory record."""
    validated = Source.validate(doc)
    output: list[dict] = []
    for hub in validated["hubs"]:
        if hub["archived"]:
            continue
        # Only non-personal metadata required to pin unverified locations.
        # No organization labels, service details, city, clients or workers.
        output.append({
            "id": hub["id"],
            "longitude": hub["longitude"],
            "latitude": hub["latitude"],
            "reported": True,
        })
    if len(output) > MAX_ACTIVE:
        raise Source.HubError("CAPACITY_EXCEEDED")
    return {
        "schema": SCHEMA,
        "revision": validated["revision"],
        "authority": "OWNER_LOCAL_ONLY_NOT_ORGANIZATION_GRANT",
        "hubs": output,
    }


def read_explicitly(command: str) -> dict:
    if command != ALLOWED_COMMAND:
        raise Source.HubError("EXPLICIT_OWNER_VIEW_REQUIRED")
    # Never run a privileged/setuid bridge. This is an owner-local session,
    # not a service account and not a tenant authorization provider.
    if os.geteuid() == 0 or os.geteuid() != os.getuid():
        raise Source.HubError("UNSAFE_PROCESS_IDENTITY")
    return projection(Source.load())


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args != [ALLOWED_COMMAND]:
            raise Source.HubError("EXPLICIT_OWNER_VIEW_REQUIRED")
        result = read_explicitly(args[0])
        # No persistence, no network calls, no organization fields.
        print(json.dumps({"ok": True, "document": result}, separators=(",", ":")))
        return 0
    except Source.HubError as error:
        print(json.dumps({"ok": False, "error": error.code}))
        return 2
    except (OSError, TypeError, ValueError):
        print(json.dumps({"ok": False, "error": "OWNER_VIEW_UNAVAILABLE"}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
