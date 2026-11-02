"""Offline P1 Phone Bridge grant fixture tests. No identity/phone system."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import TrustedPhoneGrantFixture as phone  # noqa: E402


class Clock:
    now = 100

    def __call__(self):
        return self.now


class Sessions:
    def __init__(self):
        self.active = True
        self.principal = "person-a"
        self.memberships = ("org-a",)
        self.expiry = 800

    def __call__(self, ref, now):
        if not self.active or ref != "session-a":
            return None
        return phone.HostVerifiedPhoneContext(
            principal_id=self.principal, session_ref=ref,
            expires_at=self.expiry, authorized_organizations=self.memberships,
        )


def request(**changes):
    result = {
        "schema": phone.SCHEMA, "sessionRef": "session-a",
        "deviceId": "android-a", "lineId": "personal-line",
        "ownerKind": "PERSONAL", "organizationId": None,
        "operation": "messages.receive",
    }
    result.update(changes)
    return result


def grant(*, fixture, grant_id="grant-a", **changes):
    details = {
        "grant_id": grant_id, "principal_id": "person-a",
        "device_id": "android-a", "line_id": "personal-line",
        "owner_kind": "PERSONAL", "organization_id": None,
        "operations": ["messages.receive"],
        "issued_at": 50, "expires_at": 500,
    }
    details.update(changes)
    fixture.seed_fixture_grant(**details)


class PhoneGrantFixtureTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.sessions = Sessions()
        self.store = phone.TrustedPhoneGrantFixture(
            clock=self.clock, resolve_session=self.sessions)

    def assertMatched(self, q):
        decision = self.store.check(q)
        self.assertEqual(decision["state"], "MATCHED_FIXTURE_ONLY")
        self.assertEqual(decision["execution"], "FIXTURE_ONLY")
        self.assertIs(decision["routeEligible"], False)
        self.assertIs(decision["contentAccessEnabled"], False)

    def assertDenied(self, q):
        result = self.store.check(q)
        self.assertEqual(result["state"], "DENIED")
        self.assertFalse(result["routeEligible"])
        self.assertFalse(result["contentAccessEnabled"])

    def test_no_grant_defaults_to_denial(self):
        self.assertDenied(request())

    def test_exact_personal_scope_matches_fixture_but_never_authorizes(self):
        grant(fixture=self.store)
        self.assertMatched(request())

    def test_revocation_is_visible_on_next_check(self):
        grant(fixture=self.store)
        self.assertMatched(request())
        self.assertTrue(self.store.revoke_fixture_grant("grant-a"))
        self.assertDenied(request())

    def test_revoke_is_idempotent_and_refuses_bad_ids(self):
        grant(fixture=self.store)
        self.assertTrue(self.store.revoke_fixture_grant("grant-a"))
        self.assertFalse(self.store.revoke_fixture_grant("grant-a"))
        self.assertFalse(self.store.revoke_fixture_grant("../other"))

    def test_other_device_cannot_inherit_grant(self):
        grant(fixture=self.store)
        self.assertDenied(request(deviceId="android-b"))

    def test_other_line_cannot_inherit_grant(self):
        grant(fixture=self.store)
        self.assertDenied(request(lineId="company-line"))

    def test_other_principal_cannot_inherit_grant(self):
        grant(fixture=self.store)
        self.sessions.principal = "person-b"
        self.assertDenied(request())

    def test_org_scope_does_not_inherit_personal_scope(self):
        grant(fixture=self.store)
        self.assertDenied(request(ownerKind="ORGANIZATION", organizationId="org-a"))

    def test_personal_scope_does_not_inherit_org_scope(self):
        grant(fixture=self.store, owner_kind="ORGANIZATION",
              organization_id="org-a", line_id="company-line")
        self.assertDenied(request())
        self.assertMatched(request(ownerKind="ORGANIZATION",
                                   organizationId="org-a", lineId="company-line"))

    def test_org_membership_does_not_create_phone_grant(self):
        self.assertDenied(request(ownerKind="ORGANIZATION", organizationId="org-a"))

    def test_cross_tenant_grants_are_not_portfolio_wildcards(self):
        grant(fixture=self.store, owner_kind="ORGANIZATION", organization_id="org-a",
              line_id="company-line")
        self.sessions.memberships = ("org-a", "org-b")
        self.assertDenied(request(ownerKind="ORGANIZATION",
                                  organizationId="org-b", lineId="company-line"))
        self.assertMatched(request(ownerKind="ORGANIZATION",
                                   organizationId="org-a", lineId="company-line"))

    def test_revoked_org_membership_prevents_use_of_stored_grant(self):
        grant(fixture=self.store, owner_kind="ORGANIZATION", organization_id="org-a",
              line_id="company-line")
        self.assertMatched(request(ownerKind="ORGANIZATION",
                                   organizationId="org-a", lineId="company-line"))
        self.sessions.memberships = ()
        self.assertDenied(request(ownerKind="ORGANIZATION",
                                  organizationId="org-a", lineId="company-line"))

    def test_operation_grants_do_not_cross_from_receive_to_read_or_send(self):
        grant(fixture=self.store)
        for other in ["messages.read", "messages.send", "contacts.read",
                      "calls.dial", "calls.audio", "notifications.receive"]:
            with self.subTest(other=other):
                self.assertDenied(request(operation=other))

    def test_additional_explicit_operation_is_only_fixture_match(self):
        grant(fixture=self.store, operations=["messages.receive", "messages.read"])
        self.assertMatched(request(operation="messages.read"))
        self.assertDenied(request(operation="messages.send"))

    def test_grant_expiry_is_exclusive(self):
        grant(fixture=self.store, expires_at=110)
        self.clock.now = 109
        self.assertMatched(request())
        self.clock.now = 110
        self.assertDenied(request())

    def test_session_expiry_blocks_nonexpired_grant(self):
        grant(fixture=self.store)
        self.sessions.expiry = 110
        self.clock.now = 109
        self.assertMatched(request())
        self.clock.now = 110
        self.assertDenied(request())

    def test_explicit_session_deactivation_blocks_next_event(self):
        grant(fixture=self.store)
        self.assertMatched(request())
        self.sessions.active = False
        self.assertDenied(request())

    def test_client_cannot_claim_its_own_principal_or_membership(self):
        grant(fixture=self.store)
        self.assertDenied(request(principalId="person-a"))
        self.assertDenied(request(portfolioId="portfolio-a"))
        self.assertDenied(request(grantId="grant-a"))

    def test_invalid_schema_and_opaque_identifiers_fail_closed(self):
        grant(fixture=self.store)
        for item in [request(schema="other"), request(sessionRef="../session"),
                     request(deviceId=""), request(lineId="phone:other"),
                     request(sessionRef=1), request(operation="messages.delete")]:
            with self.subTest(item=item):
                self.assertDenied(item)

    def test_bad_personal_and_org_scope_are_rejected(self):
        grant(fixture=self.store)
        for item in [request(organizationId="org-a"),
                     request(ownerKind="ORGANIZATION", organizationId=None),
                     request(ownerKind="PORTFOLIO", organizationId=None),
                     request(ownerKind="ORGANIZATION", organizationId="../org")]:
            with self.subTest(item=item):
                self.assertDenied(item)

    def test_malformed_request_never_raises_or_echoes_secrets(self):
        for item in (None, [], "secret", {}, {"schema": phone.SCHEMA}, 1):
            with self.subTest(item=item):
                decision = self.store.check(item)
                self.assertEqual(decision["state"], "DENIED")
                self.assertEqual(set(decision),
                                 {"schema", "execution", "state",
                                  "routeEligible", "contentAccessEnabled"})

    def test_duplicate_grant_ids_and_ambiguous_matches_fail(self):
        grant(fixture=self.store)
        with self.assertRaises(ValueError):
            grant(fixture=self.store)
        grant(fixture=self.store, grant_id="grant-b")
        self.assertDenied(request())

    def test_grant_seed_refuses_invalid_operations_and_unbounded_ttl(self):
        cases = [
            {"operations": []}, {"operations": ["messages.receive", "messages.receive"]},
            {"operations": ["messages.erase"]}, {"operations": "messages.receive"},
            {"issued_at": 100, "expires_at": 100},
            {"issued_at": 100, "expires_at": 1001},
            {"expires_at": True}, {"principal_id": "person/a"},
            {"owner_kind": "PERSONAL", "organization_id": "org-a"},
            {"owner_kind": "ORGANIZATION", "organization_id": None},
        ]
        for i, change in enumerate(cases):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    grant(fixture=self.store, grant_id=f"bad-{i}", **change)

    def test_signed_in_org_membership_must_be_valid_unique_bounded(self):
        grant(fixture=self.store, owner_kind="ORGANIZATION",
              organization_id="org-a", line_id="company-line")
        q = request(ownerKind="ORGANIZATION", organizationId="org-a",
                    lineId="company-line")
        for memberships in (("org-a", "org-a"), ("../org",),
                            tuple(f"org{i}" for i in range(65)),
                            ["org-a"]):
            with self.subTest(memberships=memberships):
                self.sessions.memberships = memberships
                self.assertDenied(q)

    def test_bad_or_unverified_session_context_is_denied(self):
        grant(fixture=self.store)
        self.assertDenied(request(sessionRef="unknown"))
        self.sessions.principal = "../other"
        self.assertDenied(request())

    def test_clock_rollback_denies_instead_of_reusing_old_access(self):
        grant(fixture=self.store)
        self.assertMatched(request())
        self.clock.now = 99
        self.assertDenied(request())

    def test_invalid_clock_and_resolver_exceptions_are_denials(self):
        grant(fixture=self.store)
        for value in (True, "100", -1, None):
            self.store._clock = lambda value=value: value
            self.assertDenied(request())
        self.store._clock = self.clock
        self.store._resolve = lambda ref, now: (_ for _ in ()).throw(
            ValueError("private verifier info"))
        self.assertDenied(request())

    def test_no_phone_content_or_identifiers_in_decision(self):
        grant(fixture=self.store)
        result = self.store.check(request())
        self.assertEqual(set(result), {
            "schema", "execution", "state", "routeEligible", "contentAccessEnabled"
        })
        for secret in ("person-a", "session-a", "android-a",
                       "personal-line", "grant-a", "org-a"):
            self.assertNotIn(secret, str(result))

    def test_no_grant_without_session_callback_even_if_grant_exists(self):
        grant(fixture=self.store)
        self.store._resolve = lambda ref, now: None
        self.assertDenied(request())


if __name__ == "__main__":
    unittest.main()
