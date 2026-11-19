#!/usr/bin/env python3
"""Deny-only Hospital staffing request/receipt identity and version preflight.

Phase 2 is deliberately NOT a native response verifier. Hospital #133 offers
only a synthetic receipt fixture. This parser compares that fixture with the
original PREPARE and candidate COMMIT. The separate ci-v1 receipt proposal is
an UNAPPROVED future wire shape, never a production claim or writer approval.

No network listener, file/DB write, signer, key store, auth agent or service.
The root-controlled writer, nonce consumption and actual result are Hospital's.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import socket

import StaffingTransportPreflight as Transport

REQUEST_SCHEMA = Transport.REQUEST_SCHEMA
PREPARED_SCHEMA = "postapollo.hospital.native-staffing-prepared.v1"
HOSPITAL_FIXTURE_SCHEMA = "postapollo.hospital.native-staffing-fixture-receipt.v1"
PROPOSED_RECEIPT_SCHEMA = "postapollo.connections.hospital.staffing-receipt-proposal.ci-v1"
PROPOSED_KIND = "source-only-commit-receipt"
PROTOCOL_VERSION = 1
GRANT_DOMAIN = b"post-apollo.hospital.staffing-grant.v1\x00"
PREPARED_FIELDS = frozenset((
    "schema", "requestNonce", "roomId", "action", "expectedRevision",
    "expectedDigest", "writerInstance", "state", "expiresInSeconds",
    "operatorAuthenticated", "requiresExternalConsent",
))
FIXTURE_FIELDS = frozenset((
    "schema", "requestNonce", "roomId", "action", "sessionId",
    "grantDigest", "fixtureTransactionCommitted",
    "nativeInstallationVerified", "operatorAuthenticated",
))
PROPOSED_FIELDS = frozenset((
    "schema", "protocolVersion", "kind", "requestSchema",
    "requestNonce", "roomId", "action", "sessionId",
    "writerInstance", "expectedRevision", "revisionAfter",
    "graphDigest", "grantDigest", "originalPrepareSha256",
    "commitSha256", "status",
))
STATUS = "CI_RECEIPT_IDENTITY_FORMAT_ONLY_NOT_AUTHORIZED"
PROPOSED_STATUS = "UNVERIFIED_PROPOSAL_ONLY"
SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)

DENIED = {
    "hospitalNativeReceiptSchemaApproved": False,
    "independentlyAuthenticatedHospitalWriter": False,
    "installedWriterReleaseVerified": False,
    "writerReceiptCryptographicallyVerified": False,
    "writerTransactionCommittedVerified": False,
    "hospitalPersistentReplayProtectionVerified": False,
    "nativeOperatorAuthorized": False,
    "c5HumanConsentVerified": False,
    "canApprove": False,
    "canAttachSession": False,
    "canSucceedDoctor": False,
    "productionAuthority": False,
    "credentialActionsEnabled": False,
}


class ReceiptHold(RuntimeError):
    """A read-only receipt shape, source identity, or version was refused."""


def _hold(reason):
    raise ReceiptHold("CONNECTIONS_STAFFING_RECEIPT_HOLD // " + reason)


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _exact(raw, fields, maximum=Transport.MAX_FRAME):
    try:
        parsed = Transport._exact_json(raw, maximum)
    except Transport.PreflightHold as exc:
        raise ReceiptHold("CONNECTIONS_STAFFING_RECEIPT_HOLD // NONCANONICAL_RECORD") from exc
    if set(parsed) != fields:
        _hold("UNEXPECTED_OR_MISSING_RECORD_FIELDS")
    return parsed


def _source_context(original_prepare_raw, prepared_raw, commit_raw):
    """Correlate three CI records, without promoting supplied bytes to truth."""
    try:
        original = Transport.parse_original_prepare(original_prepare_raw)
    except Transport.PreflightHold as exc:
        raise ReceiptHold("CONNECTIONS_STAFFING_RECEIPT_HOLD // ORIGINAL_PREPARE_REFUSED") from exc
    prepared = _exact(prepared_raw, PREPARED_FIELDS)
    if (prepared["schema"] != PREPARED_SCHEMA
            or prepared["requestNonce"] != original["requestNonce"]
            or prepared["roomId"] != original["roomId"]
            or prepared["action"] != original["action"]
            or prepared["state"] != "ACTIVE"
            or prepared["operatorAuthenticated"] is not False
            or prepared["requiresExternalConsent"] is not True
            or type(prepared["expectedRevision"]) is not int
            or not 0 <= prepared["expectedRevision"] < 1_000_000_000
            or type(prepared["expectedDigest"]) is not str
            or SHA256.fullmatch(prepared["expectedDigest"]) is None
            or type(prepared["expiresInSeconds"]) is not int
            or not 0 < prepared["expiresInSeconds"] <= 45):
        _hold("UNTRUSTED_OR_CHANGED_PREPARED_SOURCE")
    writer_instance = prepared["writerInstance"]
    if (type(writer_instance) is not str
            or Transport.WRITER.fullmatch(writer_instance) is None):
        _hold("INVALID_WRITER_INSTANCE")
    commit = _exact(commit_raw, Transport.COMMIT_FIELDS)
    if (commit.get("schema") != REQUEST_SCHEMA
            or commit.get("kind") != Transport.COMMIT
            or commit.get("action") != original["action"]
            or commit.get("roomId") != original["roomId"]
            or commit.get("requestNonce") != original["requestNonce"]
            or commit.get("intent") != original["intent"]
            or commit.get("writerInstance") != writer_instance):
        _hold("PREPARE_COMMIT_IDENTITY_CHANGED")
    try:
        # Byte-for-byte recompose using accepted Phase 1 framing rules;
        # the signature is shape-checked, NOT authenticated.
        encoded = commit["signedEnvelope"]
        if type(encoded) is not str or not encoded or "=" in encoded:
            _hold("INVALID_SIGNED_ENVELOPE_ENCODING")
        envelope = base64.urlsafe_b64decode(encoded + "="*(-len(encoded) % 4))
        if base64.urlsafe_b64encode(envelope).rstrip(b"=").decode("ascii") != encoded:
            _hold("NONCANONICAL_SIGNED_ENVELOPE")
        recomposed = Transport.compose_commit(
            original_prepare_raw, writer_instance, envelope)
    except (Transport.PreflightHold, ValueError, TypeError) as exc:
        raise ReceiptHold("CONNECTIONS_STAFFING_RECEIPT_HOLD // COMMIT_RECOMPOSITION_REFUSED") from exc
    if recomposed != commit_raw:
        _hold("COMMIT_NOT_ORIGINAL_PREPARE")
    signed = _exact(envelope, frozenset(("body", "signature")), Transport.MAX_GRANT_BYTES)
    body = signed["body"]
    if type(body) is not dict:
        _hold("INVALID_SIGNED_BODY")
    grant_digest = _digest(GRANT_DOMAIN + Transport.canonical(body))
    session_id = (original["intent"]["sessionId"]
                  if original["action"] == "SESSION_ATTACH"
                  else original["intent"]["newSessionId"])
    return original, prepared, commit, grant_digest, session_id


def inspect_hospital_fixture_receipt_ci_only(
        *, original_prepare_raw: bytes, prepared_raw: bytes,
        commit_raw: bytes, fixture_receipt_raw: bytes):
    """Match Hospital #133's fixture, explicitly NOT a native receipt."""
    original, prepared, _, grant_digest, session_id = _source_context(
        original_prepare_raw, prepared_raw, commit_raw)
    receipt = _exact(fixture_receipt_raw, FIXTURE_FIELDS)
    expected = {
        "schema": HOSPITAL_FIXTURE_SCHEMA,
        "requestNonce": original["requestNonce"],
        "roomId": original["roomId"],
        "action": original["action"],
        "sessionId": session_id,
        "grantDigest": grant_digest,
        "fixtureTransactionCommitted": True,
        "nativeInstallationVerified": False,
        "operatorAuthenticated": False,
    }
    if receipt != expected or any(
            type(receipt[x]) is not bool
            for x in ("fixtureTransactionCommitted",
                      "nativeInstallationVerified", "operatorAuthenticated")):
        _hold("HOSPITAL_FIXTURE_RECEIPT_MISMATCH")
    return {
        "status": STATUS,
        "sourceOnlyHospitalFixtureMatchesCurrentInputs": True,
        "fixtureLacksWriterInstanceAndCommitDigest": True,
        "untrustedSourceRevision": prepared["expectedRevision"],
        "untrustedRequestNonce": original["requestNonce"],
        **DENIED,
    }


