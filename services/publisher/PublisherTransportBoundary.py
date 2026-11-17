#!/usr/bin/env python3
"""Publisher P2.B: exact local candidate binding and DENY-ONLY host boundary.

This module has no socket, provider client, keyring, request signer, DB or
network transport. It never treats saved Social identity/account aliases,
the P1 queue "reviewed" state, a local JSON receipt or caller-provided proof
as authorization. The protected Connections/Identity authority is unconnected.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

VERSION = 1
PROVIDERS = ("discord", "bluesky", "website")
BROKER_REASON = "TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED"
REQUIRED_EVIDENCE = (
    "host_authenticated_signed_calling_process",
    "host_verified_provider_account_and_destination",
    "operator_consented_exact_scope_and_tenant",
    "durable_unexpired_unrevoked_host_grant",
    "fresh_revalidated_source_and_media",
    "unique_retry_and_provider_receipt_reconciliation",
)
# No editable request can name a system socket, endpoint, credential or grant.
FIELDS = {
    "version", "provider", "scope", "identityId", "context",
    "accountAlias", "destinationAlias", "jobId", "jobStatus",
    "draftDigest", "previewFingerprint",
}
HEX = re.compile(r"^[0-9a-f]{64}$")
IDENTITY = re.compile(r"^identity-[1-9][0-9]*$")
LABEL = re.compile(r"^[^\x00-\x1f\x7f]{1,80}$")


def refuse(reason: str) -> dict[str, Any]:
    return {
        "ok": False, "reason": reason, "phase": "LOCAL_ONLY",
        "hostBrokerConnected": False, "bindingVerified": False,
        "canDispatch": False, "sent": False, "providerReceipt": None,
    }


def _label(v: Any) -> bool:
    return (isinstance(v, str) and v == v.strip()
            and LABEL.fullmatch(v) is not None)


def _intent_check(intent: Any) -> str | None:
    if not isinstance(intent, dict) or set(intent) != FIELDS:
        return "INVALID_BINDING_FIELDS"
    if type(intent["version"]) is not int or intent["version"] != VERSION:
        return "UNSUPPORTED_BINDING_VERSION"
    if intent["provider"] not in PROVIDERS:
        return "UNSUPPORTED_PROVIDER"
    if intent["scope"] != "post.text":
        return "UNSUPPORTED_SCOPE"
    if (not isinstance(intent["identityId"], str)
            or IDENTITY.fullmatch(intent["identityId"]) is None
            or intent["context"] not in ("personal", "organization")):
        return "INVALID_IDENTITY_CONTEXT"
    if not _label(intent["accountAlias"]) or not _label(intent["destinationAlias"]):
        return "INVALID_ACCOUNT_OR_DESTINATION_ALIAS"
    if type(intent["jobId"]) is not int or not (1 <= intent["jobId"] <= 1000000000):
        return "INVALID_JOB_ID"
    if intent["jobStatus"] != "reviewed":
        return "JOB_REQUIRES_MANUAL_REVIEW"
    for key in ("draftDigest", "previewFingerprint"):
        if not isinstance(intent[key], str) or HEX.fullmatch(intent[key]) is None:
            return "INVALID_CONTENT_FINGERPRINT"
    return None


def local_candidate(preview: Any, intent: Any) -> dict[str, Any]:
    """Check a user-selected target against a P2.A preview; DO NOT authorize.

    The digest/aliases/queue status are still untrusted local assertions.
    The host must independently bind the actual program, user account,
    destination, current job and original content before a real send exists.
    """
    problem = _intent_check(intent)
    if problem:
        return refuse(problem)
    if (not isinstance(preview, dict)
            or preview.get("ok") is not True
            or preview.get("previewOnly") is not True
            or preview.get("canDispatch") is not False
            or preview.get("sent") is not False
            or preview.get("providerReceipt", object()) is not None):
        return refuse("UNTRUSTED_PROVIDER_PREVIEW")
    if (preview.get("provider") != intent["provider"]
            or preview.get("requiredScope") != intent["scope"]):
        return refuse("PREVIEW_PROVIDER_OR_SCOPE_MISMATCH")
    if preview.get("previewFingerprint") != intent["previewFingerprint"]:
        return refuse("STALE_PREVIEW_FINGERPRINT")
    expected = {
        "discord": "discord.executeWebhook",
        "bluesky": "com.atproto.repo.createRecord",
        "website": "postapollo.owned_site.localDraft",
    }[intent["provider"]]
    if preview.get("operation") != expected:
        return refuse("INVALID_PROVIDER_OPERATION")
    # SHA provides a stable local candidate identifier. It is NOT a signed
    # assertion, grant, idempotency token or provider-confirmed receipt.
    data = [
        VERSION, intent["provider"], intent["scope"], intent["identityId"],
        intent["context"], intent["accountAlias"], intent["destinationAlias"],
        intent["jobId"], intent["draftDigest"], intent["previewFingerprint"],
    ]
    fingerprint = hashlib.sha256(json.dumps(data, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "phase": "UNTRUSTED_LOCAL_CANDIDATE",
        "candidateFingerprint": fingerprint,
        "provider": intent["provider"],
        "scope": intent["scope"],
        "queueJobId": intent["jobId"],
        "hostBrokerConnected": False,
        "bindingVerified": False,
        "requiredHostEvidence": list(REQUIRED_EVIDENCE),
        "reason": BROKER_REASON,
        "canDispatch": False,
        "sent": False,
        "providerReceipt": None,
    }


def authorize(_candidate: Any, _host_claim: Any = None,
              _status: Any = None) -> dict[str, Any]:
    """Never trust caller-provided proof or convert a fixture into a grant."""
    return refuse(BROKER_REASON)


def deliver(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Production network delivery is deliberately not implemented."""
    return refuse(BROKER_REASON)


