"""Offline concurrency tests for synthetic Phone Bridge serialized host.

All events/lines/organizations and sessions are invented. No real device,
KDE Connect, identity service, content, socket or filesystem accessed.
"""
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import SerializedPhoneHostFixture as sh  # noqa: E402
import TrustedPhoneGrantFixture as pg  # noqa: E402


class SyntheticSessions:
    def __init__(self):
        self.now = 100
        self.active = True
        self.principal = "person-a"
        self.organizations = ("org-a",)
        self.expires = 400
        self.block_checks = False
        self.entered = threading.Event()
        self.permit = threading.Event()

    def clock(self):
        return self.now

    def resolve(self, ref, now):
        if self.block_checks:
            self.entered.set()
            if not self.permit.wait(timeout=3):
                raise TimeoutError("synthetic resolver timed out")
        if ref != "session-a" or not self.active:
            return None
        return pg.HostVerifiedPhoneContext(
            principal_id=self.principal, session_ref=ref,
            expires_at=self.expires, authorized_organizations=self.organizations,
        )


def request(**override):
    data = {
        "schema": pg.SCHEMA, "sessionRef": "session-a",
        "deviceId": "phone-a", "lineId": "line-a",
        "ownerKind": "PERSONAL", "organizationId": None,
        "operation": "messages.receive",
    }
    data.update(override)
    return data


