#!/usr/bin/env python3
"""DOC 1: compare two UNENROLLED local witness copies; never choose a winner.

The two inputs are results from the merged C3e split-store CI experiment.
They may both look self-consistent while representing incompatible local
histories. Even exact agreement does not establish independent currentness.
No sockets, service, signing keys, root enrollment, consensus or Sign-In.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_SPLIT_BRAIN_ORIGINAL_WITNESS_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


W = _load("c3e_split_brain_existing_shadow",
          HERE / "C3eSplitStoreRollbackWitnessCI.py")

SCHEMA = "postapollo.connections.c3e-local-split-brain-dispute-ci-v1"
STATUS = "LOCAL_WITNESS_COMPARISON_NOT_PROTECTED_CONSENSUS"
FORK = "COMPETING_EQUAL_SEQUENCE_DIFFERENT_HEADS_UNKNOWN_HOLD"
UNEQUAL = "UNEQUAL_SEQUENCE_NO_AUTHORITATIVE_WINNER_UNKNOWN_HOLD"
AGREE = "MATCHING_UNENROLLED_LOCAL_HEADS_STILL_UNKNOWN_HOLD"
UNTRUSTED = "INCONSISTENT_LOCAL_WITNESS_OBSERVATION_UNKNOWN_HOLD"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **W.DENIED,
    "custodianQuorumVerified": False,
    "independentlyEnrolledWitnessVerified": False,
    "revocationCurrentnessVerified": False,
    "independentHistoryForkResolved": False,
    "protectedChallengeSpendVerified": False,
    "signedTerminalSettlementVerified": False,
    "approvedRecoveryAction": False,
    "safeToReplay": False,
    "safeToRetry": False,
    "productionSignInAllowed": False,
}


class Refused(ValueError):
    """Malformed caller-provided diagnostic; no promotion or fallback."""


def _deny(code):
    raise Refused(code)


def _validated(report):
    required = {
        "schema", "status", "relation",
        "localObservedHeadSha256", "localObservedSequence",
        "shadowObservedHeadSha256", "shadowObservedSequence", "next",
        *W.DENIED,
    }
    if type(report) is not dict or set(report) != required:
        _deny("C3E_SPLIT_BRAIN_UNKNOWN_OR_EXTRA_DIAGNOSTIC_FIELDS")
    if (report["schema"] != W.SCHEMA
            or report["status"] != W.STATUS
            or report["next"] !=
            "HOLD_NO_AUTOMATIC_RETRY_OPERATOR_ENROLLED_CUSTODIAN_REQUIRED"
            or any(report[k] is not False for k in W.DENIED)):
        _deny("C3E_SPLIT_BRAIN_AUTHORITY_OR_STATUS_INJECTION")
    lhead, shead = (report["localObservedHeadSha256"],
                    report["shadowObservedHeadSha256"])
    lseq, sseq = (report["localObservedSequence"],
                  report["shadowObservedSequence"])
    if any(type(head) is not str or HEX64.fullmatch(head) is None
           for head in (lhead, shead)):
        _deny("C3E_SPLIT_BRAIN_INVALID_HEAD")
    if any(type(seq) is not int or seq < 1 for seq in (lseq, sseq)):
        _deny("C3E_SPLIT_BRAIN_INVALID_SEQUENCE")
    # Reconstruct claimed diagnostic from its bytes. Even a self-consistent
    # caller-provided report is NOT authenticated.
    derived = (W.STALE if lseq < sseq else
               W.AHEAD if lseq > sseq else
               W.FORK if lhead != shead else W.MATCH)
    if report["relation"] != derived:
        _deny("C3E_SPLIT_BRAIN_CONTRADICTORY_LOCAL_RELATION")
    return shead, sseq, derived


def reconcile_ci_only(*, left_observation, right_observation):
    """Inspect cloned CI-only history candidates with unconditional HOLD."""
    left_head, left_seq, left_relation = _validated(left_observation)
    right_head, right_seq, right_relation = _validated(right_observation)
    if left_relation != W.MATCH or right_relation != W.MATCH:
        dispute = UNTRUSTED
    elif left_seq == right_seq and left_head != right_head:
        dispute = FORK
    elif left_seq != right_seq:
        dispute = UNEQUAL
    else:
        dispute = AGREE
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "dispute": dispute,
        "leftLocalCandidateHeadSha256": left_head,
        "leftLocalCandidateSequence": left_seq,
        "rightLocalCandidateHeadSha256": right_head,
        "rightLocalCandidateSequence": right_seq,
        "candidateEvidence": "CALLER_PROVIDED_DISPOSABLE_LOCAL_REPORTS",
        "winner": None,
        "safeActions": [],
        "next": "UNKNOWN_HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED",
        **DENIED,
    }


def choose_protected_winner(*_args, **_kwargs):
    _deny("C3E_SPLIT_BRAIN_CANNOT_PICK_PROTECTED_WINNER_FROM_LOCAL_COPIES")
