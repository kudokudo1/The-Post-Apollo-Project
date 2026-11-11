#!/usr/bin/env python3
"""V2m FIXTURE-ONLY atomic signed capture-admission orchestrator.

This intentionally has NO CLI, NO live signer, NO Quickshell, and NO
ArchiveStore import. It proves crash/nonce/payload atomicity inside an
explicit synthetic 0700 test SQLite root, not the production Archive DB.
"""
import hashlib

from scripts.trash.archive_v2_owner_trust import (
    OwnerTrustError, verify_fixture_authority,
)
from scripts.trash.archive_v2_signed_capture import (
    SignedCaptureError, verify_test_proof,
)
from scripts.trash.archive_v2_trust_history import (
    TestOwnerTrustHistory,
)


class AtomicAdmissionError(Exception):
    """Bounded, payload-free rejection code."""


def _require(condition, code):
    if not condition:
        raise AtomicAdmissionError(code)


def admit_fixture_signed_copy(
    signed_manifest, pinned_test_root, signed_claim, *, ledger, owner_id,
    resource_id, source_revision, source_captured_ms, payload, now_ms,
    on_stage=None, peer_witness_sha256="", request_binding_sha256="",
    commit_guard=None, service_witness_sha256="",
    service_grant_sha256="", service_release_sha256="",
    origin_witness_sha256="", checkpoint_sha256="",
):
    """Verify fixture root+owner proof before atomic nonce+test-copy commit.

    A real source owner must independently validate the source process and
    owner-granted permissions; caller inputs here are synthetic fixtures.
    """
    _require(type(ledger) is TestOwnerTrustHistory,
             "TEST_ADMISSION_LEDGER_REQUIRED")
    _require(type(payload) is bytes and 0 < len(payload) <= 8*1024*1024,
             "TEST_ADMISSION_PAYLOAD_INVALID")
    _require(type(source_captured_ms) is int and source_captured_ms > 0,
             "TEST_ADMISSION_SOURCE_TIME_INVALID")
    _require(type(signed_claim) is dict
             and type(signed_claim.get("claim")) is dict
             and signed_claim["claim"].get("sourceCapturedAtMs")
                 == source_captured_ms,
             "TEST_ADMISSION_SOURCE_TIME_MISMATCH")
    digest = hashlib.sha256(payload).hexdigest()
    authority = verify_fixture_authority(
        signed_manifest, pinned_test_root, now_ms=now_ms)
    _require(authority["ownerId"] == owner_id
             and authority["sourceAuthorityVerified"] is False
             and authority["captureAllowed"] is False,
             "TEST_ADMISSION_OWNER_REFUSED")
    signed = verify_test_proof(
        signed_claim, authority["policy"], owner_id=owner_id,
        resource_id=resource_id, source_revision=source_revision,
        payload_sha256=digest, now_ms=now_ms)
    _require(signed["signatureVerified"] is True
             and signed["captureAllowed"] is False
             and signed["replayConsumed"] is False,
             "TEST_ADMISSION_EVIDENCE_INVALID")
    # The same test SQLite BEGIN IMMEDIATE now checks the enrolled
    # authority floor and inserts BOTH nonce and payload/receipt.
    result = ledger.admit_test_copy(
        authority, signed, payload, resource_id=resource_id,
        source_revision=source_revision,
        source_captured_ms=source_captured_ms,
        payload_sha256=digest, on_stage=on_stage,
        peer_witness_sha256=peer_witness_sha256,
        request_binding_sha256=request_binding_sha256,
        commit_guard=commit_guard,
        service_witness_sha256=service_witness_sha256,
        service_grant_sha256=service_grant_sha256,
        service_release_sha256=service_release_sha256,
        origin_witness_sha256=origin_witness_sha256,
        checkpoint_sha256=checkpoint_sha256)
    # This represents a committed TEST fixture, not any authorized real copy.
    return {"state":result["state"],
            "snapshotId":result["snapshotId"],
            "proofSha256":result["proofSha256"],
            "authoritySha256":result["authoritySha256"],
            "payloadSha256":result["payloadSha256"],
            "nonce":result["nonce"],
            "peerWitnessSha256":result["peerWitnessSha256"],
            "requestBindingSha256":result["requestBindingSha256"],
            "serviceWitnessSha256":result["serviceWitnessSha256"],
            "serviceGrantSha256":result["serviceGrantSha256"],
            "serviceReleaseSha256":result["serviceReleaseSha256"],
            "originWitnessSha256":result["originWitnessSha256"],
            "checkpointSha256":result["checkpointSha256"],
            "receiptIsTestOnly":True,
            "sourceProcessVerified":False,
            "trustedTimeVerified":False,
            "sourceAuthorityVerified":False,
            "humanConsentVerified":False,
            "captureAllowed":False,
            "productionAllowed":False,
            "restoreAllowed":False,
            "burnAllowed":False}
