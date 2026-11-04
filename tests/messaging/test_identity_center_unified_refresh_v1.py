"""Control 5: one guarded inline refresh for seven original local stores."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "widgets" / "messanger"
PANE = (Q / "IdentityCenterSettingsSections.qml").read_text()
REFRESH = (Q / "IdentityCenterLocalRefreshAll.qml").read_text()
EDITORS = [
    (Q / "IdentityCenterLocalOrganizationEditor.qml").read_text(),
    (Q / "IdentityCenterLocalPortfolioEditor.qml").read_text(),
    (Q / "IdentityCenterLocalStructureEditor.qml").read_text(),
    (Q / "IdentityCenterLocalRelationshipModifiers.qml").read_text(),
]


class UnifiedRefreshV1(unittest.TestCase):
    def test_one_button_same_inline_page(self):
        self.assertEqual(PANE.count("IdentityCenterLocalRefreshAll {"), 1)
        self.assertIn('objectName: "orgLocalRefreshAll"', PANE)
        self.assertEqual(REFRESH.count('label: "REFRESH ALL"'), 1)
        self.assertEqual(REFRESH.count('objectName: "orgRefreshAllButton"'), 1)
        self.assertIn('width: 150', REFRESH)
        self.assertIn('height: 28', REFRESH)
        self.assertIn('labelPixelSize: 9', REFRESH)
        for original in (
            "IdentityCenterLocalOrganizationEditor {",
            "IdentityCenterLocalPortfolioEditor {",
            "IdentityCenterLocalStructureEditor {",
            "IdentityCenterLocalRelationshipModifiers {",
            "IdentityCenterLocalSaveFeedback {",
            "IdentityCenterLocalRecordsSearch {",
        ):
            self.assertEqual(PANE.count(original), 1, original)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)
        self.assertNotIn("activeWorkspace:", PANE)

    def test_seven_original_stores_are_called_without_new_io(self):
        for field, store in (
            ("directoryStore", "localDirectoryStore"),
            ("portfolioStore", "localPortfoliosStore"),
            ("structureStore", "localStructureStore"),
            ("functionLocationStore", "localUnitLocationLinksStore"),
            ("branchLocationStore", "localBranchLocationLinksStore"),
            ("reportingStore", "localFunctionalReportingStore"),
            ("socialLinksStore", "localLinksStore"),
        ):
            self.assertIn("property var " + field + ": null", REFRESH)
            self.assertIn(field + ": sections." + store, PANE)
        self.assertIn("source.store.refresh() === true", REFRESH)
        self.assertIn("if (!canRefresh)", REFRESH)
        self.assertIn("acceptedRefreshCount", REFRESH)
        self.assertIn("rejected.join", REFRESH)
        self.assertIn("REFRESH PARTIAL", REFRESH)
        for forbidden in ("Process {", "FileView {", "Qt.openUrlExternally",
                          "save(", "update(", "unlink(", "delete(", "archive(",
                          "accessToken", "scopeGrants", "createSession"):
            self.assertNotIn(forbidden, REFRESH)

    def test_saves_loading_and_repeated_clicks_are_guarded(self):
        for expected in ('state === "saving"', 'state === "loading"',
                         'state === "error"', 'state === "ready"',
                         'typeof entry.store.refresh !== "function"',
                         "refreshInProgress", "onStateSignatureChanged: checkCompletion()",
                         "No automatic retry.", "REFRESH COMPLETE",
                         "REFRESH ENDED WITH ERRORS", "REFRESH NOT STARTED",
                         "No automatic", "Refresh reads existing local records"):
            self.assertIn(expected, REFRESH)
        self.assertIn("interactive: refreshPanel.canRefresh", REFRESH)
        self.assertIn("lastRefreshResult", REFRESH)
        self.assertIn("savingCount", (Q / "IdentityCenterLocalSaveFeedback.qml").read_text())

    def test_four_old_reload_buttons_are_hidden_only_on_shared_page(self):
        self.assertEqual(PANE.count("useSharedRefreshControl: true"), 4)
        for editor in EDITORS:
            self.assertIn("property bool useSharedRefreshControl: false", editor)
            self.assertIn("visible: !editor.useSharedRefreshControl", editor)
        for marker, editor in (
            ('label: "RELOAD DIRECTORY"', EDITORS[0]),
            ('label: "RELOAD PORTFOLIOS"', EDITORS[1]),
            ('label: "RELOAD STRUCTURE"', EDITORS[2]),
            ('label: "REFRESH LINKS"', EDITORS[3]),
        ):
            self.assertIn(marker, editor)
        for service in (
            "SocialOrganizationDirectoryStore.qml",
            "SocialLocalPortfoliosStore.qml",
            "SocialLocalOrganizationStructureStore.qml",
            "SocialLocalUnitLocationLinksStore.qml",
            "SocialLocalBranchLocationLinksStore.qml",
            "SocialLocalFunctionalReportingStore.qml",
            "SocialOrganizationLinksStore.qml",
        ):
            self.assertTrue((ROOT / "services/social" / service).is_file(), service)

    def test_verified_organization_switch_remains_disabled(self):
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        self.assertIn("interactive: false", PANE.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:240])


if __name__ == "__main__":
    unittest.main()
