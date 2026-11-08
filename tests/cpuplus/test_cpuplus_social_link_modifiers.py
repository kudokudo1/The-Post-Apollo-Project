"""CPU++ Social link modifiers: real local writer reuse, no auth escalation.

These are wiring contracts, not a live Qt/Wayland rendering assertion. The
canonical Social link and account-label writer tests run in the same CI job.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
NAV = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementNav.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusLocalManagementPane.qml").read_text(encoding="utf-8")
FORM = (ROOT / "widgets/messanger/IdentityCenterLocalRelationshipModifiers.qml").read_text(encoding="utf-8")
SOCIAL = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text(encoding="utf-8")
LINKS = (ROOT / "services/social/SocialOrganizationLinksStore.qml").read_text(encoding="utf-8")
ACCOUNTS = (ROOT / "services/social/SocialAccountDetailsStore.qml").read_text(encoding="utf-8")

class CpuPlusSocialLinkModifiers(unittest.TestCase):
    def test_middle_filters_and_task_allowlist(self):
        left = CPU.split("id: sharedInstrumentPane", 1)[1].split("id: targetPane", 1)[0]
        middle = CPU.split("id: targetPane", 1)[1].split("id: actuatorPane", 1)[0]
        right = CPU.split("id: actuatorPane", 1)[1]
        self.assertNotIn("CpuPlusLocalManagementNav {", left)
        self.assertEqual(middle.count("CpuPlusLocalManagementNav {"), 1)
        self.assertIn('id: idManagementLocalNavigation', middle)
        self.assertIn('id: localManagementSelectorPane', middle)
        self.assertIn('id: localManagementDetailsPane', right)
        self.assertIn('{id:"LINK_MODIFIERS", title:"LINK MODIFIERS"}', NAV)
        self.assertIn('signal taskRequested(string task)', NAV)
        self.assertIn('onClicked: nav.taskRequested(modelData.id)', NAV)
        self.assertIn('["EDITOR", "BRANCH_LOCATIONS", "LINK_MODIFIERS"]', CPU)
        self.assertIn("if (allowed.indexOf(task) === -1)", CPU)
        self.assertIn('if (idManagementSection !== section)', CPU)
        self.assertIn('idManagementTask = "EDITOR";', CPU)
        for x in ("implicitWidth: 1000", "implicitHeight: 834",
                  "id: sharedInstrumentPane", "width: 390",
                  "id: targetPane", "width: 260", "id: actuatorPane"):
            self.assertIn(x, CPU)
        self.assertEqual(CPU.count("CpuPlusLocalManagementPane {"), 3)

    def test_original_social_modifier_uses_original_store_owners(self):
        self.assertEqual(PANE.count("IdentityCenterLocalRelationshipModifiers {"), 1)
        component = PANE.split("IdentityCenterLocalRelationshipModifiers {", 1)[1].split(
            "\n                }", 1)[0]
        for expected in (
            'id: modifierEditor',
            'pane.section === "ORGANIZATIONS"',
            'pane.task === "LINK_MODIFIERS"',
            'height: visible ? implicitHeight : 0',
            'useSharedContext: true',
            'useSharedRefreshControl: true',
            'selectedOrgId: pane.selectedOrganizationId',
            'directoryStore: SocialOrganizationDirectoryStore',
            'structureStore: SocialLocalOrganizationStructureStore',
            'functionLocationStore: SocialLocalUnitLocationLinksStore',
            'branchLocationStore: SocialLocalBranchLocationLinksStore',
            'reportingStore: SocialLocalFunctionalReportingStore',
            'socialLinksStore: SocialOrganizationLinksStore',
            'identitiesSnapshot: SocialIdentityStore.snapshot',
            'accountDetailsStore: SocialAccountDetailsStore',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, component)
        self.assertEqual(SOCIAL.count("IdentityCenterLocalRelationshipModifiers {"), 1)
        self.assertIn('identitiesSnapshot: sections.socialIdentitiesSnapshot', SOCIAL)
        self.assertIn('accountDetailsStore: sections.socialAccountDetailsStore', SOCIAL)

    def test_actual_account_and_identity_links_and_guarded_unlink(self):
        for expected in (
            'property var identitiesSnapshot: null',
            'property var accountDetailsStore: null',
            'identitiesSnapshot.writable',
            'accountDetailsStore.recordFor(selectedTargetId).accounts',
            'accountDetailsStore.accountNamesFor(',
            'function allowed(name)',
            'selectedSourceKind === "organization"',
            'selectedSourceKind === "branch"',
            'function applyModifier()',
            'socialLinksStore.linkIdentity(',
            'socialLinksStore.linkAccountLabel(',
            'function alreadyLinked()',
            'function current(link)',
            'function unlink(link)',
            'socialLinksStore.unlink(link.id)',
            'label: "APPLY MODIFIER"',
            '"CONFIRM UNLINK" : "UNLINK MODIFIER"',
            'role: "danger"',
            'NOT AN ACCESS GRANT',
        ):
            self.assertIn(expected, FORM)
        self.assertIn('function linkIdentity(', LINKS)
        self.assertIn('function linkAccountLabel(', LINKS)
        self.assertIn('function unlink(', LINKS)
        self.assertIn('function accountNamesFor(', ACCOUNTS)
        self.assertIn('function removeAccountName(', ACCOUNTS)

    def test_navigation_resets_confirmation_and_existing_editor_remains(self):
        for expected in (
            'function cancelPendingRelationshipRemoval()',
            'modifierEditor.confirmUnlinkKey = "";',
            'onTaskChanged: pane.cancelPendingRelationshipRemoval()',
            'onSelectedOrganizationIdChanged:',
            'onSectionChanged:',
            'IdentityCenterLocalOrganizationEditor {',
            'IdentityCenterLocalStructureEditor {',
            'IdentityCenterLocalPortfolioEditor {',
            'IdentityCenterLocalArchiveTray {',
            'branchLocationEditor.confirmationId = "";',
            'unitLocationEditor.pendingRemovalId = "";',
            'reportingEditor.confirmRemovalId = "";',
            'visible: pane.task === "EDITOR"',
        ):
            self.assertIn(expected, PANE)
        self.assertIn("onSelectedOrgIdChanged:", FORM)
        self.assertIn('confirmUnlinkKey = "";', FORM)
        self.assertIn('useSharedContext: true', PANE)

    def test_single_archive_directory_binding_and_no_new_privileged_io(self):
        archive = PANE.split("IdentityCenterLocalArchiveTray {", 1)[1].split(
            "\n                }", 1)[0]
        self.assertEqual(archive.count('directoryStore: SocialOrganizationDirectoryStore'), 1)
        self.assertNotIn('directoryStore:\n', archive)
        for prohibited in (
            'FileView {', 'Process {', 'LocalStorage', 'Qt.openUrlExternally(',
            'SocialIdentityStore.selectIdentity(', 'begin_login(', 'grantPermission(',
            'setActiveOrganization(', 'Authorization: Bearer', 'access_token',
        ):
            self.assertNotIn(prohibited, NAV + PANE)
        self.assertIn("NO PROVIDER LOGIN OR ORGANIZATION PERMISSION CHANGES.", PANE)

if __name__ == "__main__":
    unittest.main()
