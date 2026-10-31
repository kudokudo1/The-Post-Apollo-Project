"""Synthetic request-boundary contract tests. No network, keys or real IdP."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

IDENTITY_SOURCE = Path(__file__).resolve().parents[2] / "services/identity"
sys.path.insert(0, str(IDENTITY_SOURCE))
import synthetic_policy_v0 as policy
import synthetic_request_boundary_v0 as boundary


class FakeIdPVerifier:
    """Only a disposable test double. Never substitute for real token validation."""

    def __init__(self) -> None:
        self.sessions: dict[str, boundary.VerifiedSession] = {}
        self.revoked: set[str] = set()
        self.raise_error = False

    def verify(self, token: str, *, now: int) -> boundary.VerifiedSession | None:
        if self.raise_error:
            raise RuntimeError("Simulated verifier outage; must fail closed")
        if token in self.revoked:
            return None
        return self.sessions.get(token)


class RequestBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = policy.SyntheticPolicyStore()
        self.addCleanup(self.store.close)
        for p in ("director", "charity_worker", "customer_worker"):
            self.store.seed_principal(p)
        for org, kind in (("llc_a", "llc"), ("llc_b", "llc"),
                          ("nonprofit", "nonprofit"), ("customer", "customer")):
            self.store.seed_organization(org, kind)
            for division in ("health", "sales"):
                self.store.seed_division(org, division)
            for unit in ("md", "va"):
                self.store.seed_unit(org, unit)
            for division in ("health", "sales"):
                for unit in ("md", "va"):
                    self.store.seed_record(org, f"{division}_{unit}", division, unit)

        self.store.seed_membership("director", "llc_a")
        self.store.seed_membership("director", "llc_b")
        self.store.seed_membership("charity_worker", "nonprofit")
        self.store.seed_membership("customer_worker", "customer")
        self.store.seed_grant("a-health", "director", "llc_a", "records.read",
                              division_id="health")
        self.store.seed_grant("b-md", "director", "llc_b", "records.read",
                              unit_id="md")
        self.store.seed_grant("np-health", "charity_worker", "nonprofit",
                              "records.read", division_id="health")
        self.store.seed_grant("customer-all", "customer_worker", "customer",
                              "records.read")

        self.store.seed_portfolio("family")
        self.store.seed_portfolio_member("family", "director")
        self.store.seed_portfolio_member("family", "charity_worker")
        for org in ("llc_a", "llc_b", "nonprofit"):
            self.store.seed_portfolio_organization("family", org)

        self.now = 100
        self.verifier = FakeIdPVerifier()
        for token, person in (("opaque-director", "director"),
                              ("opaque-charity", "charity_worker"),
                              ("opaque-customer", "customer_worker")):
            self.verifier.sessions[token] = boundary.VerifiedSession(
                principal_id=person,
                issuer="https://synthetic-idp.invalid",
                audience="post-apollo-test-api",
                session_id=f"session-{person}",
                issued_at=10,
                expires_at=200,
            )
        self.api = boundary.SyntheticRequestBoundary(
            self.store, verifier=self.verifier, clock=lambda: self.now,
            expected_issuer="https://synthetic-idp.invalid",
            expected_audience="post-apollo-test-api",
        )

    def access(self, token="opaque-director", org="llc_a",
               record="health_md", action="records.read"):
        return dict(schema=boundary.SCHEMA, operation="authorizeRecord",
                    accessToken=token, organizationId=org,
                    recordId=record, action=action)

    def portfolio(self, token="opaque-director", portfolio_id="family"):
        return dict(schema=boundary.SCHEMA,
                    operation="listPortfolioOrganizations",
                    accessToken=token, portfolioId=portfolio_id)

    def test_valid_verified_identity_can_read_granted_resource(self):
        self.assertEqual(self.api.handle(self.access()), {"status": "ALLOWED"})
        self.assertEqual(self.api.handle(self.access(org="llc_b", record="sales_md")),
                         {"status": "ALLOWED"})

    def test_denied_ungranted_division_and_geography(self):
        self.assertEqual(self.api.handle(self.access(record="sales_md")),
                         {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access(org="llc_b", record="health_va")),
                         {"status": "DENIED"})

    def test_forged_company_context_remains_denied(self):
        self.assertEqual(self.api.handle(self.access(org="nonprofit")),
                         {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access(org="customer")),
                         {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access(token="opaque-customer",
                                                    org="llc_a")),
                         {"status": "DENIED"})

    def test_client_cannot_override_verified_principal_or_roles(self):
        for value in ("charity_worker", "director", "admin"):
            request = self.access(token="opaque-customer", org="llc_a")
            request["principalId"] = value
            self.assertEqual(self.api.handle(request), {"status": "DENIED"})
            request = self.access(token="opaque-customer", org="llc_a")
            request["role"] = value
            self.assertEqual(self.api.handle(request), {"status": "DENIED"})

    def test_missing_unknown_malformed_tokens_fail_closed(self):
        for token in ("", None, {}, "nonexistent", " director ", "x" * 8193):
            with self.subTest(token_type=type(token).__name__):
                self.assertEqual(self.api.handle(self.access(token=token)),
                                 {"status": "DENIED"})

    def test_revoked_session_fails_closed_without_removing_other_user(self):
        self.verifier.revoked.add("opaque-director")
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access(token="opaque-customer",
                                                     org="customer")),
                         {"status": "ALLOWED"})

    def test_expired_token_rejected_even_when_grant_is_active(self):
        self.now = 200
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})

    def test_future_issued_and_bad_claims_are_rejected(self):
        v = self.verifier.sessions["opaque-director"]
        for changed in (
            {"issued_at": 101}, {"issued_at": -1},
            {"expires_at": 10}, {"expires_at": True},
            {"principal_id": ""}, {"session_id": ""},
            {"audience": "other-api"}, {"issuer": "https://other.invalid"},
            {"issued_at": "10"},
        ):
            self.verifier.sessions["opaque-director"] = replace(v, **changed)
            with self.subTest(changed=changed):
                self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})
        self.verifier.sessions["opaque-director"] = v

    def test_verifier_outage_never_allows_access_or_leaks_info(self):
        self.verifier.raise_error = True
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})

    def test_unsupported_operation_and_extra_fields_fail_closed(self):
        for request in (
            {}, None, [], "hello", dict(self.access(), operation="grantAdmin"),
            dict(self.access(), arbitrary=True),
            dict(self.access(), schema="other"),
            dict(self.access(), action="records.admin"),
        ):
            with self.subTest(kind=str(type(request))):
                self.assertEqual(self.api.handle(request), {"status": "DENIED"})

    def test_source_time_not_client_supplied(self):
        injected = dict(self.access(), now=10)
        self.now = 300
        self.assertEqual(self.api.handle(injected), {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})

    def test_invalid_server_clock_denied_without_error(self):
        for bad in (True, "100", -1, None):
            self.api._clock = lambda bad=bad: bad
            self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})
        def fail_clock():
            raise RuntimeError("No trusted clock")
        self.api._clock = fail_clock
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})

    def test_portfolio_listing_requires_verified_identity_and_membership(self):
        self.assertEqual(self.api.handle(self.portfolio()),
                         {"status": "OK", "organizationIds": ["llc_a", "llc_b"]})
        self.assertEqual(self.api.handle(self.portfolio(token="opaque-charity")),
                         {"status": "OK", "organizationIds": ["nonprofit"]})
        self.assertEqual(self.api.handle(self.portfolio(token="opaque-customer")),
                         {"status": "OK", "organizationIds": []})

    def test_portfolio_is_not_record_access(self):
        self.assertEqual(self.api.handle(self.portfolio()),
                         {"status": "OK", "organizationIds": ["llc_a", "llc_b"]})
        self.assertEqual(self.api.handle(self.access(org="nonprofit")),
                         {"status": "DENIED"})

    def test_revoking_tenant_membership_only_removes_that_tenant(self):
        self.store.revoke_membership("director", "llc_a")
        self.assertEqual(self.api.handle(self.access()), {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.access(org="llc_b", record="sales_md")),
                         {"status": "ALLOWED"})
        self.assertEqual(self.api.handle(self.portfolio()),
                         {"status": "OK", "organizationIds": ["llc_b"]})

    def test_revoked_portfolio_user_session_has_no_visible_orgs(self):
        self.verifier.revoked.add("opaque-director")
        self.assertEqual(self.api.handle(self.portfolio()), {"status": "DENIED"})

    def test_provider_must_be_injected_with_valid_issuer_audience_clock(self):
        with self.assertRaises(ValueError):
            boundary.SyntheticRequestBoundary(
                self.store, verifier=object(), clock=lambda: 100,
                expected_issuer="x", expected_audience="y")
        with self.assertRaises(ValueError):
            boundary.SyntheticRequestBoundary(
                self.store, verifier=self.verifier, clock=None,
                expected_issuer="x", expected_audience="y")
        with self.assertRaises(ValueError):
            boundary.SyntheticRequestBoundary(
                self.store, verifier=self.verifier, clock=lambda: 100,
                expected_issuer="", expected_audience="y")


if __name__ == "__main__":
    unittest.main()
