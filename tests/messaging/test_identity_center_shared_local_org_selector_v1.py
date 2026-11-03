"""One shared LOCAL editing focus on existing inline Organizations page."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
ORG = (ROOT / "widgets/messanger/IdentityCenterLocalOrganizationEditor.qml").read_text()
STRUCTURE = (ROOT / "widgets/messanger/IdentityCenterLocalStructureEditor.qml").read_text()
MODIFIERS = (ROOT / "widgets/messanger/IdentityCenterLocalRelationshipModifiers.qml").read_text()
PORTFOLIOS = (ROOT / "widgets/messanger/IdentityCenterLocalPortfolioEditor.qml").read_text()


class SharedLocalOrgSelectorV1(unittest.TestCase):
    def test_single_page_and_one_shared_explicit_editing_selection(self):
        self.assertEqual(PANE.count('objectName: "orgLocalEditingContext"'), 1)
        self.assertEqual(PANE.count('text: "LOCAL ORGANIZATION TO EDIT"'), 1)
        self.assertIn('label: "ALL / NO SELECTION"', PANE)
        self.assertIn('property string localEditingOrganizationId: ""', PANE)
        self.assertIn("readonly property string activeLocalEditingOrganizationId:", PANE)
        self.assertIn("return !org.archived;", PANE)
        self.assertIn("org.id === sections.localEditingOrganizationId", PANE)
        self.assertEqual(PANE.count(
            "selectedOrgId: sections.activeLocalEditingOrganizationId"), 2)
        self.assertEqual(PANE.count("useSharedContext: true"), 2)
        self.assertIn("focusedOrganizationId: sections.activeLocalEditingOrganizationId", PANE)
        for name in (
            "IdentityCenterLocalOrganizationEditor {",
            "IdentityCenterLocalPortfolioEditor {",
            "IdentityCenterLocalStructureEditor {",
            "IdentityCenterLocalRelationshipModifiers {",
        ):
            self.assertEqual(PANE.count(name), 1, name)
        self.assertNotIn("IdentityCenterLocalOrganizationsWorkspace {", PANE)
        self.assertNotIn("OPEN RELATIONSHIPS", PANE)

    def test_company_editor_can_still_show_all_and_portfolios_are_cross_company(self):
        self.assertIn('property string focusedOrganizationId: ""', ORG)
        self.assertIn('editor.focusedOrganizationId === ""', ORG)
        self.assertIn('editor.focusedOrganizationId === modelData.id', ORG)
        self.assertIn("IdentityCenterLocalPortfolioEditor {", PANE)
        self.assertIn("portfolioStore: sections.localPortfoliosStore", PANE)
        self.assertIn("function availableToAdd(portfolio)", PORTFOLIOS)
        self.assertNotIn("focusedOrganizationId", PORTFOLIOS)
        self.assertIn("showArchived", ORG)
        self.assertIn("showArchived", STRUCTURE)

    def test_structure_and_modifiers_share_focus_but_not_storage(self):
        self.assertIn("property bool useSharedContext: false", STRUCTURE)
        self.assertIn("visible: !editor.useSharedContext", STRUCTURE)
        self.assertIn("property bool useSharedContext: false", MODIFIERS)
        self.assertEqual(MODIFIERS.count("visible: !editor.useSharedContext"), 2)
        self.assertIn("onSelectedOrgIdChanged:", MODIFIERS)
        self.assertIn('selectedSourceId = "";', MODIFIERS)
        self.assertIn('selectedTargetId = "";', MODIFIERS)
        self.assertIn('onSelectedOrgIdChanged: confirmationKey = ""', STRUCTURE)
        self.assertIn("localDirectoryStore: null", PANE)
        self.assertIn("socialLinksStore: sections.localLinksStore", PANE)
        self.assertIn("functionLocationStore: sections.localUnitLocationLinksStore", PANE)

    def test_trusted_identity_switch_remains_unavailable(self):
        self.assertIn('ACTIVE ORGANIZATION // NONE VERIFIED', PANE)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        self.assertIn("interactive: false", PANE.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:240])
        for banned in ("canSwitchOrganization: true", "accessToken",
                       "refreshToken", "scopeGrants =",
                       "permission ="):
            self.assertNotIn(banned, PANE)
        for path in (
            "SocialOrganizationDirectory.py",
            "SocialLocalOrganizationStructure.py",
            "SocialLocalUnitLocationLinks.py",
            "SocialLocalBranchLocationLinks.py",
            "SocialLocalFunctionalReporting.py",
            "SocialOrganizationLinks.py",
        ):
            self.assertTrue((ROOT / "services/social" / path).is_file())


if __name__ == "__main__":
    unittest.main()
