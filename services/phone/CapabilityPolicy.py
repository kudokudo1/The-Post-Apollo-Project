"""Offline-only Social Phone route planner (P0).

No provider, transport, authorization gateway, caller identity, or device access
is implemented here. All observations are hypothetical test inputs. Never
interpret a returned ROUTE_CANDIDATE as a verified phone connection.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "post-apollo.phone.route-plan.v0"
MAX_CANDIDATES = 16
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
OPERATIONS = frozenset({
    "messages.read", "messages.send", "messages.receive",
    "contacts.read", "notifications.receive",
    "calls.dial", "calls.answer", "calls.audio", "calls.hangup",
})
MODES = frozenset({"AUTO", "NETWORK_ONLY", "MANUAL"})
TRANSPORTS = frozenset({"NETWORK", "BLUETOOTH"})
AUTH_STATES = frozenset({"VERIFIED", "UNKNOWN", "DENIED"})
PERMISSION_STATES = frozenset({"GRANTED", "UNKNOWN", "DENIED"})
HEALTH_STATES = frozenset({"READY", "DEGRADED", "OFFLINE", "UNKNOWN"})
PROBE_STATES = frozenset({"VERIFIED", "UNVERIFIED"})
IN_FLIGHT_STATES = frozenset({"NONE", "SEND_OUTCOME_UNKNOWN", "CALL_ACTIVE"})

REQUEST_FIELDS = frozenset({
    "schema", "requestId", "principalId", "deviceId", "lineId",
    "operation", "inFlight", "policy", "candidates",
})
POLICY_FIELDS = frozenset({
    "mode", "bluetoothFallback", "bluetoothOperations", "manualBackendId",
})
CANDIDATE_FIELDS = frozenset({
    "backendId", "principalId", "deviceId", "lineId",
    "transport", "operations", "authorization", "permission",
    "health", "probe",
})


def _fields(value: object, expected: frozenset[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{name} has missing or unexpected fields")
    return value


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be an opaque identifier")
    return value


def _choice(value: object, allowed: frozenset[str], name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} is not a supported value")
    return value


def _operations(value: object, name: str) -> set[str]:
    if (not isinstance(value, list) or len(value) > len(OPERATIONS)
            or any(not isinstance(op, str) or op not in OPERATIONS for op in value)
            or len(value) != len(set(value))):
        raise ValueError(f"{name} must contain unique known operations")
    return set(value)


def _policy(value: object) -> dict[str, Any]:
    policy = _fields(value, POLICY_FIELDS, "policy")
    _choice(policy["mode"], MODES, "mode")
    if type(policy["bluetoothFallback"]) is not bool:
        raise ValueError("bluetoothFallback must be boolean")
    _operations(policy["bluetoothOperations"], "bluetoothOperations")
    chosen = policy["manualBackendId"]
    if policy["mode"] == "MANUAL":
        _identifier(chosen, "manualBackendId")
    elif chosen is not None:
        raise ValueError("manualBackendId must be null outside MANUAL")
    return policy


def _candidate(value: object) -> dict[str, Any]:
    candidate = _fields(value, CANDIDATE_FIELDS, "candidate")
    for key in ("backendId", "principalId", "deviceId", "lineId"):
        _identifier(candidate[key], key)
    _choice(candidate["transport"], TRANSPORTS, "transport")
    _operations(candidate["operations"], "candidate operations")
    _choice(candidate["authorization"], AUTH_STATES, "authorization")
    _choice(candidate["permission"], PERMISSION_STATES, "permission")
    _choice(candidate["health"], HEALTH_STATES, "health")
    _choice(candidate["probe"], PROBE_STATES, "probe")
    return candidate


def plan(request: object) -> dict[str, Any]:
    """Return a non-executing, capability-scoped route proposal.

    The caller must authenticate the human and obtain all provider observations
    independently. Even VERIFIED fields are *claims from the fixture/caller*;
    this module cannot attest them. No operation, pairing or retry is executed.
    """
    payload = _fields(request, REQUEST_FIELDS, "request")
    if payload["schema"] != SCHEMA:
        raise ValueError("unsupported route schema")
    request_id = _identifier(payload["requestId"], "requestId")
    for key in ("principalId", "deviceId", "lineId"):
        _identifier(payload[key], key)
    operation = _choice(payload["operation"], OPERATIONS, "operation")
    in_flight = _choice(payload["inFlight"], IN_FLIGHT_STATES, "inFlight")
    policy = _policy(payload["policy"])
    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, list) or len(raw_candidates) > MAX_CANDIDATES:
        raise ValueError("candidates must be a bounded list")
    candidates = [_candidate(x) for x in raw_candidates]
    ids = [x["backendId"] for x in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate backendId")

    def result(state: str, reason: str, candidate: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "execution": "PLAN_ONLY",
            "requestId": request_id, "operation": operation,
            "state": state, "reason": reason,
            "backendId": candidate["backendId"] if candidate else None,
            "transport": candidate["transport"] if candidate else None,
        }

    # An uncertain send must never be silently resent over another transport.
    # Call control/audio must not be switched mid-call without a separate
    # explicit handover protocol and proof. This planner defines neither.
    if in_flight == "SEND_OUTCOME_UNKNOWN":
        return result("BLOCKED", "SEND_OUTCOME_UNKNOWN")
    if in_flight == "CALL_ACTIVE":
        return result("BLOCKED", "ACTIVE_CALL_NOT_REROUTABLE")

    usable = [
        x for x in candidates
        if x["principalId"] == payload["principalId"]
        and x["deviceId"] == payload["deviceId"]
        and x["lineId"] == payload["lineId"]
        and operation in x["operations"]
        and x["authorization"] == "VERIFIED"
        and x["permission"] == "GRANTED"
        and x["health"] == "READY"
        and x["probe"] == "VERIFIED"
    ]

    def choose(items: list[dict[str, Any]], reason: str) -> dict[str, Any] | None:
        if len(items) == 1:
            return result("ROUTE_CANDIDATE", reason, items[0])
        if len(items) > 1:
            return result("SELECTION_REQUIRED", "MULTIPLE_MATCHING_BACKENDS")
        return None

    def bluetooth_allowed() -> bool:
        return (policy["bluetoothFallback"]
                and operation in policy["bluetoothOperations"])

    if policy["mode"] == "MANUAL":
        selected = [x for x in usable if x["backendId"] == policy["manualBackendId"]
                    and (x["transport"] != "BLUETOOTH" or bluetooth_allowed())]
        return choose(selected, "MANUAL_CHOICE") or result("UNAVAILABLE", "MANUAL_ROUTE_NOT_VERIFIED")

    network = [x for x in usable if x["transport"] == "NETWORK"]
    preferred = choose(network, "NETWORK_PREFERRED")
    if preferred is not None:
        return preferred
    if policy["mode"] == "NETWORK_ONLY":
        return result("UNAVAILABLE", "NO_VERIFIED_NETWORK_ROUTE")

    if not bluetooth_allowed():
        return result("UNAVAILABLE", "NO_NETWORK_AND_BLUETOOTH_NOT_ALLOWED")
    fallback = [x for x in usable if x["transport"] == "BLUETOOTH"]
    return choose(fallback, "BLUETOOTH_FALLBACK") or result("UNAVAILABLE", "NO_VERIFIED_ROUTE")
