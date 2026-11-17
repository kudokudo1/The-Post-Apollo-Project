#!/usr/bin/env python3
"""Trash++ V3e // OFFLINE signed retrieval response verification, DENY ONLY.

Accepts test-only caller-supplied request/response/checkpoint evidence.
This is NOT a remote client, transport implementation, external authority,
replay database, production key pin, secure clock, or permission decision.
A locally substituted request+response+trust pin remains untrusted.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json

from scripts.trash import archive_v3d_external_checkpoint_review as v3d
from scripts.trash import archive_v3b_signed_rollback_witness as witness
from scripts.trash.archive_v2_signed_capture import (
    KEY_ID, Ed25519PublicKey, InvalidSignature,
)

REQUEST_KIND = "post-apollo.trashpp.v3e.offline-retrieval-request"
RESPONSE_KIND = "post-apollo.trashpp.v3e.offline-retrieval-response"
AUDIENCE = "post-apollo.trashpp.independent-checkpoint-retrieval"
ORIGIN = "OFFLINE_TEST_ONLY"
PIN_ORIGIN = "OFFLINE_SEPARATELY_SUPPLIED_TEST_RESPONDER"
REQUEST_DOMAIN = b"POST_APOLLO_TRASH_V3E_REQUEST_V1\x00"
RESPONSE_DOMAIN = b"POST_APOLLO_TRASH_V3E_RESPONSE_V1\x00"
MAX_BYTES = 2048

REQUEST_FIELDS = frozenset((
    "schema", "audience", "policyOrigin", "ownerId", "grantSha256",
    "nonce", "minimumCheckpointSequence",
))
RESPONSE_FIELDS = frozenset((
    "schema", "audience", "policyOrigin", "responderKeyId",
    "requestSha256", "nonce", "referenceCheckpointSha256",
    "checkpointSha256", "checkpointSequence", "transportStatus",
))
PIN_FIELDS = frozenset(("responderKeyId", "publicKeyBytes", "origin"))
ENVELOPE_FIELDS = frozenset(("claim", "signatureB64"))


class RetrievalRefused(ValueError):
    """Stable error code only, never caller payloads or cryptographic keys."""


def _need(condition, code):
    if not condition:
        raise RetrievalRefused(code)


def _canon(value, limit_code):
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RetrievalRefused("V3E_SERIALIZATION_REFUSED") from exc
    _need(len(raw) <= MAX_BYTES, limit_code)
    return raw


def canonical_request(value):
    """Caller nonce is format-checked, not independently proven unpredictable."""
    _need(type(value) is dict and set(value) == REQUEST_FIELDS,
          "V3E_REQUEST_SCHEMA_REFUSED")
    _need(
        value["schema"] == REQUEST_KIND and value["audience"] == AUDIENCE
        and value["policyOrigin"] == ORIGIN
        and type(value["ownerId"]) is str
        and value["ownerId"] in witness.ALLOWED_OWNERS
        and witness._sha(value["grantSha256"])
        and witness._sha(value["nonce"])
        and witness._positive(value["minimumCheckpointSequence"]),
        "V3E_REQUEST_FIELDS_REFUSED",
    )
    return REQUEST_DOMAIN + _canon(value, "V3E_REQUEST_TOO_LARGE")


def canonical_response(value):
    """Domain-separated exact payload for offline Ed25519 verification."""
    _need(type(value) is dict and set(value) == RESPONSE_FIELDS,
          "V3E_RESPONSE_SCHEMA_REFUSED")
    _need(
        value["schema"] == RESPONSE_KIND and value["audience"] == AUDIENCE
        and value["policyOrigin"] == ORIGIN
        and type(value["responderKeyId"]) is str
        and KEY_ID.fullmatch(value["responderKeyId"]) is not None
        and witness._sha(value["requestSha256"])
        and witness._sha(value["nonce"])
        and witness._sha(value["referenceCheckpointSha256"])
        and witness._sha(value["checkpointSha256"])
        and witness._positive(value["checkpointSequence"])
        and value["transportStatus"] == "TEST_CHECKPOINT_AVAILABLE",
        "V3E_RESPONSE_FIELDS_REFUSED",
    )
    return RESPONSE_DOMAIN + _canon(value, "V3E_RESPONSE_TOO_LARGE")


def _check_pin(pin, anchor_pin, witness_pin, floor_signer_public_key):
    _need(type(anchor_pin) is dict
          and set(anchor_pin) == v3d.PIN_FIELDS
          and type(anchor_pin["publicKeyBytes"]) is bytes
          and len(anchor_pin["publicKeyBytes"]) == 32
          and type(witness_pin) is dict
          and set(witness_pin) == witness.PIN_FIELDS
          and type(witness_pin["publicKeyBytes"]) is bytes
          and len(witness_pin["publicKeyBytes"]) == 32
          and type(floor_signer_public_key) is bytes
          and len(floor_signer_public_key) == 32,
          "V3E_OTHER_PINS_REFUSED")
    _need(type(pin) is dict and set(pin) == PIN_FIELDS
          and pin["origin"] == PIN_ORIGIN
          and type(pin["responderKeyId"]) is str
          and KEY_ID.fullmatch(pin["responderKeyId"]) is not None
          and type(pin["publicKeyBytes"]) is bytes
          and len(pin["publicKeyBytes"]) == 32
          and pin["publicKeyBytes"] not in (
              anchor_pin["publicKeyBytes"],
              witness_pin["publicKeyBytes"],
              floor_signer_public_key,
          ), "V3E_SEPARATE_TEST_RESPONDER_REQUIRED")
    _need(Ed25519PublicKey is not None and InvalidSignature is not None,
          "V3E_CRYPTO_UNAVAILABLE")


def _verify_envelope(envelope, pin):
    _need(type(envelope) is dict and set(envelope) == ENVELOPE_FIELDS,
          "V3E_ENVELOPE_REFUSED")
    claim = envelope["claim"]
    raw = canonical_response(claim)
    _need(claim["responderKeyId"] == pin["responderKeyId"],
          "V3E_RESPONDER_ID_REFUSED")
    encoded = envelope["signatureB64"]
    _need(type(encoded) is str and len(encoded) == 88,
          "V3E_SIGNATURE_ENCODING_REFUSED")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RetrievalRefused("V3E_SIGNATURE_ENCODING_REFUSED") from exc
    _need(len(signature) == 64
          and base64.b64encode(signature).decode("ascii") == encoded,
          "V3E_SIGNATURE_ENCODING_REFUSED")
    try:
        Ed25519PublicKey.from_public_bytes(
            pin["publicKeyBytes"]).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise RetrievalRefused("V3E_SIGNATURE_REFUSED") from exc
    return claim


def review(request, response, reference_checkpoint, presented_checkpoint,
           signed_witness, *, responder_pin, anchor_pin, witness_pin,
           observed_floor, floor_signer_public_key,
           expected_owner_id, expected_grant_sha256):
    """Refuse absent/stale/substituted retrieval evidence and ALL actions.

    Correct signatures/challenge bindings demonstrate only offline consistency.
    No trust comes from a caller-controlled nonce, transport claim or pin.
    """
    _check_pin(responder_pin, anchor_pin, witness_pin,
               floor_signer_public_key)
    canonical_req = canonical_request(request)
    _need(type(expected_owner_id) is str
          and expected_owner_id in witness.ALLOWED_OWNERS
          and witness._sha(expected_grant_sha256)
          and request["ownerId"] == expected_owner_id
          and request["grantSha256"] == expected_grant_sha256,
          "V3E_REQUEST_OWNER_GRANT_REFUSED")

    # This performs actual V3d signature/witness/release verification and
    # retains its deny-only findings. Caller-supplied prior remains untrusted.
    try:
        v3d_result = v3d.review(
            reference_checkpoint, presented_checkpoint, signed_witness,
            anchor_pin=anchor_pin, witness_pin=witness_pin,
            observed_floor=observed_floor,
            floor_signer_public_key=floor_signer_public_key,
            expected_owner_id=expected_owner_id,
            expected_grant_sha256=expected_grant_sha256,
        )
        old_sha = hashlib.sha256(
            v3d.canonical_checkpoint(reference_checkpoint["claim"])).hexdigest()
        new_sha = hashlib.sha256(
            v3d.canonical_checkpoint(presented_checkpoint["claim"])).hexdigest()
    except (v3d.CheckpointRefused, KeyError, TypeError, ValueError) as exc:
        raise RetrievalRefused("V3E_CHECKPOINT_VERIFICATION_REFUSED") from exc

    claim = _verify_envelope(response, responder_pin)
    _need(claim["requestSha256"] == hashlib.sha256(canonical_req).hexdigest()
          and claim["nonce"] == request["nonce"],
          "V3E_CHALLENGE_MISMATCH_REFUSED")
    _need(claim["referenceCheckpointSha256"] == old_sha
          and claim["checkpointSha256"] == new_sha
          and claim["checkpointSequence"]
          == v3d_result["presentedCheckpointSequenceObserved"],
          "V3E_RESPONSE_CHECKPOINT_BINDING_REFUSED")

    holds = set(v3d_result["holdReasons"])
    holds.update((
        "independent_responder_identity_unverified",
        "network_transport_not_implemented",
        "authenticated_retrieval_channel_unverified",
        "challenge_entropy_and_single_use_unverified",
        "retrieval_replay_history_unverified",
        "independent_checkpoint_storage_unverified",
        "freshness_clock_unverified",
    ))
    if claim["checkpointSequence"] < request["minimumCheckpointSequence"]:
        holds.add("checkpoint_below_requested_floor")
    if (v3d_result["presentedCheckpointSequenceObserved"]
            < v3d_result["referenceCheckpointSequenceObserved"]):
        holds.add("retrieved_checkpoint_older_than_reference")

    # No caller-supplied claim is allowed to promote any production privilege.
    return {
        "kind": "post-apollo.trashpp.v3e.offline-retrieval-review",
        "state": "RETRIEVAL_AUTHORITY_HOLD",
        "holdReasons": sorted(holds),
        "offlineResponseSignatureValid": True,
        "offlineChallengeBindingValid": True,
        "offlineCheckpointBindingValid": True,
        "observedCheckpointSequence": claim["checkpointSequence"],
        "minimumSequenceRequested": request["minimumCheckpointSequence"],
        "independentResponderAuthenticated": False,
        "authenticatedRetrievalChannelVerified": False,
        "durableReplayProtectionVerified": False,
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
    raise SystemExit(1)  # No network client, service, signer or Archive authority.
