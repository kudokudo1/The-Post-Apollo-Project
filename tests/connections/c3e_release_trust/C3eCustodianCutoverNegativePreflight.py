#!/usr/bin/env python3
"""DOC 1: pure, deny-only CI classifier for local→independent cutover candidates.

A *format-consistent candidate* is NOT an independently enrolled custodian.
This module does not copy/reopen SQLite, contact an NAS, enroll a real key,
verify a protected transport or grant authority. The future custodian must
create a truly new genesis/key hierarchy under separately approved ownership.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_CUTOVER_EXISTING_BOUNDARY_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S = _load("c3e_cutover_existing_storage_boundary",
          HERE / "C3eStorageIndependentTrustBoundary.py")

SCHEMA = "postapollo.connections.c3e-cutover-candidate-deny-only.ci-v1"
CANDIDATE_SCHEMA = "postapollo.connections.c3e-future-custodian-candidate.ci-v1"
PURPOSE = "postapollo.connections.identity-protected-custodian-migration-ci-only"
CANDIDATE = "UNENROLLED_CANDIDATE_NOT_A_CUSTODIAN"
HOLD = "CUTOVER_HOLD_NO_INDEPENDENT_TRUST"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
HEX32 = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)

CANDIDATE_FIELDS = frozenset((
    "schema", "purpose", "status", "hostId",
    "rootPublicKeySha256", "historySignerSha256",
    "newEpoch", "newGenesisHeadSha256", "newSequence",
    "importedChallengeDigests",
))
LOCAL_FIELDS = frozenset((
    "schema", "status", "source", "testHeadSha256", "testSequence",
    *S.DENIED,
))
DENIED = {
    **S.DENIED,
    "candidateCustodianEnrolled": False,
    "operatorRootPinnedOutOfBand": False,
    "independentHistoryCurrent": False,
    "independentChallengeStateCurrent": False,
    "custodianTransportAuthenticated": False,
    "localHistoryPromotedToAuthority": False,
    "cutoverAuthorized": False,
}


class Refused(ValueError):
    """Malformed candidate, unsafe state transfer or fake authority claim."""


def deny(code):
    raise Refused(code)


def _hex64(value):
    return type(value) is str and HEX64.fullmatch(value) is not None


def _fingerprints(values, *, code):
    if type(values) not in (tuple, list) or len(values) > 32:
        deny(code)
    if any(not _hex64(v) for v in values) or len(set(values)) != len(values):
        deny(code)
    return set(values)


def inspect_candidate_ci_only(
    *, local_snapshot: dict, candidate: dict,
    known_development_role_fingerprints: tuple,
    known_development_epochs: tuple,
    locally_issued_challenge_digests: tuple,
) -> dict:
    """Check only synthetic separation, never a real protected authority.

    Inputs are ALL caller-supplied fixtures. We can reject obvious promotion
    but cannot prove independence or exhaustive key/challenge inventory.
    """
    if type(local_snapshot) is not dict or set(local_snapshot) != LOCAL_FIELDS:
        deny("C3E_CUTOVER_LOCAL_EXACT_FIELDS_REQUIRED")
    if (local_snapshot["schema"] != S.SCHEMA
            or local_snapshot["status"] != S.STATUS_LOCAL
            or local_snapshot["source"] != S.LOCAL_DEVELOPMENT
            or not _hex64(local_snapshot["testHeadSha256"])
            or type(local_snapshot["testSequence"]) is not int
            or local_snapshot["testSequence"] < 1):
        deny("C3E_CUTOVER_LOCAL_SNAPSHOT_NOT_UNTRUSTED_FIXTURE")
    if any(local_snapshot[key] is not False for key in S.DENIED):
        deny("C3E_CUTOVER_LOCAL_AUTHORITY_INJECTION")

    known_keys = _fingerprints(
        known_development_role_fingerprints,
        code="C3E_CUTOVER_LOCAL_ROLE_FINGERPRINTS_INVALID",
    )
    old_challenges = _fingerprints(
        locally_issued_challenge_digests,
        code="C3E_CUTOVER_OLD_CHALLENGE_ROSTER_INVALID",
    )
    if (type(known_development_epochs) not in (tuple, list)
            or len(known_development_epochs) > 32
            or any(type(x) is not str or HEX32.fullmatch(x) is None
                   for x in known_development_epochs)
            or len(set(known_development_epochs)) != len(known_development_epochs)):
        deny("C3E_CUTOVER_LOCAL_EPOCH_ROSTER_INVALID")

    if type(candidate) is not dict or set(candidate) != CANDIDATE_FIELDS:
        deny("C3E_CUTOVER_CANDIDATE_EXACT_FIELDS_REQUIRED")
    if (candidate["schema"] != CANDIDATE_SCHEMA
            or candidate["purpose"] != PURPOSE
            or candidate["status"] != CANDIDATE
            or type(candidate["hostId"]) is not str
            or not 0 < len(candidate["hostId"]) <= 128
            or any(ord(c) < 33 or ord(c) > 126 for c in candidate["hostId"])):
        deny("C3E_CUTOVER_CANDIDATE_DOMAIN_OR_HOST_INVALID")
    if (not _hex64(candidate["rootPublicKeySha256"])
            or not _hex64(candidate["historySignerSha256"])
            or not _hex64(candidate["newGenesisHeadSha256"])
            or type(candidate["newEpoch"]) is not str
            or HEX32.fullmatch(candidate["newEpoch"]) is None
            or type(candidate["newSequence"]) is not int
            or candidate["newSequence"] != 1):
        deny("C3E_CUTOVER_NEW_GENESIS_OR_KEY_FORMAT_INVALID")
    if (candidate["rootPublicKeySha256"] == candidate["historySignerSha256"]
            or candidate["rootPublicKeySha256"] in known_keys
            or candidate["historySignerSha256"] in known_keys):
        deny("C3E_CUTOVER_OLD_OR_ALIASED_SIGNER_REFUSED")
    if candidate["newEpoch"] in known_development_epochs:
        deny("C3E_CUTOVER_LOCAL_EPOCH_CANNOT_BECOME_PROTECTED")
    if candidate["newGenesisHeadSha256"] == local_snapshot["testHeadSha256"]:
        deny("C3E_CUTOVER_LOCAL_HEAD_CANNOT_BECOME_GENESIS")
    # No outstanding fixture nonce may be accepted into a new protected epoch.
    # The entire candidate field must be EXACTLY [] or () - not a promise of
    # transfer, even if all hashes claim to be unspent or previously consumed.
    if type(candidate["importedChallengeDigests"]) not in (tuple, list):
        deny("C3E_CUTOVER_IMPORTED_CHALLENGES_INVALID")
    if candidate["importedChallengeDigests"]:
        deny("C3E_CUTOVER_LOCAL_CHALLENGE_TRANSFER_FORBIDDEN")
    # The old roster is untrusted too. Knowing these synthetic digests cannot
    # establish that all local challenges were discovered or revoked.
    if len(old_challenges) > 32:
        deny("C3E_CUTOVER_OLD_CHALLENGE_ROSTER_INVALID")

    audit_reference = hashlib.sha256(
        b"C3E_LOCAL_AUDIT_ONLY\x00"
        + local_snapshot["testHeadSha256"].encode("ascii")
        + b"\x00"
        + str(local_snapshot["testSequence"]).encode("ascii")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "status": HOLD,
        "candidateFieldsConsistentInCI": True,
        "localHistoryAuditReferenceOnlySha256": audit_reference,
        "nextRequiredAction": "OPERATOR_ENROLL_INDEPENDENT_CUSTODIAN_SEPARATELY",
        **DENIED,
    }


def protected_cutover(*_args, **_kwargs):
    """Not a transport, enrollment or production activation endpoint."""
    deny("C3E_CUTOVER_NO_PROTECTED_AUTHORITY_OR_OPERATOR_ACTIVATION")
