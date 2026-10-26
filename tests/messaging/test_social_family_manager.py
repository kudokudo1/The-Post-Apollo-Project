"""Social family manager v1: bounded QML source integration contracts.

This checks the existing Settings rail and the single-writer organization
backend. The companion CJS test executes the real layout policy in isolation.
No live desktop, browser or provider logins are tested here.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
SELECTOR=(ROOT/"widgets/messanger/AppSelector.qml").read_text()
POLICY=(ROOT/"services/social/SocialIdentityPolicy.js").read_text()
STORE=(ROOT/"services/social/SocialIdentityStore.qml").read_text()
HOST=(ROOT/"widgets/messanger/MessagingW.qml").read_text()


class SocialFamilyManagerContracts(unittest.TestCase):
    def test_in_menu_control_and_search_not_new_side_window(self):
        for needle in (
            'text: "BUTTON FAMILIES"',
            'label: appSelector.editingFamilies ? "CLOSE EDIT" : "EDIT FAMILIES"',
            'text: "SELECT FAMILY"',
            'text: "FAMILY NAME"',
            'id: familyNameInput',
            'label: "+ FAMILY"',
            'label: "RENAME"',
            'text: "MOVE APP"',
            'id: familySearchInput',
            'function matchingFamilyApps(query)',
            'label: "MOVE HERE"',
            'SocialIdentityStore.createFamily(',
            'SocialIdentityStore.renameFamily(',
            'SocialIdentityStore.moveAppToFamily(',
            'SocialIdentityStore.familyActionError',
            'appSelector.identitySnapshot.activeName',
            'appSelector.identitySnapshot.familyOptions || []',
            'appSelector.matchingFamilyApps(familySearchInput.text)',
            'appSelector.messagingApps[modelData.serviceIndex].name',
        ):
            self.assertIn(needle, SELECTOR, needle)
        self.assertEqual(SELECTOR.count('id: settingsFooter'), 1)
        self.assertIn('appSelector.settingsOpen = !appSelector.settingsOpen', SELECTOR)
        self.assertIn('bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top',
                      SELECTOR)
        self.assertIn("enabled: !appSelector.settingsOpen", SELECTOR)
        self.assertNotIn('FloatingWindow {', SELECTOR)

    def test_stale_identity_and_not_yet_saved_action_guards(self):
        for needle in (
            'property string familyEditorIdentityId: ""',
            'appSelector.familyEditorIdentityId !== appSelector.identitySnapshot.activeId',
            'function familyIsSelected()',
            'function selectedAppNeedsMove()',
            'app.familyId !== editedFamilyId',
            'property bool familyCreatePending: false',
            'appSelector.pendingNewFamilyId = newId',
            'SocialIdentityStore.storageState === "ready"',
            'appSelector.identitySnapshot.writable',
            'appSelector.identitySnapshot.familyOptions.length < 20',
        ):
            self.assertIn(needle, SELECTOR, needle)
        for needle in (
            'function applyFamilyAction(result)',
            'function createFamily(name)',
            'function renameFamily(familyId, name)',
            'function moveAppToFamily(appId, familyId)',
            'familyActionError = result && result.reason',
            'return stage(result)',
            'atomicWrites: true',
            'watchChanges: false',
            'printErrors: false',
            'identities.familyActionError = "FILE_SAVE_FAILED"',
        ):
            self.assertIn(needle, STORE, needle)
        self.assertEqual(STORE.count('FileView {'),1)

    def test_layout_policy_and_stable_provider_indices(self):
        for needle in (
            'function createFamily(doc, name)',
            'function renameFamily(doc, familyId, name)',
            'function moveAppToFamily(doc, appId, targetFamilyId)',
            'function validAppId(value)',
            'function rowsForLayout(layout)',
            'familyNames[folded] = true;',
            'familyOptions: families, appChoices: appChoices',
            'serviceIndex:index',
            'families[i].appIds.splice(index, 1)',
            'target.appIds.push(appId)',
            'return {ok:true, reason:"", document:next,',
        ):
            self.assertIn(needle, POLICY, needle)
        legacy=re.findall(r'\bname:\s*"([^"]+)"', SELECTOR)
        self.assertEqual(len(legacy),32)
        self.assertEqual(legacy[0:3],["SESSIONS","DISCORD","TELEGRAM"])
        self.assertEqual(legacy[-1],"BEREAL")
        self.assertIn('appSelector.appActivated(buttonContainer.modelData.serviceIndex);',
                      SELECTOR)
        self.assertIn('messagingWindow.activateApp(index);', HOST)
        self.assertNotIn('SocialIdentityStore', HOST)
        self.assertIn('appSelector.nextActiveAppIndex(', HOST)

    def test_no_login_or_provider_actions_in_layout_editor(self):
        for prohibited in (
            'sendMessage(', 'startLogin(', 'logout(', 'getPassword(',
            'setPassword(', 'Quickshell.execDetached(',
            'Qt.openUrlExternally(', 'Process {', 'Timer {',
        ):
            self.assertNotIn(prohibited, POLICY + STORE, prohibited)
        section=SELECTOR.split('text: "BUTTON FAMILIES"',1)[1]
        self.assertNotIn('appActivated(',section)
        self.assertNotIn('activateApp(',section)
        self.assertNotIn('FileView {',section)
        self.assertIn('Only button placement changes. Logins stay unchanged.',section)


if __name__=="__main__":
    unittest.main()
