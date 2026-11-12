#!/usr/bin/env python3
"""Trash++ V3b // fixture-only signed anti-rollback witness comparison.

Pure read-only verification of TWO Ed25519-signed test witness envelopes and
one already-observed V2w floor response. The prior anchor MUST arrive from an
independent trusted channel in a future implementation; this module cannot
authenticate that channel, preserve a high-water mark, or grant access.

No signing, key enrollment, filesystem, clock, archive, service, IPC, capture,
migration, restore, retention or Burn operation exists in this module.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json

from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, SHA, KEY_ID,
    Ed25519PublicKey, InvalidSignature,
)
from scripts.trash.archive_v3a_cutover_readiness_review import (
    ReadinessRefused, _floor,
)

KIND = "post-apollo.trashpp.v3b.fixture-signed-rollback-witness"
ORIGIN = "TEST_FIXTURE_ONLY"
PIN_ORIGIN = "EXTERNALLY_PINNED_TEST_ROOT"
CLAIM_FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "grantSha256", "epoch", "floorSequence", "floorSha256",
    "releaseSha256", "witnessSequence", "previousWitnessSha256", "revoked",
))
ENVELOPE_FIELDS = frozenset(("claim", "signatureB64"))
PIN_FIELDS = frozenset(("rootKeyId", "publicKeyBytes", "origin"))
MAX_CLAIM_BYTES = 2048


class WitnessRefused(ValueError):
    """Stable diagnostic code only, never signer's bytes or payloads."""


def _need(condition, code):
    if not condition:
        raise WitnessRefused(code)


def _sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _positive(value):
    return type(value) is int and 1 <= value <= 1000000000


