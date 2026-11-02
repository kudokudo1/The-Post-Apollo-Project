"""No-device SMS receive lifecycle: synthetic revocation and stale-event tests."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import TrustedPhoneGrantFixture as grants  # noqa: E402
import PhoneSubscriptionLifecycleFixture as life  # noqa: E402


class Host:
    def __init__(self):
        self.now = 100
        self.active = True
        self.principal = "person-a"
        self.organizations = ("org-a",)
        self.expiry = 600

    def clock(self):
        return self.now

    def resolve(self, session_ref, now):
        if not self.active or session_ref != "session-a":
            return None
        return grants.HostVerifiedPhoneContext(
            principal_id=self.principal, session_ref=session_ref,
            expires_at=self.expiry, authorized_organizations=self.organizations,
        )


def request(**changes):
    x = {
        "schema": grants.SCHEMA, "sessionRef": "session-a",
        "deviceId": "phone-a", "lineId": "line-a",
        "ownerKind": "PERSONAL", "organizationId": None,
        "operation": "messages.receive",
    }
    x.update(changes)
    return x


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.host = Host()
        self.store = grants.TrustedPhoneGrantFixture(
            resolve_session=self.host.resolve, clock=self.host.clock)
        self.store.seed_fixture_grant(
            grant_id="grant-a", principal_id="person-a",
            device_id="phone-a", line_id="line-a", owner_kind="PERSONAL",
            organization_id=None, operations=["messages.receive"],
            issued_at=80, expires_at=500,
        )
        self.stream = life.PhoneSubscriptionLifecycleFixture(
            check_grant=self.store.check)

    def arm(self, **changes):
        x = self.stream.arm(request(**changes))
        self.assertEqual(x["state"], "ARMED_FIXTURE_ONLY")
        self.assertFalse(x["routeEligible"])
        self.assertFalse(x["contentAccessEnabled"])
        return x["epoch"]

    def queue(self, epoch, ident="fixture1"):
        return self.stream.queue_synthetic_event(event_ref=ident, epoch=epoch)

    def test_deny_by_default_until_explicit_arm(self):
        self.assertEqual(self.queue(0)["state"], "CLOSED")
        self.assertEqual(self.stream.consume_synthetic(epoch=0)["state"], "CLOSED")

    def test_explicit_arm_works_for_invented_receive_only(self):
        epoch = self.arm()
        self.assertGreater(epoch, 0)
        self.assertEqual(self.stream.reconcile()["state"], "ARMED_FIXTURE_ONLY")

    def test_each_synthetic_event_rechecks_before_queue(self):
        epoch = self.arm()
        self.assertEqual(self.queue(epoch)["state"], "QUEUED_FIXTURE_ONLY")
        self.store.revoke_fixture_grant("grant-a")
        result = self.queue(epoch, "fixture2")
        self.assertEqual(result["state"], "CANCELLED")

    def test_revoke_between_queue_and_consume_discards_pending(self):
        epoch = self.arm()
        self.queue(epoch)
        self.store.revoke_fixture_grant("grant-a")
        x = self.stream.consume_synthetic(epoch=epoch)
        self.assertEqual(x["state"], "CANCELLED")
        self.assertEqual(x["syntheticDeliveredCount"], 0)
        self.assertEqual(self.stream.consume_synthetic(epoch=x["epoch"])["state"], "CLOSED")

    def test_revoked_session_before_consume_discards_pending(self):
        epoch = self.arm()
        self.queue(epoch)
        self.host.active = False
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_organization_membership_rechecked_before_release(self):
        self.store.revoke_fixture_grant("grant-a")
        self.store.seed_fixture_grant(
            grant_id="org-a", principal_id="person-a", device_id="phone-a",
            line_id="company-line", owner_kind="ORGANIZATION",
            organization_id="org-a", operations=["messages.receive"],
            issued_at=80, expires_at=500,
        )
        epoch = self.arm(ownerKind="ORGANIZATION", organizationId="org-a",
                         lineId="company-line")
        self.queue(epoch)
        self.host.organizations = ()
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_wrong_person_session_principal_cancels(self):
        epoch = self.arm()
        self.queue(epoch)
        self.host.principal = "person-b"
        self.assertEqual(self.stream.reconcile()["state"], "CANCELLED")
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CLOSED")

    def test_grant_expiry_before_delivery_cancels(self):
        epoch = self.arm()
        self.queue(epoch)
        self.host.now = 500
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_session_expiry_before_delivery_cancels(self):
        epoch = self.arm()
        self.queue(epoch)
        self.host.expiry = 101
        self.host.now = 101
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CANCELLED")

    def test_clock_rollback_cancels(self):
        epoch = self.arm()
        self.host.now = 99
        self.assertEqual(self.queue(epoch)["state"], "CANCELLED")

    def test_new_device_does_not_inherit_old_grant(self):
        denied = self.stream.arm(request(deviceId="phone-b"))
        self.assertEqual(denied["state"], "REJECTED")
        self.arm()

    def test_new_line_does_not_inherit_old_grant(self):
        self.assertEqual(self.stream.arm(request(lineId="line-b"))["state"], "REJECTED")

    def test_personal_and_org_scopes_remain_distinct(self):
        self.assertEqual(
            self.stream.arm(request(ownerKind="ORGANIZATION",
                                    organizationId="org-a"))["state"], "REJECTED")

    def test_read_and_send_are_not_receive(self):
        for action in ("messages.read", "messages.send", "calls.audio"):
            self.assertEqual(self.stream.arm(request(operation=action))["state"], "REJECTED")

    def test_repeated_arm_does_not_silently_change_binding(self):
        epoch = self.arm()
        self.assertEqual(
            self.stream.arm(request(deviceId="phone-b"))["state"], "REJECTED")
        self.assertEqual(self.queue(epoch)["state"], "QUEUED_FIXTURE_ONLY")

    def test_cancel_erases_pending_and_invalidates_epoch(self):
        epoch = self.arm()
        self.queue(epoch)
        stopped = self.stream.cancel()
        self.assertEqual(stopped["state"], "CLOSED")
        self.assertNotEqual(stopped["epoch"], epoch)
        new_epoch = self.arm()
        self.assertEqual(self.stream.consume_synthetic(epoch=new_epoch)["state"], "EMPTY")
        self.assertEqual(self.queue(epoch, "old-event")["state"], "REJECTED")

    def test_context_switch_requires_explicit_cancel_then_arm(self):
        epoch = self.arm()
        self.assertEqual(self.stream.arm(request(lineId="line-b"))["state"], "REJECTED")
        self.stream.cancel()
        self.store.seed_fixture_grant(
            grant_id="grant-b", principal_id="person-a", device_id="phone-a",
            line_id="line-b", owner_kind="PERSONAL", organization_id=None,
            operations=["messages.receive"], issued_at=80, expires_at=500,
        )
        new_epoch = self.arm(lineId="line-b")
        self.assertNotEqual(new_epoch, epoch)
        self.assertEqual(self.queue(epoch)["state"], "REJECTED")

    def test_nonempty_event_only_produces_count_not_payload(self):
        epoch = self.arm()
        self.assertEqual(self.queue(epoch)["state"], "QUEUED_FIXTURE_ONLY")
        out = self.stream.consume_synthetic(epoch=epoch)
        self.assertEqual(out["state"], "CONSUMED_FIXTURE_ONLY")
        self.assertEqual(out["syntheticDeliveredCount"], 1)
        self.assertFalse(out["contentAccessEnabled"])
        self.assertNotIn("fixture1", str(out))

    def test_epoch_type_must_be_actual_int(self):
        epoch = self.arm()
        for invalid in (True, str(epoch), None, epoch + 1, -1):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.queue(invalid)["state"], "REJECTED")
                self.assertEqual(self.stream.consume_synthetic(epoch=invalid)["state"],
                                 "REJECTED")

    def test_disallow_message_body_or_phone_number_as_event_object(self):
        epoch = self.arm()
        for invalid in (
            {"body": "private fixture"}, ["msg"], None, b"body",
            "has spaces", "../other", "x" * 65, "",
            "real-recipient@example.com",
        ):
            with self.subTest(value=str(invalid)[:12]):
                self.assertEqual(
                    self.stream.queue_synthetic_event(event_ref=invalid, epoch=epoch)["state"],
                    "REJECTED",
                )

    def test_duplicate_pending_event_rejected_without_duplicate_delivery(self):
        epoch = self.arm()
        self.queue(epoch)
        self.assertEqual(self.queue(epoch)["state"], "REJECTED")
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["syntheticDeliveredCount"], 1)
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "EMPTY")

    def test_pending_limit_is_fail_closed_and_cancels(self):
        epoch = self.arm()
        for i in range(life.MAX_PENDING):
            self.assertEqual(self.queue(epoch, f"evt{i}")["state"], "QUEUED_FIXTURE_ONLY")
        denied = self.queue(epoch, "evt_extra")
        self.assertEqual(denied["state"], "CANCELLED")
        self.assertEqual(denied["syntheticDeliveredCount"], 0)
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CLOSED")

    def test_failing_grant_callback_cancels_and_clears(self):
        epoch = self.arm()
        self.queue(epoch)
        self.stream._check = lambda q: (_ for _ in ()).throw(
            RuntimeError("private verifier info"))
        out = self.stream.consume_synthetic(epoch=epoch)
        self.assertEqual(out["state"], "CANCELLED")
        self.assertNotIn("private verifier", str(out))

    def test_forged_allowed_response_is_not_accepted(self):
        for reply in (
            {"state": "ALLOWED"},
            {"state": "MATCHED_FIXTURE_ONLY", "execution": "PRODUCTION",
             "routeEligible": False, "contentAccessEnabled": False},
            {"state": "MATCHED_FIXTURE_ONLY", "execution": "FIXTURE_ONLY",
             "routeEligible": True, "contentAccessEnabled": False},
            {"state": "MATCHED_FIXTURE_ONLY", "execution": "FIXTURE_ONLY",
             "routeEligible": False, "contentAccessEnabled": True},
            None,
        ):
            with self.subTest(reply=reply):
                stream = life.PhoneSubscriptionLifecycleFixture(
                    check_grant=lambda q, reply=reply: reply)
                self.assertEqual(stream.arm(request())["state"], "REJECTED")

    def test_invalid_or_unknown_request_fields_are_rejected(self):
        for bad in (None, {}, [], request(principalId="person-a"),
                    request(schema="wrong"), request(operation="messages.read")):
            with self.subTest(bad=bad):
                self.assertEqual(self.stream.arm(bad)["state"], "REJECTED")

    def test_reconcile_clears_pending_immediately_after_revocation(self):
        epoch = self.arm()
        self.queue(epoch)
        self.store.revoke_fixture_grant("grant-a")
        result = self.stream.reconcile()
        self.assertEqual(result["state"], "CANCELLED")
        self.assertEqual(self.stream.consume_synthetic(epoch=epoch)["state"], "CLOSED")

    def test_all_results_are_content_and_scope_free(self):
        outputs = [self.stream.reconcile(), self.stream.cancel()]
        epoch = self.arm()
        outputs.extend([self.queue(epoch), self.stream.consume_synthetic(epoch=epoch)])
        expected = {"schema", "execution", "state", "epoch",
                    "syntheticDeliveredCount", "routeEligible", "contentAccessEnabled"}
        for out in outputs:
            self.assertEqual(set(out), expected)
            for sensitive in ("person-a", "phone-a", "line-a", "session-a", "grant-a",
                              "fixture1", "org-a"):
                self.assertNotIn(sensitive, str(out))
            self.assertEqual(out["execution"], "FIXTURE_ONLY")
            self.assertFalse(out["routeEligible"])
            self.assertFalse(out["contentAccessEnabled"])


if __name__ == "__main__":
    unittest.main()
