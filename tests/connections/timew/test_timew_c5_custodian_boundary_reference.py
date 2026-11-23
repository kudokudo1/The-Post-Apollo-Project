"""Hostile tests for DOC 5's CI-only, storage-independent TimeW C5 probe."""
from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import ACTION, AUDIENCE  # noqa: E402
from TimeWC5CustodianBoundaryReference import (  # noqa: E402
    SCHEMA, hold, reconcile_fixture,
)


def claim():
    return {
        "audience": AUDIENCE, "action": ACTION,
        "grant_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "selection_sha256": "a" * 64,
        "intent_sha256": "b" * 64,
        "source_sha256": "c" * 64,
        "session_id": str(uuid.uuid4()),
        "seat_id": "seat0",
        "issuer_epoch": str(uuid.uuid4()),
        "issued_ms": 1000,
        "expires_ms": 1500,
    }


def snapshot(c, *, mode="INDEPENDENT_CANDIDATE", state="SPENT",
             head="d" * 64, sequence=7, receipt="e" * 64):
    return {
        "schema": SCHEMA, "source_mode": mode,
        "audience": c["audience"], "action": c["action"],
        "grant_id": c["grant_id"], "operation_id": c["operation_id"],
        "selection_sha256": c["selection_sha256"],
        "intent_sha256": c["intent_sha256"],
        "source_sha256": c["source_sha256"],
        "session_id": c["session_id"], "seat_id": c["seat_id"],
        "issuer_epoch": c["issuer_epoch"], "ledger_state": state,
        "head_sha256": head, "sequence": sequence,
        "terminal_receipt_sha256": receipt,
    }


class Provider:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, query):
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return self.response


class CustodianBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.c = claim()

    def probe(self, response, *, phase="PREPARED", last=None,
              now=1100):
        provider = Provider(response)
        result = reconcile_fixture(
            provider=provider, claim=self.c, journal_stage=phase,
            now_ms=now, last_seen=last)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0], {
            "audience": AUDIENCE, "action": ACTION,
            "grant_id": self.c["grant_id"],
            "operation_id": self.c["operation_id"],
        })
        self.assert_denied(result)
        return result["diagnostic"]

    def assert_denied(self, result):
        for key in (
            "production_authorized", "native_action_allowed",
            "human_consent_verified", "external_custody_verified",
            "revocation_acknowledged", "retry_allowed", "undo_allowed",
        ):
            self.assertIs(result[key], False)
        self.assertEqual(result["safe_actions"], [])

    def test_local_development_spent_never_becomes_native_custody(self):
        state = self.probe(snapshot(self.c, mode="LOCAL_DEVELOPMENT"))
        self.assertEqual(state, "LOCAL_ROLLBACKABLE_HISTORY_HOLD")

    def test_external_candidate_spent_with_local_prepared_is_unknown(self):
        state = self.probe(snapshot(self.c))
        self.assertEqual(state, "SPENT_BUT_LOCAL_PREPARED_UNKNOWN_HOLD")

    def test_local_fixture_complete_and_signed_looking_receipt_still_hold(self):
        state = self.probe(snapshot(self.c, receipt="f" * 64),
                           phase="FIXTURE_COMPLETE")
        self.assertEqual(state, "SPENT_BUT_NATIVE_TERMINAL_UNVERIFIED_HOLD")

    def test_untrusted_external_spent_with_dispatching_cannot_retry(self):
        for phase in ("DISPATCHING", "UNCERTAIN"):
            with self.subTest(phase=phase):
                state = self.probe(snapshot(self.c), phase=phase)
                self.assertEqual(state, "SPENT_NATIVE_OUTCOME_UNKNOWN_HOLD")

    def test_precommit_active_cannot_reconcile_local_dispatch(self):
        state = self.probe(snapshot(self.c, state="ACTIVE"), phase="DISPATCHING")
        self.assertEqual(state, "LOCAL_DISPATCH_WITHOUT_PROVEN_SPEND_UNKNOWN_HOLD")
        state = self.probe(snapshot(self.c, state="ACTIVE", receipt=None))
        self.assertEqual(state, "UNSPENT_UNTRUSTED_FIXTURE_HOLD")

    def test_revoked_and_unknown_are_never_terminal_native_authority(self):
        for state, expected in (
            ("REVOKED", "REVOKED_FIXTURE_HOLD"),
            ("UNKNOWN", "CUSTODIAN_UNKNOWN_HOLD"),
        ):
            with self.subTest(state=state):
                self.assertEqual(
                    self.probe(snapshot(self.c, state=state)),
                    expected)

    def test_different_grant_seat_intent_and_audience_refused(self):
        for key, wrong in (
            ("grant_id", str(uuid.uuid4())),
            ("operation_id", str(uuid.uuid4())),
            ("selection_sha256", "1" * 64),
            ("intent_sha256", "2" * 64),
            ("source_sha256", "3" * 64),
            ("session_id", str(uuid.uuid4())),
            ("seat_id", "seat1"),
            ("issuer_epoch", str(uuid.uuid4())),
            ("audience", "hospital-restore"),
            ("action", "forest-generate"),
        ):
            with self.subTest(key=key):
                altered = snapshot(self.c)
                altered[key] = wrong
                self.assertEqual(
                    self.probe(altered),
                    "MISMATCHED_PURPOSE_OR_INTENT_HOLD")

    def test_added_untrusted_authority_flag_and_malformed_receipt_refuse(self):
        candidate = snapshot(self.c)
        candidate["production_authorized"] = True
        self.assertEqual(self.probe(candidate),
                         "MALFORMED_PROVIDER_RESPONSE_HOLD")
        for value in ("no-proof", True, 0, "", "A" * 64):
            with self.subTest(value=value):
                candidate = snapshot(self.c, receipt=value)
                self.assertEqual(self.probe(candidate),
                                 "MALFORMED_PROVIDER_RESPONSE_HOLD")

    def test_prior_head_rollback_and_fork_detection_not_trust(self):
        old = {"head_sha256": "f" * 64, "sequence": 8}
        state = self.probe(snapshot(self.c, sequence=7), last=old)
        self.assertEqual(state, "OBSERVED_HISTORY_ROLLBACK_HOLD")
        old = {"head_sha256": "f" * 64, "sequence": 7}
        state = self.probe(snapshot(self.c, sequence=7), last=old)
        self.assertEqual(state, "OBSERVED_HISTORY_FORK_HOLD")
        old = {"head_sha256": "d" * 64, "sequence": 6}
        state = self.probe(snapshot(self.c, sequence=7), last=old)
        self.assertEqual(state, "INCONSISTENT_HEAD_ADVANCEMENT_HOLD")

    def test_missing_or_unavailable_provider_no_fallback_no_retry(self):
        for provider in (None, Provider(error=TimeoutError("lost ack")),
                         Provider(error=ConnectionError("offline"))):
            with self.subTest(provider=type(provider).__name__):
                result = reconcile_fixture(provider=provider, claim=self.c,
                                           journal_stage="PREPARED",
                                           now_ms=1100)
                self.assert_denied(result)
                self.assertEqual(result["diagnostic"],
                                 "PROVIDER_UNAVAILABLE_UNKNOWN_HOLD")
                if isinstance(provider, Provider):
                    self.assertEqual(len(provider.calls), 1)

    def test_expired_clock_and_invalid_journal_block_before_read(self):
        for phase, now, expected in (
            ("PREPARED", 1500, "EXPIRED_OR_NOT_YET_VALID_HOLD"),
            ("PREPARED", 999, "EXPIRED_OR_NOT_YET_VALID_HOLD"),
            ("PREPARED", True, "INVALID_CLOCK_HOLD"),
            ("PREPARED", 1100.5, "INVALID_CLOCK_HOLD"),
            ("COMPLETED", 1100, "INVALID_JOURNAL_STAGE_HOLD"),
        ):
            with self.subTest(phase=phase, now=now):
                provider = Provider(snapshot(self.c))
                result = reconcile_fixture(
                    provider=provider, claim=self.c,
                    journal_stage=phase, now_ms=now)
                self.assert_denied(result)
                self.assertEqual(result["diagnostic"], expected)
                self.assertEqual(provider.calls, [])

    def test_malformed_provider_head_and_sequence_hold(self):
        for key, value in (
            ("sequence", 0), ("sequence", True),
            ("head_sha256", "A" * 64),
            ("source_mode", "PRODUCTION"),
            ("ledger_state", "AUTHORISED"),
        ):
            with self.subTest(key=key):
                candidate = snapshot(self.c)
                candidate[key] = value
                self.assertEqual(
                    self.probe(candidate),
                    "MALFORMED_PROVIDER_RESPONSE_HOLD")


if __name__ == "__main__":
    unittest.main()
