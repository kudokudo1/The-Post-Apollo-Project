"""CPU++ Connections exposes actual Social local account labels without login authority.

Source contracts only; desktop rendering and real provider sessions are separate.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
DETAILS = (ROOT / "widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml").read_text(encoding="utf-8")
EDITOR = (ROOT / "widgets/cpuplus/CpuPlusIdAccountEditor.qml").read_text(encoding="utf-8")
LABELS = (ROOT / "services/social/SocialAccountDetailsStore.qml").read_text(encoding="utf-8")
BROKER = (ROOT / "services/connections/ConnectionsBroker.qml").read_text(encoding="utf-8")
REQUEST = (ROOT / "services/connections/ConnectionsRequestStatus.qml").read_text(encoding="utf-8")


class CpuPlusConnectionsLocalAccountEditor(unittest.TestCase):
    def test_existing_connections_three_bays_and_selection_preserved(self):
        for part in ("implicitWidth: 1000", "implicitHeight: 834",
                     "width: 390", "width: 260",
                     "id: settingsConnectionsOverview",
                     "id: settingsConnectionsList",
                     "id: settingsConnectionsDetails",
                     "selectedId: cpuPlusWindow.selectedConnectionId",
                     "selectedConnectionId = providerId;"):
            self.assertIn(part, CPU)
        self.assertEqual(CPU.count("CpuPlusSettingsConnectionsDetailsPane {"), 1)
        self.assertIn('settingsSubMode === "CONNECTIONS"', CPU)

    def test_social_account_names_use_original_editor_only_in_right_bay(self):
        self.assertIn("import qs.services.social", DETAILS)
        self.assertEqual(DETAILS.count("CpuPlusIdAccountEditor {"), 1)
        for part in ('visible: details.selectedId === "social"',
                     'id: localAccountManagement',
                     'id: connectedAccountNamesEditor',
                     'height: implicitHeight',
                     'identityId: SocialIdentityStore.snapshot',
                     'SocialIdentityStore.snapshot.activeId',
                     'CONNECTED ACCOUNTS // SAVED NAMES',
                     'PROVIDER AUTHENTICATION IS SEPARATE',
                     'LOCAL ACCOUNT LABELS'):
            self.assertIn(part, DETAILS)
        self.assertIn('onSelectedIdChanged:', DETAILS)
        self.assertIn('connectedAccountNamesEditor.resetEditor();', DETAILS)
        self.assertIn('details.selectedId === "social"', DETAILS)
        # The existing editable component still owns input/confirmation logic.
        for part in ("SocialAccountDetailsStore.accountNamesFor(",
                     "SocialAccountDetailsStore.addAccountName(",
                     "SocialAccountDetailsStore.renameAccountName(",
                     "SocialAccountDetailsStore.removeAccountName(",
                     "if (confirmRemoveId !== selectedAccountId)",
                     "CONFIRM REMOVE LABEL", "LOCAL LABELS ONLY // NOT PROVIDER SIGN-IN STATUS"):
            self.assertIn(part, EDITOR)
        for part in ("function addAccountName(", "function renameAccountName(",
                     "function removeAccountName("):
            self.assertIn(part, LABELS)
        self.assertNotIn("SocialAccountDetailsStore.addAccountName(", DETAILS)
        self.assertNotIn("SocialAccountDetailsStore.renameAccountName(", DETAILS)
        self.assertNotIn("SocialAccountDetailsStore.removeAccountName(", DETAILS)

    def test_typing_prevents_cpuplus_main_mode_shortcuts(self):
        self.assertIn('readonly property bool editingText: details.selectedId === "social"', DETAILS)
        self.assertIn('connectedAccountNamesEditor.editingText', DETAILS)
        self.assertIn('settingsSubMode === "CONNECTIONS"', CPU)
        self.assertIn('settingsConnectionsDetails.editingText', CPU)
        self.assertIn('readonly property bool editingText:', EDITOR)

    def test_no_authentication_or_new_storage_writer(self):
        self.assertIn("readonly property bool credentialActionsEnabled: false", BROKER)
        self.assertIn("readonly property bool hostAuthenticated: false", REQUEST)
        self.assertIn("readonly property bool canApprove: false", REQUEST)
        self.assertIn('ACCOUNT LOGIN AND CROSS-APP GRANTS REMAIN DISABLED', DETAILS)
        for code in (CPU, DETAILS):
            for forbidden in ("ConnectionsBroker.authorize(", "SocialIdentityStore.selectIdentity(",
                              "startLogin(", "loginProcess", "access_token", "refresh_token",
                              "Authorization: Bearer", "grantPermission(", "FileView {",
                              "secret-tool", "setActiveOrganization("):
                with self.subTest(forbidden=forbidden):
                    # CPU++ already contains unrelated services, but none of these
                    # privileged actions should be in the new account editor host.
                    if code is DETAILS:
                        self.assertNotIn(forbidden, code)
        self.assertNotIn("Process {", DETAILS)
        self.assertEqual(LABELS.count("id: writer"), 1)
        self.assertIn('identityId: SocialIdentityStore.snapshot', DETAILS)


if __name__ == "__main__":
    unittest.main()
