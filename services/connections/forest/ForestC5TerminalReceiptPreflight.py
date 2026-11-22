#!/usr/bin/env python3
"""Forest B4c // untrusted signed terminal receipt consistency (NO AUTHORITY).

This source has NO installed or independently enrolled writer root, C5 issuer,
native Forest writer, durable journal, actual COMMIT proof, operator presence,
socket, key custody, signer, database, or production actions. Callers supply
the expected key/pins and predecessor values; test results can be forged.
A valid signature shows only byte consistency with those supplied inputs.
"""
from __future__ import annotations

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from services.connections.forest import ForestC5SignedEvidencePreflight as S

RECEIPT_SCHEMA = "postapollo.forest.commit-terminal-receipt.v0"
WRITER_ROLE = "postapollo.forest.commit-writer.v1"
TERMINAL_OUTCOMES = frozenset(("COMMIT_CONFIRMED", "ROLLBACK_CONFIRMED"))
RECEIPT_FIELDS = frozenset((
    "schema", "audience", "role", "intentSha256", "permitId", "attempt",
    "grant", "request", "principal", "tree", "model", "revision",
    "consentEpoch", "challenge", "commitHostReleaseSha256",
    "writerKeySha256", "writerJournalCounter", "previousJournalSha256",
    "terminalOutcome", "storageTxnId", "recordedAtMs",
))
RECEIPT_NO_AUTHORITY = {
    "writerRootIndependentlyEnrolled": False,
    "protectedWriterProcessAuthenticated": False,
    "writerJournalDurabilityVerified": False,
    "terminalOutcomeAuthenticated": False,
    "c5RevocationFenceSettled": False,
    "c5HumanConsentVerified": False,
    "forestDatabaseCommitAllowed": False,
    "forestReadSessionAllowed": False,
    "forestToolExecutionAllowed": False,
    "productionAuthority": False,
}


class ReceiptHold(ValueError):
    """A signed fixture is not a protected native terminal receipt."""


def _hold(reason: str) -> None:
    raise ReceiptHold("FOREST_B4C_WRITER_RECEIPT_HOLD // " + reason)


def _exact_text(value: object, field: str) -> None:
    if type(value) is not str or S.IDENTIFIER.fullmatch(value) is None:
        _hold("INVALID_" + field)


def _exact_sha(value: object, field: str) -> None:
    if type(value) is not str or S.HEX64.fullmatch(value) is None:
        _hold("INVALID_" + field)


