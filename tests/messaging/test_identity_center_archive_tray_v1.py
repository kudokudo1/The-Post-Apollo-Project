"""Visible Archive Tray near top, red two-step removal and original editors."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
TRAY = (ROOT / "widgets/messanger/IdentityCenterLocalArchiveTray.qml").read_text()
REMOVE = (ROOT / "services/social/SocialLocalOrgArchivedRemoval.py").read_text()
SEARCH = (ROOT / "widgets/messanger/IdentityCenterLocalRecordsSearch.qml").read_text()


class ArchiveTrayV1(unittest.TestCase):
    def test_visible_top_archive_entry_before_search(self):
        self.assertEqual(PANE.count("IdentityCenterLocalArchiveTray {"), 1)
        self.assertLess(PANE.index("IdentityCenterLocalArchiveTray {"),
                        PANE.index("IdentityCenterLocalRecordsSearch {"))
        self.assertIn('objectName: "orgLocalArchiveTray"', PANE)
        self.assertIn('objectName: "orgArchiveTrayTitle"', TRAY)
        self.assertIn('objectName: "orgArchiveTrayToggle"', TRAY)
        self.assertIn('text: "ARCHIVE TRAY // " + tray.archivedCount', TRAY)
        self.assertIn('label: tray.expanded ? "CLOSE ARCHIVE TRAY"', TRAY)
        self.assertIn('"REMOVE PERMANENTLY"', TRAY)
        for source in ("IdentityCenterLocalOrganizationEditor {",
                       "IdentityCenterLocalPortfolioEditor {",
                       "IdentityCenterLocalStructureEditor {",
                       "IdentityCenterLocalRelationshipModifiers {",
                       "IdentityCenterLocalRecordsSearch {"):
            self.assertEqual(PANE.count(source), 1)
        self.assertIn('objectName: "localShowArchivedRecords"', SEARCH)
        self.assertIn("ARCHIVE TRAY ABOVE", SEARCH)

    def test_explicit_red_removal_and_double_confirmation(self):
        self.assertIn('objectName: "orgArchiveRemoveAction"', TRAY)
        self.assertIn('role: "danger"', TRAY)
        self.assertIn('role: "refresh"', TRAY)
        self.assertIn('label: "RESTORE"', TRAY)
        self.assertIn('"CONFIRM REMOVE" : "REMOVE PERMANENTLY"', TRAY)
        self.assertIn("if (confirmationKey !== key)", TRAY)
        self.assertIn("confirmationKey = key;", TRAY)
        self.assertIn("pendingRequest =", TRAY)
        self.assertIn("onExpandedChanged: confirmationKey = ", TRAY)
        self.assertIn("!tray.busy", TRAY)
        self.assertIn("tray.storesReady", TRAY)
        self.assertIn("REMOVE REFUSED", TRAY)
        self.assertIn("BACKUP_REQUIRED", TRAY)

    def test_backend_all_seven_locks_no_cascade_and_snapshot_requirement(self):
        self.assertIn("backups.lock_sources(stack)", REMOVE)
        self.assertIn("module.save(module.validate(doc))", REMOVE)
        self.assertIn('raise RemovalError("ARCHIVE_BEFORE_REMOVE")', REMOVE)
        self.assertIn('raise RemovalError("BACKUP_REQUIRED")', REMOVE)
        self.assertIn('raise RemovalError("REVISION_CONFLICT")', REMOVE)
        self.assertIn("if record[\"name\"] != request[\"expectedName\"]", REMOVE)
        self.assertIn("records.remove(record)", REMOVE)
        self.assertIn('doc["revision"] += 1', REMOVE)
        self.assertIn('"nextId"', (ROOT / "services/social/SocialOrganizationDirectory.py").read_text())
        for forbidden in ("shutil.rmtree", "os.remove(", "deleteLocalData",
                          "accessToken", "scopeGrants", "createSession"):
            self.assertNotIn(forbidden, REMOVE)
        self.assertIn('label: "RESTORE // LOCKED"',
                      (ROOT / "widgets/messanger/IdentityCenterLocalOrgBackup.qml").read_text())


if __name__ == "__main__":
    unittest.main()
