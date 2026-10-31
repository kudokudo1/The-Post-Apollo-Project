"""Offline permission-gate tests; synthetic entities only, no real credentials."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/identity/synthetic_policy_v0.py"
spec = importlib.util.spec_from_file_location("synthetic_identity_policy", SOURCE)
assert spec and spec.loader
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class SyntheticIdentityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = policy.SyntheticPolicyStore()
        self.addCleanup(self.db.close)

        for person in ("operator", "nonprofit_staff", "customer_user"):
            self.db.seed_principal(person)
        for org, kind in (
            ("llc_a", "llc"), ("llc_b", "llc"),
            ("nonprofit", "nonprofit"), ("customer", "customer"),
        ):
            self.db.seed_organization(org, kind)
        for org in ("llc_a", "llc_b", "nonprofit", "customer"):
            for division in ("health", "sales"):
                self.db.seed_division(org, division)
            for unit in ("maryland", "virginia"):
                self.db.seed_unit(org, unit)
            for division, unit in (("health", "maryland"), ("health", "virginia"),
                                   ("sales", "maryland"), ("sales", "virginia")):
                self.db.seed_record(org, f"{division}_{unit}", division, unit)

        self.db.seed_membership("operator", "llc_a")
        self.db.seed_membership("operator", "llc_b")
        self.db.seed_membership("nonprofit_staff", "nonprofit")
        self.db.seed_membership("customer_user", "customer")

        self.db.seed_portfolio("family")
        self.db.seed_portfolio("independent")
        for org in ("llc_a", "llc_b", "nonprofit"):
            self.db.seed_portfolio_organization("family", org)
        self.db.seed_portfolio_organization("independent", "customer")
        self.db.seed_portfolio_member("family", "operator")
        self.db.seed_portfolio_member("family", "nonprofit_staff")
        self.db.seed_portfolio_member("independent", "operator")

        # Operator has healthcare nationwide in A, Maryland only in B.
        self.db.seed_grant("a_health", "operator", "llc_a",
                           "records.read", division_id="health")
        self.db.seed_grant("b_maryland", "operator", "llc_b",
                           "records.read", unit_id="maryland")
        self.db.seed_grant("charity_read", "nonprofit_staff", "nonprofit",
                           "records.read", division_id="health")
        self.db.seed_grant("customer_read", "customer_user", "customer",
                           "records.read")

    def can(self, who: str, org: str, record: str,
            action: str = "records.read", now: int = 100) -> bool:
        return self.db.allowed(who, org, record, action, now=now)

    def test_multi_org_person_and_independent_scopes(self):
        self.assertTrue(self.can("operator", "llc_a", "health_maryland"))
        self.assertTrue(self.can("operator", "llc_a", "health_virginia"))
        self.assertFalse(self.can("operator", "llc_a", "sales_maryland"))
        self.assertTrue(self.can("operator", "llc_b", "sales_maryland"))
        self.assertFalse(self.can("operator", "llc_b", "sales_virginia"))

    def test_unrelated_customer_isolated_from_family(self):
        self.assertFalse(self.can("operator", "customer", "health_maryland"))
        self.assertFalse(self.can("customer_user", "llc_a", "health_maryland"))
        self.assertTrue(self.can("customer_user", "customer", "health_maryland"))

    def test_portfolio_membership_is_not_a_tenant_grant(self):
        self.assertEqual(self.db.visible_portfolio_orgs("operator", "family"),
                         ("llc_a", "llc_b"))
        self.assertEqual(self.db.visible_portfolio_orgs("nonprofit_staff", "family"),
                         ("nonprofit",))
        self.assertEqual(self.db.visible_portfolio_orgs("operator", "independent"), ())
        self.assertFalse(self.can("operator", "nonprofit", "health_maryland"))

    def test_unassigned_portfolio_is_invisible(self):
        self.assertEqual(self.db.visible_portfolio_orgs("customer_user", "family"), ())
        self.assertEqual(self.db.visible_portfolio_orgs("customer_user", "independent"), ())

    def test_revoke_one_membership_preserves_other_organization(self):
        self.db.revoke_membership("operator", "llc_a")
        self.assertFalse(self.can("operator", "llc_a", "health_maryland"))
        self.assertTrue(self.can("operator", "llc_b", "sales_maryland"))
        self.assertEqual(self.db.visible_portfolio_orgs("operator", "family"),
                         ("llc_b",))

    def test_revoked_membership_blocks_old_grants(self):
        self.db.revoke_membership("nonprofit_staff", "nonprofit")
        self.assertFalse(self.can("nonprofit_staff", "nonprofit", "health_maryland"))
        self.assertEqual(self.db.visible_portfolio_orgs("nonprofit_staff", "family"), ())

    def test_grant_expiry_is_exclusive_and_server_time_required(self):
        self.db.seed_grant("short", "operator", "llc_a", "records.read",
                           division_id="sales", expires_at=101)
        self.assertTrue(self.can("operator", "llc_a", "sales_virginia", now=100))
        self.assertFalse(self.can("operator", "llc_a", "sales_virginia", now=101))
        self.assertFalse(self.db.allowed("operator", "llc_a", "sales_virginia",
                                         "records.read", now=True))
        self.assertFalse(self.can("operator", "llc_a", "sales_virginia", now=-1))

    def test_function_and_geography_are_intersection_not_union(self):
        self.db.seed_grant("narrow", "operator", "llc_a", "records.write",
                           division_id="sales", unit_id="virginia")
        self.assertTrue(self.can("operator", "llc_a", "sales_virginia",
                                 "records.write"))
        self.assertFalse(self.can("operator", "llc_a", "sales_maryland",
                                  "records.write"))
        self.assertFalse(self.can("operator", "llc_a", "health_virginia",
                                  "records.write"))

    def test_read_does_not_imply_write_or_admin(self):
        self.assertTrue(self.can("operator", "llc_a", "health_maryland",
                                 "records.read"))
        self.assertFalse(self.can("operator", "llc_a", "health_maryland",
                                  "records.write"))
        self.assertFalse(self.can("operator", "llc_a", "health_maryland",
                                  "records.admin"))

    def test_unknown_principal_tenant_resource_fail_closed(self):
        self.assertFalse(self.can("missing", "llc_a", "health_maryland"))
        self.assertFalse(self.can("operator", "unknown_org", "health_maryland"))
        self.assertFalse(self.can("operator", "llc_a", "unknown_record"))
        self.assertFalse(self.can("operator", "llc_a", "' OR 1=1 --"))

    def test_malformed_values_fail_closed_without_sqlite_exception(self):
        self.assertFalse(self.db.allowed([], "llc_a", "health_maryland",
                                         "records.read", now=100))
        self.assertFalse(self.db.allowed("operator", {}, "health_maryland",
                                         "records.read", now=100))
        self.assertFalse(self.db.allowed("operator", "llc_a", None,
                                         "records.read", now=100))
        self.assertFalse(self.db.allowed("operator", "llc_a", "health_maryland",
                                         [], now=100))
        self.assertEqual(self.db.visible_portfolio_orgs([], "family"), ())
        self.assertEqual(self.db.visible_portfolio_orgs("operator", {}), ())

    def test_client_selected_org_cannot_redirect_to_another_tenant(self):
        self.assertFalse(self.can("operator", "customer", "health_maryland"))
        self.assertFalse(self.can("customer_user", "llc_b", "sales_maryland"))

    def test_database_fails_closed_on_cross_tenant_resource_links(self):
        # Function exists only in A; a resource in B cannot point to it.
        self.db.seed_division("llc_a", "private_only_a")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.seed_record("llc_b", "invalid", "private_only_a",
                                "maryland")

    def test_database_refuses_grant_for_other_tenant_or_nonmember(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.seed_grant("cross", "operator", "customer", "records.read")
        self.db.seed_division("llc_a", "private_only_a")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.seed_grant("bad_scope", "operator", "llc_b", "records.read",
                               division_id="private_only_a")

    def test_org_wide_grant_never_crosses_organizations(self):
        self.db.seed_grant("all_in_a", "operator", "llc_a", "records.read")
        self.assertTrue(self.can("operator", "llc_a", "sales_virginia"))
        self.assertFalse(self.can("operator", "nonprofit", "sales_virginia"))
        self.assertFalse(self.can("operator", "customer", "sales_virginia"))


if __name__ == "__main__":
    unittest.main()