def canonical_claim(claim):
    """Strict ASCII bytes with explicit domain separation and no extensions."""
    _need(type(claim) is dict and set(claim) == CLAIM_FIELDS,
          "V3B_CLAIM_SCHEMA_INVALID")
    _need(claim["schema"] == KIND and claim["audience"] == AUDIENCE
          and claim["purpose"] == PURPOSE
          and claim["policyOrigin"] == ORIGIN
          and type(claim["rootKeyId"]) is str
          and KEY_ID.fullmatch(claim["rootKeyId"]) is not None
          and type(claim["ownerId"]) is str
          and claim["ownerId"] in ALLOWED_OWNERS
          and _sha(claim["grantSha256"])
          and _sha(claim["floorSha256"])
          and _sha(claim["releaseSha256"])
          and _positive(claim["epoch"])
          and _positive(claim["floorSequence"])
          and _positive(claim["witnessSequence"])
          and type(claim["revoked"]) is bool,
          "V3B_CLAIM_FIELDS_INVALID")
    previous = claim["previousWitnessSha256"]
    _need(type(previous) is str and
          (previous == "" if claim["witnessSequence"] == 1
           else _sha(previous)), "V3B_WITNESS_LINK_INVALID")
    raw = json.dumps(claim, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _need(len(raw) <= MAX_CLAIM_BYTES, "V3B_CLAIM_TOO_LARGE")
    return raw


def _pin(value, floor_signer_public_key):
    _need(type(value) is dict and set(value) == PIN_FIELDS
          and value["origin"] == PIN_ORIGIN
          and type(value["rootKeyId"]) is str
          and KEY_ID.fullmatch(value["rootKeyId"]) is not None
          and type(value["publicKeyBytes"]) is bytes
          and len(value["publicKeyBytes"]) == 32
          and type(floor_signer_public_key) is bytes
          and len(floor_signer_public_key) == 32
          and value["publicKeyBytes"] != floor_signer_public_key,
          "V3B_SEPARATE_TEST_SIGNER_REQUIRED")
    _need(Ed25519PublicKey is not None and InvalidSignature is not None,
          "V3B_CRYPTO_UNAVAILABLE")


def _verify(envelope, pinned):
    """Reject valid-looking but incorrectly signed or out-of-scope evidence."""
    _need(type(envelope) is dict and set(envelope) == ENVELOPE_FIELDS,
          "V3B_ENVELOPE_INVALID")
    claim = envelope["claim"]
    raw = canonical_claim(claim)
    _need(claim["rootKeyId"] == pinned["rootKeyId"],
          "V3B_SIGNER_ID_MISMATCH")
    encoded = envelope["signatureB64"]
    _need(type(encoded) is str and len(encoded) == 88,
          "V3B_SIGNATURE_ENCODING_INVALID")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise WitnessRefused("V3B_SIGNATURE_ENCODING_INVALID") from exc
    _need(len(signature) == 64
          and base64.b64encode(signature).decode("ascii") == encoded,
          "V3B_SIGNATURE_ENCODING_INVALID")
    try:
        Ed25519PublicKey.from_public_bytes(
            pinned["publicKeyBytes"]).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise WitnessRefused("V3B_SIGNATURE_REFUSED") from exc
    return claim, hashlib.sha256(raw).hexdigest()


def compare(pinned_previous, presented_current, pinned_test_key,
            observed_floor, *, expected_owner_id, expected_grant_sha256,
            floor_signer_public_key):
    """Compare signed TEST receipts to a separately *supplied* test anchor.

    Never treat a signed witness as a trusted high-water store. A caller that
    replaces BOTH its current and prior input can hide rollback; the output
    is therefore deny-only EVEN WHEN every signature and sequence matches.
    """
    _pin(pinned_test_key, floor_signer_public_key)
    _need(type(expected_owner_id) is str
          and expected_owner_id in ALLOWED_OWNERS
          and _sha(expected_grant_sha256),
          "V3B_EXPECTED_SOURCE_POLICY_INVALID")
    try:
        _floor(observed_floor)
    except (ReadinessRefused, KeyError, TypeError, ValueError) as exc:
        raise WitnessRefused("V3B_FLOOR_OBSERVATION_INVALID") from exc

    old, old_digest = _verify(pinned_previous, pinned_test_key)
    new, new_digest = _verify(presented_current, pinned_test_key)
    _need(old["ownerId"] == new["ownerId"] ==
          observed_floor["ownerId"] == expected_owner_id
          and old["grantSha256"] == new["grantSha256"] ==
          expected_grant_sha256,
          "V3B_OWNER_GRANT_BINDING_INVALID")

    holds = set()
    if old["revoked"] or new["revoked"]:
        holds.add("revocation_witness_observed")
    if new["witnessSequence"] < old["witnessSequence"]:
        holds.add("witness_sequence_rollback")
    elif new["witnessSequence"] == old["witnessSequence"]:
        if new_digest != old_digest:
            holds.add("signed_witness_equivocation")
    elif new["witnessSequence"] != old["witnessSequence"] + 1:
        holds.add("witness_chain_gap")
    elif new["previousWitnessSha256"] != old_digest:
        holds.add("witness_chain_diverged")

    if new["epoch"] < old["epoch"]:
        holds.add("release_epoch_rollback")
    if new["epoch"] == old["epoch"] and (
        new["floorSequence"] < old["floorSequence"]):
        holds.add("release_sequence_rollback")
    if (new["epoch"] == old["epoch"] and
        new["floorSequence"] == old["floorSequence"] and
        (new["floorSha256"] != old["floorSha256"] or
         new["releaseSha256"] != old["releaseSha256"])):
        holds.add("release_same_version_changed")
    if new["epoch"] != observed_floor["epoch"]:
        holds.add("witness_floor_epoch_disagreement")
    if new["floorSequence"] != observed_floor["sequence"]:
        holds.add("witness_floor_sequence_disagreement")
    if new["floorSha256"] != observed_floor["externalFloorSha256"]:
        holds.add("witness_floor_digest_disagreement")
    if new["releaseSha256"] != observed_floor["releaseSha256"]:
        holds.add("witness_release_digest_disagreement")

    # Even valid signed witnesses cannot supply the separately protected
    # persistent anchor, time, service origin, owner consent or archive backup.
    if not observed_floor["offUidFileObserved"]:
        holds.add("same_uid_floor_fixture")
    else:
        holds.add("off_uid_file_not_monotonic_authority")

    return {
        "kind": "post-apollo.trashpp.v3b.readonly-witness-check",
        "state": "MANUAL_AUTHORITY_REVIEW_REQUIRED",
        "holdReasons": sorted(holds),
        "witnessSignatureValidFixtureOnly": True,
        "witnessSequenceObserved": new["witnessSequence"],
        "previousSequenceObserved": old["witnessSequence"],
        "expectedOwnerId": expected_owner_id,
        "externalAnchorAuthenticated": False,
        "monotonicStorageVerified": False,
        "trustedTimeVerified": False,
        "sourceOwnerAuthorityVerified": False,
        "serviceIdentityVerified": False,
        "backupCustodyVerified": False,
        "humanConsentVerified": False,
        "captureAllowed": False,
        "productionAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "automaticRetryAllowed": False,
        "automaticRollbackAllowed": False,
        "deleteOriginalAllowed": False,
        "safeActions": [],
        "readOnly": True,
        "requiresIndependentReview": True,
    }


if __name__ == "__main__":
    raise SystemExit(1)
