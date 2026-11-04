"""Direct removal of active or archived labels with no mandatory backups."""
from __future__ import annotations
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/social"))
import SocialLocalOrgArchivedRemoval as removal
import SocialLocalOrgBackup as backup
import SocialOrganizationDirectory as directory
import SocialLocalPortfolios as portfolio
import SocialLocalOrganizationStructure as structure
import SocialOrganizationLinks as social
import SocialLocalUnitLocationLinks as unit_locations
import SocialLocalBranchLocationLinks as branch_locations
import SocialLocalFunctionalReporting as reporting


class ArchivedRemoval(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fake-archived-remove-")
        self.previous = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = self.temp.name

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = self.previous
        self.temp.cleanup()

    def save_org(self, *, archived=True, branches=None):
        directory.save({
            "schema": directory.SCHEMA, "revision": 1, "nextId": 3,
            "organizations": [{"id": "org-1", "name": "Sample Company",
                               "kind": "llc", "archived": archived,
                               "branches": branches or []}],
        })

    def save_portfolio(self, *, members=None, archived=True):
        portfolio.save({
            "schema": portfolio.SCHEMA, "revision": 1, "nextId": 2,
            "portfolios": [{"id": "portfolio-1", "name": "Sample Group",
                            "archived": archived, "orgIds": members or []}],
        })

    def save_unit(self, *, archived=True):
        structure.save({
            "schema": structure.SCHEMA, "revision": 1, "nextId": 2,
            "units": [{"id": "unit-1", "orgId": "org-1", "kind": "division",
                       "name": "Sample Unit", "archived": archived}],
        })

    def request(self, kind, ident, name, *, org_id="", revision=1):
        return {"action": "remove", "kind": kind, "id": ident,
                "orgId": org_id, "expectedName": name,
                "expectedRevision": revision}

    def test_no_archive_or_backup_requirement(self):
        self.save_org(archived=False)
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        result = removal.remove(req)
        self.assertTrue(result["ok"])
        self.assertEqual(result["revision"], 2)
        self.assertEqual(directory.load()["organizations"], [])
        self.assertEqual(directory.load()["nextId"], 3)
        # No snapshot was generated during deletion.
        self.assertEqual(backup.names(), [])
        with self.assertRaisesRegex(removal.RemovalError, "REVISION_CONFLICT"):
            removal.remove(req)

    def test_archived_record_can_also_be_removed_without_backup(self):
        self.save_org(archived=True)
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(directory.load()["organizations"], [])

    def test_old_backup_is_irrelevant_to_direct_removal(self):
        backup.make_backup()  # Optional earlier empty snapshot.
        self.save_org()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(directory.load()["organizations"], [])

    def test_org_with_branches_units_or_portfolio_members_fails_closed(self):
        branch = {"id": "branch-2", "name": "Sample Branch", "archived": True}
        self.save_org(branches=[branch])
        backup.make_backup()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "REMOVE_BRANCHES_FIRST"):
            removal.remove(req)
        self.save_org()
        self.save_unit()
        with self.assertRaisesRegex(removal.RemovalError, "REMOVE_UNITS_FIRST"):
            removal.remove(req)
        structure.save(structure.initial())
        self.save_portfolio(members=["org-1"], archived=True)
        with self.assertRaisesRegex(removal.RemovalError, "DETACH_PORTFOLIOS_FIRST"):
            removal.remove(req)

    def test_branch_unlinked_social_guard_without_backup_requirement(self):
        self.save_org(archived=False, branches=[
            {"id": "branch-2", "name": "Sample Branch", "archived": True}])
        req = self.request("branch", "branch-2", "Sample Branch", org_id="org-1")
        social.save({
            "schema": social.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "link-1", "orgId": "org-1", "branchId": "branch-2",
                       "identityId": "identity-1",
                       "serviceId": None, "accountId": None}],
        })
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_BRANCH_SOCIAL_FIRST"):
            removal.remove(req)
        social.save(social.initial())
        result = removal.remove(req)
        self.assertTrue(result["ok"])
        self.assertEqual(directory.load()["organizations"][0]["branches"], [])

    def test_portfolio_member_guard_and_empty_portfolio_removal(self):
        self.save_portfolio(members=["org-1"])
        req = self.request("portfolio", "portfolio-1", "Sample Group")
        backup.make_backup()
        with self.assertRaisesRegex(removal.RemovalError, "DETACH_PORTFOLIO_MEMBERS_FIRST"):
            removal.remove(req)
        self.save_portfolio(members=[])
        # Once references are cleared, removing needs no new backup.
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(portfolio.load()["portfolios"], [])

    def test_unit_removal_and_unarchived_guard(self):
        self.save_org(archived=False)
        self.save_unit()
        req = self.request("unit", "unit-1", "Sample Unit", org_id="org-1")
        backup.make_backup()
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(structure.load()["units"], [])
        self.save_unit(archived=False)
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(structure.load()["units"], [])

    def test_organization_social_link_stays_until_explicit_unlink(self):
        self.save_org()
        social.save({
            "schema": social.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "link-1", "orgId": "org-1", "branchId": None,
                       "identityId": "identity-1", "serviceId": None,
                       "accountId": None}],
        })
        backup.make_backup()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_ORGANIZATION_FIRST"):
            removal.remove(req)
        self.assertEqual(len(directory.load()["organizations"]), 1)

    def test_branch_location_link_blocks_removal(self):
        self.save_org(archived=False, branches=[
            {"id": "branch-2", "name": "Sample Branch", "archived": True}])
        branch_locations.save({
            "schema": branch_locations.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "branch-placement-1", "orgId": "org-1",
                       "branchId": "branch-2", "locationId": "unit-1"}],
        })
        backup.make_backup()
        req = self.request("branch", "branch-2", "Sample Branch", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_BRANCH_LOCATION_FIRST"):
            removal.remove(req)
        self.assertEqual(len(directory.load()["organizations"][0]["branches"]), 1)

    def test_unit_location_and_reporting_references_block_removal(self):
        self.save_org(archived=False)
        self.save_unit()
        req = self.request("unit", "unit-1", "Sample Unit", org_id="org-1")
        unit_locations.save({
            "schema": unit_locations.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "placement-1", "orgId": "org-1",
                       "functionId": "unit-1", "locationId": "unit-2"}],
        })
        backup.make_backup()
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_UNIT_LOCATION_FIRST"):
            removal.remove(req)
        unit_locations.save(unit_locations.initial())
        branch_locations.save({
            "schema": branch_locations.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "branch-placement-1", "orgId": "org-1",
                       "branchId": "branch-2", "locationId": "unit-1"}],
        })
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_BRANCH_LOCATION_FIRST"):
            removal.remove(req)
        branch_locations.save(branch_locations.initial())
        reporting.save({
            "schema": reporting.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "report-link-1", "orgId": "org-1",
                       "parentId": "unit-1", "childId": "unit-2"}],
        })
        with self.assertRaisesRegex(removal.RemovalError, "UNLINK_REPORTING_FIRST"):
            removal.remove(req)
        reporting.save(reporting.initial())
        self.assertTrue(removal.remove(req)["ok"])
        self.assertEqual(structure.load()["units"], [])

    def test_invalid_mismatch_and_lock_refusal(self):
        self.save_org()
        backup.make_backup()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        for changed in ({"kind":"unknown"}, {"expectedRevision":99},
                        {"expectedName":"Different"}, {"orgId":"org-9"},
                        {"action":"restore"}, {"extra":True}):
            invalid = dict(req, **changed)
            with self.assertRaises(removal.RemovalError):
                removal.remove(invalid)
        root = backup.root_path()
        fd = os.open(root / ".local-portfolios.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(backup.BackupError, "STORES_BUSY"):
                removal.remove(req)
        finally:
            os.close(fd)
        self.assertEqual(directory.load()["revision"], 1)


if __name__ == "__main__":
    unittest.main()
