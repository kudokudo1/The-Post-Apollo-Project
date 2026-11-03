"""Manual branch-to-location associations, with only synthetic orgs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "social"))
import SocialOrganizationDirectory as organizations  # noqa: E402
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as socials  # noqa: E402
import SocialLocalUnitLocationLinks as functions  # noqa: E402
import SocialLocalBranchLocationLinks as branches  # noqa: E402

SETTINGS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalBranchLocationsEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialLocalBranchLocationLinksStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def edit(doc, action, **fields):
    return branches.apply(doc, {
        "action": action, "expectedRevision": doc["revision"], **fields,
    })


def add(doc, org, branch, location):
    return edit(doc, "add", orgId=org, branchId=branch, locationId=location)


class SyntheticBranchLocationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="post-apollo-branch-locations-")
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME": temp.name})
        env.start()
        self.addCleanup(env.stop)

        doc = organizations.initial()
        for name, kind in (("FAKE LLC ONE", "llc"),
                           ("FAKE LLC TWO", "llc"),
                           ("FAKE NONPROFIT", "nonprofit")):
            doc = organizations.apply(doc, {
                "action": "add_org", "expectedRevision": doc["revision"],
                "name": name, "kind": kind,
            })
        for org_id, label in (("org-1", "FAKE BRANCH A"),
                              ("org-2", "FAKE BRANCH B"),
                              ("org-3", "FAKE BRANCH C"),
                              ("org-1", "FAKE BRANCH D")):
            doc = organizations.apply(doc, {
                "action": "add_branch", "expectedRevision": doc["revision"],
                "orgId": org_id, "name": label,
            })
        organizations.save(doc)

        units = structure.initial()
        for org_id, kind, name in (
            ("org-1", "location", "FAKE NORTH"),
            ("org-1", "location", "FAKE SOUTH"),
            ("org-2", "location", "FAKE WEST"),
            ("org-3", "location", "FAKE EAST"),
            ("org-1", "team", "FAKE TEAM"),
        ):
            units = structure.apply(units, {
                "action": "create", "expectedRevision": units["revision"],
                "orgId": org_id, "kind": kind, "name": name,
            })
        structure.save(units)

        group = portfolios.apply(portfolios.initial(), {
            "action": "create", "expectedRevision": 0, "name": "FAKE GROUP",
        })
        for oid in ("org-1", "org-2", "org-3"):
            group = portfolios.apply(group, {
                "action": "attach", "expectedRevision": group["revision"],
                "portfolioId": "portfolio-1", "orgId": oid,
            })
        portfolios.save(group)
        social = socials.apply(socials.initial(), {
            "action": "add_link", "expectedRevision": 0,
            "orgId": "org-1", "branchId": "branch-4",
            "identityId": "identity-1", "serviceId": None, "accountId": None,
        })
        socials.save(social)
        function = functions.apply(functions.initial(), {
            "action": "add", "expectedRevision": 0,
            "orgId": "org-1", "functionId": "unit-5", "locationId": "unit-1",
        })
        functions.save(function)

        self.original_paths = {
            "org": organizations.location(),
            "structure": structure.storage_path(),
            "portfolio": portfolios.storage_path(),
            "social": socials.storage_path(),
            "function": functions.storage_path(),
        }
        self.original = {k: p.read_bytes() for k, p in self.original_paths.items()}

    def unchanged(self):
        for key, path in self.original_paths.items():
            self.assertEqual(path.read_bytes(), self.original[key], key)

    def test_missing_file_read_does_not_mutate(self):
        self.assertEqual(branches.load(), branches.initial())
        self.assertFalse(branches.storage_path().exists())
        self.unchanged()

    def test_many_to_many_three_organizations_and_private_durability(self):
        doc = branches.initial()
        for oid, bid, uid in (
            ("org-1", "branch-4", "unit-1"),
            ("org-1", "branch-4", "unit-2"),
            ("org-1", "branch-7", "unit-1"),
            ("org-2", "branch-5", "unit-3"),
            ("org-3", "branch-6", "unit-4"),
        ):
            doc = add(doc, oid, bid, uid)
        self.assertEqual(doc["revision"], 5)
        self.assertEqual(doc["nextId"], 6)
        self.assertEqual(doc["links"][0], {
            "id": "branch-placement-1", "orgId": "org-1",
            "branchId": "branch-4", "locationId": "unit-1",
        })
        branches.save(doc)
        self.assertEqual(branches.load(), doc)
        self.assertEqual(branches.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(branches.root_path().stat().st_mode & 0o777, 0o700)
        self.unchanged()
        for forbidden in (b"scopeGrants", b"accessToken", b"principalId",
                          b"verifiedAddress", b"managerId"):
            self.assertNotIn(forbidden, branches.storage_path().read_bytes())
        removed = edit(doc, "remove", linkId="branch-placement-1")
        self.assertEqual(removed["nextId"], 6)
        self.assertEqual(len(removed["links"]), 4)

    def test_cross_org_branch_and_location_and_wrong_kind_are_refused(self):
        doc = add(branches.initial(), "org-1", "branch-4", "unit-1")
        with self.assertRaisesRegex(branches.BranchLocationError, "DUPLICATE_LINK"):
            add(doc, "org-1", "branch-4", "unit-1")
        with self.assertRaisesRegex(branches.BranchLocationError, "BRANCH_UNAVAILABLE"):
            add(doc, "org-1", "branch-5", "unit-1")
        with self.assertRaisesRegex(branches.BranchLocationError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "branch-4", "unit-3")
        with self.assertRaisesRegex(branches.BranchLocationError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "branch-4", "unit-5")
        with self.assertRaisesRegex(branches.BranchLocationError, "ORGANIZATION_UNAVAILABLE"):
            add(doc, "org-99", "branch-4", "unit-1")
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_ID"):
            add(doc, "org-1", "unit-1", "unit-2")

    def test_archive_branch_or_location_keeps_old_link_removable(self):
        doc = add(branches.initial(), "org-1", "branch-4", "unit-1")
        branches.save(doc)
        original = organizations.load()
        original = organizations.apply(original, {
            "action": "archive_branch", "expectedRevision": original["revision"],
            "orgId": "org-1", "branchId": "branch-4",
        })
        organizations.save(original)
        with self.assertRaisesRegex(branches.BranchLocationError, "BRANCH_UNAVAILABLE"):
            add(doc, "org-1", "branch-4", "unit-2")
        self.assertEqual(branches.load(), doc)

        original = structure.load()
        original = structure.apply(original, {
            "action": "archive", "expectedRevision": original["revision"],
            "unitId": "unit-1",
        })
        structure.save(original)
        with self.assertRaisesRegex(branches.BranchLocationError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "branch-7", "unit-1")
        removed = edit(doc, "remove", linkId="branch-placement-1")
        branches.save(removed)
        self.assertEqual(branches.load()["links"], [])

    def test_corrupt_version_duplicate_keys_and_symlinks_fail_closed(self):
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_JSON"):
            branches.decode(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_JSON"):
            branches.decode(b'{"x":NaN}')
        future = branches.initial()
        future["schema"] = "post-apollo.social-local-branch-location-links.v99"
        with self.assertRaisesRegex(branches.BranchLocationError, "UNSUPPORTED_VERSION"):
            branches.validate(future)
        invalid = branches.initial()
        invalid["links"] = [{"id": "branch-placement-1",
                             "orgId": "org-1", "branchId": "branch-4",
                             "locationId": "unit-1"}]
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_DOCUMENT"):
            branches.validate(invalid)
        path = branches.storage_path()
        path.write_text("CORRUPT")
        path.chmod(0o600)
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_JSON"):
            branches.load()
        self.assertEqual(path.read_text(), "CORRUPT")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            branches.load()
        path.unlink()
        path.symlink_to(branches.root_path() / "not-a-file")
        with self.assertRaises(Exception):
            branches.load()

    def test_revision_unknown_fields_and_fixed_cli(self):
        doc = add(branches.initial(), "org-1", "branch-4", "unit-1")
        with self.assertRaisesRegex(branches.BranchLocationError, "REVISION_CONFLICT"):
            branches.apply(doc, {
                "action": "remove", "expectedRevision": 0,
                "linkId": "branch-placement-1",
            })
        with self.assertRaisesRegex(branches.BranchLocationError, "INVALID_REQUEST"):
            branches.apply(doc, {
                "action": "remove", "expectedRevision": 1,
                "linkId": "branch-placement-1", "permission": "finance.read",
            })
        script = ROOT / "services/social/SocialLocalBranchLocationLinks.py"
        payload = {"action": "add", "expectedRevision": 0,
                   "orgId": "org-1", "branchId": "branch-4",
                   "locationId": "unit-1"}
        result = subprocess.run([sys.executable, str(script), "update"],
                                input=json.dumps(payload) + "\n",
                                text=True, capture_output=True,
                                env=dict(os.environ), check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])
        conflict = subprocess.run([sys.executable, str(script), "update"],
                                  input=json.dumps(payload) + "\n",
                                  text=True, capture_output=True,
                                  env=dict(os.environ), check=False)
        self.assertEqual(conflict.returncode, 2)
        self.assertEqual(json.loads(conflict.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("branch-4", conflict.stdout)
        self.unchanged()


class BranchLocationUIContracts(unittest.TestCase):
    def test_same_settings_page_and_account_switch_still_disabled(self):
        for marker in ("IdentityCenterLocalOrganizationEditor {",
                       "IdentityCenterLocalPortfolioEditor {",
                       "IdentityCenterLocalStructureEditor {",
                       "IdentityCenterLocalRelationshipModifiers {",
                       "IdentityCenterLocalRelationshipModifiers {",
                       "IdentityCenterLocalRelationshipModifiers {"):
            self.assertIn(marker, SETTINGS)
        self.assertIn("localBranchLocationLinksStore: SocialLocalBranchLocationLinksStore",
                      SELECTOR)
        self.assertIn("singleton SocialLocalBranchLocationLinksStore 1.0", QMLDIR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SETTINGS)
        self.assertIn("interactive: false", SETTINGS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])
        for bad in ("PanelWindow {", "FloatingWindow {", "Process {",
                    "FileView {", "canSwitchOrganization: true"):
            self.assertNotIn(bad, EDITOR)

    def test_manual_ui_actions_and_stale_entries(self):
        for marker in ("BRANCH LINKS // LOCATIONS", "+ LINK BRANCH TO LOCATION",
                       "SHOW ALL LINKS", "STALE OR UNAVAILABLE",
                       "UNLINK BRANCH LOCATION", "CONFIRM UNLINK",
                       "linkBranch", "unlinkBranch"):
            self.assertIn(marker, EDITOR + STORE)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        for forbidden in ("accessToken", "scopeGrants", "refreshToken",
                          "realAddress", "AccountBroker"):
            self.assertNotIn(forbidden, EDITOR + STORE)


if __name__ == "__main__":
    unittest.main()
