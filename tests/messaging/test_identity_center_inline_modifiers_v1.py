"""Inline Organizations modifier form, not another set of nested menus."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
FORM = (ROOT / "widgets/messanger/IdentityCenterLocalRelationshipModifiers.qml").read_text()


class InlineModifierUIContracts(unittest.TestCase):
    def test_one_page_preserves_original_direct_editors(self):
        for editor in (
            "IdentityCenterLocalOrganizationEditor",
            "IdentityCenterLocalPortfolioEditor",
            "IdentityCenterLocalStructureEditor",
            "IdentityCenterLocalRelationshipModifiers",
        ):
            self.assertEqual(PANE.count(editor + " {"), 1, editor)
        for old in (
            "IdentityCenterLocalOrganizationsWorkspace {",
            "IdentityCenterLocalUnitLocationsEditor {",
            "IdentityCenterLocalBranchLocationsEditor {",
            "IdentityCenterLocalFunctionalReportingEditor {",
            "IdentityCenterLocalSocialLinksEditor {",
        ):
            self.assertNotIn(old, PANE)
        self.assertNotIn("orgNavigationV2", PANE)
        self.assertNotIn("activeWorkspace", PANE)
        self.assertNotIn("relationshipMode", PANE)
        self.assertIn('objectName: "orgModifierForm"', PANE)
        self.assertIn("ACTIVE ORGANIZATION // NONE VERIFIED", PANE)

    def test_one_source_selector_and_three_inline_modifiers(self):
        for expected in (
            'text: "ORGANIZATION LINKS // APPLY MODIFIER"',
            '"LOCATED AT"', '"REPORTS TO"', '"SOCIAL LABEL"',
            "APPLY TO // ORGANIZATION / BRANCH / FUNCTIONAL UNIT",
            'label: "APPLY MODIFIER"',
            "SAVED ORGANIZATION LINKS", "UNLINK MODIFIER",
            "CONFIRM UNLINK", "SHOW ALL ORGS", "REFRESH LINKS",
        ):
            self.assertIn(expected, FORM)
        self.assertEqual(FORM.count('label: "APPLY MODIFIER"'), 1)
        self.assertEqual(FORM.count('text: "ORGANIZATION"'), 1)
        self.assertEqual(FORM.count('text: "MODIFIER"'), 1)
        self.assertIn("subjectQuery", FORM)
        self.assertIn("visibleSubjects", FORM)
        for forbidden in (
            "activeWorkspace", "selectWorkspace", "companyMode",
            "relationshipMode", "OPEN RELATIONSHIPS",
            "OPEN STRUCTURE", "OPEN COMPANIES",
        ):
            self.assertNotIn(forbidden, FORM)

    def test_existing_four_writers_are_dispatched_by_scope(self):
        for call in (
            "branchLocationStore.linkBranch(",
            "functionLocationStore.linkToLocation(",
            "reportingStore.addRelationship(",
            "socialLinksStore.linkIdentity(",
            "socialLinksStore.linkAccountLabel(",
            "branchLocationStore.unlinkBranch(",
            "functionLocationStore.unlinkFromLocation(",
            "reportingStore.removeRelationship(",
            "socialLinksStore.unlink(",
        ):
            self.assertIn(call, FORM)
        for arg in ("functionLocationStore: sections.localUnitLocationLinksStore",
                    "branchLocationStore: sections.localBranchLocationLinksStore",
                    "reportingStore: sections.localFunctionalReportingStore",
                    "socialLinksStore: sections.localLinksStore"):
            self.assertIn(arg, PANE)
        for field in ("directoryStore", "structureStore", "functionLocationStore",
                      "branchLocationStore", "reportingStore", "socialLinksStore",
                      "identitiesSnapshot", "accountDetailsStore"):
            self.assertIn("property var " + field + ": null", FORM)

    def test_support_matrix_and_cycle_duplicate_guards(self):
        for needle in (
            'name === "social"',
            'selectedSourceKind === "organization"',
            'selectedSourceKind === "branch"',
            'name === "reporting"',
            'name === "location"',
            'selectedSourceKind === "function"',
            "alreadyLinked()", "wouldCycle()",
            "if (!validSelection) return false;",
            'currentStore.state === "ready"',
            "unit.orgId === editor.selectedOrgId",
            "selectedSourceId", "onSelectedOrgIdChanged",
            'selectedSourceId = "";', 'selectedTargetId = "";',
        ):
            self.assertIn(needle, FORM)

    def test_stale_entries_and_disabled_verified_switch_remain(self):
        self.assertIn("STALE OR UNAVAILABLE // NOT AN ACCESS GRANT", FORM)
        self.assertIn("storeFor(itemRow.modelData).state", FORM)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        self.assertIn("interactive: false", PANE.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:240])
        for forbidden in (
            "Process {", "FileView {", "PanelWindow {", "FloatingWindow {",
            "Quickshell.Io", "HttpRequest", "accessToken", "refreshToken",
            "scopeGrants", "canSwitchOrganization: true",
        ):
            self.assertNotIn(forbidden, FORM)
        for path in (
            "SocialOrganizationDirectory.py",
            "SocialLocalPortfolios.py",
            "SocialLocalOrganizationStructure.py",
            "SocialLocalUnitLocationLinks.py",
            "SocialLocalBranchLocationLinks.py",
            "SocialLocalFunctionalReporting.py",
            "SocialOrganizationLinks.py",
        ):
            self.assertTrue((ROOT / "services/social" / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
