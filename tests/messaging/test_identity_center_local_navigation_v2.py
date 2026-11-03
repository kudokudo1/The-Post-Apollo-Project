"""UI-only Organizations Navigation v2 compatibility checks.

All original storage and action providers remain untouched. The UI presents a
single local organization edit context, never an authenticated tenant switch.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
WORKSPACE = (ROOT / "widgets/messanger/IdentityCenterLocalOrganizationsWorkspace.qml").read_text()
EDITORS = [
    "IdentityCenterLocalOrganizationEditor",
    "IdentityCenterLocalPortfolioEditor",
    "IdentityCenterLocalStructureEditor",
    "IdentityCenterLocalUnitLocationsEditor",
    "IdentityCenterLocalBranchLocationsEditor",
    "IdentityCenterLocalFunctionalReportingEditor",
    "IdentityCenterLocalSocialLinksEditor",
]
SCOPED = EDITORS[2:]


class OrganizationNavigationV2Contracts(unittest.TestCase):
    def test_old_long_stack_replaced_with_single_workspace(self):
        self.assertEqual(PANE.count("IdentityCenterLocalOrganizationsWorkspace {"), 1)
        for name in EDITORS:
            self.assertNotIn(name + " {", PANE)
            self.assertEqual(WORKSPACE.count(name + " {"), 1)
        for tab in ("OVERVIEW", "COMPANIES", "STRUCTURE", "RELATIONSHIPS",
                    "ORGANIZATIONS & BRANCHES", "PORTFOLIOS",
                    "REPORTING", "FUNCTION / LOCATION",
                    "BRANCH / LOCATION", "SOCIAL ASSOCIATIONS"):
            self.assertIn('label:"' + tab + '"', WORKSPACE)
        self.assertIn('activeWorkspace: "overview"', WORKSPACE)
        self.assertIn('relationshipMode: "reporting"', WORKSPACE)
        self.assertIn('companyMode: "organizations"', WORKSPACE)

    def test_shared_organization_context_is_local_only(self):
        self.assertIn("readonly property string currentOrgId:", WORKSPACE)
        self.assertIn("filter(function(org) { return !org.archived; })", WORKSPACE)
        self.assertIn("local selection does NOT switch".lower(), WORKSPACE.lower())
        self.assertEqual(WORKSPACE.count("selectedOrgId: workspace.currentOrgId"), 5)
        self.assertEqual(WORKSPACE.count("useSharedContext: true"), 5)
        for name in SCOPED:
            content = (ROOT / ("widgets/messanger/" + name + ".qml")).read_text()
            self.assertIn("property bool useSharedContext: false", content)
            self.assertIn("visible: !editor.useSharedContext" if
                          name != "IdentityCenterLocalSocialLinksEditor"
                          else "visible: !linksEditor.useSharedContext", content)
            self.assertIn("onSelectedOrgIdChanged:", content)

    def test_only_one_workspace_and_one_relationship_mode_visible(self):
        self.assertIn('visible: workspace.activeWorkspace === "companies"', WORKSPACE)
        self.assertIn('visible: workspace.activeWorkspace === "structure"', WORKSPACE)
        self.assertIn('visible: workspace.activeWorkspace === "relationships"', WORKSPACE)
        self.assertIn('visible: workspace.relationshipMode === "reporting"', WORKSPACE)
        self.assertIn('visible: workspace.relationshipMode === "functions"', WORKSPACE)
        self.assertIn('visible: workspace.relationshipMode === "branches"', WORKSPACE)
        self.assertIn('visible: workspace.relationshipMode === "social"', WORKSPACE)
        self.assertIn('visible: workspace.companyMode === "organizations"', WORKSPACE)
        self.assertIn('visible: workspace.companyMode === "portfolios"', WORKSPACE)
        for name in ("directoryStore", "portfolioStore", "structureStore",
                     "functionLocationStore", "branchLocationStore",
                     "reportingStore", "socialLinksStore",
                     "identitiesSnapshot", "accountDetailsStore"):
            self.assertIn(name + ": sections.", PANE)
            self.assertIn("property var " + name + ": null", WORKSPACE)
        for banned in ("Process {", "FileView {", "FloatingWindow {",
                       "PanelWindow {", "HttpRequest", "Qt.openUrlExternally(",
                       "ShellRoot {", "createUser", "grantScopedRole"):
            self.assertNotIn(banned, WORKSPACE)

    def test_verified_identity_switch_remains_disabled(self):
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        switch = PANE.index('label: "SWITCH ORGANIZATION // UNAVAILABLE"')
        self.assertIn("interactive: false", PANE[switch:switch + 240])
        self.assertIn("organizationDisplayReady", PANE)
        self.assertIn("ACTIVE ORGANIZATION // NONE VERIFIED", PANE)
        for banned in ("canSwitchOrganization: true", "scopeGrants",
                       "accessToken", "refreshToken", "principalId"):
            self.assertNotIn(banned, WORKSPACE)
        # A summary count may use local saved records but cannot mint authority.
        self.assertIn('count(directoryStore, "organizations")', WORKSPACE)
        self.assertIn('count(portfolioStore, "portfolios")', WORKSPACE)

    def test_original_local_storage_modules_are_preserved(self):
        for path in (
            "services/social/SocialOrganizationDirectory.py",
            "services/social/SocialLocalPortfolios.py",
            "services/social/SocialLocalOrganizationStructure.py",
            "services/social/SocialLocalUnitLocationLinks.py",
            "services/social/SocialLocalBranchLocationLinks.py",
            "services/social/SocialLocalFunctionalReporting.py",
            "services/social/SocialOrganizationLinks.py",
        ):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
