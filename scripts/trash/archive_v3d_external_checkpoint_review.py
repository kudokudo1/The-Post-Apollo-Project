#!/usr/bin/env python3
"""Trash++ V3d // OFFLINE read-only two-root external checkpoint review.

This verifies an independently signed *candidate* checkpoint and a signed
V3b test witness. It does NOT contact or persist an external authority,
authenticate a checkpoint retrieval channel, provision keys, grant capture,
or claim that the pinned older checkpoint survives a compromised host.

Only an independently administered authority, with its own trusted storage,
key custody and recovery process, could turn this contract into a useful
production rollback boundary. Never connect this module to live ArchiveStore.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json

from scripts.trash import archive_v3b_signed_rollback_witness as witness
from scripts.trash.archive_v2_signed_capture import KEY_ID, Ed25519PublicKey, InvalidSignature

KIND = "post-apollo.trashpp.v3d.offline-independent-checkpoint"
AUDIENCE = "post-apollo.trashpp.archive-independent-checkpoint"
ORIGIN = "OFFLINE_TEST_ONLY"
PIN_ORIGIN = "OFFLINE_SEPARATELY_SUPPLIED_TEST_KEY"
SIGNING_DOMAIN = b"POST_APOLLO_TRASH_V3D_CHECKPOINT_V1\x00"
MAX_CLAIM_BYTES = 2048
CLAIM_FIELDS = frozenset((
    "schema", "audience", "policyOrigin", "anchorKeyId",
    "ownerId", "grantSha256", "checkpointSequence",
    "previousCheckpointSha256", "witnessSequence", "witnessSha256",
    "epoch", "floorSequence", "floorSha256", "releaseSha256", "revoked",
))
PIN_FIELDS = frozenset(("anchorKeyId", "publicKeyBytes", "origin"))
ENVELOPE_FIELDS = frozenset(("claim", "signatureB64"))


class CheckpointRefused(ValueError):
    """Fixed error code only. No signer bytes, supplied fields, or paths."""


def _need(ok, code):
    if not ok:
        raise CheckpointRefused(code)


def canonical_checkpoint(claim):
    """Domain-separated exact-schema signature bytes, bounded for auditing."""
    _need(type(claim) is dict and set(claim) == CLAIM_FIELDS,
          "V3D_CHECKPOINT_SCHEMA_REFUSED")
    _need(
        claim["schema"] == KIND
        and claim["audience"] == AUDIENCE
        and claim["policyOrigin"] == ORIGIN
        and type(claim["anchorKeyId"]) is str
        and KEY_ID.fullmatch(claim["anchorKeyId"]) is not None
        and type(claim["ownerId"]) is str
        and claim["ownerId"] in witness.ALLOWED_OWNERS
        and witness._sha(claim["grantSha256"])
        and witness._positive(claim["checkpointSequence"])
        and witness._positive(claim["witnessSequence"])
        and witness._sha(claim["witnessSha256"])
        and witness._positive(claim["epoch"])
        and witness._positive(claim["floorSequence"])
        and witness._sha(claim["floorSha256"])
        and witness._sha(claim["releaseSha256"])
        and type(claim["revoked"]) is bool,
        "V3D_CHECKPOINT_FIELDS_REFUSED",
    )
    old = claim["previousCheckpointSha256"]
    _need(type(old) is str and
          (old == "" if claim["checkpointSequence"] == 1
           else witness._sha(old)), "V3D_CHECKPOINT_LINK_REFUSED")
    try:
        raw = json.dumps(claim, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CheckpointRefused("V3D_CHECKPOINT_ENCODING_REFUSED") from exc
    _need(len(raw) <= MAX_CLAIM_BYTES, "V3D_CHECKPOINT_TOO_LARGE")
    return SIGNING_DOMAIN + raw


def _check_pins(anchor_pin, witness_pin, floor_signer_public_key):
    try:
        witness._pin(witness_pin, floor_signer_public_key)
    except (witness.WitnessRefused, TypeError, ValueError) as exc:
        raise CheckpointRefused("V3D_WITNESS_PIN_REFUSED") from exc
    _need(type(anchor_pin) is dict and set(anchor_pin) == PIN_FIELDS
          and anchor_pin["origin"] == PIN_ORIGIN
          and type(anchor_pin["anchorKeyId"]) is str
          and KEY_ID.fullmatch(anchor_pin["anchorKeyId"]) is not None
          and type(anchor_pin["publicKeyBytes"]) is bytes
          and len(anchor_pin["publicKeyBytes"]) == 32
          and anchor_pin["publicKeyBytes"] != witness_pin["publicKeyBytes"]
          and anchor_pin["publicKeyBytes"] != floor_signer_public_key,
          "V3D_INDEPENDENT_TEST_ROOT_REQUIRED")
    _need(Ed25519PublicKey is not None and InvalidSignature is not None,
          "V3D_CRYPTO_UNAVAILABLE")


def _verify_checkpoint(envelope, anchor_pin):
    _need(type(envelope) is dict and set(envelope) == ENVELOPE_FIELDS,
          "V3D_CHECKPOINT_ENVELOPE_REFUSED")
    claim = envelope["claim"]
    raw = canonical_checkpoint(claim)
    _need(claim["anchorKeyId"] == anchor_pin["anchorKeyId"],
          "V3D_ANCHOR_KEY_ID_REFUSED")
    encoded = envelope["signatureB64"]
    _need(type(encoded) is str and len(encoded) == 88,
          "V3D_SIGNATURE_ENCODING_REFUSED")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CheckpointRefused("V3D_SIGNATURE_ENCODING_REFUSED") from exc
    _need(len(signature) == 64
          and base64.b64encode(signature).decode("ascii") == encoded,
          "V3D_SIGNATURE_ENCODING_REFUSED")
    try:
        Ed25519PublicKey.from_public_bytes(
            anchor_pin["publicKeyBytes"]).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise CheckpointRefused("V3D_SIGNATURE_REFUSED") from exc
    return claim, hashlib.sha256(raw).hexdigest()


def review(reference_checkpoint, presented_checkpoint, signed_witness, *,
           anchor_pin, witness_pin, observed_floor,
           floor_signer_public_key, expected_owner_id,
           expected_grant_sha256):
    """Compare signed offline evidence without asserting trust in its custody.

    reference_checkpoint MUST eventually come from a trusted independent
    retrieval and durable high-water system. Here BOTH are caller supplied;
    cryptographic validity alone is never evidence of that independent state.
    """
    _check_pins(anchor_pin, witness_pin, floor_signer_public_key)
    _need(type(expected_owner_id) is str
          and expected_owner_id in witness.ALLOWED_OWNERS
          and witness._sha(expected_grant_sha256),
          "V3D_EXPECTED_POLICY_REFUSED")
    try:
        witness._floor(observed_floor)
    except (ValueError, TypeError, KeyError) as exc:
        raise CheckpointRefused("V3D_FLOOR_SHAPE_REFUSED") from exc
    try:
        signed_claim, signed_digest = witness._verify(
            signed_witness, witness_pin)
    except (witness.WitnessRefused, TypeError, ValueError) as exc:
        raise CheckpointRefused("V3D_SIGNED_WITNESS_REFUSED") from exc

    old, old_hash = _verify_checkpoint(reference_checkpoint, anchor_pin)
    new, new_hash = _verify_checkpoint(presented_checkpoint, anchor_pin)
    _need(old["ownerId"] == new["ownerId"] == signed_claim["ownerId"]
          == expected_owner_id == observed_floor["ownerId"]
          and old["grantSha256"] == new["grantSha256"]
          == signed_claim["grantSha256"] == expected_grant_sha256,
          "V3D_OWNER_GRANT_REFUSED")

    holds = {
        "independent_checkpoint_custody_unverified",
        "trusted_reference_highwater_unverified",
        "remote_authority_service_unverified",
        "independent_signing_key_custody_unverified",
        "trusted_time_unverified",
        "source_owner_consent_unverified",
        "c3e_c5_authorization_unverified",
        "archive_backup_and_cutover_unverified",
    }
    if new["checkpointSequence"] < old["checkpointSequence"]:
        holds.add("signed_checkpoint_sequence_rollback")
    elif new["checkpointSequence"] == old["checkpointSequence"]:
        if new_hash != old_hash:
            holds.add("signed_checkpoint_same_sequence_fork")
    elif new["checkpointSequence"] != old["checkpointSequence"] + 1:
        holds.add("signed_checkpoint_chain_gap")
    elif new["previousCheckpointSha256"] != old_hash:
        holds.add("signed_checkpoint_chain_diverged")

    if new["witnessSequence"] < old["witnessSequence"]:
        holds.add("anchored_witness_sequence_rollback")
    elif new["witnessSequence"] == old["witnessSequence"]:
        if new["witnessSha256"] != old["witnessSha256"]:
            holds.add("anchored_witness_same_sequence_fork")
    elif new["witnessSequence"] != old["witnessSequence"] + 1:
        holds.add("anchored_witness_chain_gap")
    elif signed_claim["previousWitnessSha256"] != old["witnessSha256"]:
        holds.add("signed_witness_predecessor_mismatch")

    if new["witnessSequence"] != signed_claim["witnessSequence"]:
        holds.add("current_witness_sequence_mismatch")
    if new["witnessSha256"] != signed_digest:
        holds.add("current_witness_digest_mismatch")
    if new["revoked"] != signed_claim["revoked"]:
        holds.add("current_revocation_mismatch")
    if old["revoked"] and not new["revoked"]:
        holds.add("irreversible_revocation_reversed")
    if old["epoch"] > new["epoch"]:
        holds.add("signed_release_epoch_rollback")
    if old["epoch"] == new["epoch"]:
        if new["floorSequence"] < old["floorSequence"]:
            holds.add("signed_release_sequence_rollback")
        if (new["floorSequence"] == old["floorSequence"]
                and (new["floorSha256"] != old["floorSha256"]
                     or new["releaseSha256"] != old["releaseSha256"])):
            holds.add("signed_release_same_version_fork")

    for field, other, reason in (
        ("epoch", "epoch", "current_floor_epoch_mismatch"),
        ("floorSequence", "sequence", "current_floor_sequence_mismatch"),
        ("floorSha256", "externalFloorSha256", "current_floor_digest_mismatch"),
        ("releaseSha256", "releaseSha256", "current_release_digest_mismatch"),
    ):
        if new[field] != observed_floor[other]:
            holds.add(reason)
        if new[field] != signed_claim[field]:
            holds.add("current_witness_" + field + "_mismatch")

    # The result NEVER promotes caller-supplied pin origin, floor metadata or
    # signature correctness into external custody, trusted time or authority.
    return {
        "kind": "post-apollo.trashpp.v3d.offline-checkpoint-review",
        "state": "INDEPENDENT_AUTHORITY_HOLD",
        "holdReasons": sorted(holds),
        "checkpointSignatureValidOfflineOnly": True,
        "witnessSignatureValidFixtureOnly": True,
        "referenceCheckpointSequenceObserved": old["checkpointSequence"],
        "presentedCheckpointSequenceObserved": new["checkpointSequence"],
        "signedWitnessSequenceObserved": signed_claim["witnessSequence"],
        "independentAuthorityAuthenticated": False,
        "externallyProtectedMonotonicAuthorityVerified": False,
        "trustedReferenceHighwaterVerified": False,
        "trustedClockVerified": False,
        "sourceOwnerAuthorityVerified": False,
        "c3eAuthenticatedSourceVerified": False,
        "c5HumanConsentVerified": False,
        "backupCustodyVerified": False,
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
    raise SystemExit(1)  # Not a signer, authority client, service or CLI.
