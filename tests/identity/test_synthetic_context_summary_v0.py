"""Identity Center read-only /me-context contract using SYNTHETIC verified sessions.

No HTTP listener, real IdP, production database, desktop UI or real credentials.
All data and fake sessions exist exclusively in this disposable test process.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from synthetic_policy_v0 import SyntheticPolicyStore
from synthetic_request_boundary_v0 import (
    CONTEXT_SCHEMA, SCHEMA, SyntheticRequestBoundary, VerifiedSession,
)


class FakeVerifier:
    """Trusted test setup only. NEVER a production identity verifier."""

    def __init__(self) -> None:
        self.sessions: dict[str, VerifiedSession] = {}
        self.revoked: set[str] = set()
        self.fail = False

    def verify(self, token: str, *, now: int) -> VerifiedSession | None:
        if self.fail:
            raise RuntimeError("Simulated protected verifier outage")
        return None if token in self.revoked else self.sessions.get(token)


class ContextSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SyntheticPolicyStore()
        self.addCleanup(self.store.close)
        for principal in ("operator", "charity", "customer", "portfolio_only"):
            self.store.seed_principal(principal)
        for org, kind in (("llc_a", "llc"), ("llc_b", "llc"),
                          ("nonprofit", "nonprofit"), ("customer_org", "customer")):
            self.store.seed_organization(org, kind)
            for division in ("health", "sales"):
                self.store.seed_division(org, division)
            for unit in ("maryland", "virginia"):
                self.store.seed_unit(org, unit)
            for div in ("health", "sales"):
                for unit in ("maryland", "virginia"):
                    self.store.seed_record(org, f"{div}_{unit}", div, unit)

        for p, org in (("operator", "llc_a"), ("operator", "llc_b"),
                       ("charity", "nonprofit"), ("customer", "customer_org")):
            self.store.seed_membership(p, org)
        self.store.seed_grant("llc-a-health", "operator", "llc_a",
                              "records.read", division_id="health")
        self.store.seed_grant("llc-b-md", "operator", "llc_b",
                              "records.read", unit_id="maryland")
        self.store.seed_grant("charity", "charity", "nonprofit", "records.read")
        self.store.seed_grant("customer", "customer", "customer_org",
                              "records.write")
        for name in ("family", "customer_group", "empty"):
            self.store.seed_portfolio(name)
        for org in ("llc_a", "llc_b", "nonprofit"):
            self.store.seed_portfolio_organization("family", org)
        self.store.seed_portfolio_organization("customer_group", "customer_org")
        self.store.seed_portfolio_organization("empty", "nonprofit")
        for person in ("operator", "charity", "portfolio_only"):
            self.store.seed_portfolio_member("family", person)
        self.store.seed_portfolio_member("customer_group", "operator")
        self.store.seed_portfolio_member("empty", "operator")

        self.now = 100
        self.verifier = FakeVerifier()
        for person in ("operator", "charity", "customer", "portfolio_only"):
            self.verifier.sessions["session-" + person] = VerifiedSession(
                principal_id=person, issuer="https://test-idp.invalid",
                audience="post-apollo-test", session_id="sid-" + person,
                issued_at=10, expires_at=200,
            )
        self.api = SyntheticRequestBoundary(
            self.store, verifier=self.verifier, clock=lambda: self.now,
            expected_issuer="https://test-idp.invalid",
            expected_audience="post-apollo-test",
        )

    def request(self, token: str = "session-operator") -> dict:
        return {"schema": SCHEMA, "operation": "readMyContexts",
                "accessToken": token}

    def summary(self, token: str = "session-operator") -> dict:
        return self.api.handle(self.request(token))

    def test_verifier_derived_person_gets_only_two_active_organizations(self):
        result = self.summary()
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["schema"], CONTEXT_SCHEMA)
        self.assertEqual([x["organizationId"] for x in result["organizations"]],
                         ["llc_a", "llc_b"])
        self.assertEqual([x["kind"] for x in result["organizations"]],
                         ["llc", "llc"])

    def test_function_and_location_scope_previews_are_distinct(self):
        orgs = self.summary()["organizations"]
        self.assertEqual(orgs[0]["scopeGrants"], [{
            "action": "records.read", "divisionId": "health",
            "unitId": None, "expiresAt": None,
        }])
        self.assertEqual(orgs[1]["scopeGrants"], [{
            "action": "records.read", "divisionId": None,
            "unitId": "maryland", "expiresAt": None,
        }])
        self.assertFalse(self.store.allowed(
            "operator", "llc_a", "sales_maryland", "records.read", now=self.now,
        ))

    def test_active_membership_does_not_imply_resource_access(self):
        self.store.seed_membership("operator", "customer_org")
        result = self.summary()
        org = next(o for o in result["organizations"]
                   if o["organizationId"] == "customer_org")
        self.assertEqual(org["scopeGrants"], [])
        self.assertFalse(self.store.allowed(
            "operator", "customer_org", "health_maryland",
            "records.read", now=self.now,
        ))

    def test_portfolio_view_shows_only_independently_joined_companies(self):
        result = self.summary()
        self.assertEqual(result["portfolios"], [{
            "portfolioId": "family", "organizationIds": ["llc_a", "llc_b"],
        }])
        self.assertNotIn("nonprofit", repr(result))
        self.assertNotIn("customer_org", repr(result))

    def test_portfolio_only_person_sees_no_tenant_info(self):
        result = self.summary("session-portfolio_only")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["organizations"], [])
        self.assertEqual(result["portfolios"], [])

    def test_nonprofit_worker_stays_out_of_llcs_and_other_tenants(self):
        result = self.summary("session-charity")
        self.assertEqual([o["organizationId"] for o in result["organizations"]],
                         ["nonprofit"])
        self.assertEqual(result["portfolios"], [{
            "portfolioId": "family", "organizationIds": ["nonprofit"],
        }])

    def test_unrelated_customer_does_not_learn_family_portfolio(self):
        result = self.summary("session-customer")
        self.assertEqual([o["organizationId"] for o in result["organizations"]],
                         ["customer_org"])
        self.assertEqual(result["portfolios"], [])
        self.assertNotIn("family", repr(result))
        self.assertNotIn("llc_a", repr(result))

    def test_expiring_grant_is_excluded_exactly_at_expiry(self):
        self.store.seed_grant("short", "operator", "llc_a", "records.write",
                              division_id="sales", unit_id="virginia",
                              expires_at=101)
        self.assertEqual(len(self.summary()["organizations"][0]["scopeGrants"]), 2)
        self.now = 101
        self.assertEqual(len(self.summary()["organizations"][0]["scopeGrants"]), 1)

    def test_grant_scopes_remain_intersection_in_readonly_preview(self):
        self.store.seed_grant("narrow", "operator", "llc_a", "records.write",
                              division_id="sales", unit_id="virginia")
        grants = self.summary()["organizations"][0]["scopeGrants"]
        self.assertIn({"action": "records.write", "divisionId": "sales",
                       "unitId": "virginia", "expiresAt": None}, grants)
        self.assertFalse(self.store.allowed(
            "operator", "llc_a", "sales_maryland", "records.write", now=self.now,
        ))

    def test_revoking_one_tenant_keeps_another_and_recalculates_portfolio(self):
        self.store.revoke_membership("operator", "llc_a")
        result = self.summary()
        self.assertEqual([o["organizationId"] for o in result["organizations"]],
                         ["llc_b"])
        self.assertEqual(result["portfolios"], [{
            "portfolioId": "family", "organizationIds": ["llc_b"],
        }])

    def test_revoked_token_is_denied_not_empty_success(self):
        self.verifier.revoked.add("session-operator")
        self.assertEqual(self.summary(), {"status": "DENIED"})

    def test_expired_or_future_issued_token_is_denied(self):
        self.now = 200
        self.assertEqual(self.summary(), {"status": "DENIED"})
        self.now = 100
        old = self.verifier.sessions["session-operator"]
        self.verifier.sessions["session-operator"] = replace(old, issued_at=150)
        self.assertEqual(self.summary(), {"status": "DENIED"})

    def test_untrusted_request_cannot_supply_person_role_org_or_time(self):
        for name, val in (("principalId", "charity"), ("organizationId", "nonprofit"),
                          ("portfolioId", "family"), ("role", "admin"),
                          ("now", 12), ("scope", "all")):
            with self.subTest(name=name):
                req = self.request()
                req[name] = val
                self.assertEqual(self.api.handle(req), {"status": "DENIED"})

    def test_invalid_sessions_and_verifier_outage_fail_closed(self):
        for token in ("", None, {}, "fake", "session-operator "):
            with self.subTest(token=type(token).__name__):
                self.assertEqual(self.api.handle(self.request(token)),
                                 {"status": "DENIED"})
        self.verifier.fail = True
        self.assertEqual(self.summary(), {"status": "DENIED"})

    def test_wrong_issuer_audience_or_clock_denies(self):
        orig = self.verifier.sessions["session-operator"]
        for attrs in ({"issuer": "https://wrong.invalid"},
                      {"audience": "other-api"}):
            self.verifier.sessions["session-operator"] = replace(orig, **attrs)
            self.assertEqual(self.summary(), {"status": "DENIED"})
        self.verifier.sessions["session-operator"] = orig
        for value in (-1, True, None, "100"):
            self.api._clock = lambda v=value: v
            self.assertEqual(self.summary(), {"status": "DENIED"})

    def test_duplicate_equivalent_grants_do_not_duplicate_visible_scope(self):
        self.store.seed_grant("llc-a-health-dup", "operator", "llc_a",
                              "records.read", division_id="health")
        self.assertEqual(len(self.summary()["organizations"][0]["scopeGrants"]), 1)

    def test_subject_not_exposed_and_token_not_echoed(self):
        result = self.summary()
        self.assertNotIn("principalId", result)
        self.assertNotIn("subject", result)
        self.assertNotIn("accessToken", result)
        self.assertNotIn("session-operator", repr(result))
        self.assertNotIn("grantId", repr(result))

    def test_summary_is_read_only_and_cannot_mutate_grants(self):
        req = self.request()
        req["operation"] = "grantWrite"
        self.assertEqual(self.api.handle(req), {"status": "DENIED"})
        before = self.summary()
        self.assertEqual(self.summary(), before)
        self.assertFalse(self.store.allowed(
            "operator", "llc_a", "sales_virginia",
            "records.write", now=self.now,
        ))

    def test_existing_request_operations_keep_original_behavior(self):
        record = {"schema": SCHEMA, "operation": "authorizeRecord",
                  "accessToken": "session-operator", "organizationId": "llc_a",
                  "recordId": "health_maryland", "action": "records.read"}
        self.assertEqual(self.api.handle(record), {"status": "ALLOWED"})
        portfolio = {"schema": SCHEMA,
                     "operation": "listPortfolioOrganizations",
                     "accessToken": "session-operator", "portfolioId": "family"}
        self.assertEqual(self.api.handle(portfolio),
                         {"status": "OK", "organizationIds": ["llc_a", "llc_b"]})


if __name__ == "__main__":
    unittest.main()
