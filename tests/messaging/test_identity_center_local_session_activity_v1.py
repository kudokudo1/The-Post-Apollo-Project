"""Control 7: current-session observed local outcomes, not a fictional audit log."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "widgets" / "messanger"
PANE = (Q / "IdentityCenterSettingsSections.qml").read_text()
ACT = (Q / "IdentityCenterLocalSessionActivity.qml").read_text()
SAVE = (Q / "IdentityCenterLocalSaveFeedback.qml").read_text()
REFRESH = (Q / "IdentityCenterLocalRefreshAll.qml").read_text()
BACKUP = (Q / "IdentityCenterLocalOrgBackup.qml").read_text()
CHECKLIST = (ROOT / "MODEL/contracts/social-org-manager-deferred-live-tests-v1.md").read_text()


class CurrentSessionActivityContracts(unittest.TestCase):
    def test_single_page_observation_and_no_new_storage(self):
        self.assertEqual(PANE.count("IdentityCenterLocalSessionActivity {"), 1)
        self.assertIn('objectName: "orgLocalSessionActivity"', PANE)
        for bind in ("saveFeedback: localSaveFeedback",
                     "refreshPanel: localRefreshAll", "backupPanel: localOrgBackup",
                     'sections.activeSection === "ORGANIZATIONS"'):
            self.assertIn(bind, PANE)
        for original in ("IdentityCenterLocalRecordsSearch {",
                         "IdentityCenterLocalSaveFeedback {",
                         "IdentityCenterLocalRefreshAll {",
                         "IdentityCenterLocalOrgBackup {",
                         "IdentityCenterLocalOrganizationEditor {",
                         "IdentityCenterLocalPortfolioEditor {",
                         "IdentityCenterLocalStructureEditor {",
                         "IdentityCenterLocalRelationshipModifiers {"):
            self.assertEqual(PANE.count(original), 1)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)

    def test_only_existing_confirmed_outcomes_are_recorded(self):
        self.assertIn("signal activityObserved(string kind, string source, string detail)", SAVE)
        self.assertIn('feedback.activityObserved(lastKind, source.label, lastMessage)', SAVE)
        self.assertIn('feedback.activityObserved("failure", source.label, lastMessage)', SAVE)
        self.assertIn('feedback.activityObserved("loaded", source.label, lastMessage)', SAVE)
        self.assertIn("rev > baseline", SAVE)
        self.assertIn("signal activityObserved(string kind, string detail)", REFRESH)
        self.assertIn("refreshPanel.activityObserved(", REFRESH)
        self.assertIn("signal activityObserved(string kind, string detail)", BACKUP)
        for kind in ("failure", "listing", "backup", "validation"):
            self.assertIn('backupPanel.activityObserved("' + kind + '"', BACKUP)
        self.assertEqual(ACT.count("Connections {"), 3)
        for handle in ("onActivityObserved(kind, source, detail)",
                       "onActivityObserved(kind, detail)"):
            self.assertIn(handle, ACT)
        self.assertIn("if (!recordingEnabled)", ACT)

    def test_bounded_ephemeral_history_and_clear_button(self):
        for needle in ("CURRENT SESSION ACTIVITY // OBSERVED OUTCOMES",
                       "No past edit timeline, actor identity or server audit log",
                       "Times indicate when this screen observed a result.",
                       "entries = [entry].concat(entries).slice(0, 40)",
                       'entries.slice(0, 6)',
                       'label: "CLEAR SESSION VIEW"',
                       '"SHOW SESSION EVENTS"', '"SHOW RECENT SIX"',
                       'objectName: "orgSessionClearView"',
                       'objectName: "orgSessionShowAll"',
                       'height: 28', 'labelPixelSize: 9'):
            self.assertIn(needle, ACT)
        for forbidden in ("Process {", "FileView {", "JsonStore {",
                          "Qt.openUrlExternally(", "fetch(", "save(", "refresh(",
                          "unlink(", "import(", "accessToken", "refreshToken",
                          "scopeGrants", "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, ACT)
        self.assertIn('label: "RESTORE // LOCKED"', BACKUP)
        self.assertIn("interactive: false", BACKUP.split(
            'label: "RESTORE // LOCKED"')[1][:110])

    def test_operator_live_backup_pass_recorded_without_fake_restore(self):
        self.assertIn("OPERATOR-PASSED (2026-11-04)", CHECKLIST)
        self.assertIn("backup and viewed the list", CHECKLIST.lower())
        self.assertIn("validated it in the live UI", CHECKLIST)
        self.assertIn("| 6c. Restore", CHECKLIST)
        self.assertIn("NOT IMPLEMENTED", CHECKLIST)
        for n in range(1, 6):
            self.assertIn("| " + str(n) + ".", CHECKLIST)
        self.assertIn("DEFERRED", CHECKLIST)
        self.assertIn("not live user acceptance", CHECKLIST)


if __name__ == "__main__":
    unittest.main()
