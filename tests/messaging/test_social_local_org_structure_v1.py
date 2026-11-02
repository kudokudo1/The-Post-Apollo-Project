"""Synthetic local org structure tests: labels, not Identity Center grants."""
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
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialOrganizationDirectory as directory  # noqa: E402

SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
APP = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalStructureEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialLocalOrganizationStructureStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def edit(doc, action, **fields):
    return structure.apply(doc, {"action": action,
                                 "expectedRevision": doc["revision"], **fields})


class LocalStructureModel(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="post-apollo-org-structure-")
        self.addCleanup(tmp.cleanup)
        context = patch.dict(os.environ, {"XDG_DATA_HOME": tmp.name})
        context.start()
        self.addCleanup(context.stop)
        base = directory.initial()
        for label, kind in (
            ("SYNTHETIC LLC A", "llc"),
            ("SYNTHETIC LLC B", "llc"),
            ("SYNTHETIC NONPROFIT", "nonprofit"),
        ):
            base = directory.apply(base, {"action": "add_org",
                "expectedRevision": base["revision"], "name": label, "kind": kind})
        base = directory.apply(base, {"action": "add_branch",
            "expectedRevision": base["revision"], "orgId": "org-1",
            "name": "Legacy branch stays distinct"})
        directory.save(base)

    def test_empty_read_has_no_side_effect(self):
        self.assertEqual(structure.load(), structure.initial())
        self.assertFalse(structure.storage_path().exists())

    def test_all_four_kinds_across_independent_organizations(self):
        doc = structure.initial()
        for kind in structure.TYPES:
            doc = edit(doc, "create", orgId="org-1", kind=kind,
                       name="SYNTHETIC " + kind.upper())
        doc = edit(doc, "create", orgId="org-2", kind="division",
                   name="SYNTHETIC DIVISION")
        doc = edit(doc, "create", orgId="org-3", kind="team",
                   name="SYNTHETIC TEAM")
        self.assertEqual(doc["revision"], 6)
        self.assertEqual(doc["nextId"], 7)
        self.assertEqual(len(doc["units"]), 6)
        self.assertEqual({u["kind"] for u in doc["units"]}, set(structure.TYPES))
        self.assertEqual(doc["units"][0]["id"], "unit-1")
        self.assertEqual(doc["units"][-1]["orgId"], "org-3")
        structure.save(doc)
        self.assertEqual(structure.load(), doc)
        self.assertEqual(structure.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(structure.root_path().stat().st_mode & 0o777, 0o700)
        self.assertEqual(directory.load()["organizations"][0]["branches"][0]["name"],
                         "Legacy branch stays distinct")
        content = structure.storage_path().read_text()
        for bad in ("scopeGrants", "principalId", "accessToken",
                    "refreshToken", "providerSubject", "managerId"):
            self.assertNotIn(bad, content)

    def test_rename_archive_restore_retains_id_and_org_kind(self):
        doc = edit(structure.initial(), "create", orgId="org-1",
                   kind="department", name="SYNTHETIC SALES")
        doc = edit(doc, "rename", unitId="unit-1", name="SYNTHETIC SUPPORT")
        doc = edit(doc, "archive", unitId="unit-1")
        self.assertTrue(doc["units"][0]["archived"])
        doc = edit(doc, "restore", unitId="unit-1")
        self.assertFalse(doc["units"][0]["archived"])
        self.assertEqual(doc["units"][0], {
            "id": "unit-1", "orgId": "org-1",
            "kind": "department", "name": "SYNTHETIC SUPPORT", "archived": False,
        })
        self.assertEqual(doc["revision"], 4)
        structure.save(doc)
        self.assertEqual(structure.load(), doc)

    def test_duplicate_scoped_by_org_and_category_and_restore_collision(self):
        doc = edit(structure.initial(), "create", orgId="org-1",
                   kind="division", name="Education")
        with self.assertRaisesRegex(structure.StructureError, "DUPLICATE_NAME"):
            edit(doc, "create", orgId="org-1", kind="division", name="education")
        doc = edit(doc, "create", orgId="org-1", kind="department", name="Education")
        doc = edit(doc, "create", orgId="org-2", kind="division", name="Education")
        doc = edit(doc, "archive", unitId="unit-1")
        doc = edit(doc, "create", orgId="org-1", kind="division", name="education")
        with self.assertRaisesRegex(structure.StructureError, "DUPLICATE_NAME"):
            edit(doc, "restore", unitId="unit-1")
        self.assertEqual(doc["units"][0]["orgId"], "org-1")

    def test_missing_and_archived_org_write_refusal(self):
        with self.assertRaisesRegex(structure.StructureError, "ORGANIZATION_UNAVAILABLE"):
            edit(structure.initial(), "create", orgId="org-99",
                 kind="team", name="Ghost")
        with self.assertRaisesRegex(structure.StructureError, "INVALID_ID"):
            edit(structure.initial(), "create", orgId="tenant-1",
                 kind="team", name="Ghost")
        doc = edit(structure.initial(), "create",
                   orgId="org-3", kind="location", name="SYNTHETIC REGIONAL")
        structure.save(doc)
        base = directory.load()
        directory.save(directory.apply(base, {"action": "archive_org",
            "expectedRevision": base["revision"], "orgId": "org-3"}))
        self.assertEqual(structure.load()["units"][0]["name"],
                         "SYNTHETIC REGIONAL")  # Historic label retained.
        with self.assertRaisesRegex(structure.StructureError, "ORGANIZATION_UNAVAILABLE"):
            edit(doc, "rename", unitId="unit-1", name="New name")
        doc = edit(doc, "archive", unitId="unit-1")  # Historical tidy-up allowed.
        with self.assertRaisesRegex(structure.StructureError, "ORGANIZATION_UNAVAILABLE"):
            edit(doc, "restore", unitId="unit-1")

    def test_exact_actions_invalid_names_ids_and_optimistic_revision(self):
        doc = edit(structure.initial(), "create", orgId="org-1",
                   kind="team", name="Example")
        for kind in ("employee", "region", "branch", 42, None):
            with self.assertRaisesRegex(structure.StructureError, "INVALID_KIND"):
                edit(doc, "create", orgId="org-1", kind=kind, name="Bad")
        with self.assertRaisesRegex(structure.StructureError, "INVALID_NAME"):
            edit(doc, "create", orgId="org-1", kind="team", name="New\nLine")
        with self.assertRaisesRegex(structure.StructureError, "INVALID_ID"):
            edit(doc, "rename", unitId="org-1", name="Bad")
        with self.assertRaisesRegex(structure.StructureError, "INVALID_REQUEST"):
            structure.apply(doc, {"action":"archive", "expectedRevision":1,
                                  "unitId":"unit-1", "role":"administrator"})
        with self.assertRaisesRegex(structure.StructureError, "REVISION_CONFLICT"):
            structure.apply(doc, {"action":"archive", "expectedRevision":0,
                                  "unitId":"unit-1"})
        with self.assertRaisesRegex(structure.StructureError, "NO_CHANGE"):
            edit(doc, "rename", unitId="unit-1", name="Example")

    def test_invalid_json_corrupt_files_symlinks_and_future_versions(self):
        with self.assertRaisesRegex(structure.StructureError, "INVALID_JSON"):
            structure.decode(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(structure.StructureError, "INVALID_JSON"):
            structure.decode(b'{"x":NaN}')
        future = structure.initial()
        future["schema"] = "post-apollo.social-local-org-structure.v99"
        with self.assertRaisesRegex(structure.StructureError, "UNSUPPORTED_VERSION"):
            structure.validate(future)
        invalid = structure.initial()
        invalid["units"] = [{
            "id":"unit-1", "orgId":"org-1", "kind":"location",
            "name":"X", "archived":False,
        }]
        with self.assertRaisesRegex(structure.StructureError, "INVALID_DOCUMENT"):
            structure.validate(invalid)  # nextId must exceed existing ID
        path = structure.storage_path()
        path.write_text("CORRUPT FILE")
        path.chmod(0o600)
        with self.assertRaisesRegex(structure.StructureError, "INVALID_JSON"):
            structure.load()
        self.assertEqual(path.read_text(), "CORRUPT FILE")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            structure.load()
        path.unlink()
        path.symlink_to(structure.root_path() / "another-file")
        with self.assertRaises(Exception):
            structure.load()

    def test_cli_read_update_and_revision_conflict(self):
        cli = ROOT / "services/social/SocialLocalOrganizationStructure.py"
        command = {"action": "create", "expectedRevision": 0,
                   "orgId": "org-1", "kind": "division", "name": "Fake unit"}
        env = dict(os.environ)
        first = subprocess.run([sys.executable, str(cli), "update"], env=env,
                               input=json.dumps(command) + "\n",
                               text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertTrue(json.loads(first.stdout)["ok"])
        second = subprocess.run([sys.executable, str(cli), "update"], env=env,
                                input=json.dumps(command) + "\n",
                                text=True, capture_output=True, check=False)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("Fake unit", second.stdout)
        read = subprocess.run([sys.executable, str(cli), "read"], env=env,
                              text=True, capture_output=True, check=False)
        self.assertEqual(read.returncode, 0)
        self.assertEqual(len(json.loads(read.stdout)["document"]["units"]), 1)


class StructureUIContracts(unittest.TestCase):
    def test_existing_organizations_portfolios_and_social_links_preserved(self):
        for marker in ("IdentityCenterLocalOrganizationEditor {",
                       "IdentityCenterLocalPortfolioEditor {",
                       "IdentityCenterLocalSocialLinksEditor {",
                       "IdentityCenterLocalStructureEditor {"):
            self.assertIn(marker, SECTIONS)
        self.assertIn("localStructureStore: SocialLocalOrganizationStructureStore", APP)
        self.assertIn("singleton SocialLocalOrganizationStructureStore 1.0", QMLDIR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        self.assertIn("interactive: false", SECTIONS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])

    def test_four_categories_source_only_no_privileges(self):
        for marker in ("MY STRUCTURE // LOCAL ORGANIZATION UNITS",
                       "DIVISIONS", "DEPARTMENTS", "LOCATIONS", "TEAMS",
                       "+ ADD UNIT", "CONFIRM ARCHIVE", "RESTORE",
                       "createUnit", "renameUnit", "archiveUnit", "restoreUnit"):
            self.assertIn(marker, EDITOR + STORE)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        for bad in ("scopeGrants", "accessToken", "refreshToken",
                    "canSwitchOrganization: true", "RoleAssignment",
                    "PanelWindow {", "FloatingWindow {", "FileView {"):
            self.assertNotIn(bad, EDITOR + STORE)


if __name__ == "__main__":
    unittest.main()
