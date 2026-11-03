"""Unified local-only search on the original Organizations settings page."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "widgets" / "messanger"
PANE = (Q / "IdentityCenterSettingsSections.qml").read_text()
SEARCH = (Q / "IdentityCenterLocalRecordsSearch.qml").read_text()
ORG = (Q / "IdentityCenterLocalOrganizationEditor.qml").read_text()
PORT = (Q / "IdentityCenterLocalPortfolioEditor.qml").read_text()
STRUCTURE = (Q / "IdentityCenterLocalStructureEditor.qml").read_text()
MODIFIER = (Q / "IdentityCenterLocalRelationshipModifiers.qml").read_text()


class UnifiedSearchContracts(unittest.TestCase):
    def test_inline_controls_no_extra_navigation(self):
        self.assertEqual(PANE.count("IdentityCenterLocalRecordsSearch {"), 1)
        self.assertIn('objectName: "orgLocalSearch"', PANE)
        self.assertIn('text: "SEARCH LOCAL ORGANIZATION RECORDS"', SEARCH)
        self.assertIn("Search all local records...", SEARCH)
        self.assertIn('label: "CLEAR SEARCH"', SEARCH)
        self.assertEqual(SEARCH.count("TextInput {"), 1)
        self.assertIn("maximumLength: 80", SEARCH)
        for name in ("IdentityCenterLocalOrganizationEditor {",
                     "IdentityCenterLocalPortfolioEditor {",
                     "IdentityCenterLocalStructureEditor {",
                     "IdentityCenterLocalRelationshipModifiers {"):
            self.assertEqual(PANE.count(name), 1)
        for banned in ("IdentityCenterLocalOrganizationsWorkspace {",
                       "activeWorkspace:", "OPEN RELATIONSHIPS",
                       "PanelWindow {", "FloatingWindow {",
                       "Process {", "FileView {"):
            self.assertNotIn(banned, SEARCH + PANE)

    def test_five_record_categories_and_read_only_store_inputs(self):
        for field in ("directoryStore", "portfolioStore", "structureStore",
                      "functionLocationStore", "branchLocationStore",
                      "reportingStore", "socialLinksStore", "identitiesSnapshot",
                      "accountDetailsStore"):
            self.assertIn("property var " + field + ": null", SEARCH)
        for name in ("all", "organizations", "portfolios", "units", "links"):
            self.assertIn('id:"' + name + '"', SEARCH)
        self.assertIn("onRecordFocused:", PANE)
        self.assertIn("sections.localEditingOrganizationId = orgId", PANE)
        self.assertIn("localStructureEditor.selectedKind = unitKind", PANE)
        self.assertIn("visibleMatches: matches.slice(0, 60)", SEARCH)
        self.assertIn("includeArchived", SEARCH)
        self.assertIn("ARCHIVED OR STALE", SEARCH)
        self.assertIn("org.branches", SEARCH)
        self.assertIn("portfolio.orgIds", SEARCH)
        self.assertIn("unit.kind", SEARCH)
        for name in ("functionLocationStore", "branchLocationStore",
                     "reportingStore", "socialLinksStore"):
            self.assertIn('records(' + name + ', "links")', SEARCH)

    def test_original_inline_editors_receive_search_only(self):
        self.assertEqual(PANE.count(
            "searchQuery: localRecordsSearch.searchText"), 4)
        for content in (ORG, PORT, STRUCTURE, MODIFIER):
            self.assertIn('property string searchQuery: ""', content)
            self.assertIn("normalizedSearch", content)
        self.assertIn("matchesOrganization(modelData)", ORG)
        self.assertIn("matchesBranch(orgRow.modelData, modelData)", ORG)
        self.assertIn("matchesPortfolio(modelData)", PORT)
        self.assertIn("matchesUnit(unit)", STRUCTURE)
        self.assertIn("unit.kind === editor.selectedKind", STRUCTURE)
        self.assertIn("visibleSavedEntries", MODIFIER)
        self.assertIn("model: editor.visibleSavedEntries", MODIFIER)
        self.assertIn("editor.describe(link)", MODIFIER)

    def test_no_auth_network_or_storage_behavior(self):
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        self.assertIn("interactive: false", PANE.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:240])
        for banned in ("https", "fetch(", "accessToken", "refreshToken",
                       "scopeGrants", "switchTenant(", "createSession",
                       "writer.", "save(", "unlink(", "archive("):
            self.assertNotIn(banned, SEARCH)


if __name__ == "__main__":
    unittest.main()
