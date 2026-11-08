"""CPU++ location and reporting editors reuse existing Social data owners.

Source-contract tests; native Qt/Quickshell rendering and real operator data
are outside this isolated review branch. Canonical synthetic backend suites
are run separately by the CPU++ workflow on the same PR commit.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
NAV = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementNav.qml").read_text(
    encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementPane.qml").read_text(
    encoding="utf-8")
BRANCH = (ROOT / "widgets/messanger/IdentityCenterLocalBranchLocationsEditor.qml").read_text(
    encoding="utf-8")
UNIT = (ROOT / "widgets/messanger/IdentityCenterLocalUnitLocationsEditor.qml").read_text(
    encoding="utf-8")
REPORT = (ROOT / "widgets/messanger/IdentityCenterLocalFunctionalReportingEditor.qml").read_text(
    encoding="utf-8")


class CpuPlusSocialRelationshipEditors(unittest.TestCase):
    def test_secondary_filters_stay_in_middle_bay_below_category_filters(self):
        left = CPU.split("id: sharedInstrumentPane", 1)[1].split(
            "id: targetPane", 1
        )[0]
        middle = CPU.split("id: targetPane", 1)[1].split(
            "id: actuatorPane", 1
        )[0]
        right = CPU.split("id: actuatorPane", 1)[1]
        self.assertNotIn("CpuPlusLocalManagementNav {", left)
        self.assertEqual(middle.count("CpuPlusLocalManagementNav {"), 1)
        self.assertIn("id: idManagementLocalNavigation", middle)
        self.assertIn("anchors.top: targetHeaderLine.bottom", middle)
        self.assertIn("anchors.top: idManagementLocalNavigation.bottom", middle)
        self.assertIn("id: localManagementSelectorPane", middle)
        self.assertIn("id: localManagementDetailsPane", right)
        self.assertIn("id: localManagementOverviewPane", left)
        self.assertIn('text: "FILTER // LOCAL RECORDS"', NAV)
        self.assertIn('text: "EDIT // LOCAL RELATIONSHIPS"', NAV)
        self.assertIn("signal taskRequested(string task)", NAV)
        self.assertIn("onClicked: nav.taskRequested(modelData.id)", NAV)
        self.assertIn("onTaskRequested: function(task)", middle)
        self.assertIn("cpuPlusWindow.selectLocalManagementTask(task);", middle)
        self.assertIn("columns: 2", NAV)
        for expected in (
            '{id:"EDITOR", title:"COMPANIES / BRANCHES"}',
            '{id:"BRANCH_LOCATIONS", title:"BRANCH LOCATIONS"}',
            '{id:"EDITOR", title:"EDIT UNITS"}',
            '{id:"UNIT_LOCATIONS", title:"UNIT LOCATIONS"}',
            '{id:"REPORTING", title:"REPORTING"}',
        ):
            self.assertIn(expected, NAV)

    def test_task_state_is_restricted_and_reset_on_main_category_change(self):
        for expected in (
            'property string idManagementTask: "EDITOR"',
            "function selectLocalManagementTask(task)",
            'idManagementSection === "ORGANIZATIONS"',
            '["EDITOR", "BRANCH_LOCATIONS"]',
            'idManagementSection === "STRUCTURE"',
            '["EDITOR", "UNIT_LOCATIONS", "REPORTING"]',
            'if (allowed.indexOf(task) === -1)',
            'if (idManagementSection !== section)',
            'idManagementTask = "EDITOR";',
            'idManagementTask = task;',
            'task: cpuPlusWindow.idManagementTask',
        ):
            self.assertIn(expected, CPU)
        # One task binding in middle navigation, three in the same three bays.
        self.assertEqual(CPU.count("task: cpuPlusWindow.idManagementTask"), 4)
        self.assertEqual(CPU.count("CpuPlusLocalManagementPane {"), 3)
        self.assertIn("implicitWidth: 1000", CPU)
        self.assertIn("implicitHeight: 834", CPU)
        self.assertIn("id: sharedInstrumentPane", CPU)
        self.assertIn("width: 390", CPU)
        self.assertIn("id: targetPane", CPU)
        self.assertIn("width: 260", CPU)
        self.assertIn("id: actuatorPane", CPU)

    def test_original_social_editors_bound_to_original_singletons(self):
        for component, store, task, section in (
            ("IdentityCenterLocalBranchLocationsEditor", "SocialLocalBranchLocationLinksStore",
             "BRANCH_LOCATIONS", "ORGANIZATIONS"),
            ("IdentityCenterLocalUnitLocationsEditor", "SocialLocalUnitLocationLinksStore",
             "UNIT_LOCATIONS", "STRUCTURE"),
            ("IdentityCenterLocalFunctionalReportingEditor", "SocialLocalFunctionalReportingStore",
             "REPORTING", "STRUCTURE"),
        ):
            with self.subTest(component=component):
                self.assertEqual(PANE.count(component + " {"), 1)
                block = PANE.split(component + " {", 1)[1].split("\n                }", 1)[0]
                self.assertIn('pane.section === "' + section + '"', block)
                self.assertIn('pane.task === "' + task + '"', block)
                self.assertIn("width: parent.width", block)
                self.assertIn("height: visible ? implicitHeight : 0", block)
                self.assertIn("directoryStore: SocialOrganizationDirectoryStore", block)
                self.assertIn("structureStore: SocialLocalOrganizationStructureStore", block)
                self.assertIn(store, block)
                self.assertIn("useSharedContext: true", block)
                self.assertIn("selectedOrgId: pane.selectedOrganizationId", block)

        for expected in (
            'pane.task === "EDITOR"',
            "IdentityCenterLocalOrganizationEditor {",
            "IdentityCenterLocalStructureEditor {",
            "IdentityCenterLocalPortfolioEditor {",
            "IdentityCenterLocalArchiveTray {",
            'visible: pane.task === "EDITOR"',
            "removalController: archiveTray",
        ):
            self.assertIn(expected, PANE)

    def test_original_link_editors_expose_real_add_and_confirmed_unlink(self):
        for source, create, remove, confirmation in (
            (BRANCH, "linkStore.linkBranch(", "linkStore.unlinkBranch(",
             "editor.confirmationId === linkRow.modelData.id"),
            (UNIT, "linkStore.linkToLocation(", "linkStore.unlinkFromLocation(",
             "editor.pendingRemovalId === linkRow.modelData.id"),
            (REPORT, "reportingStore.addRelationship(", "reportingStore.removeRelationship(",
             "editor.confirmRemovalId === row.modelData.id"),
        ):
            with self.subTest(create=create):
                self.assertIn(create, source)
                self.assertIn(remove, source)
                self.assertIn(confirmation, source)
                self.assertIn("CONFIRM UNLINK", source)
                self.assertIn("state === \"ready\"", source)
                self.assertIn("NOT AN ACCESS GRANT", source)
        self.assertIn("function wouldCycle()", REPORT)
        self.assertIn("!editor.wouldCycle()", REPORT)

    def test_navigation_and_record_selection_clear_pending_unlink(self):
        for expected in (
            "function cancelPendingRelationshipRemoval()",
            "onTaskChanged: pane.cancelPendingRelationshipRemoval()",
            "pane.cancelPendingRelationshipRemoval();",
            'branchLocationEditor.confirmationId = "";',
            'unitLocationEditor.pendingRemovalId = "";',
            'reportingEditor.confirmRemovalId = "";',
            "archiveTray.cancelDelete();",
        ):
            self.assertIn(expected, PANE)
        self.assertIn("onSelectedOrgIdChanged:", BRANCH)
        self.assertIn("onSelectedOrgIdChanged:", UNIT)
        self.assertIn("onSelectedOrgIdChanged:", REPORT)
        # Original seven-store deletion still guards local company/unit records.
        self.assertIn("SocialOrganizationLinksStore", PANE)
        self.assertIn("SocialLocalBranchLocationLinksStore", PANE)
        self.assertIn("SocialLocalUnitLocationLinksStore", PANE)
        self.assertIn("SocialLocalFunctionalReportingStore", PANE)
        for prohibited in (
            "FileView {", "Process {", "LocalStorage",
            "SocialIdentityStore.selectIdentity(", "begin_login(",
            "grantPermission(", "setActiveOrganization(",
            "Qt.openUrlExternally(", "Authorization: Bearer",
        ):
            self.assertNotIn(prohibited, NAV + PANE)


if __name__ == "__main__":
    unittest.main()
