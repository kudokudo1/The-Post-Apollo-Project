"""Untrusted Social PHONE intent validation. OFFLINE, no authorization.

Pure parser for the proposed Identity Center <-> Phone Bridge boundary.
Accepts ONLY human UI selectors, not identities, grants, token claims,
provider capability assertions or phone content. A valid selection is never
authority to subscribe to KDE Connect or receive a message.

This module performs no I/O and is not wired to Social or the Identity host.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

INTENT_SCHEMA = "post-apollo.phone.host-intent.v0-proposal"
STATUS_SCHEMA = "post-apollo.phone.host-intent-status.v0-proposal"
EXPECTED_FIELDS = frozenset({
    "contract", "operation", "deviceSelector", "lineSelector",
    "ownerKind", "organizationSelector", "requestedCapability",
})
# Selectors are opaque *input labels*, not verified device IDs or principals.
_SELECTOR = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z", re.ASCII)


@dataclass(frozen=True, slots=True, repr=False)
class UntrustedReceiveSelection:
    """Private host input ONLY, not a grant, identity or provider evidence.

    repr=False prevents default repr from echoing user-provided selectors.
    Do not expose this object as an IPC result or QML authorization flag.
    """
    device_selector: str = field(repr=False)
    line_selector: str = field(repr=False)
    owner_kind: str = field(repr=False)
    organization_selector: str | None = field(repr=False)


def _selector(value: object) -> str | None:
    if type(value) is not str or not _SELECTOR.fullmatch(value):
        return None
    return value


def parse_untrusted_receive_selection(request: object) -> UntrustedReceiveSelection | None:
    """Validate exact UI intent. NEVER authenticate, grant, or route access.

    A hostile client could invent valid-looking selectors. Only the future
    host-owned verified-session/device-binding service can resolve them.
    """
    if type(request) is not dict or set(request) != EXPECTED_FIELDS:
        return None
    if (request["contract"] != INTENT_SCHEMA
            or request["operation"] != "requestReceiveAccess"
            or request["requestedCapability"] != "messages.receive"):
        return None
    device = _selector(request["deviceSelector"])
    line = _selector(request["lineSelector"])
    kind = request["ownerKind"]
    if device is None or line is None or type(kind) is not str:
        return None
    if kind == "PERSONAL":
        if request["organizationSelector"] is not None:
            return None
        organization = None
    elif kind == "ORGANIZATION":
        organization = _selector(request["organizationSelector"])
        if organization is None:
            return None
    else:
        return None
    return UntrustedReceiveSelection(
        device_selector=device, line_selector=line,
        owner_kind=kind, organization_selector=organization,
    )


def sanitized_intent_status(request: object) -> dict[str, object]:
    """Non-authoritative status, safe to show without selector or phone data."""
    selection = parse_untrusted_receive_selection(request)
    return {
        "contract": STATUS_SCHEMA,
        "execution": "INTENT_VALIDATION_ONLY",
        "status": "AUTHORIZATION_REQUIRED" if selection is not None else "INVALID_REQUEST",
        "requestedCapability": "messages.receive",
        "platform": "UNVERIFIED",
        "transport": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
    }
