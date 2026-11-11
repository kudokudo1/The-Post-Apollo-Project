#!/usr/bin/env python3
"""V2l source-owner key enrollment VERIFIER; synthetic trust roots only.

A self-declared public key is never a trust anchor. The caller must supply an
independently pinned TEST root. No root enrollment CLI, signer, source access,
ArchiveStore integration, or live capture authority exists here.
"""
import base64
import binascii
import hashlib
import json
import re

from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, KEY_ID, MAX_CLOCK_MS,
    Ed25519PublicKey, InvalidSignature, verify_test_proof,
)

SCHEMA = "post-apollo.trash-source-owner-authority.v2l"
POLICY_ORIGIN = "TEST_FIXTURE_ONLY"
ROOT_ORIGIN = "EXTERNALLY_PINNED_TEST_ROOT"
MAX_MANIFEST_BYTES = 2048
MAX_GENERATION = 1000000000
MAX_MANIFEST_VALIDITY_MS = 366 * 24 * 60 * 60 * 1000
FUTURE_SKEW_MS = 30000
HEX = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "keyId", "publicKeyB64", "generation", "issuedAtMs",
    "validFromMs", "validUntilMs", "revoked", "previousManifestSha256",
))
ENVELOPE_FIELDS = frozenset(("manifest", "signatureB64"))
ROOT_FIELDS = frozenset(("rootKeyId", "publicKeyBytes", "origin"))


class OwnerTrustError(Exception):
    """Stable error code, never path, key material or source content."""


def _require(ok, code):
    if not ok:
        raise OwnerTrustError(code)


def _ms(value):
    return type(value) is int and 1 <= value <= MAX_CLOCK_MS


def _raw_b64(value, expected, code):
    _require(type(value) is str, code)
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise OwnerTrustError(code) from exc
    _require(len(raw) == expected
             and base64.b64encode(raw).decode("ascii") == value, code)
    return raw


def canonical_authority(manifest):
    """Fixed canonical signature bytes. Test-only; no secret material."""
    _require(type(manifest) is dict
             and set(manifest) == MANIFEST_FIELDS,
             "SOURCE_AUTHORITY_SCHEMA_INVALID")
    _require(manifest["schema"] == SCHEMA
             and manifest["audience"] == AUDIENCE
             and manifest["purpose"] == PURPOSE
             and manifest["policyOrigin"] == POLICY_ORIGIN,
             "SOURCE_TRUST_NOT_PROVISIONED")
    _require(type(manifest["ownerId"]) is str
             and manifest["ownerId"] in ALLOWED_OWNERS
             and type(manifest["keyId"]) is str
             and KEY_ID.fullmatch(manifest["keyId"])
             and type(manifest["rootKeyId"]) is str
             and KEY_ID.fullmatch(manifest["rootKeyId"])
             and type(manifest["revoked"]) is bool
             and type(manifest["generation"]) is int
             and 1 <= manifest["generation"] <= MAX_GENERATION,
             "SOURCE_AUTHORITY_FIELDS_INVALID")
    _raw_b64(manifest["publicKeyB64"], 32,
             "SOURCE_AUTHORITY_KEY_INVALID")
    _require(_ms(manifest["issuedAtMs"])
             and _ms(manifest["validFromMs"])
             and _ms(manifest["validUntilMs"])
             and manifest["validFromMs"] <= manifest["issuedAtMs"]
             and manifest["issuedAtMs"] < manifest["validUntilMs"]
             and manifest["validUntilMs"] - manifest["validFromMs"]
                 <= MAX_MANIFEST_VALIDITY_MS,
             "SOURCE_AUTHORITY_TIME_INVALID")
    previous = manifest["previousManifestSha256"]
    _require(type(previous) is str
             and (previous == "" if manifest["generation"] == 1
                  else HEX.fullmatch(previous) is not None),
             "SOURCE_AUTHORITY_LINEAGE_INVALID")
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(len(raw) <= MAX_MANIFEST_BYTES,
             "SOURCE_AUTHORITY_TOO_LARGE")
    return raw


