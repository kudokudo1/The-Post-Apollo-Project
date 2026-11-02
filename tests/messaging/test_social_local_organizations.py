"""Synthetic local organization directory security, persistence and UI contracts."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/social"))
import SocialOrganizationDirectory as directory  # noqa: E402

SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalOrganizationEditor.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
STORE = (ROOT / "services/social/SocialOrganizationDirectoryStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def update(doc, action, **kwargs):
    return directory.apply(doc, {"action": action,
                                 "expectedRevision": doc["revision"], **kwargs})


class LocalDirectoryModel(unittest.TestCase):
    def test_three_kinds_rename_branches_archive_restore(self):
        doc = directory.initial()
        for name, kind in [("SYNTHETIC LLC A", "llc"),
                           ("SYNTHETIC CHARITY", "nonprofit"),
                           ("SYNTHETIC OTHER", "other")]:
            doc = update(doc, "add_org", name=name, kind=kind)
        oid = doc["organizations"][0]["id"]
        doc = update(doc, "add_branch", orgId=oid, name="Fake division")
        bid = doc["organizations"][0]["branches"][0]["id"]
        doc = update(doc, "rename_branch", orgId=oid, branchId=bid, name="Fake program")
        doc = update(doc, "archive_branch", orgId=oid, branchId=bid)
        self.assertTrue(doc["organizations"][0]["branches"][0]["archived"])
        doc = update(doc, "restore_branch", orgId=oid, branchId=bid)
        doc = update(doc, "rename_org", orgId=oid, name="FAKE LLC RENAMED")
        doc = update(doc, "archive_org", orgId=oid)
        self.assertTrue(doc["organizations"][0]["archived"])
        doc = update(doc, "restore_org", orgId=oid)
        self.assertFalse(doc["organizations"][0]["archived"])
        self.assertEqual(doc["revision"], 10)
        self.assertEqual(len(doc["organizations"]), 3)
        self.assertEqual(doc["organizations"][0]["branches"][0]["name"], "Fake program")

    def test_duplicate_casefold_and_restore_conflict(self):
        doc = update(directory.initial(), "add_org", name="Test Corp", kind="llc")
        with self.assertRaisesRegex(directory.DirectoryError, "DUPLICATE_NAME"):
            update(doc, "add_org", name="test corp", kind="nonprofit")
        doc = update(doc, "archive_org", orgId="org-1")
        doc = update(doc, "add_org", name="test corp", kind="llc")
        with self.assertRaisesRegex(directory.DirectoryError, "DUPLICATE_NAME"):
            update(doc, "restore_org", orgId="org-1")
        doc = update(doc, "add_branch", orgId="org-3", name="Program")
        with self.assertRaisesRegex(directory.DirectoryError, "DUPLICATE_NAME"):
            update(doc, "add_branch", orgId="org-3", name="program")

    def test_revision_lock_invalid_ids_and_validation(self):
        doc = directory.initial()
        with self.assertRaisesRegex(directory.DirectoryError, "REVISION_CONFLICT"):
            directory.apply(doc, {"action":"add_org", "name":"test", "kind":"llc",
                                  "expectedRevision":9})
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_REQUEST"):
            directory.apply(doc, {"action":"add_org", "name":"test", "kind":"llc",
                                  "expectedRevision":0, "scopeGrants":[]})
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_ID"):
            update(doc, "archive_org", orgId="identity-1")
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_NAME"):
            update(doc, "add_org", name="Bad\nname", kind="llc")
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_KIND"):
            update(doc, "add_org", name="Good", kind="government")

    def test_corrupt_documents_and_duplicate_json_keys(self):
        bad = directory.initial()
        bad["organizations"] = [{"id":"org-1","name":"Fake","kind":"llc",
                                 "archived":False,"branches":[]}]
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_DOCUMENT"):
            directory.validate(bad)
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_JSON"):
            directory.decode(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(directory.DirectoryError, "INVALID_JSON"):
            directory.decode(b'{"x":NaN}')

    def test_private_atomic_disk_and_absent_read_no_write(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"XDG_DATA_HOME":tmp}):
            self.assertEqual(directory.load(), directory.initial())
            self.assertFalse(directory.location().exists())
            doc = update(directory.load(), "add_org", name="FAKE", kind="llc")
            directory.save(doc)
            self.assertEqual(directory.location().stat().st_mode & 0o777, 0o600)
            self.assertEqual(directory.root_path().stat().st_mode & 0o777, 0o700)
            self.assertEqual(directory.load(), doc)
            self.assertEqual([p.name for p in directory.root_path().iterdir()],
                             [directory.FILE_NAME])

    def test_unsafe_corrupt_and_symlink_refuse_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"XDG_DATA_HOME":tmp}):
            root = directory.root_path()
            root.mkdir(parents=True, mode=0o700)
            path = directory.location()
            path.write_text("CORRUPT")
            path.chmod(0o600)
            with self.assertRaisesRegex(directory.DirectoryError, "INVALID_JSON"):
                directory.load()
            self.assertEqual(path.read_text(), "CORRUPT")
            path.chmod(0o644)
            with self.assertRaises(Exception):
                directory.load()
            path.unlink()
            path.symlink_to(root / "another-file")
            with self.assertRaises(Exception):
                directory.load()


class LocalDirectoryUI(unittest.TestCase):
    def test_settings_and_identity_boundaries(self):
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        self.assertIn("interactive: false", SECTIONS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])
        self.assertIn('text: "ACTIVE ORGANIZATION // NONE VERIFIED"', SECTIONS)
        self.assertIn("IdentityCenterLocalOrganizationEditor {", SECTIONS)
        self.assertIn("localDirectoryStore: SocialOrganizationDirectoryStore", SELECTOR)
        self.assertIn("property var localDirectoryStore: null", SECTIONS)
        self.assertIn("singleton SocialOrganizationDirectoryStore 1.0", QMLDIR)
        self.assertNotIn("FileView {", SECTIONS)
        self.assertNotIn("Process {", SECTIONS)
        self.assertNotIn("SocialIdentityStore", STORE)

    def test_actions_and_read_only_cli(self):
        for name in ("+ ORGANIZATION", "+ BRANCH", "SAVE", "CONFIRM ARCHIVE",
                     "RESTORE", "SHOW ARCHIVED", "HIDE ARCHIVED"):
            self.assertIn(name, EDITOR)
        for name in ("archiveOrganization", "restoreOrganization",
                     "archiveBranch", "restoreBranch", "renameOrganization",
                     "renameBranch"):
            self.assertIn("directoryStore." + name, EDITOR)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        self.assertNotIn("accessToken", STORE)
        self.assertNotIn("canSwitchOrganization: true", EDITOR)


if __name__ == "__main__":
    unittest.main()
