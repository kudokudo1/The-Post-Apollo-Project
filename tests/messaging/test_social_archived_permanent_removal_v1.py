"""Fail-closed permanent removal of archived owner-local labels only."""
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

    def test_requires_archived_and_matching_private_backup(self):
        self.save_org()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "BACKUP_REQUIRED"):
            removal.remove(req)
        self.assertEqual(len(directory.load()["organizations"]), 1)
        backup.make_backup()
        updated = removal.remove(req)
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["revision"], 2)
        doc = directory.load()
        self.assertEqual(doc["organizations"], [])
        self.assertEqual(doc["nextId"], 3)
        with self.assertRaisesRegex(removal.RemovalError, "REVISION_CONFLICT"):
            removal.remove(req)

    def test_active_unarchived_record_cannot_be_removed(self):
        self.save_org(archived=False)
        backup.make_backup()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "ARCHIVE_BEFORE_REMOVE"):
            removal.remove(req)

    def test_backup_must_include_exact_current_archived_record(self):
        backup.make_backup()  # Valid snapshot from before the record existed.
        self.save_org()
        req = self.request("organization", "org-1", "Sample Company", org_id="org-1")
        with self.assertRaisesRegex(removal.RemovalError, "BACKUP_REQUIRED"):
            removal.remove(req)
        self.assertEqual(directory.load()["revision"], 1)

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

    def test_branch_requires_archive_backup_and_unlinked_social(self):
        self.save_org(archived=False, branches=[
            {"id": "branch-2", "name": "Sample Branch", "archived": True}])
        req = self.request("branch", "branch-2", "Sample Branch", org_id="org-1")
        social.save({
            "schema": social.SCHEMA, "revision": 1, "nextId": 2,
            "links": [{"id": "link-1", "orgId": "org-1", "branchId": "branch-2",
                       "identityId": "identity-1",
                       "serviceId": None, "accountId": None}],
        })
        backup.make_backup()
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
        # Earlier backup is not a snapshot of the empty portfolio state.
        with self.assertRaisesRegex(removal.RemovalError, "BACKUP_REQUIRED"):
            removal.remove(req)
        backup.make_backup()
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
        with self.assertRaisesRegex(removal.RemovalError, "ARCHIVE_BEFORE_REMOVE"):
            removal.remove(req)

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
