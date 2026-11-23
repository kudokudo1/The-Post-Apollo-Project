#!/usr/bin/env python3
"""Forest C5 storage-independent authority contract (DENY ONLY).

The reviewed Forest B4c consumer owns its persisted attempt; DOC 1's C3e
storage-neutral *test* client is not an independent C5 custodian. No installed
Forest writer/root, protected issuer, human consent, journal or transport exists
here. This module performs only optional CI/reference binding diagnostics.
ALL protected operations fail closed, without a local SQLite or mock fallback.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5TerminalReceiptPreflight as R

SCHEMA = "postapollo.forest.c5-authority-boundary.v0"
MODE_REFERENCE = "FOREST_CONTRACT_REFERENCE_ONLY"
MODE_PROTECTED = "INDEPENDENT_FOREST_CUSTODIAN_REQUIRED"
STATUS_HOLD = "INDEPENDENT_FOREST_CUSTODIAN_UNAVAILABLE_HOLD"
STATUS_REFERENCE = "UNTRUSTED_FOREST_BINDING_MATCHES_SESSION_UNSIGNED_HOLD"
BINDING_FIELDS = frozenset((
    "owner_key", "tree_key", "session_id", "user_turn_id", "attempt_id",
    "request_id", "model_key", "expected_revision",
))
# The missing signed session_id is an integration question for the Forest
# backend/Connections owners, not authorization to change their source.
SIGNED_EQUIVALENTS = MappingProxyType({
    "owner_key": "principal",
    "tree_key": "tree",
    "user_turn_id": "userTurn",
    "attempt_id": "attempt",
    "request_id": "request",
    "model_key": "model",
    "expected_revision": "revision",
})
NO_AUTHORITY = MappingProxyType({
    **S.NO_AUTHORITY,
    **R.RECEIPT_NO_AUTHORITY,
    "independentForestCustodianAuthenticated": False,
    "forestCurrentTrustHeadAuthenticated": False,
    "forestGrantRevocationSerialized": False,
    "forestProtectedPermitIssued": False,
    "forestWriterJournalCustodyVerified": False,
    "forestSessionIdentitySigned": False,
    "forestProtectedTerminalReconciled": False,
})


class ForestC5Hold(ValueError):
    """The only public error for missing/unsafe protected authority."""


def _deny(reason: str) -> None:
    raise ForestC5Hold("FOREST_C5_AUTHORITY_HOLD // " + reason)


def _ident(value: object, label: str) -> None:
    if type(value) is not str or S.IDENTIFIER.fullmatch(value) is None:
        _deny("INVALID_" + label)


class ForestC5AuthorityBoundary:
    """Storage-neutral semantic boundary with NO authorized backend adapter.

    A protected custodian cannot be introduced by passing an arbitrary object,
    endpoint, development DB, or caller-selected root. Adding a real transport
    needs a separate owner-approved implementation, exact-head review and
    operator acceptance. This class intentionally never grants a permit.
    """

    def __init__(self, *, required_mode: str, backend=None, local_ledger=None,
                 remote_endpoint=None, trusted_root=None):
        if type(required_mode) is not str or required_mode not in (
                MODE_REFERENCE, MODE_PROTECTED):
            _deny("UNKNOWN_TRUST_MODE")
        if any(value is not None for value in (
                backend, local_ledger, remote_endpoint, trusted_root)):
            _deny("CALLER_PROVIDED_TRUST_SOURCE_REFUSED")
        self._mode = required_mode

    def status(self) -> dict:
        """Return a diagnostic, never a current-head or authority proof."""
        return {
            "schema": SCHEMA,
            "status": STATUS_HOLD,
            "requiredMode": self._mode,
            "safeActions": [],
            **dict(NO_AUTHORITY),
        }

    def inspect_reference_binding(self, intent_wire: bytes,
                                  forest_binding: dict) -> dict:
        """Compare B4c's 8 persisted fields to a C5 intent for CI ONLY.

        Even a complete match is not proof of the actual persisted DB row:
        the caller supplies BOTH objects. Additionally, the signed intent
        lacks B4c's session_id, so the original exact Forest session cannot
        be cryptographically bound. No root, owner or source is trusted.
        """
        if self._mode != MODE_REFERENCE:
            _deny("PROTECTED_MODE_REFUSES_UNTRUSTED_REFERENCE_INSPECTION")
        if type(forest_binding) is not dict or set(forest_binding) != BINDING_FIELDS:
            _deny("EXACT_FOREST_BINDING_FIELDS_REQUIRED")
        for name in (
                "owner_key", "tree_key", "session_id", "user_turn_id",
                "attempt_id", "request_id"):
            _ident(forest_binding[name], name)
        if not 16 <= len(forest_binding["request_id"]) <= 96:
            _deny("FOREST_REQUEST_ID_LENGTH_MISMATCH")
        if (type(forest_binding["model_key"]) is not str or
                S.MODEL.fullmatch(forest_binding["model_key"]) is None):
            _deny("INVALID_MODEL_KEY")
        if (type(forest_binding["expected_revision"]) is not int or
                not 0 <= forest_binding["expected_revision"] < 2**63):
            _deny("INVALID_EXPECTED_REVISION")
        try:
            original = S._parse_exact(intent_wire, S.INTENT_FIELDS)
            intent, intent_sha = S._intent(
                intent_wire, now_ms=original["issuedAtMs"]
            )
        except (S.EvidenceHold, TypeError, KeyError) as exc:
            raise ForestC5Hold(
                "FOREST_C5_AUTHORITY_HOLD // UNTRUSTED_INTENT_INVALID"
            ) from exc
        for field, intended in SIGNED_EQUIVALENTS.items():
            if forest_binding[field] != intent[intended]:
                _deny("REFERENCE_BINDING_MISMATCH_" + field)
        # Do NOT manufacture an attested session ID or use a Tree as a
        # session substitute. Reference equality does not settle C5.
        return {
            "schema": SCHEMA,
            "status": STATUS_REFERENCE,
            "requiredMode": self._mode,
            "intentSha256ObservedUntrusted": intent_sha,
            "forestBindingSha256ObservedUntrusted": hashlib.sha256(
                S.canonical_bytes(forest_binding)).hexdigest(),
            "signedIntentMissingForestSessionId": True,
            "bindingSourceCallerControlled": True,
            "safeActions": [],
            **dict(NO_AUTHORITY),
        }

    def read_current_trust_snapshot(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_NO_LOCAL_FALLBACK")

    def prepare_generate(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_NO_PREPARE")

    def acquire_commit_permit(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_NO_PERMIT")

    def lookup_terminal_outcome(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_UNKNOWN_HOLD")

    def settle_terminal_receipt(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_NO_SETTLEMENT")

    def request_revocation(self, *_args, **_kwargs):
        _deny("INDEPENDENT_CUSTODIAN_REQUIRED_NO_REVOCATION_ACK")

    def authorize_read_session(self, *_args, **_kwargs):
        _deny("READ_SESSION_SEPARATE_PROTECTED_POLICY_REQUIRED")

    def authorize_tool_execution(self, *_args, **_kwargs):
        _deny("FOREST_TOOL_EXECUTION_DISABLED")

    def production_admission(self, *_args, **_kwargs):
        _deny("FOREST_C5_PRODUCTION_AUTHORITY_HOLD")
