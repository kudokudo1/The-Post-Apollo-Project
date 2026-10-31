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

    def test_open_app_magenta_border_halo_preserves_active_yellow(self):
        # Only app rows receive the new outline. Their active/background
        # identity still comes from controller and real Sway observations,
        # not keyboard or pointer preview.
        app = SELECTOR.split("id: appButton", 1)[1].split(
            "// The app rail remains", 1
        )[0]
        self.assertIn(
            "readonly property bool isOpenStyled: isActive || isBackgroundOpen",
            app,
        )
        self.assertIn("border.width: appButton.isOpenStyled ? 1 : 0", app)
        self.assertIn("border.color: Colors.magenta", app)
        halo = app.split("// OPEN-APP MAGENTA BORDER HALO", 1)[1].split(
            "// CLOCK-STYLE CLOSE GLOW", 1
        )[0]
        self.assertIn("RectangularShadow {", halo)
        self.assertIn("anchors.fill: parent", halo)
        self.assertIn("spread: 3", halo)
        self.assertIn("color: Colors.magenta", halo)
        self.assertIn("opacity: appButton.isOpenStyled ? 0.55 : 0.0", halo)
        # New glow is stronger than the yellow close/wide planes but
        # remains behind the app rectangle, preserving visible yellow fill.
        self.assertIn("z: -0.5", halo)
        self.assertIn("color: appButton.isActive ? Colors.yellow", app)
        self.assertIn("opacity: appButton.isActive ? 0.55", app)
        self.assertIn("opacity: appButton.isActive ? 0.12", app)
        self.assertIn("appButton.isBackgroundOpen ? Colors.dark", app)
        self.assertIn("appButton.isBackgroundOpen ? 0.0", app)
        self.assertIn("color: appButton.isOpenStyled ? Colors.magenta", app)
        self.assertIn(
            "color: appButton.isOpenStyled ? Colors.magenta : Colors.orange",
            app,
        )

    def test_expanded_folder_uses_orange_without_becoming_selected(self):
        # Family expand/collapse is an organization filter, not selection
        # of the currently displayed app. Only its idle foreground/border/
        # content glow identity changes to orange while expanded.
        family = SELECTOR.split("ActionButton {", 1)[1].split(
            "onTriggered: SocialIdentityStore.toggleFamily(", 1
        )[0]
        self.assertIn("visible: buttonContainer.isFamilyRow", family)
        self.assertIn("buttonContainer.modelData.expanded ? \"▾ \" : \"▸ \"", family)
        self.assertIn(
            "accentColor: buttonContainer.modelData.expanded", family
        )
        self.assertIn("? Colors.orange : Colors.cyan", family)
        self.assertNotIn("selected: buttonContainer.modelData.expanded", family)
        self.assertNotIn("selectedFillColor:", family)
        self.assertIn("SocialIdentityStore.toggleFamily(", SELECTOR)
        self.assertEqual(SELECTOR.count("id: appButton"), 1)

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
        self.assertIn("messagingWindow.appSelectorWidth : socialWindow.width",
                      HOST)
        self.assertIn("appSelector.settingsOpen", HOST)


if __name__ == "__main__":
    unittest.main()
