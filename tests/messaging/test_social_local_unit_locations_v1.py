"""Fictional function-to-location planning links. Never authorized tenant scopes."""
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
import SocialOrganizationDirectory as directory  # noqa: E402
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialLocalUnitLocationLinks as locations  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as social_links  # noqa: E402

SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
# The original editors now live in the consolidated local workspace.
SECTIONS += "\n" + (ROOT / "widgets/messanger/IdentityCenterLocalOrganizationsWorkspace.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalUnitLocationsEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialLocalUnitLocationLinksStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def edit(doc, action, **kwargs):
    return locations.apply(doc, {
        "action": action, "expectedRevision": doc["revision"], **kwargs
    })


def add(doc, org_id, function_id, location_id):
    return edit(doc, "add", orgId=org_id,
                functionId=function_id, locationId=location_id)


class SyntheticLocationLinks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="social-local-location-links-")
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME": tmp.name})
        env.start()
        self.addCleanup(env.stop)

        companies = directory.initial()
        for name, kind in (
            ("FAKE LLC A", "llc"), ("FAKE LLC B", "llc"),
            ("FAKE NONPROFIT", "nonprofit"),
        ):
            companies = directory.apply(companies, {
                "action": "add_org", "expectedRevision": companies["revision"],
                "name": name, "kind": kind,
            })
        directory.save(companies)

        units = structure.initial()
        specs = (
            ("org-1", "division", "FAKE EDUCATION"),
            ("org-1", "department", "FAKE OPERATIONS"),
            ("org-1", "team", "FAKE SUPPORT"),
            ("org-1", "location", "FAKE NORTH"),
            ("org-1", "location", "FAKE SOUTH"),
            ("org-2", "division", "FAKE EDUCATION"),
            ("org-2", "location", "FAKE NORTH"),
            ("org-3", "team", "FAKE OUTREACH"),
            ("org-3", "location", "FAKE EAST"),
        )
        for org_id, kind, name in specs:
            units = structure.apply(units, {
                "action": "create", "expectedRevision": units["revision"],
                "orgId": org_id, "kind": kind, "name": name,
            })
        structure.save(units)

        group = portfolios.apply(portfolios.initial(), {
            "action": "create", "expectedRevision": 0, "name": "FAKE PORTFOLIO",
        })
        for org_id in ("org-1", "org-2", "org-3"):
            group = portfolios.apply(group, {
                "action": "attach", "expectedRevision": group["revision"],
                "portfolioId": "portfolio-1", "orgId": org_id,
            })
        portfolios.save(group)
        local_link = social_links.apply(social_links.initial(), {
            "action": "add_link", "expectedRevision": 0,
            "orgId": "org-1", "branchId": None, "identityId": "identity-1",
            "serviceId": None, "accountId": None,
        })
        social_links.save(local_link)
        self.original = {
            "organizations": directory.location().read_bytes(),
            "structure": structure.storage_path().read_bytes(),
            "portfolios": portfolios.storage_path().read_bytes(),
            "social": social_links.storage_path().read_bytes(),
        }

    def assert_other_stores_unchanged(self):
        self.assertEqual(directory.location().read_bytes(), self.original["organizations"])
        self.assertEqual(structure.storage_path().read_bytes(), self.original["structure"])
        self.assertEqual(portfolios.storage_path().read_bytes(), self.original["portfolios"])
        self.assertEqual(social_links.storage_path().read_bytes(), self.original["social"])

    def test_missing_read_is_non_mutating(self):
        self.assertEqual(locations.load(), locations.initial())
        self.assertFalse(locations.storage_path().exists())
        self.assert_other_stores_unchanged()

    def test_many_to_many_scoped_to_all_three_organizations(self):
        doc = locations.initial()
        doc = add(doc, "org-1", "unit-1", "unit-4")
        doc = add(doc, "org-1", "unit-1", "unit-5")
        doc = add(doc, "org-1", "unit-2", "unit-4")
        doc = add(doc, "org-1", "unit-3", "unit-4")
        doc = add(doc, "org-2", "unit-6", "unit-7")
        doc = add(doc, "org-3", "unit-8", "unit-9")
        self.assertEqual(doc["revision"], 6)
        self.assertEqual(doc["nextId"], 7)
        self.assertEqual(len(doc["links"]), 6)
        self.assertEqual(doc["links"][0], {
            "id": "placement-1", "orgId": "org-1",
            "functionId": "unit-1", "locationId": "unit-4",
        })
        locations.save(doc)
        self.assertEqual(locations.load(), doc)
        self.assertEqual(locations.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(locations.root_path().stat().st_mode & 0o777, 0o700)
        self.assert_other_stores_unchanged()
        raw = locations.storage_path().read_bytes()
        for forbidden in (b"scopeGrants", b"accessToken", b"principalId",
                          b"role", b"providerSubject", b"managerId"):
            self.assertNotIn(forbidden, raw)

    def test_cross_org_wrong_category_and_duplicate_are_refused(self):
        doc = add(locations.initial(), "org-1", "unit-1", "unit-4")
        with self.assertRaisesRegex(locations.PlacementError, "DUPLICATE_LINK"):
            add(doc, "org-1", "unit-1", "unit-4")
        with self.assertRaisesRegex(locations.PlacementError, "FUNCTION_UNAVAILABLE"):
            add(doc, "org-1", "unit-7", "unit-4")
        with self.assertRaisesRegex(locations.PlacementError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "unit-1", "unit-7")
        with self.assertRaisesRegex(locations.PlacementError, "FUNCTION_UNAVAILABLE"):
            add(doc, "org-1", "unit-4", "unit-5")
        with self.assertRaisesRegex(locations.PlacementError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "unit-1", "unit-2")
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_REQUEST"):
            add(doc, "org-1", "unit-4", "unit-4")
        with self.assertRaisesRegex(locations.PlacementError, "ORGANIZATION_UNAVAILABLE"):
            add(doc, "org-99", "unit-1", "unit-4")

    def test_archived_org_or_unit_is_rejected_but_old_link_can_unlink(self):
        doc = add(locations.initial(), "org-1", "unit-1", "unit-4")
        locations.save(doc)
        current = structure.load()
        structure.save(structure.apply(current, {
            "action": "archive", "expectedRevision": current["revision"],
            "unitId": "unit-4",
        }))
        with self.assertRaisesRegex(locations.PlacementError, "LOCATION_UNAVAILABLE"):
            add(doc, "org-1", "unit-2", "unit-4")
        self.assertEqual(locations.load(), doc)
        current = directory.load()
        directory.save(directory.apply(current, {
            "action": "archive_org", "expectedRevision": current["revision"],
            "orgId": "org-1",
        }))
        with self.assertRaisesRegex(locations.PlacementError, "ORGANIZATION_UNAVAILABLE"):
            add(doc, "org-1", "unit-1", "unit-5")
        doc = edit(doc, "remove", linkId="placement-1")
        locations.save(doc)
        self.assertEqual(locations.load()["links"], [])

    def test_revisions_strict_schema_ids_and_no_privilege_escalation(self):
        doc = add(locations.initial(), "org-1", "unit-1", "unit-4")
        with self.assertRaisesRegex(locations.PlacementError, "REVISION_CONFLICT"):
            locations.apply(doc, {"action": "remove", "expectedRevision": 0,
                                  "linkId": "placement-1"})
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_ID"):
            edit(doc, "remove", linkId="org-1")
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_REQUEST"):
            locations.apply(doc, {"action": "remove", "expectedRevision": 1,
                                  "linkId": "placement-1",
                                  "scopeGrants": ["finance.read"]})
        with self.assertRaisesRegex(locations.PlacementError, "LINK_NOT_FOUND"):
            edit(doc, "remove", linkId="placement-55")
        doc = edit(doc, "remove", linkId="placement-1")
        self.assertEqual(doc["revision"], 2)
        self.assertEqual(doc["nextId"], 2)  # Stable IDs are not recycled.

    def test_future_corrupt_duplicate_key_and_symlink_fail_closed(self):
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_JSON"):
            locations.decode(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_JSON"):
            locations.decode(b'{"x":NaN}')
        future = locations.initial()
        future["schema"] = "post-apollo.social-local-unit-location-links.v99"
        with self.assertRaisesRegex(locations.PlacementError, "UNSUPPORTED_VERSION"):
            locations.validate(future)
        bogus = locations.initial()
        bogus["links"] = [{
            "id": "placement-1", "orgId": "org-1",
            "functionId": "unit-1", "locationId": "unit-4",
        }]
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_DOCUMENT"):
            locations.validate(bogus)  # nextId too small.
        path = locations.storage_path()
        path.write_text("CORRUPT")
        path.chmod(0o600)
        with self.assertRaisesRegex(locations.PlacementError, "INVALID_JSON"):
            locations.load()
        self.assertEqual(path.read_text(), "CORRUPT")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            locations.load()
        path.unlink()
        path.symlink_to(locations.root_path() / "not-real")
        with self.assertRaises(Exception):
            locations.load()

    def test_fixed_cli_stdin_revision_conflict(self):
        script = ROOT / "services/social/SocialLocalUnitLocationLinks.py"
        data = {"action": "add", "expectedRevision": 0,
                "orgId": "org-1", "functionId": "unit-1", "locationId": "unit-4"}
        env = dict(os.environ)
        first = subprocess.run([sys.executable, str(script), "update"],
                               input=json.dumps(data) + "\n", env=env,
                               text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertTrue(json.loads(first.stdout)["ok"])
        second = subprocess.run([sys.executable, str(script), "update"],
                                input=json.dumps(data) + "\n", env=env,
                                text=True, capture_output=True, check=False)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("unit-1", second.stdout)
        query = subprocess.run([sys.executable, str(script), "read"],
                               capture_output=True, text=True, env=env, check=False)
        self.assertEqual(query.returncode, 0)
        self.assertEqual(len(json.loads(query.stdout)["document"]["links"]), 1)
        self.assert_other_stores_unchanged()


class PlacementUIContracts(unittest.TestCase):
    def test_existing_editor_and_injection_no_new_window(self):
        for name in ("IdentityCenterLocalOrganizationEditor {",
                     "IdentityCenterLocalPortfolioEditor {",
                     "IdentityCenterLocalStructureEditor {",
                     "IdentityCenterLocalUnitLocationsEditor {",
                     "IdentityCenterLocalSocialLinksEditor {"):
            self.assertIn(name, SECTIONS)
        self.assertIn("localUnitLocationLinksStore: SocialLocalUnitLocationLinksStore", SELECTOR)
        self.assertIn("singleton SocialLocalUnitLocationLinksStore 1.0", QMLDIR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        self.assertIn("interactive: false", SECTIONS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])
        for forbidden in ("PanelWindow {", "FloatingWindow {", "Process {", "FileView {"):
            self.assertNotIn(forbidden, EDITOR)

    def test_link_labels_and_stale_rows(self):
        for needle in ("STRUCTURE LINKS // FUNCTIONS & LOCATIONS",
                       "+ LINK TO LOCATION", "UNLINK LOCATION", "CONFIRM UNLINK",
                       "SHOW ALL LINKS", "STALE OR UNAVAILABLE",
                       "linkToLocation", "unlinkFromLocation",
                       "not reporting lines", "localUnitLocationLinksStore"):
            self.assertIn(needle.lower(), (EDITOR + STORE + SECTIONS).lower())
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        for forbidden in ("accessToken", "refreshToken", "scopeGrants",
                          "canSwitchOrganization: true", "AccountBroker",
                          "Qt.openUrlExternally"):
            self.assertNotIn(forbidden, EDITOR + STORE)


if __name__ == "__main__":
    unittest.main()
