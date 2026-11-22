"""Negative-only tests of the C5 Scope A test-reference serialization model."""
from __future__ import annotations

import multiprocessing
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import (  # noqa: E402
    ACTION, AUDIENCE, ReferenceRefused, TestOnlyC5Fence,
)


def claim():
    return {
        "audience": AUDIENCE, "action": ACTION,
        "grant_id": str(uuid.uuid4()), "operation_id": str(uuid.uuid4()),
        "selection_sha256": "a" * 64,
        "intent_sha256": uuid.uuid4().hex * 2,
        "source_sha256": "c" * 64,
        "session_id": str(uuid.uuid4()), "seat_id": "seat0",
        "issuer_epoch": str(uuid.uuid4()),
        "issued_ms": 1000, "expires_ms": 1500,
    }


def worker_spend(path, evidence, gate, results):
    gate.wait(timeout=8)
    try:
        result = TestOnlyC5Fence(path).spend_fixture(evidence, now_ms=1100)
        results.put(("spent", result))
    except ReferenceRefused:
        results.put(("refused", None))


class ReferenceFenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "test-only-c5.db"
        self.fence = TestOnlyC5Fence(self.path)
        self.fence.initialize_fixture()
        self.item = claim()

    def assert_no_authority(self, result):
        for field in ("production_authorized", "native_action_allowed",
                      "production_revocation_ack", "retry_allowed", "undo_allowed"):
            self.assertIs(result[field], False)
        self.assertEqual(result["safe_actions"], [])

    def test_registered_fixture_and_spent_after_lost_reply(self):
        self.assert_no_authority(self.fence.register_fixture(self.item))
        self.assert_no_authority(self.fence.spend_fixture(self.item, now_ms=1100))
        # The result is lost. Reopened reference must never infer UNUSED.
        observed = TestOnlyC5Fence(self.path).inspect_fixture(self.item["grant_id"])
        self.assertEqual(observed["fixture_state"], "SPENT_UNKNOWN_HOLD")
        self.assert_no_authority(observed)
        with self.assertRaises(ReferenceRefused):
            self.fence.spend_fixture(self.item, now_ms=1101)

    def test_revoke_then_spend_and_spend_then_revoke(self):
        self.fence.register_fixture(self.item)
        result = self.fence.revoke_fixture(self.item["grant_id"])
        self.assertEqual(result["fixture_state"], "REVOKED_BEFORE_SPEND_FIXTURE")
        self.assert_no_authority(result)
        with self.assertRaises(ReferenceRefused):
            self.fence.spend_fixture(self.item, now_ms=1100)
        other = claim()
        self.fence.register_fixture(other)
        self.fence.spend_fixture(other, now_ms=1100)
        result = self.fence.revoke_fixture(other["grant_id"])
        self.assertEqual(result["fixture_state"], "SPENT_REVOCATION_PENDING_UNKNOWN_HOLD")
        self.assert_no_authority(result)
        self.assertEqual(self.fence.inspect_fixture(other["grant_id"])["fixture_state"],
                         "SPENT_REVOCATION_PENDING_UNKNOWN_HOLD")

    def test_exact_claim_and_expiration_refusals(self):
        self.fence.register_fixture(self.item)
        for key, replacement in (
            ("source_sha256", "f" * 64), ("selection_sha256", "d" * 64),
            ("intent_sha256", "b" * 64), ("seat_id", "seat1"),
            ("session_id", str(uuid.uuid4())),
            ("issuer_epoch", str(uuid.uuid4())),
            ("operation_id", str(uuid.uuid4())),
        ):
            with self.subTest(key=key):
                changed = dict(self.item, **{key: replacement})
                with self.assertRaises(ReferenceRefused):
                    self.fence.spend_fixture(changed, now_ms=1100)
        for moment in (999, 1500, True, 1100.0, -1):
            with self.subTest(moment=moment):
                with self.assertRaises(ReferenceRefused):
                    self.fence.spend_fixture(self.item, now_ms=moment)

    def test_wrong_audience_bad_types_and_duplicate_intent(self):
        for key, replacement in (
            ("audience", "hospital-room-restore"), ("action", "READ_SESSION"),
            ("grant_id", "not-a-uuid"), ("seat_id", "seat\n0"),
            ("expires_ms", 12000), ("expires_ms", False),
            ("intent_sha256", "A" * 64),
        ):
            with self.subTest(key=key, replacement=replacement):
                with self.assertRaises(ReferenceRefused):
                    self.fence.register_fixture(dict(self.item, **{key: replacement}))
        self.fence.register_fixture(self.item)
        with self.assertRaises(ReferenceRefused):
            self.fence.register_fixture(self.item)
        another = claim()
        another["intent_sha256"] = self.item["intent_sha256"]
        with self.assertRaises(ReferenceRefused):
            self.fence.register_fixture(another)

    def test_missing_or_replaced_store_never_means_unspent(self):
        absent = self.fence.inspect_fixture(self.item["grant_id"])
        self.assertEqual(absent["fixture_state"], "ABSENT_UNKNOWN_HOLD")
        self.assert_no_authority(absent)
        self.path.unlink()
        with self.assertRaises(ReferenceRefused):
            self.fence.spend_fixture(self.item, now_ms=1100)
        with self.assertRaises(ReferenceRefused):
            self.fence.inspect_fixture(self.item["grant_id"])

    def test_two_independent_processes_cannot_both_spend(self):
        self.fence.register_fixture(self.item)
        ctx = multiprocessing.get_context("spawn")  # Distinct interpreters/SQLite handles.
        gate, results = ctx.Event(), ctx.Queue()
        workers = [ctx.Process(target=worker_spend,
                               args=(self.path, self.item, gate, results)) for _ in range(2)]
        for proc in workers:
            proc.start()
        gate.set()
        outcomes = [results.get(timeout=15) for _ in workers]
        for proc in workers:
            proc.join(timeout=15)
            self.assertEqual(proc.exitcode, 0)
        self.assertEqual(sorted(tag for tag, _ in outcomes), ["refused", "spent"])
        self.assert_no_authority(next(result for tag, result in outcomes if tag == "spent"))
        self.assertEqual(self.fence.inspect_fixture(self.item["grant_id"])["fixture_state"],
                         "SPENT_UNKNOWN_HOLD")


if __name__ == "__main__":
    unittest.main()