# Pure, explicitly MOCK-ONLY lifecycle. Observations are synthetic and never
# become production delivery evidence. This models timeout/duplicate behavior
# so a later protected host executor can be tested against the same cases.
FIXTURE_STATES = {
    "fixture_prepared", "fixture_pending", "fixture_unknown",
    "fixture_confirmed", "fixture_blocked",
}
FIXTURE_EVENTS = {
    "begin": ("fixture_prepared", "fixture_pending"),
    "timeout": ("fixture_pending", "fixture_unknown"),
    "negative_lookup": ("fixture_unknown", "fixture_unknown"),
    "confirmation": ("fixture_pending", "fixture_confirmed"),
    "confirm_after_timeout": ("fixture_unknown", "fixture_confirmed"),
    "cancel": ("fixture_prepared", "fixture_blocked"),
}


def fixture_transition(state: Any, event: Any, *, same_account: bool = True,
                       same_content: bool = True) -> dict[str, Any]:
    """Offline test-state machine; cannot publish or confirm a real post."""
    if not isinstance(state, str) or not isinstance(event, str) \
            or state not in FIXTURE_STATES or event not in FIXTURE_EVENTS:
        return refuse("INVALID_FIXTURE_TRANSITION")
    if type(same_account) is not bool or type(same_content) is not bool:
        return refuse("INVALID_FIXTURE_OBSERVATION")
    if not same_account or not same_content:
        return {
            **refuse("FIXTURE_BINDING_CHANGED"),
            "simulation": True, "fixtureState": "fixture_blocked",
        }
    before, after = FIXTURE_EVENTS[event]
    if state != before:
        return {
            **refuse("FIXTURE_RETRY_OR_ORDER_REFUSED"),
            "simulation": True, "fixtureState": state,
        }
    return {
        "ok": True, "phase": "OFFLINE_TEST_ONLY",
        "simulation": True, "fixtureState": after,
        "retryAutomatically": False,
        "requiresReconciliation": after == "fixture_unknown",
        "canDispatch": False, "sent": False,
        "realPosted": False, "providerReceipt": None,
        "reason": "SIMULATED_EVENT_NOT_DELIVERY",
    }


def fixture_observe(state: Any, evidence: Any) -> dict[str, Any]:
    """A mock receipt is never treated as authentic provider evidence."""
    if not isinstance(state, str) or state not in FIXTURE_STATES \
            or not isinstance(evidence, dict):
        return refuse("INVALID_FIXTURE_OBSERVATION")
    if set(evidence) != {"type", "accountMatches", "contentMatches"}:
        return refuse("INVALID_FIXTURE_FIELDS")
    if not isinstance(evidence["type"], str):
        return refuse("INVALID_FIXTURE_EVENT")
    event = {
        "timeout": "timeout",
        "not_found": "negative_lookup",
        "positive_mock_receipt": (
            "confirm_after_timeout" if state == "fixture_unknown"
            else "confirmation"
        ),
    }.get(evidence["type"])
    if event is None:
        return refuse("UNKNOWN_FIXTURE_EVENT")
    return fixture_transition(
        state, event,
        same_account=evidence["accountMatches"],
        same_content=evidence["contentMatches"],
    )


def strict_candidate_json(raw: Any) -> dict[str, Any]:
    """Optional bounded local input parser for calling code, no secrets."""
    if not isinstance(raw, str) or len(raw) > 14000:
        return refuse("INVALID_CANDIDATE_INPUT")
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("DUPLICATE_JSON_KEY")
            output[key] = value
        return output
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError):
        return refuse("INVALID_CANDIDATE_JSON")
    problem = _intent_check(value)
    return refuse(problem) if problem else {"ok": True, "candidate": value}
