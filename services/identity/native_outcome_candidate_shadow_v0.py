"""DOC 6 Identity V5 negative-only native command outcome candidate shadow.

A caller-injected, one-shot provider may report a *candidate* history/command
outcome. Invoking that arbitrary provider is NOT necessarily read-only.
The snapshot-only comparator is pure but cannot authenticate source custody,
the original host, an external history head, an operator seat, or C5 consent.
Even a perfect candidate match remains UNKNOWN_HOLD with zero safe actions.

This module has no built-in socket, signer, UI, native client, storage, retry,
reconciliation or IdP operation, but a caller-injected callback can do those
things itself. This is NOT a deployable issuer interface.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Callable

SCHEMA = "post-apollo.identity.outcome-candidate.untrusted-v0"
_ACTIONS = frozenset(("BEGIN", "STATUS", "CANCEL", "RECOVER"))
_RESULTS = frozenset(("CLAIMED_NO_EFFECT", "CLAIMED_COMMITTED",
                      "CLAIMED_ABORTED", "CLAIMED_UNKNOWN"))
_HEX32 = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_CANDIDATE_FIELDS = frozenset((
    "schema", "attemptId", "action", "requestDigest", "nonceDigest",
    "hostInstanceDigest", "seatDigest", "sessionDigest",
    "challengeDigest", "historyDigest", "issuerEpoch",
    "sequence", "claimedResult",
))


class CandidateRefused(ValueError):
    """Malformed original binding: never issue even a diagnostic lookup."""


@dataclass(frozen=True, slots=True)
class OriginalCommandBinding:
    """Expected digests are supplied by caller; this is NOT provenance."""

    attempt_id: str
    action: str
    request_digest: str | None
    nonce_digest: str
    host_instance_digest: str
    seat_digest: str
    session_digest: str
    challenge_digest: str
    history_digest: str
    issuer_epoch: int
    minimum_sequence: int

    def __post_init__(self) -> None:
        if type(self.attempt_id) is not str or not _HEX32.fullmatch(self.attempt_id):
            raise CandidateRefused("Bad original attempt ID")
        if type(self.action) is not str or self.action not in _ACTIONS:
            raise CandidateRefused("Bad original native command action")
        if self.action == "BEGIN":
            if self.request_digest is not None:
                raise CandidateRefused("BEGIN must not select an old request ID")
        elif (type(self.request_digest) is not str
              or not _HEX64.fullmatch(self.request_digest)):
            raise CandidateRefused("Missing host-issued request digest")
        for field in (
            "nonce_digest", "host_instance_digest", "seat_digest",
            "session_digest", "challenge_digest", "history_digest",
        ):
            value = getattr(self, field)
            if type(value) is not str or not _HEX64.fullmatch(value):
                raise CandidateRefused("Invalid original command digest")
        if (type(self.issuer_epoch) is not int or self.issuer_epoch <= 0
                or type(self.minimum_sequence) is not int
                or self.minimum_sequence <= 0):
            raise CandidateRefused("Invalid issuer generation or sequence floor")


@dataclass(frozen=True, slots=True)
class UntrustedOutcomeInspection:
    """No method or field on this type represents settlement or admission."""

    schema: str
    state: str
    reason: str
    lookup_count: int
    safe_actions: tuple[str, ...] = ()
    can_retry: bool = False
    can_begin_sign_in: bool = False
    can_cancel: bool = False
    can_recover: bool = False
    can_connect_provider: bool = False
    original_host_authenticated: bool = False
    original_operator_consented: bool = False
    issuer_reconciled: bool = False
    terminal_receipt_authenticated: bool = False
    production_authority: bool = False


def _held(reason: str, calls: int) -> UntrustedOutcomeInspection:
    return UntrustedOutcomeInspection(
        schema=SCHEMA, state="UNKNOWN_HOLD",
        reason=reason, lookup_count=calls,
    )


def inspect_candidate_once(
    *,
    original: OriginalCommandBinding,
    provider: Callable[[OriginalCommandBinding], object] | None,
) -> UntrustedOutcomeInspection:
    """Legacy CI-only injected callback: execution is NOT guaranteed read-only.

    The arbitrary provider can run any caller-supplied Python; this path is
    retained for existing disposable tests only, not a native recovery consumer.
    Use inspect_supplied_candidate() for callback-free comparison. Neither a
    claimed independent source nor signature makes a terminal result trusted.
    No return value can authorize a command or clear UNKNOWN_HOLD.
    """
    if type(original) is not OriginalCommandBinding:
        raise CandidateRefused("Original native command identity required")
    if provider is None or not callable(provider):
        return _held("INDEPENDENT_PROVIDER_NOT_AVAILABLE", 0)
    try:
        # Deliberately at most one provider invocation. Repeated queries or
        # fallback to a local store cannot be used to settle UNKNOWN.
        candidate = provider(original)
    except Exception:
        return _held("PROVIDER_FAILED_OR_UNAVAILABLE", 1)

    return _inspect_supplied(original, candidate, 1)


def inspect_supplied_candidate(
    *,
    original: OriginalCommandBinding,
    candidate: object,
) -> UntrustedOutcomeInspection:
    """Pure snapshot-only validation; NO external provider execution.

    A caller must already possess the value. This module neither queries nor
    attests its source; lookup_count is always zero in this path.
    Even valid matching candidate contents grant zero authority.
    """
    if type(original) is not OriginalCommandBinding:
        raise CandidateRefused("Original native command identity required")
    if candidate is None:
        return _held("SUPPLIED_CANDIDATE_NOT_AVAILABLE", 0)
    return _inspect_supplied(original, candidate, 0)


def _inspect_supplied(
    original: OriginalCommandBinding, candidate: object, lookups: int,
) -> UntrustedOutcomeInspection:
    # This helper only compares supplied values. It cannot prove that an
    # independently protected issuer supplied or freshly signed anything.
    if type(candidate) is not dict or set(candidate) != _CANDIDATE_FIELDS:
        return _held("MALFORMED_UNTRUSTED_CANDIDATE", lookups)
    if (type(candidate["schema"]) is not str
            or candidate["schema"] != SCHEMA
            or type(candidate["attemptId"]) is not str
            or not _HEX32.fullmatch(candidate["attemptId"])
            or type(candidate["action"]) is not str
            or candidate["action"] not in _ACTIONS
            or type(candidate["claimedResult"]) is not str
            or candidate["claimedResult"] not in _RESULTS
            or type(candidate["issuerEpoch"]) is not int
            or candidate["issuerEpoch"] <= 0
            or type(candidate["sequence"]) is not int
            or candidate["sequence"] <= 0):
        return _held("MALFORMED_UNTRUSTED_CANDIDATE", lookups)

    for field in ("nonceDigest", "hostInstanceDigest", "seatDigest",
                  "sessionDigest", "challengeDigest", "historyDigest"):
        if (type(candidate[field]) is not str
                or not _HEX64.fullmatch(candidate[field])):
            return _held("MALFORMED_UNTRUSTED_CANDIDATE", lookups)
    if (candidate["requestDigest"] is not None
            and (type(candidate["requestDigest"]) is not str
                 or not _HEX64.fullmatch(candidate["requestDigest"]))):
        return _held("MALFORMED_UNTRUSTED_CANDIDATE", lookups)

    comparison = (
        (candidate["attemptId"], original.attempt_id),
        (candidate["action"], original.action),
        (candidate["requestDigest"], original.request_digest),
        (candidate["nonceDigest"], original.nonce_digest),
        (candidate["hostInstanceDigest"], original.host_instance_digest),
        (candidate["seatDigest"], original.seat_digest),
        (candidate["sessionDigest"], original.session_digest),
        (candidate["challengeDigest"], original.challenge_digest),
        (candidate["historyDigest"], original.history_digest),
        (candidate["issuerEpoch"], original.issuer_epoch),
    )
    if (any(actual != expected for actual, expected in comparison)
            or candidate["sequence"] < original.minimum_sequence):
        return _held("CONFLICTING_UNTRUSTED_CANDIDATE", lookups)

    # Even a matching "no effect" is a *self-report*. It cannot justify
    # reissuing an uncertain BEGIN, CANCEL or RECOVER.
    return _held("MATCHED_CLAIM_STILL_UNTRUSTED", lookups)
