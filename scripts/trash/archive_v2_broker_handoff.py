#!/usr/bin/env python3
"""V2n test-only signed request + kernel-peer binding for future broker handoff.

No Unix socket listener, IPC service, key signer, real source reader,
ArchiveStore access, CLI or live activation. Test fixture policies alone
cannot authenticate an actual source owner; all permission fields stay DENY.
"""
import hashlib
import json

from scripts.trash.archive_v2_atomic_admission import (
    admit_fixture_signed_copy,
)
from scripts.trash.archive_v2_owner_trust import (
    canonical_authority,
)
from scripts.trash.archive_v2_peer_evidence import (
    inspect_fixture_peer,
)
from scripts.trash.archive_v2_signed_capture import canonical_claim

SCHEMA = "post-apollo.trashpp.peer-bound-request.v2n"


class BrokerHandoffError(Exception):
    """Safe refusal, no source bytes or process paths."""


def _require(value, code):
    if not value:
        raise BrokerHandoffError(code)


def admit_peer_bound_fixture(
    peer_connection, expected_peer_policy, signed_manifest, pinned_test_root,
    signed_claim, *, ledger, owner_id, resource_id, source_revision,
    source_captured_ms, payload, now_ms, on_stage=None,
    commit_guard=None, expected_peer_witness_sha256=None,
    service_witness_sha256="", service_grant_sha256="",
    service_release_sha256="", origin_witness_sha256="",
    checkpoint_sha256="",
):
    """Bind a live kernel peer witness to a signed TEST copy and its nonce.

    The witness itself is broker-generated; it is not a signer claim.
    A production broker would additionally require a protected service UID,
    pinned source-specific executable AND script/unit integrity, process
    lifetime binding, trusted clock, owner grant, and authorized ArchiveStore.
    """
    evidence = inspect_fixture_peer(peer_connection, expected_peer_policy)
    _require(expected_peer_witness_sha256 is None
             or (type(expected_peer_witness_sha256) is str
                 and expected_peer_witness_sha256 == evidence["peerWitnessSha256"]),
             "BROKER_LIFECYCLE_WITNESS_CHANGED")
    _require(evidence["ownerId"] == owner_id
             and evidence["captureAllowed"] is False,
             "BROKER_OWNER_PEER_MISMATCH")
    _require(type(signed_claim) is dict
             and type(signed_claim.get("claim")) is dict
             and type(signed_manifest) is dict
             and type(signed_manifest.get("manifest")) is dict,
             "BROKER_REQUEST_FORMAT_INVALID")
    claim = signed_claim["claim"]
    manifest = signed_manifest["manifest"]
    encoded_claim = canonical_claim(claim)
    encoded_manifest = canonical_authority(manifest)
    _require(claim["ownerId"] == owner_id
             and claim["resourceId"] == resource_id
             and claim["sourceRevision"] == source_revision
             and claim["sourceCapturedAtMs"] == source_captured_ms,
             "BROKER_REQUEST_SCOPE_MISMATCH")
    _require(type(service_witness_sha256) is str
             and (service_witness_sha256 == ""
                  or (len(service_witness_sha256) == 64
                      and all(c in "0123456789abcdef"
                              for c in service_witness_sha256))),
             "BROKER_SERVICE_WITNESS_INVALID")
    _require(type(service_grant_sha256) is str
             and (service_grant_sha256 == ""
                  or (len(service_grant_sha256) == 64
                      and all(c in "0123456789abcdef"
                              for c in service_grant_sha256)))
             and (service_grant_sha256 == "" or service_witness_sha256 != ""),
             "BROKER_SERVICE_GRANT_INVALID")
    _require(type(service_release_sha256) is str
             and (service_release_sha256 == ""
                  or (len(service_release_sha256) == 64
                      and all(c in "0123456789abcdef"
                              for c in service_release_sha256)))
             and (service_release_sha256 == "" or service_grant_sha256 != ""),
             "BROKER_SERVICE_RELEASE_INVALID")
    _require(type(origin_witness_sha256) is str
             and (origin_witness_sha256 == ""
                  or (len(origin_witness_sha256) == 64
                      and all(c in "0123456789abcdef"
                              for c in origin_witness_sha256)))
             and (origin_witness_sha256 == "" or expected_peer_witness_sha256),
             "BROKER_ORIGIN_WITNESS_INVALID")
    _require(type(checkpoint_sha256) is str
             and (checkpoint_sha256 == ""
                  or (len(checkpoint_sha256) == 64
                      and all(c in "0123456789abcdef"
                              for c in checkpoint_sha256)))
             and (checkpoint_sha256 == "" or service_release_sha256 != ""),
             "BROKER_CHECKPOINT_INVALID")
    claim_hash = hashlib.sha256(encoded_claim).hexdigest()
    authority_hash = hashlib.sha256(encoded_manifest).hexdigest()
    request = {
        "schema":SCHEMA,
        "ownerId":owner_id,
        "resourceId":resource_id,
        "sourceRevision":source_revision,
        "sourceCapturedAtMs":source_captured_ms,
        "payloadSha256":claim["payloadSha256"],
        "nonce":claim["nonce"],
        "claimSha256":claim_hash,
        "authoritySha256":authority_hash,
        "peerWitnessSha256":evidence["peerWitnessSha256"],
    }
    if service_witness_sha256:
        request["serviceWitnessSha256"] = service_witness_sha256
    if service_grant_sha256:
        request["serviceGrantSha256"] = service_grant_sha256
    if service_release_sha256:
        request["serviceReleaseSha256"] = service_release_sha256
    if origin_witness_sha256:
        request["originWitnessSha256"] = origin_witness_sha256
    if checkpoint_sha256:
        request["checkpointSha256"] = checkpoint_sha256
    encoded = json.dumps(request, sort_keys=True, ensure_ascii=True,
                         separators=(",",":"), allow_nan=False)
    binding = hashlib.sha256(encoded.encode("ascii")).hexdigest()
    # V2m checks real Ed25519 fixture signatures and current authority
    # generation, then atomically saves nonce, payload and both digests
    # in one test-only SQLite commit.
    result = admit_fixture_signed_copy(
        signed_manifest, pinned_test_root, signed_claim, ledger=ledger,
        owner_id=owner_id, resource_id=resource_id,
        source_revision=source_revision,
        source_captured_ms=source_captured_ms,
        payload=payload, now_ms=now_ms, on_stage=on_stage,
        peer_witness_sha256=evidence["peerWitnessSha256"],
        request_binding_sha256=binding,
        commit_guard=commit_guard,
        service_witness_sha256=service_witness_sha256,
        service_grant_sha256=service_grant_sha256,
        service_release_sha256=service_release_sha256,
        origin_witness_sha256=origin_witness_sha256,
        checkpoint_sha256=checkpoint_sha256,
    )
    _require(result["peerWitnessSha256"] == evidence["peerWitnessSha256"]
             and result["requestBindingSha256"] == binding,
             "BROKER_BINDING_MISMATCH")
    return {
        "state":"TEST_KERNEL_PEER_BOUND_COPY_DENY_ONLY",
        "snapshotId":result["snapshotId"],
        "ownerId":owner_id,
        "claimSha256":claim_hash,
        "authoritySha256":authority_hash,
        "peerWitnessSha256":evidence["peerWitnessSha256"],
        "requestBindingSha256":binding,
        "serviceWitnessSha256":service_witness_sha256,
        "serviceGrantSha256":service_grant_sha256,
        "serviceReleaseSha256":service_release_sha256,
        "originWitnessSha256":origin_witness_sha256,
        "checkpointSha256":checkpoint_sha256,
        "nonce":claim["nonce"],
        "kernelPeerMatchedFixture":True,
        "payloadIntegrityStored":True,
        "sourceProcessVerified":False,
        "sourceAuthorityVerified":False,
        "humanConsentVerified":False,
        "trustedTimeVerified":False,
        "captureAllowed":False,
        "restoreAllowed":False,
        "burnAllowed":False,
        "productionAllowed":False,
    }
