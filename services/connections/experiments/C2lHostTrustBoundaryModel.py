#!/usr/bin/env python3
"""C2l OFFLINE-only host identity feasibility and refusal policy.

This module consumes synthetic, caller-supplied descriptions. It never probes
the user's machine, starts a process, binds sockets, requests credentials, or
issues a trust/permission grant. A reported privileged identity is NOT proof:
the first real identity proof must come from an independently protected
installation and a verified OS transport outside this module.
"""
from __future__ import annotations

from collections.abc import Mapping

SCHEMA = "post-apollo.connections.c2l.synthetic-trust-boundary.v1"
CURRENT_SOCKET = "c2i-private-unix-socket"
PROPOSED_BUS = "proposed-protected-system-bus"
FIELDS = frozenset({
    "schema", "transport", "clientUid", "peerUid", "serviceUid",
    "unitRootOwned", "codeRootOwned", "busPolicyRootOwned",
    "operatorConsentVerified",
})
ALLOWED_TRANSPORTS = frozenset({CURRENT_SOCKET, PROPOSED_BUS})


def _decision(reason: str, review_candidate: bool = False) -> dict[str, object]:
    # Synthetic facts cannot authenticate anything or activate any operations.
    return {
        "status": "DENY",
        "reason": reason,
        "reviewCandidate": review_candidate,
        "hostAuthenticated": False,
        "credentialPresent": False,
        "grantActive": False,
        "canApprove": False,
        "canUseApi": False,
    }


def assess(evidence: object) -> dict[str, object]:
    """Classify fake identity topologies, never authenticate a real host.

    Evidence is deliberately caller supplied and must never be wired into a
    production entitlement decision. Even the favorable topology has only a
    REVIEW_CANDIDATE label, because no OS-verified evidence exists here.
    """
    if type(evidence) is not dict or set(evidence) != FIELDS:
        return _decision("INVALID_EVIDENCE")
    e = evidence
    if (e["schema"] != SCHEMA
            or type(e["transport"]) is not str
            or e["transport"] not in ALLOWED_TRANSPORTS
            or any(type(e[k]) is not int or not 0 <= e[k] <= 0xFFFFFFFF
                   for k in ("clientUid", "peerUid", "serviceUid"))
            or any(type(e[k]) is not bool for k in (
                "unitRootOwned", "codeRootOwned", "busPolicyRootOwned",
                "operatorConsentVerified"))):
        return _decision("INVALID_EVIDENCE")

    if e["transport"] == CURRENT_SOCKET:
        # C2i/C2j share a per-user private socket and insist on matching UID.
        # Matching UID never authenticates a Post-Apollo process.
        if e["peerUid"] == e["clientUid"]:
            return _decision("SAME_UID_SOCKET_NOT_IDENTITY")
        return _decision("C2I_C2J_CROSS_UID_INCOMPATIBLE")

    # A future protected system bus could transport a differently privileged
    # service but it is NOT implemented. These are synthetic design checks.
    if e["peerUid"] == e["clientUid"]:
        return _decision("PROPOSED_PEER_NOT_ISOLATED")
    if e["serviceUid"] != e["peerUid"]:
        return _decision("PROPOSED_SERVICE_PEER_MISMATCH")
    if not (e["unitRootOwned"] and e["codeRootOwned"]
            and e["busPolicyRootOwned"]):
        return _decision("PROPOSED_INSTALL_PROTECTION_MISSING")
    if not e["operatorConsentVerified"]:
        return _decision("PROPOSED_CONSENT_NOT_PROVEN")
    return _decision("PROPOSAL_ONLY_NO_DEPLOYED_TRUST_ROOT", True)


if __name__ == "__main__":
    raise SystemExit("C2L_REVIEW_MODEL_NO_LIVE_ENTRYPOINT")
