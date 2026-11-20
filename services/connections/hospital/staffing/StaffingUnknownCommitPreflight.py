#!/usr/bin/env python3
"""Source-only deny-by-default response uncertainty contract for Hospital staffing.

NO production writer, native receipt schema, installed signer, network client,
database, authorization or durable recovery is implemented here. An interrupted
COMMIT may already have executed at the Hospital writer. This module *never*
retries, declares COMMITTED, or accepts an unverified receipt claim.

The supplied stage and observation describe a caller's synthetic test trace;
they are not authenticated process facts or real transaction records.
"""
from __future__ import annotations

import hashlib

import StaffingReceiptIdentityPreflight as Receipt

SCHEMA = "postapollo.connections.hospital.staffing-unknown-commit.ci-v1"
STATUS = "CI_ONLY_UNTRUSTED_COMMIT_OUTCOME"
LOCAL = "LOCAL_BEFORE_SEND"
ATTEMPTED = "SEND_ATTEMPTED"
RESPONSE = "UNVERIFIED_RESPONSE_OBSERVED"

ALLOWED_OBSERVATIONS = {
    LOCAL: frozenset((
        "COMPOSITION_REFUSED", "LOCAL_SCOPE_REFUSED",
        "CANCELLED_BEFORE_SEND",
    )),
    ATTEMPTED: frozenset((
        "SEND_STARTED_NO_ACK", "SEND_EXCEPTION", "TIMEOUT", "DISCONNECT",
        "RECEIPT_TRUNCATED", "RECEIPT_VERSION_UNKNOWN",
        "MALFORMED_REPLY", "WRITER_RESTART",
    )),
    RESPONSE: frozenset(("RESPONSE_BYTES_OBSERVED",)),
}
MAX_REPLY_BYTES = 16384
DENIED = {
    "writerIdentityAuthenticated": False,
    "installedWriterReleaseVerified": False,
    "writerReceiptAuthenticated": False,
    "writerTransactionCommittedVerified": False,
    "writerTransactionRefusedVerified": False,
    "writerAlreadyAppliedVerified": False,
    "hospitalReplayLedgerVerified": False,
    "hospitalNativeReceiptSchemaApproved": False,
    "nativeOperatorAuthorized": False,
    "c5HumanConsentVerified": False,
    "canRetryWithSameGrant": False,
    "canReplayCommit": False,
    "canAttachSession": False,
    "canSucceedDoctor": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class UnknownCommitHold(ValueError):
    """Wrong synthetic trace or request identity, not native recovery."""


def _deny(reason):
    raise UnknownCommitHold("STAFFING_UNKNOWN_COMMIT_HOLD // " + reason)


def inspect_unknown_commit_ci_only(
    *, original_prepare_raw: bytes, prepared_raw: bytes, commit_raw: bytes,
    stage: str, observation: str, unverified_response_raw: bytes | None = None,
):
    """Classify an immutable *CI trace*, never a real writer result.

    Any send attempt may have reached the Hospital writer. An apparently
    successful receipt cannot change that fact without independent trust.
    No native response parser or privileged endpoint consumes this output.
    """
    if (type(stage) is not str or stage not in ALLOWED_OBSERVATIONS
            or type(observation) is not str
            or observation not in ALLOWED_OBSERVATIONS[stage]):
        _deny("UNRECOGNIZED_STAGE_OR_OBSERVATION")
    if stage == RESPONSE:
        if (type(unverified_response_raw) is not bytes
                or not 0 < len(unverified_response_raw) <= MAX_REPLY_BYTES):
            _deny("BOUNDED_RESPONSE_BYTES_REQUIRED")
    elif unverified_response_raw is not None:
        _deny("RESPONSE_BYTES_IN_WRONG_STAGE")

    try:
        original, prepared, _, _grant_digest, _session = Receipt._source_context(
            original_prepare_raw, prepared_raw, commit_raw)
    except (Receipt.ReceiptHold, TypeError, ValueError) as exc:
        raise UnknownCommitHold(
            "STAFFING_UNKNOWN_COMMIT_HOLD // UNTRUSTED_REQUEST_CONTEXT_REFUSED"
        ) from exc

    post_send = stage != LOCAL
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "diagnosticStage": stage,
        "diagnosticObservation": observation,
        "requestNonceFromCallerCI": original["requestNonce"],
        "writerInstanceFromCallerCI": prepared["writerInstance"],
        "commitSha256FromCallerCI": hashlib.sha256(commit_raw).hexdigest(),
        "unverifiedResponseSha256": (
            hashlib.sha256(unverified_response_raw).hexdigest()
            if stage == RESPONSE else None
        ),
        "uncertainty": (
            "POST_SEND_UNKNOWN_MAY_HAVE_COMMITTED"
            if post_send else "NO_SEND_OBSERVED_IN_CALLER_CI_TRACE"
        ),
        "manualHospitalReconciliationNeededInCI": post_send,
        "neverAutoRetryThisGrant": True,
        **DENIED,
    }


def run_native_staffing_recovery(*_args, **_kwargs):
    _deny("NATIVE_HOSPITAL_WRITER_RECOVERY_NOT_INSTALLED")