def inspect_proposed_receipt_ci_only(
        *, original_prepare_raw: bytes, prepared_raw: bytes,
        commit_raw: bytes, proposed_receipt_raw: bytes):
    """Proposed v1 byte binding; Hospital has NOT accepted this wire schema.

    Any caller able to fabricate both the proposed receipt and its expectations
    can get a syntactic match; NEVER turn this result into a native receipt.
    """
    original, prepared, _, grant_digest, session_id = _source_context(
        original_prepare_raw, prepared_raw, commit_raw)
    proposed = _exact(proposed_receipt_raw, PROPOSED_FIELDS)
    expected = {
        "schema": PROPOSED_RECEIPT_SCHEMA,
        "protocolVersion": PROTOCOL_VERSION,
        "kind": PROPOSED_KIND,
        "requestSchema": REQUEST_SCHEMA,
        "requestNonce": original["requestNonce"],
        "roomId": original["roomId"],
        "action": original["action"],
        "sessionId": session_id,
        "writerInstance": prepared["writerInstance"],
        "expectedRevision": prepared["expectedRevision"],
        "revisionAfter": prepared["expectedRevision"] + 1,
        "graphDigest": prepared["expectedDigest"],
        "grantDigest": grant_digest,
        "originalPrepareSha256": _digest(original_prepare_raw),
        "commitSha256": _digest(commit_raw),
        "status": PROPOSED_STATUS,
    }
    if type(proposed["protocolVersion"]) is not int or proposed != expected:
        _hold("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH")
    return {
        "status": STATUS,
        "proposedReceiptMatchesProvidedSourceBytesInCI": True,
        "candidateReceiptSha256": _digest(proposed_receipt_raw),
        "untrustedWriterInstance": prepared["writerInstance"],
        **DENIED,
    }


def inspect_proposed_receipt_kernel_packet_ci_only(
        sock: socket.socket, *, expected_uid: int,
        original_prepare_raw: bytes, prepared_raw: bytes, commit_raw: bytes):
    """Actual kernel packet observation, supplied expected UID is NOT enrolled."""
    try:
        packet, peer = Transport.observe_kernel_packet(
            sock, expected_uid=expected_uid)
    except Transport.PreflightHold as exc:
        raise ReceiptHold("CONNECTIONS_STAFFING_RECEIPT_HOLD // KERNEL_SENDER_REFUSED") from exc
    result = inspect_proposed_receipt_ci_only(
        original_prepare_raw=original_prepare_raw,
        prepared_raw=prepared_raw, commit_raw=commit_raw,
        proposed_receipt_raw=packet)
    result["observedKernelPeerInCI"] = {
        "pid": peer[0], "uid": peer[1], "gid": peer[2]}
    return result


def run_native_staffing_receipt_verifier(*_args, **_kwargs):
    """No production verifier/authorization exists on this branch."""
    _hold("NATIVE_WRITER_RECEIPT_AUTHORITY_NOT_INSTALLED")
