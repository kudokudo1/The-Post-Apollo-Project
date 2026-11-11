#!/usr/bin/env python3
"""Trash++ V2k DENY-ONLY Ed25519 source-capture evidence preflight.

There are NO live owner keys, NO production trust store, NO host integration,
NO sign operation, and NO ArchiveStore call. Only explicit synthetic
TEST_FIXTURE policies can pass; even success never grants capture, Restore or
Burn authority. The caller must separately establish policy provenance and
source consent in a future reviewed milestone.
"""
import base64
import binascii
import hashlib
import hmac
import json
import re

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # Missing dependency must DENY; never try custom crypto.
    InvalidSignature = None
    Ed25519PublicKey = None

SCHEMA = "post-apollo.trash-capture-owner-proof.v2k"
AUDIENCE = "post-apollo.trashpp.archive-v2"
PURPOSE = "independent-readonly-copy"
ALLOWED_OWNERS = frozenset(("demo-scrape", "weather-events"))
MAX_CLOCK_MS = 9999999999999
MAX_TTL_MS = 300000
CLOCK_SKEW_MS = 30000
RESOURCE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
KEY_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^[0-9a-f]{32}$")

CLAIM_KEYS = frozenset((
    "schema", "audience", "purpose", "ownerId", "resourceId",
    "sourceRevision", "payloadSha256", "sourceCapturedAtMs",
    "issuedAtMs", "expiresAtMs", "keyId", "nonce"
))
PROOF_KEYS = frozenset(("claim", "signatureB64"))
POLICY_KEYS = frozenset(("ownerId", "keyId", "publicKeyBytes",
                         "validFromMs", "validUntilMs", "revoked",
                         "purpose", "policyOrigin"))


class SignedCaptureError(Exception):
    """Safe fixed error code, never reveals source data or signature bytes."""


def _check(ok, code):
    if not ok:
        raise SignedCaptureError(code)


def _bounded_ms(value):
    return type(value) is int and 1 <= value <= MAX_CLOCK_MS


def canonical_claim(claim):
    """Canonical bytes: no flexible JSON serialization or unknown fields."""
    _check(type(claim) is dict and set(claim) == CLAIM_KEYS,
           "CAPTURE_CLAIM_SCHEMA_INVALID")
    _check(claim["schema"] == SCHEMA
           and claim["audience"] == AUDIENCE
           and claim["purpose"] == PURPOSE, "CAPTURE_CLAIM_SCOPE_INVALID")
    _check(type(claim["ownerId"]) is str
           and claim["ownerId"] in ALLOWED_OWNERS
           and type(claim["resourceId"]) is str
           and RESOURCE.fullmatch(claim["resourceId"])
           and type(claim["keyId"]) is str
           and KEY_ID.fullmatch(claim["keyId"])
           and type(claim["sourceRevision"]) is str
           and SHA.fullmatch(claim["sourceRevision"])
           and type(claim["payloadSha256"]) is str
           and SHA.fullmatch(claim["payloadSha256"])
           and type(claim["nonce"]) is str
           and NONCE.fullmatch(claim["nonce"]),
           "CAPTURE_CLAIM_FIELDS_INVALID")
    _check(all(_bounded_ms(claim[x]) for x in (
        "sourceCapturedAtMs", "issuedAtMs", "expiresAtMs")),
        "CAPTURE_CLAIM_TIME_INVALID")
    _check(claim["sourceCapturedAtMs"] <= claim["issuedAtMs"]
           and claim["issuedAtMs"] < claim["expiresAtMs"]
           and claim["expiresAtMs"] - claim["issuedAtMs"] <= MAX_TTL_MS,
           "CAPTURE_CLAIM_TIME_INVALID")
    raw = json.dumps(claim, sort_keys=True, ensure_ascii=True,
                     allow_nan=False, separators=(",", ":")).encode("ascii")
    _check(len(raw) <= 2048, "CAPTURE_CLAIM_TOO_LARGE")
    return raw