def _exact_int(value: object, field: str, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value < 2**63:
        _hold("INVALID_" + field)


def verify_unenrolled_terminal_receipt(
    intent_wire: bytes,
    receipt_wire: bytes,
    writer_signature: bytes,
    writer_public: bytes,
    *,
    expected_writer_key_sha256: str,
    expected_previous_journal_sha256: str,
    expected_writer_release_sha256: str,
    expected_permit_id: str,
    expected_minimum_journal_counter: int,
) -> dict:
    """Diagnostic matching of UNTRUSTED inputs, never a commit ACK.

    The caller supplying the pins/seq is *not* a protected root/issuer. The
    output intentionally excludes any actionable or durable settlement state.
    A production issuer must obtain pins/history from its independently
    protected custody, authenticate the exact writer process and verify that
    the writer's journal result was persisted after actual SQLite COMMIT.
    """
    _exact_sha(expected_writer_key_sha256, "EXPECTED_WRITER_KEY")
    _exact_sha(expected_previous_journal_sha256, "EXPECTED_PREVIOUS_JOURNAL")
    _exact_sha(expected_writer_release_sha256, "EXPECTED_WRITER_RELEASE")
    _exact_text(expected_permit_id, "EXPECTED_PERMIT")
    _exact_int(expected_minimum_journal_counter, "EXPECTED_COUNTER_FLOOR")

    # Terminal outcome may be received after the original consent expires.
    # Validate the signed intent's structure and original lease rather than
    # incorrectly refusing reconciliation solely because time has advanced.
    try:
        original = S._parse_exact(intent_wire, S.INTENT_FIELDS)
        original, original_digest = S._intent(
            intent_wire, now_ms=original["issuedAtMs"]
        )
        receipt = S._parse_exact(receipt_wire, RECEIPT_FIELDS)
    except S.EvidenceHold as exc:
        # One public fail-closed exception contract for all receipt inputs.
        raise ReceiptHold("FOREST_B4C_WRITER_RECEIPT_HOLD // " + str(exc)) from exc
    if (receipt["schema"] != RECEIPT_SCHEMA or
            receipt["audience"] != S.AUDIENCE or
            receipt["role"] != WRITER_ROLE):
        _hold("WRONG_WRITER_DOMAIN")
    if type(receipt["terminalOutcome"]) is not str:
        _hold("OUTCOME_TYPE")
    if receipt["terminalOutcome"] not in TERMINAL_OUTCOMES:
        _hold("NONTERMINAL_OR_FORGED_OUTCOME")
    for field in ("permitId", "attempt", "grant", "request",
                  "principal", "tree", "challenge", "storageTxnId"):
        _exact_text(receipt[field], field)
    if type(receipt["model"]) is not str or S.MODEL.fullmatch(receipt["model"]) is None:
        _hold("INVALID_MODEL")
    for field in ("intentSha256", "commitHostReleaseSha256",
                  "writerKeySha256", "previousJournalSha256"):
        _exact_sha(receipt[field], field)
    for field in ("revision", "recordedAtMs"):
        _exact_int(receipt[field], field)
    for field in ("consentEpoch", "writerJournalCounter"):
        _exact_int(receipt[field], field, 1)

    expected_exact = {
        "intentSha256": original_digest,
        "permitId": expected_permit_id,
        "attempt": original["attempt"],
        "grant": original["grant"],
        "request": original["request"],
        "principal": original["principal"],
        "tree": original["tree"],
        "model": original["model"],
        "revision": original["revision"],
        "consentEpoch": original["consentEpoch"],
        "challenge": original["challenge"],
        "commitHostReleaseSha256": original["commitHostReleaseSha256"],
        "writerKeySha256": expected_writer_key_sha256,
        "previousJournalSha256": expected_previous_journal_sha256,
    }
    for field, trusted_fixture_value in expected_exact.items():
        if receipt[field] != trusted_fixture_value:
            _hold("EXACT_RECEIPT_BINDING_MISMATCH_" + field)
    if receipt["commitHostReleaseSha256"] != expected_writer_release_sha256:
        _hold("WRITER_RELEASE_MISMATCH")
    if (receipt["writerJournalCounter"] <= expected_minimum_journal_counter or
            receipt["recordedAtMs"] < original["issuedAtMs"]):
        _hold("STALE_JOURNAL_OR_TIME")

    if type(writer_public) is not bytes or len(writer_public) != 32:
        _hold("WRITER_PUBLIC_KEY_BOUNDS")
    if type(writer_signature) is not bytes or len(writer_signature) != 64:
        _hold("WRITER_SIGNATURE_BOUNDS")
    observed_pin = hashlib.sha256(writer_public).hexdigest()
    if observed_pin != expected_writer_key_sha256:
        _hold("UNPINNED_WRITER_KEY")
    try:
        Ed25519PublicKey.from_public_bytes(writer_public).verify(
            writer_signature, receipt_wire)
    except (InvalidSignature, ValueError) as exc:
        raise ReceiptHold(
            "FOREST_B4C_WRITER_RECEIPT_HOLD // INVALID_SIGNATURE"
        ) from exc
    return {
        "schema": "postapollo.forest.unenrolled-terminal-consistency.v0",
        "status": "UNENROLLED_RECEIPT_SIGNATURE_CONSISTENT_NOT_SETTLED",
        "receiptSha256Untrusted": hashlib.sha256(receipt_wire).hexdigest(),
        "intentSha256Untrusted": original_digest,
        "claimedTerminalOutcomeUntrusted": receipt["terminalOutcome"],
        "claimedJournalCounterUntrusted": receipt["writerJournalCounter"],
        "fixturePinsCallerControlled": True,
        "safeActions": [],
        **RECEIPT_NO_AUTHORITY,
    }
