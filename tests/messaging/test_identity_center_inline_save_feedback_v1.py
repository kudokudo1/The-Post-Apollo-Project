"""Inline save feedback observer uses real store states and revisions."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT/"widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
FEEDBACK = (ROOT/"widgets/messanger/IdentityCenterLocalSaveFeedback.qml").read_text()

class InlineSaveFeedback(unittest.TestCase):
    def test_single_inline_observer_reads_all_original_stores(self):
        self.assertEqual(PANE.count("IdentityCenterLocalSaveFeedback {"), 1)
        self.assertIn('objectName: "orgLocalSaveFeedback"', PANE)
        for name, bound in (
            ("directoryStore","localDirectoryStore"),
            ("portfolioStore","localPortfoliosStore"),
            ("structureStore","localStructureStore"),
            ("functionLocationStore","localUnitLocationLinksStore"),
            ("branchLocationStore","localBranchLocationLinksStore"),
            ("reportingStore","localFunctionalReportingStore"),
            ("socialLinksStore","localLinksStore"),
        ):
            self.assertIn("property var " + name + ": null", FEEDBACK)
            self.assertIn(name + ": sections." + bound, PANE)
        for editor in ("IdentityCenterLocalOrganizationEditor {",
                       "IdentityCenterLocalPortfolioEditor {",
                       "IdentityCenterLocalStructureEditor {",
                       "IdentityCenterLocalRelationshipModifiers {"):
            self.assertEqual(PANE.count(editor), 1)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)

    def test_saving_is_not_a_confirmed_revision(self):
        for key in (
            'state === "saving"', 'state === "error"', 'state === "ready"',
            "rev > baseline", 'lastKind = "saved"',
            'lastKind = "unconfirmed"', '"NOT CONFIRMED // "',
            '"SAVING // "', '"SAVED // "', '"REVISION_CONFLICT"',
            '"No new write was confirmed."', "snapshotSignature",
            "onSnapshotSignatureChanged: observeAll()", "inFlight",
            "lastKind = code ===", 'lastKind = "loaded"',
        ):
            self.assertIn(key, FEEDBACK)
        self.assertIn("No automatic overwrite or retry.", FEEDBACK)

    def test_errors_and_store_names(self):
        for word in ("Organizations / Branches", "Portfolios", "Structure",
                     "Function / Location", "Branch / Location",
                     "Functional Reporting", "Social Associations",
                     "activeFailures", "savingCount", "lastMessage",
                     "codeOf(store)", 'objectName: "orgLocalSaveStatusText"'):
            self.assertIn(word, FEEDBACK)

    def test_observation_only_no_trusted_switch(self):
        for forbidden in ("Process {", "FileView {", "PanelWindow {",
                          "FloatingWindow {", "onTriggered:", "save(",
                          "update(", "refresh(", "unlink(", "accessToken",
                          "refreshToken", "scopeGrants", "createSession"):
            self.assertNotIn(forbidden, FEEDBACK)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        for file in ("SocialOrganizationDirectoryStore.qml",
                     "SocialLocalPortfoliosStore.qml",
                     "SocialLocalOrganizationStructureStore.qml",
                     "SocialLocalUnitLocationLinksStore.qml",
                     "SocialLocalBranchLocationLinksStore.qml",
                     "SocialLocalFunctionalReportingStore.qml",
                     "SocialOrganizationLinksStore.qml"):
            self.assertTrue((ROOT/"services/social"/file).is_file())

if __name__ == "__main__":
    unittest.main()
