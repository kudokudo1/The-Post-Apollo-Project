"""Synthetic functional graph tests, never workforce permission assertions."""
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
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as social_links  # noqa: E402
import SocialLocalUnitLocationLinks as function_locations  # noqa: E402
import SocialLocalBranchLocationLinks as branch_locations  # noqa: E402
import SocialLocalFunctionalReporting as reporting  # noqa: E402

SETTINGS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalFunctionalReportingEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialLocalFunctionalReportingStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def edit(doc, action, **kwargs):
    return reporting.apply(doc, {
        "action": action, "expectedRevision": doc["revision"], **kwargs,
    })


def link(doc, org, parent, child):
    return edit(doc, "add", orgId=org, parentId=parent, childId=child)


class SyntheticFunctionalReporting(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="social-functional-reporting-")
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME": tmp.name})
        env.start()
        self.addCleanup(env.stop)

        orgs = directory.initial()
        for name, kind in (
            ("FAKE LLC ONE", "llc"), ("FAKE LLC TWO", "llc"),
            ("FAKE NONPROFIT", "nonprofit"),
        ):
            orgs = directory.apply(orgs, {
                "action": "add_org", "expectedRevision": orgs["revision"],
                "name": name, "kind": kind,
            })
        orgs = directory.apply(orgs, {
            "action": "add_branch", "expectedRevision": orgs["revision"],
            "orgId": "org-1", "name": "FAKE BRANCH",
        })
        directory.save(orgs)

        units = structure.initial()
        for org, kind, label in (
            ("org-1", "division", "FAKE DIVISION"),
            ("org-1", "department", "FAKE DEPARTMENT"),
            ("org-1", "team", "FAKE TEAM"),
            ("org-1", "department", "FAKE SECOND DEPARTMENT"),
            ("org-1", "location", "FAKE OFFICE"),
            ("org-2", "department", "FAKE OTHER COMPANY DEPARTMENT"),
            ("org-2", "team", "FAKE OTHER COMPANY TEAM"),
            ("org-3", "division", "FAKE NONPROFIT DIVISION"),
            ("org-3", "team", "FAKE NONPROFIT TEAM"),
        ):
            units = structure.apply(units, {
                "action": "create", "expectedRevision": units["revision"],
                "orgId": org, "kind": kind, "name": label,
            })
        structure.save(units)

        group = portfolios.apply(portfolios.initial(), {
            "action": "create", "expectedRevision": 0, "name": "FAKE PORTFOLIO",
        })
        for org in ("org-1", "org-2", "org-3"):
            group = portfolios.apply(group, {
                "action": "attach", "expectedRevision": group["revision"],
                "portfolioId": "portfolio-1", "orgId": org,
            })
        portfolios.save(group)

        social = social_links.apply(social_links.initial(), {
            "action": "add_link", "expectedRevision": 0,
            "orgId": "org-1", "branchId": "branch-4",
            "identityId": "identity-1", "serviceId": None, "accountId": None,
        })
        social_links.save(social)
        locations = function_locations.apply(function_locations.initial(), {
            "action": "add", "expectedRevision": 0,
            "orgId": "org-1", "functionId": "unit-3", "locationId": "unit-5",
        })
        function_locations.save(locations)
        branch = branch_locations.apply(branch_locations.initial(), {
            "action": "add", "expectedRevision": 0,
            "orgId": "org-1", "branchId": "branch-4", "locationId": "unit-5",
        })
        branch_locations.save(branch)

        self.orig_files = {
            "org": directory.location(), "structure": structure.storage_path(),
            "portfolio": portfolios.storage_path(),
            "social": social_links.storage_path(),
            "function_locations": function_locations.storage_path(),
            "branch_locations": branch_locations.storage_path(),
        }
        self.orig_bytes = {name: path.read_bytes()
                           for name, path in self.orig_files.items()}

    def unchanged(self):
        for name, path in self.orig_files.items():
            self.assertEqual(path.read_bytes(), self.orig_bytes[name], name)

    def test_empty_read_has_no_file_side_effect(self):
        self.assertEqual(reporting.load(), reporting.initial())
        self.assertFalse(reporting.storage_path().exists())
        self.unchanged()

    def test_three_organizations_multi_parent_graph_and_durable_private_file(self):
        doc = reporting.initial()
        for org, parent, child in (
            ("org-1", "unit-1", "unit-2"),
            ("org-1", "unit-2", "unit-3"),
            ("org-1", "unit-4", "unit-3"),
            ("org-1", "unit-1", "unit-4"),
            ("org-2", "unit-6", "unit-7"),
            ("org-3", "unit-8", "unit-9"),
        ):
            doc = link(doc, org, parent, child)
        self.assertEqual(doc["revision"], 6)
        self.assertEqual(doc["nextId"], 7)
        self.assertEqual(len(doc["links"]), 6)
        self.assertEqual(doc["links"][0], {
            "id": "report-link-1", "orgId": "org-1",
            "parentId": "unit-1", "childId": "unit-2",
        })
        reporting.save(doc)
        self.assertEqual(reporting.load(), doc)
        self.assertEqual(reporting.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(reporting.root_path().stat().st_mode & 0o777, 0o700)
        self.unchanged()
        for forbidden in (b"scopeGrants", b"accessToken", b"verifiedOwner",
                          b"managerId", b"employeeId", b"roleAssignment"):
            self.assertNotIn(forbidden, reporting.storage_path().read_bytes())
        doc = edit(doc, "remove", linkId="report-link-3")
        self.assertEqual(doc["revision"], 7)
        self.assertEqual(doc["nextId"], 7)

    def test_cycle_self_link_duplicate_and_reverse_edge_rejected(self):
        doc = link(reporting.initial(), "org-1", "unit-1", "unit-2")
        doc = link(doc, "org-1", "unit-2", "unit-3")
        with self.assertRaisesRegex(reporting.ReportingError, "CYCLE_DETECTED"):
            link(doc, "org-1", "unit-3", "unit-1")
        with self.assertRaisesRegex(reporting.ReportingError, "CYCLE_DETECTED"):
            link(doc, "org-1", "unit-2", "unit-1")
        with self.assertRaisesRegex(reporting.ReportingError, "SELF_LINK"):
            link(doc, "org-1", "unit-1", "unit-1")
        with self.assertRaisesRegex(reporting.ReportingError, "DUPLICATE_LINK"):
            link(doc, "org-1", "unit-1", "unit-2")
        # A corrupt file with a cycle is also rejected on read/validate.
        corrupt = doc.copy()
        corrupt["links"] = [x.copy() for x in doc["links"]]
        corrupt["links"].append({
            "id": "report-link-3", "orgId": "org-1",
            "parentId": "unit-3", "childId": "unit-1",
        })
        corrupt["nextId"] = 4
        with self.assertRaisesRegex(reporting.ReportingError, "CYCLE_DETECTED"):
            reporting.validate(corrupt)

    def test_reject_cross_org_location_archived_and_missing_targets(self):
        doc = reporting.initial()
        with self.assertRaisesRegex(reporting.ReportingError, "PARENT_UNAVAILABLE"):
            link(doc, "org-1", "unit-6", "unit-3")
        with self.assertRaisesRegex(reporting.ReportingError, "CHILD_UNAVAILABLE"):
            link(doc, "org-1", "unit-1", "unit-7")
        with self.assertRaisesRegex(reporting.ReportingError, "PARENT_UNAVAILABLE"):
            link(doc, "org-1", "unit-5", "unit-3")
        with self.assertRaisesRegex(reporting.ReportingError, "CHILD_UNAVAILABLE"):
            link(doc, "org-1", "unit-1", "unit-5")
        with self.assertRaisesRegex(reporting.ReportingError, "ORGANIZATION_UNAVAILABLE"):
            link(doc, "org-99", "unit-1", "unit-2")
        doc = link(doc, "org-1", "unit-1", "unit-2")
        reporting.save(doc)
        current = structure.load()
        structure.save(structure.apply(current, {
            "action": "archive", "expectedRevision": current["revision"],
            "unitId": "unit-2",
        }))
        with self.assertRaisesRegex(reporting.ReportingError, "CHILD_UNAVAILABLE"):
            link(doc, "org-1", "unit-4", "unit-2")
        self.assertEqual(reporting.load(), doc)  # Old edge is visible.
        current = directory.load()
        directory.save(directory.apply(current, {
            "action": "archive_org", "expectedRevision": current["revision"],
            "orgId": "org-1",
        }))
        with self.assertRaisesRegex(reporting.ReportingError, "ORGANIZATION_UNAVAILABLE"):
            link(doc, "org-1", "unit-1", "unit-3")
        doc = edit(doc, "remove", linkId="report-link-1")
        reporting.save(doc)
        self.assertEqual(reporting.load()["links"], [])

    def test_invalid_json_schema_file_modes_and_symlink_fail_closed(self):
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_JSON"):
            reporting.decode(b'{"duplicate":1,"duplicate":2}')
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_JSON"):
            reporting.decode(b'{"bad":Infinity}')
        future = reporting.initial()
        future["schema"] = "post-apollo.social-local-functional-reporting.v99"
        with self.assertRaisesRegex(reporting.ReportingError, "UNSUPPORTED_VERSION"):
            reporting.validate(future)
        broken = reporting.initial()
        broken["links"] = [{"id": "report-link-1", "orgId": "org-1",
                            "parentId": "unit-1", "childId": "unit-2"}]
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_DOCUMENT"):
            reporting.validate(broken)
        path = reporting.storage_path()
        path.write_text("BAD FILE")
        path.chmod(0o600)
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_JSON"):
            reporting.load()
        self.assertEqual(path.read_text(), "BAD FILE")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            reporting.load()
        path.unlink()
        path.symlink_to(reporting.root_path() / "not-real")
        with self.assertRaises(Exception):
            reporting.load()

    def test_strict_request_stale_revision_and_cli(self):
        doc = link(reporting.initial(), "org-1", "unit-1", "unit-2")
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_REQUEST"):
            reporting.apply(doc, {"action": "remove", "expectedRevision": 1,
                                  "linkId": "report-link-1",
                                  "privilege": "finance.read"})
        with self.assertRaisesRegex(reporting.ReportingError, "REVISION_CONFLICT"):
            reporting.apply(doc, {"action": "remove", "expectedRevision": 0,
                                  "linkId": "report-link-1"})
        with self.assertRaisesRegex(reporting.ReportingError, "INVALID_ID"):
            edit(doc, "remove", linkId="unit-1")
        with self.assertRaisesRegex(reporting.ReportingError, "LINK_NOT_FOUND"):
            edit(doc, "remove", linkId="report-link-99")
        script = ROOT / "services/social/SocialLocalFunctionalReporting.py"
        payload = {"action": "add", "expectedRevision": 0,
                   "orgId": "org-1", "parentId": "unit-1", "childId": "unit-2"}
        first = subprocess.run([sys.executable, str(script), "update"],
                               input=json.dumps(payload) + "\n",
                               text=True, capture_output=True,
                               env=dict(os.environ), check=False)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertTrue(json.loads(first.stdout)["ok"])
        second = subprocess.run([sys.executable, str(script), "update"],
                                input=json.dumps(payload) + "\n",
                                text=True, capture_output=True,
                                env=dict(os.environ), check=False)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("unit-1", second.stdout)
        self.unchanged()


class FunctionalReportingUIContracts(unittest.TestCase):
    def test_integrated_without_new_window_or_organization_switch(self):
        for marker in ("IdentityCenterLocalOrganizationEditor {",
                       "IdentityCenterLocalPortfolioEditor {",
                       "IdentityCenterLocalStructureEditor {",
                       "IdentityCenterLocalUnitLocationsEditor {",
                       "IdentityCenterLocalBranchLocationsEditor {",
                       "IdentityCenterLocalFunctionalReportingEditor {",
                       "IdentityCenterLocalSocialLinksEditor {"):
            self.assertIn(marker, SETTINGS)
        self.assertIn("localFunctionalReportingStore: SocialLocalFunctionalReportingStore",
                      SELECTOR)
        self.assertIn("singleton SocialLocalFunctionalReportingStore 1.0", QMLDIR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SETTINGS)
        self.assertIn("interactive: false", SETTINGS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])
        for forbidden in ("PanelWindow {", "FloatingWindow {", "Process {",
                          "FileView {", "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, EDITOR)

    def test_local_graph_controls_and_stale_cleanups(self):
        for marker in ("FUNCTIONAL REPORTING // LOCAL MAP", "+ LINK FUNCTIONS",
                       "SHOW ALL LINKS", "STALE OR UNAVAILABLE",
                       "UNLINK FUNCTIONS", "CONFIRM UNLINK", "wouldCycle",
                       "addRelationship", "removeRelationship"):
            self.assertIn(marker, EDITOR + STORE)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        for forbidden in ("accessToken", "scopeGrants", "refreshToken",
                          "employeeId", "RoleAssignment", "AccountBroker"):
            self.assertNotIn(forbidden, EDITOR + STORE)


if __name__ == "__main__":
    unittest.main()
