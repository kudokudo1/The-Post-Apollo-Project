"""Control 3: one archived-record visibility control, original CRUD intact."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "widgets" / "messanger"
PANE = (Q / "IdentityCenterSettingsSections.qml").read_text()
SEARCH = (Q / "IdentityCenterLocalRecordsSearch.qml").read_text()
ORG = (Q / "IdentityCenterLocalOrganizationEditor.qml").read_text()
PORT = (Q / "IdentityCenterLocalPortfolioEditor.qml").read_text()
STRUCTURE = (Q / "IdentityCenterLocalStructureEditor.qml").read_text()


class SharedArchiveAndRecordActions(unittest.TestCase):
    def test_one_page_wide_toggle_all_three_editors_and_search(self):
        self.assertEqual(SEARCH.count('objectName: "localShowArchivedRecords"'), 1)
        self.assertEqual(SEARCH.count('"SHOW ARCHIVED RECORDS"'), 1)
        self.assertEqual(SEARCH.count('"HIDE ARCHIVED RECORDS"'), 1)
        self.assertIn("onTriggered: search.includeArchived = !search.includeArchived", SEARCH)
        self.assertLess(SEARCH.index('objectName: "localShowArchivedRecords"'),
                        SEARCH.index('visible: search.needle.length > 0'))
        self.assertIn("RECORD ACTIONS // ADD, EDIT NAME + SAVE, ARCHIVE + CONFIRM, RESTORE", SEARCH)
        self.assertIn("select ALL / NO SELECTION", SEARCH)
        self.assertEqual(PANE.count("useSharedArchiveControl: true"), 3)
        self.assertEqual(PANE.count("localRecordsSearch.includeArchived"), 3)
        for item in ('showArchived: localRecordsSearch.includeArchived',
                     'showArchivedUnits: localRecordsSearch.includeArchived',
                     'objectName: "orgLocalDirectoryEditor"',
                     'objectName: "orgLocalPortfolioEditor"',
                     'objectName: "localStructureEditor"'):
            self.assertIn(item, PANE)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)
        self.assertNotIn("activeWorkspace:", PANE)

    def test_original_add_rename_archive_restore_handlers_remain(self):
        for name in ("addOrganization(", "renameOrganization(",
                     "archiveOrganization(", "restoreOrganization(",
                     "addBranch(", "renameBranch(", "archiveBranch(",
                     "restoreBranch("):
            self.assertIn(name, ORG)
        for name in ("createPortfolio(", "renamePortfolio(",
                     "archivePortfolio(", "restorePortfolio(",
                     "attachOrganization(", "detachOrganization("):
            self.assertIn(name, PORT)
        for name in ("createUnit(", "renameUnit(", "archiveUnit(",
                     "restoreUnit("):
            self.assertIn(name, STRUCTURE)
        for source in (ORG, PORT, STRUCTURE):
            for label in ('"SAVE"', '"RESTORE"', '"ARCHIVE"',
                          '"CONFIRM ARCHIVE"'):
                self.assertIn(label, source)
        self.assertIn('"org:" + orgRow.modelData.id', ORG)
        self.assertIn('"branch:" + branchRow.modelData.id', ORG)
        self.assertIn('"p:" + portfolioRow.modelData.id', PORT)
        self.assertIn('"unit:" + unitRow.modelData.id', STRUCTURE)

    def test_red_direct_x_and_confirmation_are_in_original_rows(self):
        for source, expected in ((ORG, 2), (PORT, 1), (STRUCTURE, 1)):
            self.assertEqual(source.count('objectName: "orgDirectDeleteX"'), expected)
            self.assertEqual(source.count('label: "CONFIRM DELETE"'), expected)
            self.assertEqual(source.count('label: "CANCEL"'), expected)
            self.assertIn('role: "danger"', source)
            self.assertIn("requestDirectDelete(", source)
            self.assertIn("deletePending(", source)
            self.assertIn("removalController: null", source)
        self.assertEqual(PANE.count("removalController: localArchiveTray"), 3)

    def test_legacy_standalone_controls_remain_available_if_unembedded(self):
        for source in (ORG, PORT, STRUCTURE):
            self.assertIn("property bool useSharedArchiveControl: false", source)
            self.assertIn("visible: !editor.useSharedArchiveControl", source)
            self.assertIn('confirmationKey = ""', source)
        self.assertIn("onShowArchivedChanged:", ORG)
        self.assertIn("onShowArchivedChanged:", PORT)
        self.assertIn("onShowArchivedUnitsChanged:", STRUCTURE)

    def test_existing_backend_auth_and_storage_boundaries(self):
        for source in (SEARCH, PANE):
            for token in ("canSwitchOrganization: true", "accessToken =",
                          "scopeGrants =", "CreateRoleGrant", "deleteLocalData"):
                self.assertNotIn(token, source)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        for name in (
            "SocialOrganizationDirectory.py",
            "SocialLocalPortfolios.py",
            "SocialLocalOrganizationStructure.py",
            "SocialLocalFunctionalReporting.py",
        ):
            self.assertTrue((ROOT / "services/social" / name).is_file())


if __name__ == "__main__":
    unittest.main()