def verify_fixture_authority(signed_manifest, pinned_root, *, now_ms):
    """Only an EXTERNALLY supplied root can authenticate one fixture record."""
    _require(type(signed_manifest) is dict
             and set(signed_manifest) == ENVELOPE_FIELDS,
             "SOURCE_AUTHORITY_ENVELOPE_INVALID")
    _require(type(pinned_root) is dict
             and set(pinned_root) == ROOT_FIELDS
             and pinned_root["origin"] == ROOT_ORIGIN,
             "SOURCE_TRUST_NOT_PROVISIONED")
    m = signed_manifest["manifest"]
    raw = canonical_authority(m)
    _require(type(pinned_root["rootKeyId"]) is str
             and pinned_root["rootKeyId"] == m["rootKeyId"]
             and type(pinned_root["publicKeyBytes"]) is bytes
             and len(pinned_root["publicKeyBytes"]) == 32,
             "SOURCE_ROOT_PIN_MISMATCH")
    _require(_ms(now_ms), "SOURCE_TRUST_CLOCK_UNAVAILABLE")
    _require(m["issuedAtMs"] <= now_ms + FUTURE_SKEW_MS
             and m["validFromMs"] <= now_ms < m["validUntilMs"],
             "SOURCE_AUTHORITY_EXPIRED")
    sig = _raw_b64(signed_manifest["signatureB64"], 64,
                   "SOURCE_AUTHORITY_SIGNATURE_INVALID")
    if Ed25519PublicKey is None:
        raise OwnerTrustError("SOURCE_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            pinned_root["publicKeyBytes"]).verify(sig, raw)
    except (InvalidSignature, ValueError) as exc:
        raise OwnerTrustError("SOURCE_AUTHORITY_SIGNATURE_REFUSED") from exc
    public_key = _raw_b64(m["publicKeyB64"], 32,
                          "SOURCE_AUTHORITY_KEY_INVALID")
    manifest_hash = hashlib.sha256(raw).hexdigest()
    return {
        "state": "TEST_AUTHORITY_SIGNATURE_MATCHED_DENY_ONLY",
        "ownerId": m["ownerId"],
        "keyId": m["keyId"],
        "generation": m["generation"],
        "manifestSha256": manifest_hash,
        "previousManifestSha256": m["previousManifestSha256"],
        "rootFingerprint": hashlib.sha256(
            pinned_root["publicKeyBytes"]).hexdigest(),
        "revoked": m["revoked"],
        "policy": {
            "ownerId": m["ownerId"],
            "keyId": m["keyId"],
            "publicKeyBytes": public_key,
            "validFromMs": m["validFromMs"],
            "validUntilMs": m["validUntilMs"],
            "revoked": m["revoked"],
            "purpose": PURPOSE,
            "policyOrigin": POLICY_ORIGIN,
        },
        "sourceAuthorityVerified": False,
        "captureAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "productionAllowed": False,
    }


def verify_enrolled_test_claim(
    signed_manifest, pinned_root, proof, *, ledger, owner_id,
    resource_id, source_revision, payload_sha256, now_ms,
):
    """Check signed enrolled test key and consume nonce in one TEST ledger txn.

    The test trust ledger and ArchiveStore are deliberately separate.
    Success returns DENY_ONLY; real capture is never authorized here.
    """
    from scripts.trash.archive_v2_trust_history import TestOwnerTrustHistory
    _require(type(ledger) is TestOwnerTrustHistory,
             "SOURCE_TRUST_LEDGER_REQUIRED")
    evidence = verify_fixture_authority(
        signed_manifest, pinned_root, now_ms=now_ms)
    _require(evidence["ownerId"] == owner_id,
             "SOURCE_OWNER_SCOPE_REFUSED")
    # V2k validates signed claim against the policy established by the
    # independently pinned fixture authority, not a key inside the claim.
    signed = verify_test_proof(
        proof, evidence["policy"], owner_id=owner_id,
        resource_id=resource_id, source_revision=source_revision,
        payload_sha256=payload_sha256, now_ms=now_ms)
    ledger.consume_under_current_policy(evidence, signed)
    return {
        "state": "TEST_ENROLLED_CAPTURE_RECORDED_DENY_ONLY",
        "ownerId": owner_id,
        "keyId": evidence["keyId"],
        "authorityGeneration": evidence["generation"],
        "authoritySha256": evidence["manifestSha256"],
        "claimSha256": signed["proofSha256"],
        "signatureVerified": True,
        "authorityManifestSignatureVerified": True,
        "replayConsumed": True,
        "sourceAuthorityVerified": False,
        "humanConsentVerified": False,
        "captureAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "productionAllowed": False,
    }
