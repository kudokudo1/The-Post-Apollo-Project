"""Social organization Step 5: source and isolation contracts.

Real policy behavior is exercised in the matching Node test. These are
structural checks only, not a running Quickshell desktop or provider login.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
POLICY=(ROOT/"services/social/SocialIdentityPolicy.js").read_text()
STORE=(ROOT/"services/social/SocialIdentityStore.qml").read_text()
SELECTOR=(ROOT/"widgets/messanger/AppSelector.qml").read_text()
HOST=(ROOT/"widgets/messanger/MessagingW.qml").read_text()


class SocialFamilyOrderVisibility(unittest.TestCase):
    def test_family_and_app_reorder_keep_canonical_ids(self):
        for required in (
            "function reorderFamily(doc, familyId, direction)",
            "function reorderApp(doc, familyId, appId, direction)",
            "function setAppHidden(doc, appId, hidden)",
            "if (direction !== -1 && direction !== 1)",
            "return {ok:false, reason:\"NO_CHANGE\"}",
            "return {ok:false, reason:\"APP_NOT_IN_FAMILY\"}",
            "return {ok:false, reason:\"INVALID_VISIBILITY\"}",
            "families[destination] = previous",
            "family.appIds[destination] = previous",
            "active.layout.hiddenAppIds",
            "hiddenIds.push(appId)",
            "hiddenIds.splice(index, 1)",
            "familyOptions: families, appChoices: appChoices",
            "orderIndex:orderIndex",
            "siblingCount:family ? family.appIds.length : 0",
            "hidden:identity.layout.hiddenAppIds.indexOf(appId) !== -1",
            "serviceIndex:index",
        ):
            self.assertIn(required,POLICY,required)
        catalog=re.findall(r'\bname:\s*"([^"]+)"',SELECTOR)
        self.assertEqual(len(catalog),32)
        self.assertEqual(catalog[:4],["SESSIONS","DISCORD","TELEGRAM","X"])
        self.assertEqual(catalog[-1],"BEREAL")
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);",
                      SELECTOR)
        self.assertIn("appSelector.nextActiveAppIndex(",HOST)
        self.assertIn("if (appSelector.isAppVisible(appSelector.selectedIndex))",HOST)

    def test_uses_existing_atomic_single_writer(self):
        for required in (
            "function reorderFamily(familyId, direction)",
            "function reorderApp(familyId, appId, direction)",
            "function setAppHidden(appId, hidden)",
            "IdentityPolicy.reorderFamily(",
            "IdentityPolicy.reorderApp(",
            "IdentityPolicy.setAppHidden(",
            "return applyFamilyAction(",
            "return stage(result)",
            "atomicWrites: true",
            "watchChanges: false",
            "onSaved:",
            "onSaveFailed: function(error)",
        ):
            self.assertIn(required,STORE,required)
        self.assertEqual(STORE.count("FileView {"),1)
        self.assertEqual(STORE.count("identityFile.setText("),1)
        self.assertNotIn("SocialIdentityStore",HOST)
        for forbidden in ("startLogin(", "sendMessage(", "activateApp(",
                          "Process {", "Timer {", "Quickshell.execDetached("):
            self.assertNotIn(forbidden,POLICY+STORE,forbidden)

    def test_settings_editor_adds_real_button_controls(self):
        for required in (
            "function selectedFamilyOption()",
            "function selectedAppOption()",
            "function familyCanStep(direction)",
            "function appCanStep(direction)",
            "familyEditorIdentityId !== identitySnapshot.activeId",
            "app.familyId === editedFamilyId",
            "label: \"FAMILY UP\"",
            "label: \"FAMILY DOWN\"",
            "label: \"APP UP\"",
            "label: \"APP DOWN\"",
            '"SHOW APP" : "HIDE APP"',
            "SocialIdentityStore.reorderFamily(",
            "SocialIdentityStore.reorderApp(",
            "SocialIdentityStore.setAppHidden(",
            "appSelector.familyCanStep(-1)",
            "appSelector.familyCanStep(1)",
            "appSelector.appCanStep(-1)",
            "appSelector.appCanStep(1)",
            "appSelector.identitySnapshot.writable",
            "appSelector.selectedAppOption().familyId !== \"\"",
            "Hidden apps keep their family and account.",
            "Only button placement changes. Logins stay unchanged.",
        ):
            self.assertIn(required,SELECTOR,required)
        self.assertEqual(SELECTOR.count("id: settingsFooter"),1)
        self.assertIn('label: "USER // SETTINGS"',SELECTOR)
        self.assertIn("model: appSelector.railRows",SELECTOR)
        self.assertIn("bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top",
                      SELECTOR)
        section=SELECTOR.split('text: "BUTTON FAMILIES"',1)[1].split(
            'text: "LINKED ACCOUNTS"',1)[0]
        for forbidden in ("appActivated(", "activateApp(", "FileView {",
                          "Qt.openUrlExternally(", "Process {"):
            self.assertNotIn(forbidden,section)

if __name__=="__main__":
    unittest.main()
