#!/usr/bin/env python3
"""DOC 1 storage-neutral trust boundary: local CI observations, protected HOLD.

This is an adapter contract experiment, NOT an independently enrolled remote
service. LOCAL_DEVELOPMENT can call the existing root-guarded SQLite test
ledger. PROTECTED_REQUIRED never talks to SQLite, never falls back to local
state and always refuses until a separately reviewed protected custodian is
implemented, enrolled, and authorized. No production entry point.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "c3e_storage_existing_local_development_ledger",
        HERE / "C3eLocalDevelopmentHistoryLedger.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_STORAGE_LOCAL_LEDGER_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


L = _load()

SCHEMA = "postapollo.connections.c3e-storage-boundary-ci-v1"
LOCAL_DEVELOPMENT = "LOCAL_DEVELOPMENT_ONLY"
PROTECTED_REQUIRED = "INDEPENDENT_CUSTODIAN_REQUIRED"
STATUS_LOCAL = "LOCAL_FIXTURE_VALID_NOT_INDEPENDENT_TRUST"
STATUS_HOLD = "INDEPENDENT_CUSTODIAN_UNAVAILABLE_HOLD"
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
# The union of all inherited denied flags remains false on *every* result.
DENIED = {
    **L.H.DENIED,
    **L.DENIED,
    "trustedCurrentHeadVerified": False,
    "independentOneUseChallengeVerified": False,
    "protectedCustodianReachable": False,
}


class Refused(ValueError):
    """Malformed fixture or attempted crossing of the storage/authority gate."""


class UnknownAfterCommit(RuntimeError):
    """The development ledger may have committed; inspect outcome, never retry."""


def deny(reason: str):
    raise Refused(reason)


def _no_authority(record: dict, required: set[str]):
    if type(record) is not dict or set(record) != required:
        deny("C3E_STORAGE_UNEXPECTED_BACKEND_FIELDS")
    for flag in (set(record) & set(DENIED)):
        if record[flag] is not False:
            deny("C3E_STORAGE_BACKEND_ATTEMPTED_AUTHORITY_PROMOTION")


class LocalSQLiteTestAdapter:
    """Not a general backend plugin: accepts exactly our CI-only ledger."""

    def __init__(self, ledger: L.DevelopmentLedger):
        if type(ledger) is not L.DevelopmentLedger:
            deny("C3E_STORAGE_ONLY_KNOWN_DISPOSABLE_LOCAL_LEDGER")
        self._ledger = ledger

    def snapshot(self):
        return self._ledger.snapshot()

    def issue(self, **inputs):
        return self._ledger.issue(**inputs)

    def commit(self, **inputs):
        return self._ledger.record(**inputs)

    def outcome(self, challenge):
        return self._ledger.outcome(challenge)


class TrustBoundary:
    """Stable semantic operations without selecting a production wire protocol.

    This release deliberately has only ONE concrete adapter: local CI.
    A future protected service needs a separate operator-accepted protocol,
    enrolled root, native test and independent pre-merge security review.
    Never guess that any backend claiming mode=PROTECTED is trusted.
    """

    def __init__(self, *, required_mode: str, local_adapter=None):
        if type(required_mode) is not str or required_mode not in (LOCAL_DEVELOPMENT, PROTECTED_REQUIRED):
            deny("C3E_STORAGE_UNKNOWN_TRUST_MODE")
        if required_mode == LOCAL_DEVELOPMENT:
            if type(local_adapter) is not LocalSQLiteTestAdapter:
                deny("C3E_STORAGE_EXPLICIT_LOCAL_CI_ADAPTER_REQUIRED")
        elif local_adapter is not None:
            deny("C3E_STORAGE_PROTECTED_MODE_REFUSES_LOCAL_ADAPTER")
        self._mode = required_mode
        self._local = local_adapter

    def _require_local(self):
        if self._mode != LOCAL_DEVELOPMENT or self._local is None:
            deny("C3E_STORAGE_PROTECTED_CUSTODIAN_HOLD_NO_FALLBACK")
        return self._local

    def read_current_snapshot(self):
        """Untrusted development *observation*, never a current trust root."""
        adapter = self._require_local()
        raw = adapter.snapshot()
        expected = {
            "schema", "status", "testEpoch",
            "previousHeadSha256", "previousSequence", *L.DENIED,
        }
        _no_authority(raw, expected)
        if (raw["schema"] != L.SCHEMA or raw["status"] != L.STATUS
                or type(raw["testEpoch"]) is not str
                or re.fullmatch(r"[0-9a-f]{32}", raw["testEpoch"]) is None
                or type(raw["previousHeadSha256"]) is not str
                or HEX.fullmatch(raw["previousHeadSha256"]) is None
                or type(raw["previousSequence"]) is not int
                or raw["previousSequence"] < 1):
            deny("C3E_STORAGE_UNTRUSTED_LOCAL_SNAPSHOT_MALFORMED")
        return {
            "schema": SCHEMA,
            "status": STATUS_LOCAL,
            "source": LOCAL_DEVELOPMENT,
            "testHeadSha256": raw["previousHeadSha256"],
            "testSequence": raw["previousSequence"],
            **DENIED,
        }

    def issue_challenge(self, *, host: str, release_epoch: int,
                        release_seq: int, now_ms: int, ttl_ms: int):
        adapter = self._require_local()
        challenge = adapter.issue(
            host=host, release_epoch=release_epoch,
            release_seq=release_seq, now_ms=now_ms, ttl_ms=ttl_ms)
        if type(challenge) is not bytes or len(challenge) != 32:
            deny("C3E_STORAGE_LOCAL_CHALLENGE_MALFORMED")
        return {"schema": SCHEMA, "status": STATUS_LOCAL,
                "source": LOCAL_DEVELOPMENT, "testChallenge": challenge, **DENIED}

    def commit_signed_history(self, **existing_verifier_args):
        """Call unchanged #2192 verifier via local ledger; never remote trust."""
        adapter = self._require_local()
        try:
            raw = adapter.commit(**existing_verifier_args)
        except L.UnknownAfterCommit as exc:
            raise UnknownAfterCommit(
                "C3E_STORAGE_LOCAL_ACK_UNKNOWN_QUERY_OUTCOME_NO_RETRY"
            ) from exc
        expected = {
            "schema", "status", "developmentOnlyHeadAdvanced",
            "nextHistoryHeadSha256", "nextHistorySequence", *L.DENIED,
        }
        _no_authority(raw, expected)
        if (raw["schema"] != L.SCHEMA or raw["status"] != L.STATUS
                or raw["developmentOnlyHeadAdvanced"] is not True
                or type(raw["nextHistoryHeadSha256"]) is not str
                or HEX.fullmatch(raw["nextHistoryHeadSha256"]) is None
                or type(raw["nextHistorySequence"]) is not int
                or raw["nextHistorySequence"] < 2):
            deny("C3E_STORAGE_UNTRUSTED_LOCAL_COMMIT_MALFORMED")
        return {
            "schema": SCHEMA,
            "status": STATUS_LOCAL,
            "source": LOCAL_DEVELOPMENT,
            "testHeadSha256": raw["nextHistoryHeadSha256"],
            "testSequence": raw["nextHistorySequence"],
            **DENIED,
        }

    def lookup_terminal_outcome(self, challenge: bytes):
        """Untrusted local status; does not replay an unknown operation."""
        adapter = self._require_local()
        raw = adapter.outcome(challenge)
        expected = {
            "schema", "status", "developmentOnlyState",
            "developmentOnlyCommittedHeadSha256", *L.DENIED,
        }
        _no_authority(raw, expected)
        state, head = raw["developmentOnlyState"], raw[
            "developmentOnlyCommittedHeadSha256"]
        if (raw["schema"] != L.SCHEMA or raw["status"] != L.STATUS
                or state not in ("issued", "consumed")
                or (state == "issued" and head is not None)
                or (state == "consumed"
                    and (type(head) is not str or HEX.fullmatch(head) is None))):
            deny("C3E_STORAGE_UNTRUSTED_LOCAL_OUTCOME_MALFORMED")
        return {
            "schema": SCHEMA,
            "status": STATUS_LOCAL,
            "source": LOCAL_DEVELOPMENT,
            "testState": state,
            "testHeadSha256": head,
            **DENIED,
        }

    def revoke_enrollment(self, *_args, **_kwargs):
        """No test capability can revoke a production enrollment."""
        deny("C3E_STORAGE_NO_AUTHORIZED_ENROLLMENT_TO_REVOKE")

    def protected_admission(self, *_args, **_kwargs):
        """There is no production-custodian implementation in this milestone."""
        deny("C3E_STORAGE_NO_PROTECTED_AUTHORITY_OR_SIGNIN")

    def protected_required_status(self):
        """The only non-throwing protected-mode result is unambiguous HOLD."""
        if self._mode != PROTECTED_REQUIRED:
            deny("C3E_STORAGE_MODE_NOT_PROTECTED")
        return {
            "schema": SCHEMA, "status": STATUS_HOLD,
            "source": PROTECTED_REQUIRED,
            **DENIED,
        }
