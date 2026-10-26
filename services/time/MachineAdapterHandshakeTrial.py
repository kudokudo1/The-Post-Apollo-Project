"""MACHINE M2d2: bounded, simulation-only app/host handshake lifecycle.

This code is a protocol policy TEST HARNESS, not a transport or security
principal. All observations and permission flags are caller-supplied fixture
data: satisfying them never establishes real process identity, user consent,
session continuity, or authority to recover. No live OS/app communications,
filesystem access, token issuance for production, or action dispatch.
"""
from __future__ import annotations

import uuid

from MachineAdapterRegistry import (
    RegistryError, build_registry, find_declared_adapter,
)

MAX_PROBES = 512
MIN_TTL_SECONDS = 1
MAX_TTL_SECONDS = 30
MAX_TIME_SECONDS = 10 ** 12


class HandshakeError(ValueError):
    pass


def _uuid(value):
    if not isinstance(value, str):
        raise HandshakeError("INVALID IDENTIFIER")
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HandshakeError("INVALID IDENTIFIER") from exc
    if canonical != value:
        raise HandshakeError("INVALID IDENTIFIER")
    return value


def _name(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 128
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise HandshakeError("INVALID APPLICATION IDENTIFIER")
    return value


def _seconds(value):
    if (type(value) not in (int, float)
            or not 0 <= value <= MAX_TIME_SECONDS
            or value != value):
        raise HandshakeError("INVALID FIXTURE CLOCK")
    return value


def _fields(data, names):
    if not isinstance(data, dict) or set(data) != set(names):
        raise HandshakeError("UNEXPECTED OR PRIVATE OBSERVATION")


class SyntheticHandshakeSession:
    """In-memory fail-closed trial of future connector protocol expectations.

    scope_id: unique fixture-only attempt identifier. All returned records
    remain explicitly UNTRUSTED, irrespective of successful challenge echo.
    """

    def __init__(self, scope_id, *, adapter_manifests=()):
        self.scope_id = _uuid(scope_id)
        try:
            self.registry = build_registry(adapter_manifests)
        except RegistryError as exc:
            raise HandshakeError("INVALID SCHEMA REGISTRY") from exc
        self.pending = {}
        self.all_nonces = set()
        self.used_host_ids = set()
        self.used_instances = set()

    def begin(self, *, nonce, host_observation_id, app_id, adapter_id,
              host_target, now_seconds, ttl_seconds, permission_fixture):
        """Model one explicitly selected, time-bounded READ ONLY fixture.

        Permission here is a simulated flag; an actual permission grant must
        come from a separately authenticated operator/host implementation.
        """
        nonce = _uuid(nonce)
        host_observation_id = _uuid(host_observation_id)
        app_id = _name(app_id)
        if host_target not in ("linux_wayland", "linux_x11", "windows", "macos"):
            raise HandshakeError("UNRECOGNIZED HOST TARGET")
        now = _seconds(now_seconds)
        if (type(ttl_seconds) is not int
                or not MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS):
            raise HandshakeError("INVALID FIXTURE TTL")
        if permission_fixture != "explicit_synthetic_allow":
            raise HandshakeError("FIXTURE PERMISSION NOT ALLOWED")
        try:
            descriptor = find_declared_adapter(self.registry, adapter_id, app_id)
        except RegistryError as exc:
            raise HandshakeError("UNREGISTERED APPLICATION ADAPTER") from exc
        if adapter_id == "none" or host_target not in descriptor["target_hosts"]:
            raise HandshakeError("NO DECLARED HOST CAPABILITY")
        if nonce in self.all_nonces or host_observation_id in self.used_host_ids:
            raise HandshakeError("NONCE OR HOST ALREADY USED")
        if len(self.all_nonces) >= MAX_PROBES:
            raise HandshakeError("FIXTURE CAPACITY REACHED")
        self.all_nonces.add(nonce)
        self.used_host_ids.add(host_observation_id)
        self.pending[nonce] = {
            "app_id": app_id,
            "adapter_id": adapter_id,
            "host_observation_id": host_observation_id,
            "expires_at": now + ttl_seconds,
            "started_at": now,
        }
        return {
            "kind": "machine-synthetic-handshake-challenge",
            "scope_id": self.scope_id,
            "nonce": nonce,
            "target_host_observation_id": host_observation_id,
            "read_only": True,
            "synthetic_only": True,
            "expires_at_fixture_seconds": now + ttl_seconds,
            "action_allowed": False,
        }

    def cancel(self, nonce):
        nonce = _uuid(nonce)
        if self.pending.pop(nonce, None) is None:
            raise HandshakeError("MISSING OR CONSUMED CHALLENGE")
        return {"status": "cancelled_fixture", "action_allowed": False}

    def verify(self, nonce, host_echo, app_echo, *, now_seconds):
        """Consume the challenge BEFORE checking any untrusted reply.

        Success describes fixture conformance, NEVER trusted correlation.
        Replays, wrong process claims, stale responses and unexpected private
        fields fail closed and cannot be retried with the same nonce.
        """
        nonce = _uuid(nonce)
        probe = self.pending.pop(nonce, None)
        if probe is None:
            raise HandshakeError("UNKNOWN OR CONSUMED CHALLENGE")
        now = _seconds(now_seconds)
        if now < probe["started_at"] or now > probe["expires_at"]:
            raise HandshakeError("EXPIRED OR REGRESSED FIXTURE CLOCK")
        _fields(host_echo, ("scope_id", "nonce", "host_observation_id",
                            "app_id", "source"))
        _fields(app_echo, ("scope_id", "nonce", "host_observation_id",
                           "app_id", "adapter_id", "namespace_key",
                           "instance_key", "inner_item_count", "source"))
        if (host_echo["source"] != "synthetic_host"
                or app_echo["source"] != "synthetic_app"):
            raise HandshakeError("UNSUPPORTED OBSERVATION PROVENANCE")
        if any(_uuid(record["scope_id"]) != self.scope_id
               or _uuid(record["nonce"]) != nonce
               or _uuid(record["host_observation_id"])
               != probe["host_observation_id"]
               for record in (host_echo, app_echo)):
            raise HandshakeError("OBSERVATION SCOPE OR WINDOW MISMATCH")
        if (host_echo["app_id"] != probe["app_id"]
                or app_echo["app_id"] != probe["app_id"]
                or app_echo["adapter_id"] != probe["adapter_id"]):
            raise HandshakeError("CROSS-APPLICATION CLAIM")
        namespace_key = (None if app_echo["namespace_key"] is None
                         else _uuid(app_echo["namespace_key"]))
        instance_key = _uuid(app_echo["instance_key"])
        count = app_echo["inner_item_count"]
        if type(count) is not int or not 0 <= count <= 4096:
            raise HandshakeError("INVALID INNER ITEM COUNT")
        identity = (probe["adapter_id"], namespace_key, instance_key)
        if identity in self.used_instances:
            raise HandshakeError("DUPLICATE FIXTURE SESSION")
        self.used_instances.add(identity)
        return {
            "kind": "machine-synthetic-handshake-result",
            "status": "fixture_challenge_echo_matched",
            "scope_id": self.scope_id,
            "host_observation_id": probe["host_observation_id"],
            "reported_inner_item_count": count,
            "synthetic_provenance_only": True,
            "real_app_identity_verified": False,
            "real_host_binding_verified": False,
            "operator_consent_verified": False,
            "exact_session_match": False,
            "read_only": True,
            "executable": False,
            "action_allowed": False,
            "safe_actions": [],
        }