def _policy(policy, claim):
    # There is intentionally no production-policy variant yet: a caller must
    # not turn an arbitrary public key into source-owner authority.
    _check(type(policy) is dict and set(policy) == POLICY_KEYS
           and policy["policyOrigin"] == "TEST_FIXTURE_ONLY",
           "SOURCE_TRUST_NOT_PROVISIONED")
    _check(type(policy["ownerId"]) is str
           and type(policy["keyId"]) is str
           and policy["ownerId"] == claim["ownerId"]
           and policy["keyId"] == claim["keyId"]
           and policy["purpose"] == PURPOSE
           and type(policy["revoked"]) is bool,
           "CAPTURE_SIGNER_SCOPE_REFUSED")
    _check(policy["revoked"] is False, "CAPTURE_SIGNER_REVOKED")
    _check(type(policy["publicKeyBytes"]) is bytes
           and len(policy["publicKeyBytes"]) == 32
           and _bounded_ms(policy["validFromMs"])
           and _bounded_ms(policy["validUntilMs"])
           and policy["validFromMs"] < policy["validUntilMs"],
           "CAPTURE_SIGNER_KEY_INVALID")
    _check(policy["validFromMs"] <= claim["issuedAtMs"]
           and claim["expiresAtMs"] <= policy["validUntilMs"],
           "CAPTURE_SIGNER_KEY_EXPIRED")


def verify_test_proof(proof, policy, *, owner_id, resource_id,
                      source_revision, payload_sha256, now_ms):
    """Check one fixture-only signature; return DENY-ONLY verification evidence.

    No arbitrary key supplied by the proof is ever trusted. The external
    protected source owner must pin a real policy in a future integration.
    """
    _check(type(proof) is dict and set(proof) == PROOF_KEYS,
           "CAPTURE_PROOF_FORMAT_INVALID")
    claim = proof["claim"]
    encoded = canonical_claim(claim)
    _policy(policy, claim)
    _check(type(owner_id) is str and type(resource_id) is str
           and type(source_revision) is str and type(payload_sha256) is str
           and (claim["ownerId"], claim["resourceId"],
                claim["sourceRevision"], claim["payloadSha256"])
           == (owner_id, resource_id, source_revision, payload_sha256),
           "CAPTURE_SOURCE_MISMATCH")
    _check(_bounded_ms(now_ms), "CAPTURE_CLOCK_UNAVAILABLE")
    _check(claim["issuedAtMs"] <= now_ms + CLOCK_SKEW_MS
           and now_ms < claim["expiresAtMs"],
           "CAPTURE_PROOF_EXPIRED")
    signature = proof["signatureB64"]
    _check(type(signature) is str and len(signature) == 88,
           "CAPTURE_SIGNATURE_INVALID")
    try:
        decoded = base64.b64decode(signature, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SignedCaptureError("CAPTURE_SIGNATURE_INVALID") from exc
    _check(len(decoded) == 64
           and base64.b64encode(decoded).decode("ascii") == signature,
           "CAPTURE_SIGNATURE_INVALID")
    if Ed25519PublicKey is None:
        raise SignedCaptureError("CAPTURE_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            policy["publicKeyBytes"]).verify(decoded, encoded)
    except (InvalidSignature, ValueError) as exc:
        raise SignedCaptureError("CAPTURE_SIGNATURE_REFUSED") from exc
    return {
        "state": "TEST_SIGNATURE_VALID_DENY_ONLY",
        "proofSha256": hashlib.sha256(encoded).hexdigest(),
        "ownerId": owner_id, "resourceId": resource_id,
        "keyId": claim["keyId"], "nonce": claim["nonce"],
        "issuedAtMs": claim["issuedAtMs"],
        "expiresAtMs": claim["expiresAtMs"],
        "signatureVerified": True,
        "replayConsumed": False,
        "sourceAuthorityVerified": False,
        "humanConsentVerified": False,
        "captureAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "productionAllowed": False,
    }


def verify_test_and_record(proof, policy, *, ledger, owner_id, resource_id,
                           source_revision, payload_sha256, now_ms):
    """Consume fixture nonce after valid Ed25519 verification; still deny use.

    Ledger's durability is tested independently. This is NOT transactional
    with ArchiveStore and cannot authorize any actual copy.
    """
    evidence = verify_test_proof(
        proof, policy, owner_id=owner_id, resource_id=resource_id,
        source_revision=source_revision, payload_sha256=payload_sha256,
        now_ms=now_ms)
    from scripts.trash.archive_v2_replay_ledger import TestReplayLedger
    _check(type(ledger) is TestReplayLedger,
           "CAPTURE_REPLAY_LEDGER_REQUIRED")
    ledger.consume(evidence["ownerId"], evidence["keyId"],
                   evidence["nonce"], evidence["proofSha256"])
    evidence["replayConsumed"] = True
    evidence["state"] = "TEST_RECORDED_DENY_ONLY"
    return evidence
