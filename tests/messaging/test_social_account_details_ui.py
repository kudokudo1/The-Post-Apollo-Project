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
            '+ ACCOUNT NAME" : "SAVE ACCOUNT NAME"',
            'label: "MOVE UP"',
            'label: "MOVE DOWN"',
            'CONFIRM REMOVE NAME',
            'SocialAccountDetailsStore.addAccountName(',
            'SocialAccountDetailsStore.renameAccountName(',
            'SocialAccountDetailsStore.removeAccountName(',
            'SocialAccountDetailsStore.moveAccountName(',
        ):
            self.assertIn(part,sidebar,part)
        self.assertIn('id: settingsAppPane',SELECTOR)
        self.assertIn('id: settingsFamilyPane',SELECTOR)
        self.assertIn('id: settingsIdentityPane',SELECTOR)
        self.assertIn('label: "USER // SETTINGS"',SELECTOR)
        self.assertEqual(SELECTOR.count("id: settingsFooter"),1)

    def test_browser_sessions_moved_to_family_pane_bottom_without_signin_moving(self):
        sidebar = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        middle = SELECTOR.split("id: settingsFamilyPane", 1)[1].split(
            "id: settingsAppPane", 1
        )[0]
        self.assertNotIn('text: "BROWSER SESSIONS"', sidebar)
        self.assertIn('text: "BROWSER SIGN-IN // MANUAL"', sidebar)
        self.assertIn('label: "CHECK WINDOW"', sidebar)
        self.assertIn('label: "OPEN SIGN-IN WINDOW"', sidebar)
        self.assertIn('text: "BROWSER SESSIONS"', middle)
        self.assertIn("appSelector.isolatedBrowserModeToggleRequested()", middle)
        self.assertIn("SETUP NOTES ONLY. A label does not connect or sign in.", middle)
        # Independent section follows the editing column, not hidden inside
        # its visible: editingFamilies gate or the account names accordion.
        self.assertLess(
            middle.index('} // end family editing actions'),
            middle.index('text: "BROWSER SESSIONS"'),
        )
        self.assertEqual(SELECTOR.count('text: "BROWSER SESSIONS"'), 1)
        self.assertEqual(SELECTOR.count("appSelector.isolatedBrowserModeToggleRequested()"), 1)

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

    def test_account_submission_renamed_without_changing_creation_or_editing(self):
        sidebar = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        self.assertIn('label: "+ NEW ACCOUNT NAME"', sidebar)
        self.assertIn('"+ ACCOUNT NAME" : "SAVE ACCOUNT NAME"', sidebar)
        self.assertIn("accentColor: appSelector.accountSelectedEntryId", sidebar)
        self.assertIn("? Colors.magenta : Colors.cyan", sidebar)
        self.assertIn("SocialAccountDetailsStore.addAccountName(", sidebar)
        self.assertIn("SocialAccountDetailsStore.renameAccountName(", sidebar)
        self.assertIn("SocialAccountDetailsStore.removeAccountName(", sidebar)
        self.assertNotIn('?"ADD ACCOUNT NAME"', sidebar)

    def test_collapsed_all_app_picker_fades_unrecorded_without_blocking_setup(self):
        sidebar = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        self.assertIn("visible: appSelector.accountManagerOpen", sidebar)
        self.assertIn("appSelector.accountManagerOpen =", sidebar)
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

    def test_marked_settings_fields_use_magenta_text_and_orange_caret(self):
        # One cursor delegate, no duplicated cursor animation or shared
        # TextInput replacement. The original orange input borders remain.
        self.assertIn("id: settingsOrangeCaret", SELECTOR)
        cursor = SELECTOR.split("id: settingsOrangeCaret", 1)[1].split(
            "// The app rail remains", 1
        )[0]
        self.assertIn("Rectangle {", cursor)
        self.assertIn("width: 2", cursor)
        self.assertIn("color: Colors.orange", cursor)
        fields = (
            "newIdentityName", "accountEmailInput", "accountPhoneInput",
            "accountServiceSearchInput", "accountLabelInput",
            "familyNameInput", "familySearchInput",
        )
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(SELECTOR.count("id: " + field), 1)
                body = SELECTOR.split("id: " + field, 1)[1].split("}", 1)[0]
                self.assertIn("color: Colors.magenta", body)
                self.assertIn("cursorDelegate: settingsOrangeCaret", body)
                self.assertNotIn("color: Colors.white", body)
        self.assertEqual(
            SELECTOR.count("cursorDelegate: settingsOrangeCaret"),
            len(fields),
        )
        # Existing field borders and writable form flows are unchanged.
        self.assertIn("SocialAccountDetailsStore.saveContact(", SELECTOR)
        self.assertIn("SocialAccountDetailsStore.addAccountName(", SELECTOR)

    def test_account_picker_has_cyan_star_scrollbar_with_reserved_label_lane(self):
        viewport = SELECTOR.split("id: accountAppPickerViewport", 1)[1].split(
            'text: "FADED = NO NAME SAVED HERE.', 1
        )[0]
        self.assertIn("id: accountAppFlickable", viewport)
        self.assertIn("anchors.rightMargin: 22", viewport)
        self.assertIn("contentHeight: accountAppList.height + 8", viewport)
        self.assertIn("NeonScrollBar {", viewport)
        self.assertIn("flickable: accountAppFlickable", viewport)
        self.assertIn("geometryHost: accountAppPickerViewport", viewport)
        self.assertIn('geometryMode: "box"', viewport)
        self.assertIn('handleStyle: "star"', viewport)
        self.assertIn("starSceneGraphRenderer: true", viewport)
        self.assertIn("railColor: Colors.cyan", viewport)
        self.assertIn("handleColor: Colors.magenta", viewport)
        self.assertIn('nestedScrollMode: "contain"', viewport)
        self.assertIn('visibilityMode: "auto"', viewport)
        self.assertIn("reserveSpace: false", viewport)
        # Only the inner, overflowing app list gains a scroll handle. The
        # outer identity pane's regular scrolling and app selection remain.
        self.assertIn("contentHeight: settingsIdentityColumn.height + 24", SELECTOR)
        self.assertIn("appSelector.selectAccountService(", viewport)

    def test_browser_sign_in_section_remains_separate_and_unchanged(self):
        settings = SELECTOR.split('text: "BROWSER SIGN-IN // MANUAL"', 1)[1]
        for part in (
            "appSelector.browserWindowStatusText()",
            'label: "CHECK WINDOW"',
            'label: "OPEN SIGN-IN WINDOW"',
            "appSelector.browserWindowCheckRequested(",
            "appSelector.browserOpenSignInRequested(",
            "The provider website owns sign-in and reconnection.",
        ):
            self.assertIn(part, settings)

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
