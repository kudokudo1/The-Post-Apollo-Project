"""UI source contracts for staged private organization backup controls."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
QML = (ROOT / "widgets/messanger/IdentityCenterLocalOrgBackup.qml").read_text()
SCRIPT = (ROOT / "services/social/SocialLocalOrgBackup.py").read_text()


class BackupUIContracts(unittest.TestCase):
    def test_single_inline_backup_panel(self):
        self.assertEqual(PANE.count("IdentityCenterLocalOrgBackup {"), 1)
        self.assertIn('objectName: "orgLocalBackup"', PANE)
        for name in ("IdentityCenterLocalRecordsSearch {",
                     "IdentityCenterLocalSaveFeedback {",
                     "IdentityCenterLocalRefreshAll {",
                     "IdentityCenterLocalOrganizationEditor {",
                     "IdentityCenterLocalPortfolioEditor {",
                     "IdentityCenterLocalStructureEditor {",
                     "IdentityCenterLocalRelationshipModifiers {"):
            self.assertEqual(PANE.count(name), 1)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)

    def test_original_store_scope_and_no_restore(self):
        for name, bind in (
            ("directoryStore", "localDirectoryStore"),
            ("portfolioStore", "localPortfoliosStore"),
            ("structureStore", "localStructureStore"),
            ("functionLocationStore", "localUnitLocationLinksStore"),
            ("branchLocationStore", "localBranchLocationLinksStore"),
            ("reportingStore", "localFunctionalReportingStore"),
            ("socialLinksStore", "localLinksStore"),
        ):
            self.assertIn("property var " + name + ": null", QML)
            self.assertIn(name + ": sections." + bind, PANE)
        for op in ('runAction("create")', 'runAction("list")', 'runAction("verify")'):
            self.assertIn(op, QML)
        self.assertIn("restoreAvailable", SCRIPT)
        self.assertIn("interactive: false", QML.split(
            'label: "RESTORE // LOCKED"')[1][:100])

    def test_locks_modes_and_existing_button_geometry(self):
        for text in ("MAX_BACKUPS = 40", "0o600", "LOCK_EX | fcntl.LOCK_NB",
                     "O_NOFOLLOW", "sha256", "checksum", "os.link("):
            self.assertIn(text, SCRIPT)
        self.assertIn("height: 28", QML)
        self.assertIn("labelPixelSize: 9", QML)
        for forbidden in ("password", "accessToken", "refreshToken",
                          "scopeGrants", "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, QML)


if __name__ == "__main__":
    unittest.main()