class SerializedPhoneHostTests(unittest.TestCase):
    def setUp(self):
        self.sessions = SyntheticSessions()
        self.host = sh.SerializedPhoneHostFixture(
            resolve_session=self.sessions.resolve, clock=self.sessions.clock,
        )
        self.host.seed_fixture_grant(
            grant_id="grant-a", principal_id="person-a",
            device_id="phone-a", line_id="line-a",
            owner_kind="PERSONAL", organization_id=None,
            operations=["messages.receive"], issued_at=50, expires_at=300,
        )

    def arm(self, **kwargs):
        result = self.host.arm(request(**kwargs))
        self.assertEqual(result["state"], "ARMED_FIXTURE_ONLY")
        return result["epoch"]

    def queue(self, epoch, ident="eventA"):
        return self.host.queue_synthetic_event(event_ref=ident, epoch=epoch)

    def test_start_queue_and_consume_has_no_phone_content(self):
        epoch = self.arm()
        self.assertEqual(self.queue(epoch)["state"], "QUEUED_FIXTURE_ONLY")
        x = self.host.consume_synthetic(epoch=epoch)
        self.assertEqual(x["state"], "CONSUMED_FIXTURE_ONLY")
        self.assertEqual(x["syntheticDeliveredCount"], 1)
        self.assertFalse(x["routeEligible"])
        self.assertFalse(x["contentAccessEnabled"])

    def test_revocation_clears_queued_event_under_same_lock(self):
        epoch = self.arm()
        self.queue(epoch)
        result = self.host.revoke_fixture_grant("grant-a")
        self.assertEqual(result["state"], "CANCELLED")
        self.assertNotEqual(result["epoch"], epoch)
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["state"], "CLOSED")

    def test_revoked_grant_cannot_rearm(self):
        self.host.revoke_fixture_grant("grant-a")
        self.assertEqual(self.host.arm(request())["state"], "REJECTED")

    def test_expired_grant_cancels_instead_of_consuming(self):
        epoch = self.arm()
        self.queue(epoch)
        self.sessions.now = 300
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_signout_cancels_queued_event(self):
        epoch = self.arm()
        self.queue(epoch)
        self.sessions.active = False
        self.assertEqual(self.host.reconcile()["state"], "CANCELLED")

    def test_expired_session_cancels_queued_event(self):
        epoch = self.arm()
        self.queue(epoch)
        self.sessions.expires = 101
        self.sessions.now = 101
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_new_line_cannot_cross_personal_line(self):
        self.assertEqual(self.host.arm(request(lineId="line-b"))["state"], "REJECTED")

    def test_org_membership_does_not_imply_phone_access(self):
        self.assertEqual(self.host.arm(request(ownerKind="ORGANIZATION", organizationId="org-a"))["state"], "REJECTED")

    def test_no_unknown_or_legacy_content_fields_accepted(self):
        for raw in [request(body="fake text"), request(principalId="person-a"),
                    request(operation="messages.send"), request(operation="messages.read")]:
            with self.subTest(raw=raw):
                self.assertEqual(self.host.arm(raw)["state"], "REJECTED")

    def test_cancel_invalidates_epoch_and_prevents_stale_delivery(self):
        epoch = self.arm()
        self.queue(epoch)
        self.host.cancel()
        later = self.arm()
        self.assertNotEqual(epoch, later)
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["state"], "REJECTED")
        self.assertEqual(self.host.consume_synthetic(epoch=later)["state"], "EMPTY")

    def test_two_concurrent_consumers_only_claim_one_event(self):
        epoch = self.arm()
        self.queue(epoch)
        ready = threading.Barrier(3)
        results = []
        def consume():
            ready.wait(timeout=3)
            results.append(self.host.consume_synthetic(epoch=epoch))
        workers = [threading.Thread(target=consume) for _ in range(2)]
        for thread in workers:
            thread.start()
        try:
            ready.wait(timeout=3)
            for thread in workers:
                thread.join(timeout=3)
            self.assertFalse(any(t.is_alive() for t in workers))
            self.assertEqual(sorted(x["state"] for x in results),
                             ["CONSUMED_FIXTURE_ONLY", "EMPTY"])
            self.assertEqual(sum(x["syntheticDeliveredCount"] for x in results), 1)
        finally:
            for thread in workers:
                thread.join(timeout=3)

    def test_two_concurrent_arm_calls_never_replace_current_scope(self):
        ready = threading.Barrier(3)
        results = []
        def arm():
            ready.wait(timeout=3)
            results.append(self.host.arm(request()))
        workers = [threading.Thread(target=arm) for _ in range(2)]
        for thread in workers:
            thread.start()
        ready.wait(timeout=3)
        for thread in workers:
            thread.join(timeout=3)
        self.assertFalse(any(t.is_alive() for t in workers))
        self.assertEqual(sorted(x["state"] for x in results),
                         ["ARMED_FIXTURE_ONLY", "REJECTED"])

    def test_two_concurrent_queues_same_event_cannot_duplicate_pending(self):
        epoch = self.arm()
        ready = threading.Barrier(3)
        results = []
        def queue():
            ready.wait(timeout=3)
            results.append(self.queue(epoch))
        workers = [threading.Thread(target=queue) for _ in range(2)]
        for thread in workers:
            thread.start()
        ready.wait(timeout=3)
        for thread in workers:
            thread.join(timeout=3)
        self.assertFalse(any(t.is_alive() for t in workers))
        self.assertEqual(sorted(x["state"] for x in results),
                         ["QUEUED_FIXTURE_ONLY", "REJECTED"])
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["syntheticDeliveredCount"], 1)

    def test_revoke_first_linearization_blocks_release(self):
        epoch = self.arm()
        self.queue(epoch)
        revoked = threading.Event()
        outcome = {}
        def revoke():
            outcome["revoke"] = self.host.revoke_fixture_grant("grant-a")
            revoked.set()
        def release():
            self.assertTrue(revoked.wait(timeout=3))
            outcome["consume"] = self.host.consume_synthetic(epoch=epoch)
        a = threading.Thread(target=revoke)
        b = threading.Thread(target=release)
        a.start()
        b.start()
        a.join(timeout=3)
        b.join(timeout=3)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(outcome["revoke"]["state"], "CANCELLED")
        self.assertEqual(outcome["consume"]["state"], "CLOSED")
        self.assertEqual(outcome["consume"]["syntheticDeliveredCount"], 0)

    def test_release_first_linearization_then_revocation_blocks_future(self):
        epoch = self.arm()
        self.queue(epoch, "eventBefore")
        self.sessions.block_checks = True
        results = {}
        revoke_attempting = threading.Event()
        def release():
            results["release"] = self.host.consume_synthetic(epoch=epoch)
        def revoke():
            revoke_attempting.set()
            results["revoke"] = self.host.revoke_fixture_grant("grant-a")
        delivery = threading.Thread(target=release)
        cancel = threading.Thread(target=revoke)
        delivery.start()
        try:
            self.assertTrue(self.sessions.entered.wait(timeout=3))
            # The consume currently holds the arbiter lock while its
            # synthetic resolver is blocked. Revoke can begin but must
            # linearize AFTER consume releases the lock.
            cancel.start()
            self.assertTrue(revoke_attempting.wait(timeout=3))
        finally:
            self.sessions.permit.set()
            delivery.join(timeout=3)
            if cancel.ident is not None:
                cancel.join(timeout=3)
        self.assertFalse(delivery.is_alive() or cancel.is_alive())
        self.assertEqual(results["release"]["state"], "CONSUMED_FIXTURE_ONLY")
        self.assertEqual(results["revoke"]["state"], "CANCELLED")
        self.assertEqual(self.queue(epoch, "after")["state"], "CLOSED")

    def test_concurrent_cancel_does_not_leave_orphaned_event(self):
        epoch = self.arm()
        self.queue(epoch)
        ready = threading.Barrier(3)
        outcomes = []
        def cancel():
            ready.wait(timeout=3)
            outcomes.append(self.host.cancel()["state"])
        def consume():
            ready.wait(timeout=3)
            outcomes.append(self.host.consume_synthetic(epoch=epoch)["state"])
        workers = [threading.Thread(target=cancel), threading.Thread(target=consume)]
        for thread in workers:
            thread.start()
        ready.wait(timeout=3)
        for thread in workers:
            thread.join(timeout=3)
        self.assertFalse(any(t.is_alive() for t in workers))
        self.assertIn("CLOSED", outcomes)
        self.assertTrue(set(outcomes) <= {"CLOSED", "CONSUMED_FIXTURE_ONLY"})
        self.assertEqual(self.host.consume_synthetic(epoch=epoch)["state"], "CLOSED")

    def test_host_grant_seed_does_not_silently_override_current_subscription(self):
        epoch = self.arm()
        self.host.seed_fixture_grant(
            grant_id="other-b", principal_id="person-a",
            device_id="phone-b", line_id="line-b",
            owner_kind="PERSONAL", organization_id=None,
            operations=["messages.receive"], issued_at=50, expires_at=300,
        )
        self.assertEqual(self.host.arm(request(deviceId="phone-b", lineId="line-b"))["state"], "REJECTED")
        self.assertEqual(self.queue(epoch)["state"], "QUEUED_FIXTURE_ONLY")

    def test_conflicting_duplicate_scope_grants_fail_closed(self):
        epoch = self.arm()
        self.host.seed_fixture_grant(
            grant_id="duplicate-b", principal_id="person-a",
            device_id="phone-a", line_id="line-a",
            owner_kind="PERSONAL", organization_id=None,
            operations=["messages.receive"], issued_at=50, expires_at=300,
        )
        self.assertEqual(self.queue(epoch)["state"], "CANCELLED")

    def test_no_identifiers_or_sms_payloads_in_any_result(self):
        replies = [self.host.reconcile(), self.host.cancel()]
        epoch = self.arm()
        replies += [self.queue(epoch), self.host.consume_synthetic(epoch=epoch),
                    self.host.revoke_fixture_grant("grant-a")]
        for item in replies:
            self.assertEqual(set(item), {
                "schema", "execution", "state", "epoch",
                "syntheticDeliveredCount", "routeEligible", "contentAccessEnabled",
            })
            self.assertFalse(item["routeEligible"])
            self.assertFalse(item["contentAccessEnabled"])
            for sensitive in ["person-a", "phone-a", "line-a", "grant-a", "session-a", "eventA"]:
                self.assertNotIn(sensitive, str(item))


if __name__ == "__main__":
    unittest.main()
