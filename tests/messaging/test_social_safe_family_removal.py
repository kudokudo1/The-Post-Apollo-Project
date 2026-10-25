"""Social organization Step 6 source contracts: removal stays non-destructive.

The companion Node test runs real policy functions. These checks do not
certify live Quickshell, account status, or mouse/keyboard compositor behavior.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
SELECTOR=(ROOT/"widgets/messanger/AppSelector.qml").read_text()
POLICY=(ROOT/"services/social/SocialIdentityPolicy.js").read_text()
STORE=(ROOT/"services/social/SocialIdentityStore.qml").read_text()
HOST=(ROOT/"widgets/messanger/MessagingW.qml").read_text()


class SafeFamilyRemovalContracts(unittest.TestCase):
    def test_policy_requires_destination_and_preserves_layout(self):
        for needle in (
            "function removeFamily(doc, familyId, targetFamilyId)",
            'return {ok:false, reason:"REHOME_REQUIRED"}',
            'return {ok:false, reason:"SAME_FAMILY"}',
            'return {ok:false, reason:"INVALID_TARGET_FAMILY"}',
            'return {ok:false, reason:"TARGET_NOT_NEEDED"}',
            "destination.appIds = destination.appIds.concat(source.appIds);",
            "families.splice(index, 1)",
            "var next = clone(doc);",
            "var after = validate(next);",
            "rehomedAppCount:source.appIds.length",
            "function validate(doc)",
            "hiddenAppIds: layout.hiddenAppIds.slice()",
        ):
            self.assertIn(needle,POLICY,needle)
        self.assertNotIn("nextFamilyId--",POLICY)
        self.assertNotIn("appIds = []",POLICY.split("function removeFamily(",1)[1].split(
            "// Reorder only metadata",1)[0])

    def test_store_reuses_single_writer_and_never_opens_provider(self):
        self.assertIn("function removeFamily(familyId, targetFamilyId)",STORE)
        self.assertIn("IdentityPolicy.removeFamily(",STORE)
        self.assertIn("return applyFamilyAction(",STORE)
        self.assertEqual(STORE.count("FileView {"),1)
        self.assertEqual(STORE.count("identityFile.setText("),1)
        self.assertIn("atomicWrites: true",STORE)
        self.assertIn("watchChanges: false",STORE)
        for banned in ("Process {", "Timer {", "startLogin(", "sendMessage(",
                       "activateApp(", "Qt.openUrlExternally(", "getPassword("):
            self.assertNotIn(banned,POLICY+STORE,banned)

    def test_explicit_rehome_and_two_click_confirmation(self):
        for needle in (
            'property string removalTargetFamilyId: ""',
            'property string removalConfirmIdentityId: ""',
            'property string removalConfirmFamilyId: ""',
            'property string removalConfirmTargetId: ""',
            "function resetFamilyRemovalConfirmation()",
            "function rehomeFamilyOptions()",
            "function removalTargetValid()",
            "function familyCanBeRemoved()",
            "function familyRemovalConfirmationMatches()",
            "selected.count === 0 || removalTargetValid()",
            "removalConfirmIdentityId === identitySnapshot.activeId",
            "removalConfirmFamilyId === editedFamilyId",
            'text: "REHOME TO"',
            'text: "CREATE ANOTHER FAMILY FIRST"',
            'text: "REMOVE FAMILY"',
            '? "CONFIRM REMOVE" : "REMOVE FAMILY"',
            "if (!appSelector.familyRemovalConfirmationMatches())",
            "appSelector.removalConfirmTargetId = destination;",
            "SocialIdentityStore.removeFamily(",
            "onIdentitySnapshotChanged: Qt.callLater",
            "onSettingsOpenChanged:",
            "appSelector.resetFamilyRemovalConfirmation();",
            'text: "Apps append to destination. Hidden stays hidden."',
        ):
            self.assertIn(needle,SELECTOR,needle)
        self.assertIn("appSelector.removalTargetFamilyId = \"\";",SELECTOR)
        self.assertIn("appSelector.familyEditorIdentityId !== appSelector.identitySnapshot.activeId",SELECTOR)
        self.assertIn("appSelector.identitySnapshot.writable",SELECTOR)
        self.assertIn("visible: appSelector.familyIsSelected()",SELECTOR)

    def test_original_app_routing_settings_and_32_labels_intact(self):
        names=re.findall(r'\bname:\s*"([^"]+)"',SELECTOR)
        self.assertEqual(len(names),32)
        self.assertEqual(names[:4],["SESSIONS","DISCORD","TELEGRAM","X"])
        self.assertEqual(names[-1],"BEREAL")
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);",
                      SELECTOR)
        self.assertIn("model: appSelector.railRows",SELECTOR)
        self.assertIn("appSelector.nextActiveAppIndex(",HOST)
        self.assertIn("messagingWindow.activateApp(index);",HOST)
        self.assertIn('label: "USER // SETTINGS"',SELECTOR)
        self.assertEqual(SELECTOR.count("id: settingsFooter"),1)
        section=SELECTOR.split('text: "BUTTON FAMILIES"',1)[1].split(
            'text: "LINKED ACCOUNTS"',1)[0]
        for prohibited in ("activateApp(", "appActivated(", "Process {",
                           "FileView {", "Qt.openUrlExternally("):
            self.assertNotIn(prohibited,section,prohibited)


if __name__=="__main__":
    unittest.main()
