"""CPU++ local organization association editor: UI and ownership contracts.

Data relationships are synthetic and exercised separately by the canonical
SocialOrganizationLinks.py suite. This module asserts the CPU++ wiring only.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
DETAILS = (ROOT / "widgets/cpuplus/CpuPlusIdDetailsEditor.qml").read_text(
    encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(
    encoding="utf-8")
ORGS = (ROOT / "widgets/cpuplus/CpuPlusIdOrganizationLinksEditor.qml").read_text(
    encoding="utf-8")
DIRECTORY = (ROOT / "services/social/SocialOrganizationDirectoryStore.qml").read_text(
    encoding="utf-8")
LINK_STORE = (ROOT / "services/social/SocialOrganizationLinksStore.qml").read_text(
    encoding="utf-8")
DETAIL_STORE = (ROOT / "services/social/SocialAccountDetailsStore.qml").read_text(
    encoding="utf-8")


class CpuPlusLocalOrganizationLinksContracts(unittest.TestCase):
    def test_no_chassis_change_and_editor_stays_in_existing_right_bay(self):
        for expected in ("implicitWidth: 1000", "implicitHeight: 834",
                         "id: sharedInstrumentPane", "width: 390",
                         "id: targetPane", "width: 260",
                         "id: actuatorPane", 'name: "ID MANAGEMENT"',
                         "id: idManagementDetailsPane"):
            self.assertIn(expected, CPU)
        self.assertIn("CpuPlusIdOrganizationLinksEditor {", DETAILS)
        self.assertIn("identityId: detailsEditor.identityId", DETAILS)
        self.assertIn("id: organizationLinks", DETAILS)
        self.assertIn("SAVE NAME", DETAILS)
        self.assertIn("SAVE CONTACT", DETAILS)
        self.assertIn("CpuPlusIdAccountEditor {", DETAILS)
        self.assertIn("LOCAL ORGANIZATIONS // ", PANE)
        self.assertIn("ID ASSOCIATIONS // ", PANE)

    def test_real_organization_and_branch_models_not_new_copies(self):
        for expected in (
            "SocialOrganizationDirectoryStore.saved.organizations",
            "SocialOrganizationDirectoryStore.state",
            "SocialOrganizationLinksStore.saved.links",
            "SocialIdentityStore.snapshot",
            "entry.identityId === editor.identityId",
            "entry.archived",
            "branch.archived",
            "MISSING ORGANIZATION",
            "MISSING BRANCH",
            "ARCHIVED",
            "SocialAccountDetailsStore.recordFor(",
            "SocialAccountDetailsStore.accountNamesFor(",
        ):
            self.assertIn(expected, ORGS)
        for method in ("function addOrganization(", "function addBranch("):
            self.assertIn(method, DIRECTORY)
            self.assertNotIn(method, ORGS)
        self.assertIn("SOCIAL // USER SETTINGS // ORGANIZATIONS", ORGS)

    def test_explicit_user_link_and_unlink_calls_existing_owner_store(self):
        for expected in (
            "function saveLink()",
            "function requestUnlink(link)",
            "function resetChoices()",
            "onIdentityIdChanged:",
            "SocialOrganizationLinksStore.linkIdentity(",
            "SocialOrganizationLinksStore.linkAccountLabel(",
            "SocialOrganizationLinksStore.unlink(",
            "confirmUnlinkId",
            "CONFIRM X",
            "CANCEL UNLINK",
            "SocialOrganizationLinksStore.state === \"ready\"",
            "ASSOCIATION SAVED // LOCAL",
            "ASSOCIATION REMOVED // LOCAL",
            "ASSOCIATION SAVE FAILED",
            "canSaveLink",
            "targetAlreadyLinked",
            "editor.accountChoiceValid",
            "+ LINK LOCAL ID",
            "+ LINK ACCOUNT NAME",
            "pendingIdentityId",
        ):
            self.assertIn(expected, ORGS)
        for expected in ("function linkIdentity(", "function linkAccountLabel(",
                         "function unlink(", "expectedRevision:saved.revision"):
            self.assertIn(expected, LINK_STORE)

    def test_only_real_saved_account_labels_are_selectable(self):
        self.assertIn("IdentityPolicy.APP_IDS", ORGS)
        self.assertIn("Object.keys(savedAccountRecord.accounts)", ORGS)
        self.assertIn("accountServices.indexOf(chosenServiceId)", ORGS)
        self.assertIn("entry.id === editor.chosenAccountId", ORGS)
        self.assertIn("chosenBranchId || null", ORGS)
        self.assertIn("!targetAlreadyLinked", ORGS)
        self.assertIn("!entry.archived", ORGS)

    def test_fail_closed_and_no_privileged_auth_or_new_writer(self):
        for prohibited in (
            "Process {", "FileView {", "PanelWindow {",
            "FloatingWindow {", "Qt.openUrlExternally(",
            "SocialIdentityStore.selectIdentity(",
            "SocialIdentityStore.removeIdentity(",
            "startLogin(", "logout(", "sendMessage(",
            "accessToken:", "session_token", "pkexec",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, ORGS)
        self.assertIn("NO LOGIN, MEMBERSHIP OR PERMISSION CHANGE.", ORGS)
        self.assertIn("directoryReady && linksReady", ORGS)
        self.assertIn("validIdentity && directoryReady", ORGS)
        self.assertIn("editor.pendingAction === \"\"", ORGS)
        self.assertIn("SocialOrganizationDirectoryStore.refresh()", ORGS)
        self.assertIn("SocialOrganizationLinksStore.refresh()", ORGS)


if __name__ == "__main__":
    unittest.main()
