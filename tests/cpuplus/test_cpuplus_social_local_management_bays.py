"""CPU++ Social local-management UI: reuse owners, preserve geometry and trust.

Source-level integration assertions only, not live Qt/Wayland rendering tests.
The canonical Social data-writer and seven-store removal tests run in CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
NAV = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementNav.qml").read_text(
    encoding="utf-8")
LOCAL = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementPane.qml").read_text(
    encoding="utf-8")
ID = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(
    encoding="utf-8")
ORGANIZATIONS = (
    ROOT / "widgets/messanger/IdentityCenterLocalOrganizationEditor.qml"
).read_text(encoding="utf-8")
STRUCTURE = (
    ROOT / "widgets/messanger/IdentityCenterLocalStructureEditor.qml"
).read_text(encoding="utf-8")
PORTFOLIOS = (
    ROOT / "widgets/messanger/IdentityCenterLocalPortfolioEditor.qml"
).read_text(encoding="utf-8")
REMOVAL = (
    ROOT / "widgets/messanger/IdentityCenterLocalArchiveTray.qml"
).read_text(encoding="utf-8")
SOCIAL = (
    ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml"
).read_text(encoding="utf-8")


class CpuPlusSocialManagementBays(unittest.TestCase):
    def test_current_six_mode_rail_and_three_existing_bays_unchanged(self):
        for expected in (
            "implicitWidth: 1000", "implicitHeight: 834",
            'name: "ID MANAGEMENT"', "id: modeRail", "height: 110",
            "id: sharedInstrumentPane", "width: 390",
            "id: targetPane", "width: 260",
            "id: actuatorPane", "id: idManagementOverviewPane",
            "id: idManagementSelectorPane", "id: idManagementDetailsPane",
            "id: settingsConnectionsOverview", "id: settingsConnectionsList",
            "id: settingsConnectionsDetails",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, CPU)
        for panel in (LOCAL, NAV):
            for forbidden in ("PanelWindow {", "FloatingWindow {"):
                self.assertNotIn(forbidden, panel)

    def test_compact_tabs_are_working_local_editor_navigation_not_dead_controls(self):
        for section in ("IDS", "ORGANIZATIONS", "STRUCTURE", "PORTFOLIOS"):
            self.assertIn(f'id:"{section}"', NAV)
            self.assertIn(f'"{section}"', CPU)
        for expected in (
            "property string idManagementSection",
            "function selectLocalManagementSection(section)",
            "onSectionRequested: function(section)",
            "cpuPlusWindow.selectLocalManagementSection(section);",
            "selected: nav.section === modelData.id",
            "onClicked: nav.sectionRequested(modelData.id)",
            "id: idManagementLocalNavigation",
            "area: \"overview\"", "area: \"selector\"",
            "area: \"details\"",
        ):
            self.assertIn(expected, CPU + NAV)
        self.assertEqual(CPU.count("CpuPlusLocalManagementPane {"), 3)
        self.assertIn('cpuPlusWindow.idManagementSection === "IDS"', CPU)
        self.assertIn('cpuPlusWindow.idManagementSection !== "IDS"', CPU)

    def test_category_filters_are_in_middle_bay_not_left_overview(self):
        left = CPU.split("id: sharedInstrumentPane", 1)[1].split(
            "id: targetPane", 1)[0]
        middle = CPU.split("id: targetPane", 1)[1].split(
            "id: actuatorPane", 1)[0]
        right = CPU.split("id: actuatorPane", 1)[1]
        self.assertNotIn("CpuPlusLocalManagementNav {", left)
        self.assertNotIn("idManagementLocalNavigation.bottom", left)
        self.assertIn("CpuPlusLocalManagementNav {", middle)
        self.assertEqual(middle.count("CpuPlusLocalManagementNav {"), 1)
        self.assertIn("id: idManagementLocalNavigation", middle)
        self.assertIn("anchors.top: targetHeaderLine.bottom", middle)
        self.assertEqual(
            middle.count("anchors.top: idManagementLocalNavigation.bottom"), 2
        )
        self.assertIn("id: idManagementSelectorPane", middle)
        self.assertIn("id: localManagementSelectorPane", middle)
        self.assertLess(
            middle.index("id: idManagementLocalNavigation"),
            middle.index("id: idManagementSelectorPane"),
        )
        self.assertLess(
            middle.index("id: idManagementLocalNavigation"),
            middle.index("id: localManagementSelectorPane"),
        )
        self.assertIn("id: idManagementOverviewPane", left)
        self.assertIn("id: localManagementOverviewPane", left)
        self.assertEqual(
            left.count("anchors.top: sharedStateHeader.bottom"), 3
        )
        self.assertIn("id: idManagementDetailsPane", right)
        self.assertIn("id: localManagementDetailsPane", right)
        self.assertIn('text: "FILTER // LOCAL RECORDS"', NAV)
        self.assertIn("columns: 2", NAV)
        self.assertIn("width: Math.floor((navigation.width - 5) / 2)", NAV)
        self.assertIn("height: 31", NAV)
        self.assertNotIn("FileView {", NAV)
        self.assertNotIn("Process {", NAV)

    def test_selectors_drive_real_selected_local_record_editor_focus(self):
        for expected in (
            "availableLocalManagementOrganizations",
            "effectiveLocalManagementOrganizationId",
            "availableLocalManagementPortfolios",
            "effectiveLocalManagementPortfolioId",
            "selectedLocalOrganizationForManagement = orgId;",
            "selectedLocalPortfolioForManagement = portfolioId;",
            "property string selectedOrganizationId",
            "property string selectedPortfolioId",
            "signal organizationRequested(string id)",
            "signal portfolioRequested(string id)",
            "onClicked: pane.selectRecord(record.modelData)",
            "focusedOrganizationId: pane.selectedOrganizationId",
            "selectedOrgId: pane.selectedOrganizationId",
            "focusedPortfolioId: pane.selectedPortfolioId",
            "placeholder: \"SEARCH LOCAL RECORDS\"",
        ):
            self.assertIn(expected, CPU + LOCAL)
        self.assertIn("property string focusedPortfolioId: \"\"", PORTFOLIOS)
        self.assertIn('editor.focusedPortfolioId === ""', PORTFOLIOS)
        self.assertIn("modelData.id === editor.focusedPortfolioId", PORTFOLIOS)
        self.assertIn("IdentityCenterLocalPortfolioEditor {", SOCIAL)
        # Unset focus preserves the full existing Social portfolio list.
        self.assertNotIn("focusedPortfolioId:", SOCIAL)

    def test_local_management_reuses_real_social_editors_and_stores(self):
        for expected in (
            'import "../messanger"',
            "import qs.services.social",
            "IdentityCenterLocalOrganizationEditor {",
            "IdentityCenterLocalStructureEditor {",
            "IdentityCenterLocalPortfolioEditor {",
            "IdentityCenterLocalArchiveTray {",
            "SocialOrganizationDirectoryStore",
            "SocialLocalOrganizationStructureStore",
            "SocialLocalPortfoliosStore",
            "SocialLocalUnitLocationLinksStore",
            "SocialLocalBranchLocationLinksStore",
            "SocialLocalFunctionalReportingStore",
            "SocialOrganizationLinksStore",
            "useSharedContext: true",
            "useSharedArchiveControl: true",
            "removalController: archiveTray",
        ):
            self.assertIn(expected, LOCAL)
        # No second writer, backend script or separate local data directory.
        for forbidden in (
            "FileView {", "Process {", "SQLite", "LocalStorage",
            "SocialIdentityStore.selectIdentity(", "begin_login(",
            "grantPermission(", "setActiveOrganization(",
            "Qt.openUrlExternally(",
        ):
            self.assertNotIn(forbidden, LOCAL + NAV)

    def test_operator_requested_create_rename_archive_restore_delete_remain_real(self):
        for expected in (
            "directoryStore.addOrganization(", "directoryStore.addBranch(",
            "directoryStore.renameOrganization(", "directoryStore.renameBranch(",
            "directoryStore.archiveOrganization(", "directoryStore.archiveBranch(",
            'label: "X"', '"CONFIRM DELETE"',
        ):
            self.assertIn(expected, ORGANIZATIONS)
        for expected in (
            "structureStore.createUnit(", "structureStore.renameUnit(",
            "structureStore.archiveUnit(", '"CONFIRM DELETE"',
        ):
            self.assertIn(expected, STRUCTURE)
        for expected in (
            "portfolioStore.createPortfolio(", "portfolioStore.renamePortfolio(",
            "portfolioStore.attachOrganization(",
            "portfolioStore.detachOrganization(", '"CONFIRM DELETE"',
        ):
            self.assertIn(expected, PORTFOLIOS)
        for expected in (
            "function requestRemove(record)",
            "function isConfirmed(record)",
            "function cancelDelete()",
            "expectedRevision:record.revision",
            "function restore(record)",
            "No backup is required",
            "storesReady",
        ):
            self.assertIn(expected, REMOVAL)
        self.assertIn("LOCAL RECORDS ONLY // NOT VERIFIED TENANT MEMBERSHIP.", LOCAL)
        self.assertIn("NO SIGN-IN OR COMPANY SWITCH PERFORMED.", LOCAL)

    def test_existing_id_profiles_account_labels_and_host_view_not_replaced(self):
        for expected in (
            "SocialIdentityStore.createIdentity(", "SocialIdentityStore.removeIdentity(",
            "CpuPlusIdDetailsEditor {", "CpuPlusIdVerifiedContextPane {",
        ):
            self.assertIn(expected, ID)
        self.assertIn("idManagementSelectorPane.editingText", CPU)
        self.assertIn("idManagementDetailsPane.editingText", CPU)
        self.assertIn('idManagementSection !== "IDS"', CPU)
        self.assertIn("function selectLocalManagementSection(section)", CPU)
        self.assertIn("section: cpuPlusWindow.idManagementSection", CPU)


if __name__ == "__main__":
    unittest.main()
