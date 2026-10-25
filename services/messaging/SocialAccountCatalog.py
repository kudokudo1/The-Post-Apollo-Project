#!/usr/bin/env python3
"""Read-only Social account-manager handoff catalog and Connect All planner.

No login, credential access, browser launch, token handling, session switching,
or filesystem mutation. This is a typed handoff for the separately owned
account manager, not a replacement for one.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

MAX_REQUEST_BYTES = 32768
IDENTITY = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
# Exact Social selector order from AppSelector.qml as of 2026-10-24.
# CI checks every entry against the real selector and XBrowser SITES.
ITEMS: tuple[tuple[str, str, str], ...] = (
    ("sessions", "SESSIONS", "native_session"),
    ("discord", "DISCORD", "external_app"),
    ("telegram", "TELEGRAM", "native_telegram"),
    ("x", "X", "browser_profile"),
    ("instagram", "INSTAGRAM", "browser_profile"),
    ("facebook", "FACEBOOK", "browser_profile"),
    ("reddit", "REDDIT", "browser_profile"),
    ("threads", "THREADS", "browser_profile"),
    ("pinterest", "PINTEREST", "browser_profile"),
    ("truthsocial", "TRUTH SOCIAL", "browser_profile"),
    ("bluesky", "BLUESKY", "browser_profile"),
    ("tumblr", "TUMBLR", "browser_profile"),
    ("tiktok", "TIKTOK", "browser_profile"),
    ("snapchat", "SNAPCHAT", "browser_profile"),
    ("whatsapp", "WHATSAPP", "unsupported_personal"),
    ("messenger", "MESSENGER", "unsupported_personal"),
    ("linkedin", "LINKEDIN", "browser_profile"),
    ("mastodon", "MASTODON", "browser_profile"),
    ("nextdoor", "NEXTDOOR", "browser_profile"),
    ("steamchat", "STEAM CHAT", "browser_profile"),
    ("element", "ELEMENT", "browser_profile"),
    ("groupme", "GROUPME", "browser_profile"),
    ("lemon8", "LEMON8", "browser_profile"),
    ("quora", "QUORA", "browser_profile"),
    ("pixelfed", "PIXELFED", "browser_profile"),
    ("zalo", "ZALO", "browser_profile"),
    ("signal", "SIGNAL", "unsupported_personal"),
    ("wechat", "WECHAT", "unsupported_personal"),
    ("line", "LINE", "unsupported_personal"),
    ("viber", "VIBER", "unsupported_personal"),
    ("kakaotalk", "KAKAOTALK", "unsupported_personal"),
    ("bereal", "BEREAL", "unsupported_mobile"),
)
ITEM_BY_ID = {item[0]: (i, item[1], item[2]) for i, item in enumerate(ITEMS)}
BROWSER_IDS = {item[0] for item in ITEMS if item[2] == "browser_profile"}
BLOCKED = {"unsupported_personal", "unsupported_mobile"}


def catalog() -> dict[str, Any]:
    """Catalog is discovery metadata, NOT an authentication status feed."""
    return {
        "schema": "post-apollo.social-accounts.v0",
        "authority": "catalog_only",
        "services": [
            {
                "serviceId": service_id, "label": label,
                "selectorIndex": index, "channel": channel,
                "supportsManagedBatchLogin": False,
            }
            for index, (service_id, label, channel) in enumerate(ITEMS)
        ],
    }


def _require_ids(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) > len(ITEMS):
        raise ValueError(f"{field} must be a bounded list of service IDs")
    if not all(isinstance(x, str) and x in ITEM_BY_ID for x in value):
        raise ValueError(f"{field} contains an unknown service")
    if len(set(value)) != len(value):
        raise ValueError(f"{field} contains duplicate services")
    return value


def plan(payload: object) -> dict[str, Any]:
    """Produce a fail-closed, identity-scoped batch plan; do not execute it."""
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    if set(payload) != {"schema", "identityId", "services", "linkedServices"}:
        raise ValueError("request must contain only schema, identityId, services, linkedServices")
    if payload["schema"] != "post-apollo.social-accounts.v0":
        raise ValueError("unknown catalog schema")
    identity = payload["identityId"]
    if not isinstance(identity, str) or not IDENTITY.fullmatch(identity):
        raise ValueError("identityId must be an opaque 1-64 character identifier")
    requested = _require_ids(payload["services"], "services")
    linked = set(_require_ids(payload["linkedServices"], "linkedServices"))
    if not linked.issubset(set(requested)):
        raise ValueError("linkedServices must be within selected services")

    rows: list[dict[str, Any]] = []
    for service_id in requested:
        index, _, channel = ITEM_BY_ID[service_id]
        # Supported browser sign-in remains controlled by the provider website,
        # and its existing Chromium data directory is shared across identities.
        # Never claim that an existing profile equals successful authentication.
        if channel in BLOCKED:
            status, action = "UNSUPPORTED", "none"
        elif service_id not in linked:
            status, action = "UNLINKED", "account_manager_link"
        elif identity != "default":
            status, action = "IDENTITY_ISOLATION_PENDING", "none"
        elif channel == "browser_profile":
            status, action = "PROFILE_OPEN_AVAILABLE", "open_existing_browser_profile"
        elif channel == "native_telegram":
            status, action = "INTERACTIVE_AUTH_AVAILABLE", "telegram_in_menu"
        elif channel == "native_session":
            status, action = "STATUS_CHECK_AVAILABLE", "session_existing"
        else:
            status, action = "EXTERNAL_APP_AVAILABLE", "vesktop_existing"

        rows.append({
            "serviceId": service_id, "selectorIndex": index,
            "channel": channel, "status": status, "nextAction": action,
            "authenticated": None,  # Unknown, never fabricated.
            "batchLoginPerformed": False,
        })
    return {
        "schema": "post-apollo.social-accounts.v0",
        "identityId": identity,
        "execution": "PLAN_ONLY",
        "requested": len(rows),
        "openable": sum(r["nextAction"] == "open_existing_browser_profile" for r in rows),
        "interactive": sum(r["nextAction"] == "telegram_in_menu" for r in rows),
        "blocked": sum(r["nextAction"] == "none" for r in rows),
        "services": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Social account manager handoff (read-only)")
    parser.add_argument("operation", choices=("catalog", "plan"))
    args = parser.parse_args(argv)
    try:
        if args.operation == "catalog":
            result = catalog()
        else:
            # Bounded one-line request, no secrets. Never log request contents.
            line = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
            if not line or len(line) > MAX_REQUEST_BYTES or not line.endswith(b"\n"):
                raise ValueError("malformed or oversized request")
            result = plan(json.loads(line))
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"error": "Invalid account-planning request; no action performed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
