from dataclasses import replace
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_resource_custody_h2 as H
from test_heart_dispatch_reference_h1 import fixture
from resource_governor_p1 import ResourceAvailability


def reference(s):
    scope = s.binding.recommendation.original.scope
    return H.AttemptRef(scope.context, scope.turn_id, s.operation_id, s.attempt_id)


def claim(c, s=None):
    s = fixture() if s is None else s
    return c.claim_reference(s, replace(s, captured_ns=s.captured_ns+100),
                             now_ns=s.captured_ns+200)


def release(s, **changes):
    obs = H.ReleaseReference(reference(s), "clock", 500,
                             ResourceAvailability("available", 64, 0, 1), False)
    return replace(obs, **changes)


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.c = H.ResourceCustody()
        self.s = fixture()

    def terminal(self, outcome="COMMITTED"):
        return self.c.observe_terminal_reference(reference(self.s),
                                                 outcome=outcome, clock_domain="clock", observed_ns=400)

    def test_claim_and_separate_release(self):
        self.assertEqual(claim(self.c, self.s), "REFERENCE_HELD")
        self.assertEqual(self.c.account_release_reference(release(self.s), now_ns=600),
                         "TERMINAL_REQUIRED_HOLD")
        self.assertEqual(self.terminal(), "TERMINAL_REFERENCE_HELD")
        self.assertTrue(self.c.status()["fixture_slot_occupied"])
        self.assertEqual(self.c.account_release_reference(release(self.s), now_ns=600),
                         "REFERENCE_RELEASED")
        self.assertFalse(self.c.status()["fixture_slot_occupied"])
        self.assertEqual(self.c.status()["status"], "IDLE")

    def test_h1_is_recomputed(self):
        changed = replace(self.s, availability=replace(self.s.availability, memory_mib=1))
        self.assertEqual(claim(self.c, changed), "DISPATCH_REFERENCE_HOLD")
        self.assertFalse(self.c.status()["fixture_slot_occupied"])
        self.assertEqual(claim(self.c, self.s), "REFERENCE_HELD")

    def test_one_slot_under_concurrency(self):
        for _ in range(16):
            c = H.ResourceCustody()
            barrier = threading.Barrier(8)
            results = []
            def worker():
                barrier.wait(timeout=3)
                results.append(claim(c))
            workers = [threading.Thread(target=worker) for _ in range(8)]
            for t in workers:
                t.start()
            for t in workers:
                t.join(5)
                self.assertFalse(t.is_alive())
            self.assertEqual(results.count("REFERENCE_HELD"), 1)
            self.assertEqual(results.count("SLOT_OCCUPIED"), 7)

    def test_unknown_is_sticky(self):
        claim(self.c, self.s)
        self.assertEqual(self.terminal("UNKNOWN"), "UNKNOWN_HOLD")
        self.assertEqual(self.terminal("COMMITTED"), "UNKNOWN_HOLD")
        self.assertEqual(self.c.account_release_reference(release(self.s), now_ns=600),
                         "TERMINAL_REQUIRED_HOLD")
        self.assertEqual(claim(self.c), "SLOT_OCCUPIED")

    def test_duplicate_terminal_holds(self):
        claim(self.c, self.s)
        self.terminal()
        self.assertEqual(self.terminal("FAILED"), "UNKNOWN_HOLD")

    def test_exact_attempt_and_context_required(self):
        claim(self.c, self.s)
        a = reference(self.s)
        for other in (replace(a, operation_id="other"), replace(a, attempt_id="other"),
                      replace(a, turn_id="other"),
                      replace(a, context=replace(a.context, generation=2))):
            with self.assertRaisesRegex(H.CustodyRefusal, "ATTEMPT_MISMATCH"):
                self.c.observe_terminal_reference(other, outcome="FAILED", clock_domain="clock", observed_ns=400)
            with self.assertRaisesRegex(H.CustodyRefusal, "ATTEMPT_MISMATCH"):
                self.c.account_release_reference(release(self.s, attempt=other), now_ns=600)
        self.assertTrue(self.c.status()["fixture_slot_occupied"])

    def test_stop_and_transport_closure_are_not_terminal(self):
        claim(self.c, self.s)
        for outcome in ("STOP", "EOF", "COMMIT_ENTRY", "COMPLETE", True):
            with self.assertRaisesRegex(H.CustodyRefusal, "INVALID_TERMINAL_REFERENCE"):
                self.terminal(outcome)
        self.assertEqual(self.c.status()["status"], "REFERENCE_HELD")

    def test_release_time_refusals(self):
        claim(self.c, self.s)
        self.assertEqual(self.c.observe_terminal_reference(reference(self.s),
                         outcome="FAILED", clock_domain="clock", observed_ns=299), "TERMINAL_CLOCK_HOLD")
        self.assertEqual(self.c.observe_terminal_reference(reference(self.s),
                         outcome="FAILED", clock_domain="other", observed_ns=400),
                         "TERMINAL_CLOCK_HOLD")
        self.terminal()
        for obs, now in ((release(self.s, observed_ns=400), 600),
                         (release(self.s, observed_ns=601), 600),
                         (release(self.s, clock_domain="other"), 600),
                         (release(self.s), 6_000_000_000)):
            self.assertEqual(self.c.account_release_reference(obs, now_ns=now),
                             "RELEASE_CLOCK_HOLD")
        self.assertTrue(self.c.status()["fixture_slot_occupied"])

    def test_release_requires_current_accounting(self):
        claim(self.c, self.s)
        self.terminal("CANCELLED")
        for obs in (release(self.s, active_workload=True),
                    release(self.s, active_workload=None),
                    release(self.s, availability=ResourceAvailability("other", 1, 1, 1)),
                    release(self.s, availability=ResourceAvailability("available", 1, None, 1))):
            self.assertEqual(self.c.account_release_reference(obs, now_ns=600),
                             "RESOURCE_ACCOUNTING_HOLD")
        self.assertEqual(self.c.account_release_reference(release(self.s), now_ns=600),
                         "REFERENCE_RELEASED")

    def test_release_does_not_make_old_attempt_reusable(self):
        claim(self.c, self.s)
        self.terminal("NOT_DISPATCHED")
        self.c.account_release_reference(release(self.s), now_ns=600)
        for changes in ({}, {"attempt_id": "new-attempt"},
                        {"operation_id": "new-operation"},
                        {"operation_id": "new-operation", "attempt_id": "new-attempt"}):
            self.assertEqual(claim(self.c, replace(self.s, captured_ns=700, **changes)),
                             "REPLAY_HOLD")

    def test_bounded_tombstones_never_evict(self):
        with patch.object(H, "MAX_OPERATIONS", 1):
            claim(self.c, self.s)
            self.terminal()
            self.c.account_release_reference(release(self.s), now_ns=600)
            self.assertEqual(claim(self.c), "HISTORY_LIMIT_HOLD")

    def test_status_never_implies_permission(self):
        claim(self.c, self.s)
        status = self.c.status()
        for key in ("physical_resources_reserved", "physical_resources_released",
                    "source_authenticated", "terminal_verified", "durable_recovery",
                    "safe_to_start_inference", "permission_granted", "production_authority"):
            self.assertIs(status[key], False)
        self.assertEqual(status["safe_actions"], [])
        for value in ("example:latest", "owner", "operation", "attempt", "sha256:"):
            self.assertNotIn(value, str(status))
