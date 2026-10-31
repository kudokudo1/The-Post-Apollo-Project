"""Contract checks for non-authenticated identity details UI.

This is not a live Quickshell login test. The Python backend contract is
executed separately with a temporary owner-only local filesystem.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
SELECTOR=(ROOT/"widgets/messanger/AppSelector.qml").read_text()
HOST=(ROOT/"widgets/messanger/MessagingW.qml").read_text()
QMLSTORE=(ROOT/"services/social/SocialAccountDetailsStore.qml").read_text()
PYHELPER=(ROOT/"services/social/SocialAccountDetails.py").read_text()
QMLDIR=(ROOT/"services/social/qmldir").read_text()
IDENTITYSTORE=(ROOT/"services/social/SocialIdentityStore.qml").read_text()
BROWSER=(ROOT/"widgets/messanger/XBrowser.py").read_text()
TELEGRAM=(ROOT/"services/messaging/bridges/telegram/bridge.py").read_text()


class SocialAccountDetailsUiContracts(unittest.TestCase):
    def test_contact_fields_are_in_existing_contact_pane(self):
        sidebar=SELECTOR.split("id: settingsIdentityPane",1)[1].split(
            "id: settingsEditorPane",1)[0]
        for part in (
            'text: "IDENTITIES"',
            'text: "IDENTITY DETAILS"',
            'text: "DEFAULT EMAIL"',
            'text: "DEFAULT PHONE"',
            'id: accountEmailInput',
            'id: accountPhoneInput',
            'label: "SAVE CONTACT"',
            'SocialAccountDetailsStore.saveContact(',
            'label: "RELOAD DETAILS"',
            'SocialAccountDetailsStore.refresh()',
            'text: "ACCOUNT NAMES"',
            'id: accountNameManager',
            'id: accountServiceSearchInput',
            'id: accountAppList',
            'id: accountLabelInput',
            'label: "+ NEW ACCOUNT NAME"',
            'ADD ACCOUNT NAME" : "SAVE ACCOUNT NAME"',
            'label: "MOVE UP"',
            'label: "MOVE DOWN"',
            'CONFIRM REMOVE NAME',
            'SocialAccountDetailsStore.addAccountName(',
            'SocialAccountDetailsStore.renameAccountName(',
            'SocialAccountDetailsStore.removeAccountName(',
            'SocialAccountDetailsStore.moveAccountName(',
            'SETUP NOTES ONLY. A label does not connect or sign in.',
        ):
            self.assertIn(part,sidebar,part)
        self.assertIn('id: settingsAppPane',SELECTOR)
        self.assertIn('id: settingsFamilyPane',SELECTOR)
        self.assertIn('id: settingsIdentityPane',SELECTOR)
        self.assertIn('label: "USER // SETTINGS"',SELECTOR)
        self.assertEqual(SELECTOR.count("id: settingsFooter"),1)

    def test_account_record_scoped_to_selected_identity(self):
        for part in (
            'function matchingAccountServices(query)',
            'function refreshAccountForm()',
            'property string accountEditorIdentityId: ""',
            'property string accountSelectedServiceId: ""',
            'property string accountSelectedEntryId: ""',
            'property bool accountManagerOpen: false',
            'property bool accountAppPickerOpen: false',
            'function accountNamesFor(serviceId)',
            'function selectAccountService(serviceId)',
            'function selectedAccountPosition()',
            'readonly property var accountDetails:',
            'SocialAccountDetailsStore.recordFor(identitySnapshot.activeId)',
            'accountEditorIdentityId !== appSelector.identitySnapshot.activeId',
            'accountEditorIdentityId === identitySnapshot.activeId',
            'onIdentitySnapshotChanged: Qt.callLater',
            'accountEditorIdentityId = id',
            'accountServiceSearchInput.text = "";',
            'accountLabelInput.text = "";',
        ):
            self.assertIn(part,SELECTOR,part)
        self.assertIn('SocialIdentityStore.selectIdentity(modelData.id)',SELECTOR)
        self.assertIn('SocialIdentityStore.createIdentity(',SELECTOR)
        self.assertIn('appSelector.identitySnapshot.writable',SELECTOR)

    def test_collapsed_all_app_picker_fades_unrecorded_without_blocking_setup(self):
        sidebar = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        self.assertIn("visible: appSelector.accountManagerOpen", sidebar)
        self.assertIn("onTriggered: appSelector.accountManagerOpen =", sidebar)
        self.assertIn("visible: appSelector.accountAppPickerOpen", sidebar)
        self.assertIn(
            "model: appSelector.matchingAccountServices(", sidebar
        )
        self.assertIn('label: "+ NEW ACCOUNT NAME"', sidebar)
        self.assertIn("available: savedNames > 0", sidebar)
        self.assertIn("unavailableOpacity: 0.38", sidebar)
        self.assertIn("interactive: appSelector.identitySnapshot.writable", sidebar)
        self.assertIn("FADED = NO NAME SAVED HERE. SELECT TO ADD.", sidebar)
        self.assertNotIn("}).slice(0, 8);", SELECTOR.split(
            "function matchingAccountServices(query)", 1
        )[1].split("function accountNamesFor(", 1)[0])
        # The user cannot be told a label proves provider authentication.
        self.assertIn("Names belong to this Post-Apollo identity.", sidebar)
        self.assertIn("A running website window never proves login", sidebar)
        self.assertIn("Existing Telegram and browser sign-in paths stay unchanged.", sidebar)

    def test_helper_only_persists_local_non_auth_account_notes(self):
        for part in (
            'stdinEnabled: true',
            'writer.write(JSON.stringify(accountDetails.pending)',
            'id: reader',
            'id: writer',
            'function saveContact(identityId, email, phone)',
            'function setAccountLabel(identityId, serviceId, label)',
            'function accountNamesFor(identityId, serviceId)',
            'function addAccountName(identityId, serviceId, label)',
            'function renameAccountName(identityId, serviceId, accountId, label)',
            'function moveAccountName(identityId, serviceId, accountId, direction)',
            'function removeAccountName(identityId, serviceId, accountId)',
            'function refresh()',
            'property string state: "loading"',
            'state = "saving"',
            'state = "error"',
            'saved = result.document',
        ):
            self.assertIn(part,QMLSTORE,part)
        self.assertIn('singleton SocialAccountDetailsStore 1.0',QMLDIR)
        self.assertIn('singleton SocialIdentityStore 1.0',QMLDIR)
        self.assertIn('social-identities-v1.json',IDENTITYSTORE)
        self.assertIn('identity-account-details-v1.json',PYHELPER)
        self.assertIn('0o700',PYHELPER)
        self.assertIn('0o600',PYHELPER)
        self.assertIn('os.replace(temporary, target)',PYHELPER)
        self.assertIn('expectedRevision',QMLSTORE)
        self.assertIn('REVISION_CONFLICT',PYHELPER)
        self.assertIn('SocialAccountCatalog import ITEM_BY_ID',PYHELPER)
        for banned in ('loginProcess', 'apiHash', 'refreshMessages(', 'sendMessage('):
            self.assertNotIn(banned,QMLSTORE)
        self.assertNotIn('SocialAccountDetailsStore',HOST)

    def test_existing_launchers_browser_telegram_and_families_unchanged(self):
        names=re.findall(r'\bname:\s*"([^"]+)"',SELECTOR)
        self.assertEqual(len(names),32)
        self.assertEqual(names[:4],["SESSIONS","DISCORD","TELEGRAM","X"])
        self.assertEqual(names[-1],"BEREAL")
        self.assertIn('appSelector.appActivated(buttonContainer.modelData.serviceIndex);',
                      SELECTOR)
        self.assertIn('model: appSelector.railRows',SELECTOR)
        self.assertIn('settingsWorkspaceParent: messagingContent.contentItem',HOST)
        self.assertIn('function showDiscord()',HOST)
        self.assertIn('def browser_profile(', BROWSER)
        self.assertIn('site: str, prefix: list[str] | None = None,', BROWSER)
        self.assertIn('return data_root / "post-apollo" / profile_dir', BROWSER)
        # Scoped Telegram sessions add a namespace without changing the
        # legacy shared default used by the existing native QML adapter.
        self.assertIn('base = root / "post-apollo" / "telegram"', TELEGRAM)
        self.assertIn('if identity is None:', TELEGRAM)
        self.assertIn('return base / "personal.session"', TELEGRAM)
        self.assertIn('base / "identities" / identity / "personal.session"', TELEGRAM)
        self.assertEqual(QMLSTORE.count("Process {"),2)
        self.assertEqual(QMLSTORE.count("FileView {"),0)
        self.assertEqual(QMLSTORE.count("Qt.openUrlExternally("),0)


if __name__=="__main__":
    unittest.main()
