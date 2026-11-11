#!/usr/bin/env python3
"""V2r authority-signed service-release grant (DENY-ONLY TEST FIXTURE).

This verifies a separately pinned Ed25519 test root signed a particular
V2q file/socket policy and V2l enrolled owner key identity. It does not
provision trust, enroll actual Weather/research owners, prove systemd launched
the unit, or authorize an ArchiveStore capture.
"""
import hashlib
import json

from scripts.trash.archive_v2_fixture_service_identity import (
    PinnedFixtureServiceFiles, POLICY_KEYS,
)
from scripts.trash.archive_v2_owner_trust import (
    _raw_b64, canonical_authority, ROOT_FIELDS, ROOT_ORIGIN,
)
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, Ed25519PublicKey, InvalidSignature,
    KEY_ID, SHA,
)

SCHEMA = "post-apollo.trashpp.fixture-service-grant.v2r"
FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "captureKeyId", "servicePolicySha256",
    "sourceManifestSha256", "generation", "issuedAtMs",
    "validFromMs", "validUntilMs", "revoked",
))
ENVELOPE_FIELDS = frozenset(("grant", "signatureB64"))
MAX_VALIDITY_MS = 24 * 60 * 60 * 1000
MAX_BYTES = 2048


class ServiceGrantError(Exception):
    """Bounded refusal with no sensitive files or signing material."""


def _need(value, code):
    if not value:
        raise ServiceGrantError(code)


def _ms(value):
    return type(value) is int and 1 <= value <= 9999999999999


def canonical_service_policy(policy):
    """Deterministic V2q policy digest; never trust request-provided policy."""
    _need(type(policy) is dict and set(policy) == POLICY_KEYS
          and policy["origin"] == "TEST_FIXTURE_ONLY",
          "SERVICE_GRANT_POLICY_INVALID")
    # V2q constructor strictly validates field types, names and hashes.
    try:
        raw = json.dumps(policy, sort_keys=True, ensure_ascii=True,
                         allow_nan=False, separators=(",", ":")).encode("ascii")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ServiceGrantError("SERVICE_GRANT_POLICY_INVALID") from exc
    _need(len(raw) <= 2048, "SERVICE_GRANT_POLICY_INVALID")
    return raw


def canonical_service_grant(grant):
    _need(type(grant) is dict and set(grant) == FIELDS,
          "SERVICE_GRANT_SCHEMA_INVALID")
    _need(grant["schema"] == SCHEMA
          and grant["audience"] == AUDIENCE
          and grant["purpose"] == PURPOSE
          and grant["policyOrigin"] == "TEST_FIXTURE_ONLY",
          "SERVICE_GRANT_SCOPE_INVALID")
    _need(type(grant["rootKeyId"]) is str
          and KEY_ID.fullmatch(grant["rootKeyId"])
          and type(grant["ownerId"]) is str
          and grant["ownerId"] in ALLOWED_OWNERS
          and type(grant["captureKeyId"]) is str
          and KEY_ID.fullmatch(grant["captureKeyId"])
          and type(grant["servicePolicySha256"]) is str
          and SHA.fullmatch(grant["servicePolicySha256"])
          and type(grant["sourceManifestSha256"]) is str
          and SHA.fullmatch(grant["sourceManifestSha256"])
          and type(grant["revoked"]) is bool
          and type(grant["generation"]) is int
          and 1 <= grant["generation"] <= 1000000000,
          "SERVICE_GRANT_FIELDS_INVALID")
    _need(all(_ms(grant[t]) for t in (
          "issuedAtMs", "validFromMs", "validUntilMs"))
          and grant["validFromMs"] <= grant["issuedAtMs"]
          < grant["validUntilMs"]
          and grant["validUntilMs"] - grant["validFromMs"] <= MAX_VALIDITY_MS,
          "SERVICE_GRANT_TIME_INVALID")
    raw = json.dumps(grant, sort_keys=True, ensure_ascii=True,
                     allow_nan=False, separators=(",", ":")).encode("ascii")
    _need(len(raw) <= MAX_BYTES, "SERVICE_GRANT_LIMIT")
    return raw


