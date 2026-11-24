#!/usr/bin/env python3
"""Forest C5 // UNENROLLED writer enrollment + journal custody claim consistency.

This is a deny-only source contract for a future protected evidence producer.
Three Ed25519 signatures are independently checked, but EVERY key and every
journal/enrollment claim comes from the untrusted caller. No operator-enrolled
trust root, protected process/seat, real Forest writer, durable ledger, or C5
issuer is present. NEVER use this result as a settlement/authorization decision.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5TerminalReceiptPreflight as R

ENROLLMENT_SCHEMA = "postapollo.forest.writer-enrollment-claim.v0"
CUSTODY_SCHEMA = "postapollo.forest.journal-custody-claim.v0"
ENROLLER_ROLE = "postapollo.forest.fixture-writer-enroller.v0"
CUSTODIAN_ROLE = "postapollo.forest.fixture-journal-custodian.v0"
ENROLLMENT_FIELDS = frozenset((
    "schema", "audience", "role", "writerKeySha256",
    "writerReleaseSha256", "writerInstance", "enrollmentEpoch",
    "validFromMs", "validUntilMs", "enrollerKeySha256",
))
CUSTODY_FIELDS = frozenset((
    "schema", "audience", "role", "writerKeySha256",
    "writerReleaseSha256", "writerInstance", "enrollmentEpoch",
    "intentSha256", "receiptSha256", "permitId", "storageTxnId",
    "writerJournalCounter", "previousJournalSha256", "terminalOutcome",
    "recordedAtMs", "custodianKeySha256",
))

# No untrusted caller can elevate these outputs by fabricating more signatures.
NO_AUTHORITY = MappingProxyType({
    **R.RECEIPT_NO_AUTHORITY,
    "writerEnrollmentIndependentlyAuthenticated": False,
    "journalCustodianIndependentlyAuthenticated": False,
    "nativeWriterPeerAndSeatVerified": False,
    "historicalWriterKeyRevocationChecked": False,
    "custodyAntirollbackVerified": False,
})


class CustodyHold(ValueError):
    """Untrusted or mismatched writer/journal evidence must remain on HOLD."""


def _hold(reason: str) -> None:
    raise CustodyHold("FOREST_C5_WRITER_CUSTODY_HOLD // " + reason)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _public(public: object, signature: object, label: str) -> str:
    if type(public) is not bytes or len(public) != 32:
        _hold(label + "_PUBLIC_KEY_BOUNDS")
    if type(signature) is not bytes or len(signature) != 64:
        _hold(label + "_SIGNATURE_BOUNDS")
    return _digest(public)


def _signature(public: bytes, signature: bytes, wire: bytes, label: str) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, wire)
    except (InvalidSignature, ValueError):
        pass
    else:
        return
    _hold(label + "_INVALID_SIGNATURE")


def verify_unenrolled_custody_claims(
    intent_wire: bytes, receipt_wire: bytes, writer_signature: bytes,
    writer_public: bytes, enrollment_wire: bytes, enrollment_signature: bytes,
    enroller_public: bytes, custody_wire: bytes, custody_signature: bytes,
    custodian_public: bytes, *, claimed_counter_floor: int,
) -> dict:
    """Validate three *caller-supplied* signed claims without granting authority.

    Production MUST replace caller-controlled roots/history with independently
    operator-enrolled writer identity and protected issuer/journal custody.
    Receipt arrival after the original consent expires is valid for *inspection*
    only. No result here can settle UNKNOWN_HOLD.
    """
    # Reject invalid original intent bytes before hashing or verification.
    if type(intent_wire) is not bytes or not 0 < len(intent_wire) <= S.MAX_WIRE:
        _hold("INTENT_WIRE_BOUNDS")
    try:
        enrollment = S._parse_exact(enrollment_wire, ENROLLMENT_FIELDS)
        custody = S._parse_exact(custody_wire, CUSTODY_FIELDS)
        receipt = S._parse_exact(receipt_wire, R.RECEIPT_FIELDS)

        R._exact_int(claimed_counter_floor, "COUNTER_FLOOR")
        R._exact_text(enrollment["writerInstance"], "WRITER_INSTANCE")
        R._exact_text(custody["writerInstance"], "CUSTODY_WRITER_INSTANCE")
        for record in (enrollment, custody):
            for name in ("writerKeySha256", "writerReleaseSha256"):
                R._exact_sha(record[name], name)
            R._exact_int(record["enrollmentEpoch"], "ENROLLMENT_EPOCH", 1)
        R._exact_sha(enrollment["enrollerKeySha256"], "ENROLLER_KEY")
        R._exact_sha(custody["custodianKeySha256"], "CUSTODIAN_KEY")
        for name in ("validFromMs", "validUntilMs"):
            R._exact_int(enrollment[name], name)
        for name in ("intentSha256", "receiptSha256", "previousJournalSha256"):
            R._exact_sha(custody[name], name)
        for name in ("permitId", "storageTxnId"):
            R._exact_text(custody[name], name)
        for name in ("writerJournalCounter", "recordedAtMs"):
            R._exact_int(custody[name], name, 1)
        R._exact_int(receipt["recordedAtMs"], "RECEIPT_RECORDED_AT")
        if (enrollment["schema"] != ENROLLMENT_SCHEMA or
                enrollment["audience"] != S.AUDIENCE or
                enrollment["role"] != ENROLLER_ROLE or
                custody["schema"] != CUSTODY_SCHEMA or
                custody["audience"] != S.AUDIENCE or
                custody["role"] != CUSTODIAN_ROLE):
            _hold("WRONG_DOMAIN_OR_ROLE")
        if (enrollment["validFromMs"] >= enrollment["validUntilMs"] or
                not enrollment["validFromMs"] <= receipt["recordedAtMs"] <
                enrollment["validUntilMs"]):
            _hold("CLAIMED_WRITER_ENROLLMENT_TIME_MISMATCH")
        if custody["recordedAtMs"] < receipt["recordedAtMs"]:
            _hold("CUSTODY_CLAIM_PREDATES_RECEIPT")
        writer_pin = _public(writer_public, writer_signature, "WRITER")
        enroller_pin = _public(enroller_public, enrollment_signature, "ENROLLER")
        custodian_pin = _public(custodian_public, custody_signature, "CUSTODIAN")
        if len({writer_public, enroller_public, custodian_public}) != 3:
            _hold("THREE_DISTINCT_SIGNER_ROLES_REQUIRED")
        if (writer_pin != enrollment["writerKeySha256"] or
                enroller_pin != enrollment["enrollerKeySha256"] or
                custodian_pin != custody["custodianKeySha256"]):
            _hold("CLAIMED_KEY_PIN_MISMATCH")
        _signature(enroller_public, enrollment_signature, enrollment_wire, "ENROLLMENT")
        _signature(custodian_public, custody_signature, custody_wire, "CUSTODY")
        expected = {
            "writerInstance": enrollment["writerInstance"],
            "enrollmentEpoch": enrollment["enrollmentEpoch"],
            "writerKeySha256": writer_pin,
            "writerReleaseSha256": enrollment["writerReleaseSha256"],
            "intentSha256": _digest(intent_wire),
            "receiptSha256": _digest(receipt_wire),
            "permitId": receipt["permitId"],
            "storageTxnId": receipt["storageTxnId"],
            "writerJournalCounter": receipt["writerJournalCounter"],
            "previousJournalSha256": receipt["previousJournalSha256"],
            "terminalOutcome": receipt["terminalOutcome"],
        }
        for name, value in expected.items():
            if custody[name] != value:
                _hold("CUSTODY_RECEIPT_BINDING_MISMATCH_" + name)
        if (receipt["writerKeySha256"] != writer_pin or
                receipt["commitHostReleaseSha256"] != enrollment["writerReleaseSha256"]):
            _hold("WRITER_ENROLLMENT_RECEIPT_MISMATCH")
        # Reuse the original signed receipt verifier; do not weaken its bounds.
        claim = R.verify_unenrolled_terminal_receipt(
            intent_wire, receipt_wire, writer_signature, writer_public,
            expected_writer_key_sha256=writer_pin,
            expected_previous_journal_sha256=custody["previousJournalSha256"],
            expected_writer_release_sha256=enrollment["writerReleaseSha256"],
            expected_permit_id=custody["permitId"],
            expected_minimum_journal_counter=claimed_counter_floor,
        )
    except (S.EvidenceHold, R.ReceiptHold) as exc:
        refusal = str(exc)
    else:
        refusal = None
    if refusal is not None:
        _hold(refusal)

    return {
        "schema": "postapollo.forest.unenrolled-custody-consistency.v0",
        "status": "THREE_UNENROLLED_SIGNATURE_CLAIMS_CONSISTENT_NOT_SETTLED",
        "claimedReceiptSha256Untrusted": claim["receiptSha256Untrusted"],
        "claimedTerminalOutcomeUntrusted": claim["claimedTerminalOutcomeUntrusted"],
        "claimedJournalCounterUntrusted": claim["claimedJournalCounterUntrusted"],
        "enrollmentAndCustodyRootsCallerControlled": True,
        "claimedWriterEnrollmentUntrusted": True,
        "claimedDurableCustodyUntrusted": True,
        "safeActions": [],
        **NO_AUTHORITY,
    }
