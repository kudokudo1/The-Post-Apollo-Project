"""Offline source checks for identity-aware, collapsible Social app rail.

These are not live Quickshell/Sway or login tests. The corresponding Node test
exercises the real identity policy with no files, accounts, or network access.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
POLICY = (ROOT / "services/social/SocialIdentityPolicy.js").read_text()
STORE = (ROOT / "services/social/SocialIdentityStore.qml").read_text()


class SocialFamilyRailSource(unittest.TestCase):
    def test_catalog_and_legacy_provider_mapping(self):
        raw = SELECTOR.split("property var messagingApps:", 1)[1].split(
            "// SIZE / PANEL", 1)[0]
        labels = re.findall(r'\bname:\s*"([^"]+)"', raw)
        self.assertEqual(len(labels), 32)
        self.assertEqual(labels[0:4], ["SESSIONS", "DISCORD", "TELEGRAM", "X"])
        self.assertEqual(labels[-1], "BEREAL")
        self.assertIn("readonly property var appData: isAppRow", SELECTOR)
        self.assertIn("appSelector.messagingApps[modelData.serviceIndex]", SELECTOR)
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);", SELECTOR)
        self.assertIn("messagingWindow.activateApp(index);", HOST)
        self.assertIn("function rowsForLayout(layout)", POLICY)
        self.assertIn("serviceIndex:serviceIndex", POLICY)
        self.assertIn("var serviceIndex = APP_IDS.indexOf(members[j])", POLICY)

    def test_family_header_and_fixed_settings_footer(self):
        self.assertIn("model: appSelector.railRows", SELECTOR)
        self.assertIn("readonly property var railRows: identitySnapshot.railRows || []", SELECTOR)
        self.assertIn("buttonContainer.isFamilyRow", SELECTOR)
        self.assertIn("SocialIdentityStore.toggleFamily(", SELECTOR)
        self.assertIn('modelData.kind === "empty"', SELECTOR)
        self.assertIn('text: "NO FAMILIES', SELECTOR)
        self.assertIn("id: settingsFooter", SELECTOR)
        self.assertIn("anchors.bottom: parent.bottom", SELECTOR)
        self.assertIn("bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top",
                      SELECTOR)
        self.assertIn("appSelector.settingsOpen = !appSelector.settingsOpen", SELECTOR)

    def test_hidden_actions_cannot_be_launched_from_navigation(self):
        for required in (
            "function isAppVisible(index)", "function moveSelection(direction)",
            "function nextActiveAppIndex(activeIndex, reverse)",
            "function ensureValidSelection()", "onIdentitySnapshotChanged:",
            "!appSelector.isAppVisible(buttonContainer.modelData.serviceIndex)",
            'row.kind === "app" && row.serviceIndex === selectedIndex',
        ):
            self.assertIn(required, SELECTOR)
        for required in (
            "const count = appSelector.visibleAppIndices.length;",
            "appSelector.nextActiveAppIndex(",
            "appSelector.moveSelection(-1);",
            "appSelector.moveSelection(1);",
            "if (appSelector.isAppVisible(appSelector.selectedIndex))",
            "Qt.callLater(function() { appSelector.ensureValidSelection(); });",
        ):
            self.assertIn(required, HOST)
        self.assertNotIn("appSelector.messagingApps.length", HOST)

    def test_layout_only_mutation_and_identity_isolation(self):
        self.assertIn("function toggleFamily(doc, familyId)", POLICY)
        self.assertIn("family.expanded = !family.expanded", POLICY)
        self.assertIn("var next = clone(doc)", POLICY)
        self.assertIn("function toggleFamily(familyId)", STORE)
        self.assertIn("IdentityPolicy.toggleFamily(document, familyId)", STORE)
        self.assertIn("atomicWrites: true", STORE)
        self.assertIn("watchChanges: false", STORE)
        self.assertIn("IdentityPolicy.view(storageState, document, errorCode)", STORE)
        self.assertIn("identityFile.setText(", STORE)
        self.assertNotIn("SocialIdentityStore", HOST)
        for forbidden in ("startLogin(", "sendMessage(", "activateApp("):
            self.assertNotIn(forbidden, POLICY + STORE)
        self.assertIn("messagingWindow.externalSelected ? messagingWindow.appSelectorWidth : socialWindow.width",
                      HOST)


if __name__ == "__main__":
    unittest.main()