def verify_fixture_service_grant(
    signed_grant, pinned_root, service_files, signed_manifest, *, now_ms
):
    """Check authority-signed TEST service policy and enrolled-key linkage.

    The broker must pass trust root, file checker and manifest independently.
    These values are never read from the untrusted client's wire packet.
    """
    _need(type(signed_grant) is dict
          and set(signed_grant) == ENVELOPE_FIELDS,
          "SERVICE_GRANT_ENVELOPE_INVALID")
    _need(type(pinned_root) is dict
          and set(pinned_root) == ROOT_FIELDS
          and pinned_root["origin"] == ROOT_ORIGIN,
          "SERVICE_GRANT_TRUST_UNPROVISIONED")
    _need(type(service_files) is PinnedFixtureServiceFiles,
          "SERVICE_GRANT_FILES_REQUIRED")
    _need(type(signed_manifest) is dict
          and set(signed_manifest) == ("manifest", "signatureB64")
          and type(signed_manifest["manifest"]) is dict,
          "SERVICE_GRANT_MANIFEST_INVALID")
    grant = signed_grant["grant"]
    raw = canonical_service_grant(grant)
    m = signed_manifest["manifest"]
    # V2l verifies this manifest signature in the separate broker path.
    # Here its canonical bytes are bound into the service grant.
    manifest_raw = canonical_authority(m)
    policy_raw = canonical_service_policy(service_files.policy)
    _need(grant["rootKeyId"] == pinned_root["rootKeyId"]
          and type(pinned_root["publicKeyBytes"]) is bytes
          and len(pinned_root["publicKeyBytes"]) == 32,
          "SERVICE_GRANT_ROOT_MISMATCH")
    _need(grant["ownerId"] == service_files.policy["ownerId"]
          and grant["ownerId"] == m["ownerId"]
          and grant["captureKeyId"] == m["keyId"]
          and grant["generation"] == m["generation"]
          and grant["sourceManifestSha256"]
              == hashlib.sha256(manifest_raw).hexdigest()
          and grant["servicePolicySha256"]
              == hashlib.sha256(policy_raw).hexdigest(),
          "SERVICE_GRANT_BINDING_MISMATCH")
    _need(_ms(now_ms) and grant["issuedAtMs"] <= now_ms + 30000
          and grant["validFromMs"] <= now_ms < grant["validUntilMs"],
          "SERVICE_GRANT_EXPIRED")
    _need(grant["revoked"] is False, "SERVICE_GRANT_REVOKED")
    try:
        sig = _raw_b64(
            signed_grant["signatureB64"], 64,
            "SERVICE_GRANT_SIGNATURE_INVALID")
    except Exception as exc:
        raise ServiceGrantError("SERVICE_GRANT_SIGNATURE_INVALID") from exc
    _need(Ed25519PublicKey is not None,
          "SERVICE_GRANT_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            pinned_root["publicKeyBytes"]).verify(sig, raw)
    except (InvalidSignature, ValueError) as exc:
        raise ServiceGrantError("SERVICE_GRANT_SIGNATURE_REFUSED") from exc
    checked = service_files.require_unchanged()
    _need(checked["serviceWitnessSha256"] and
          checked["sourceServiceVerified"] is False,
          "SERVICE_GRANT_WITNESS_INVALID")
    return {
        "state": "TEST_SERVICE_GRANT_MATCHED_DENY_ONLY",
        "serviceGrantSha256": hashlib.sha256(raw).hexdigest(),
        "serviceWitnessSha256": checked["serviceWitnessSha256"],
        "sourceManifestSha256": grant["sourceManifestSha256"],
        "generation": grant["generation"], "ownerId": grant["ownerId"],
        "serviceGrantSignatureVerified": True,
        "sourceServiceVerified": False, "sourceAuthorityVerified": False,
        "captureAllowed": False, "productionAllowed": False,
        "restoreAllowed": False, "burnAllowed": False,
    }
