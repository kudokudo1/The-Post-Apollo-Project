"""Post-Apollo Social Settings in contact-list/chat-feed workspace.

Static source integration contracts only. Live Wayland/Sway stacking, focus
and rendering still require desktop operator verification.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
FRAME = (ROOT / "components/WindowPanelFrame.qml").read_text()
SURFACE = (ROOT / "components/SurfaceFrame.qml").read_text()
POLICY = (ROOT / "services/social/SocialIdentityPolicy.js").read_text()
STORE = (ROOT / "services/social/SocialIdentityStore.qml").read_text()


class SettingsContactChatWorkspaceContracts(unittest.TestCase):
    def test_existing_social_window_and_real_content_areas(self):
        self.assertEqual(HOST.count("FloatingWindow {"), 1)
        self.assertIn('title: "QS_SOCIAL_MENU"', HOST)
        self.assertIn("width: messagingWindow.sharedPanelWidth", HOST)
        self.assertIn("height: messagingWindow.sharedPanelHeight", HOST)
        self.assertIn("settingsWorkspaceParent: messagingContent.contentItem", HOST)
        self.assertIn("settingsContactWidth: messagingWindow.contactListWidth", HOST)
        self.assertIn("readonly property Item contentItem: surface.contentItem", FRAME)
        self.assertIn("readonly property Item contentItem: contentHost", SURFACE)
        for part in (
            "property Item settingsWorkspaceParent: null",
            "property int settingsContactWidth: 200",
            "id: settingsPage",
            "parent: appSelector.settingsWorkspaceParent",
            "? appSelector.settingsWorkspaceParent : appSelector",
            "? appSelector.right : parent.left",
            "id: settingsIdentityPane",
            "id: settingsEditorPane",
            "id: settingsFamilyPane",
            "id: settingsAppPane",
            "id: settingsIdentityColumn",
            "id: settingsColumn",
            "id: settingsAppsColumn",
            "width: Math.min(parent.width, appSelector.settingsContactWidth)",
            "z: 10",
        ):
            self.assertIn(part, SELECTOR, part)
        self.assertNotIn("FloatingWindow {", SELECTOR)
        self.assertNotIn("PanelWindow {", SELECTOR)
        self.assertNotIn("PopupWindow {", SELECTOR)

    def test_left_rail_stays_live_preview_but_cannot_launch_apps(self):
        self.assertIn("model: appSelector.railRows", SELECTOR)
        self.assertIn("visible: true", SELECTOR)
        self.assertIn("enabled: !appSelector.settingsOpen", SELECTOR)
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);", SELECTOR)
        self.assertIn("onIdentitySnapshotChanged: Qt.callLater", SELECTOR)
        self.assertIn("appSelector.ensureValidSelection();", SELECTOR)
        self.assertIn("appSelector.ensureSelectedVisible();", SELECTOR)
        self.assertIn("readonly property var identitySnapshot: SocialIdentityStore.snapshot", SELECTOR)
        self.assertIn("identityFile.setText(", STORE)
        self.assertIn("onSaved:", STORE)
        self.assertIn("document = identities.pendingDocument;", STORE)
        self.assertIn("railRows: display.rows, visibleAppIndices: display.appIndices", POLICY)
        labels = re.findall(r'\bname:\s*"([^"]+)"', SELECTOR)
        self.assertEqual(len(labels), 32)
        self.assertEqual(labels[:4], ["SESSIONS", "DISCORD", "TELEGRAM", "X"])
        self.assertEqual(labels[-1], "BEREAL")

    def test_editor_occupies_contact_and_chat_with_independent_scroll(self):
        sidebar = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        family = SELECTOR.split("id: settingsFamilyPane", 1)[1].split(
            "id: settingsAppPane", 1
        )[0]
        app = SELECTOR.split("id: settingsAppPane", 1)[1].split(
            "// This entry point is always visible", 1
        )[0]
        for part in (
            'text: "IDENTITIES"', 'text: "ACCOUNT NAMES"',
            'text: "IDENTITY DETAILS"', "id: newIdentityName",
            'text: "DEFAULT EMAIL"', 'text: "DEFAULT PHONE"',
            "SocialIdentityStore.selectIdentity(modelData.id)",
            "SocialIdentityStore.createIdentity(",
        ):
            self.assertIn(part, sidebar, part)
        for part in (
            'text: "BUTTON FAMILIES"', "id: familyNameInput",
            "SocialIdentityStore.createFamily(",
            "SocialIdentityStore.renameFamily(",
            "SocialIdentityStore.reorderFamily(",
            "SocialIdentityStore.removeFamily(",
            "rehomeFamilyOptions()",
        ):
            self.assertIn(part, family, part)
        for part in (
            'text: "APP ORGANIZATION"', "id: familySearchInput",
            "SocialIdentityStore.moveAppToFamily(",
            "SocialIdentityStore.reorderApp(",
            "SocialIdentityStore.setAppHidden(",
            "Saved edits update the live rail on the left.",
        ):
            self.assertIn(part, app, part)
        self.assertGreaterEqual(SELECTOR.count("Flickable {"), 4)
        self.assertIn("visible: appSelector.editingFamilies", family)
        self.assertIn("visible: appSelector.editingFamilies", app)
        self.assertIn("editingFamilies = true;", SELECTOR)

    def test_input_mask_is_full_only_during_settings_and_restores(self):
        mask = HOST.split("id: socialWindow", 1)[1].split(
            "// GEOMETRY HELPERS", 1
        )[0]
        for part in (
            "mask: Region {", "width: messagingWindow.menuOpen",
            "appSelector.settingsOpen", "? socialWindow.width",
            "messagingWindow.externalSelected",
            "? messagingWindow.appSelectorWidth : socialWindow.width",
            ": 0",
        ):
            self.assertIn(part, mask, part)
        self.assertIn("socialWindow.requestActivate()", HOST)
        self.assertIn("discordRaiseDelay.stop();", HOST)
        self.assertIn("xRaiseDelay.stop();", HOST)
        self.assertIn("messagingWindow.raiseDiscord();", HOST)
        self.assertIn("messagingWindow.raiseX();", HOST)
        self.assertIn("appSelector.settingsOpen = false;", HOST)
        self.assertIn("if (appSelector.settingsOpen) {", HOST)
        self.assertIn("Qt.Key_Escape", HOST)

    def test_provider_surfaces_suspend_only_while_editor_is_open(self):
        self.assertIn("id: contactList", HOST)
        self.assertIn("id: chatFeed", HOST)
        self.assertIn("id: telegramConnectPanel", HOST)
        self.assertIn("id: providerAccessPanel", HOST)
        self.assertGreaterEqual(
            HOST.count("visible: messagingWindow.menuOpen && !appSelector.settingsOpen"),
            4,
        )
        self.assertIn("discordMode: messagingWindow.externalSelected", HOST)
        self.assertIn("property bool providerDesktopManaged: false", HOST)
        self.assertIn("function syncDiscordGeometry(focusWindow)", HOST)
        self.assertIn("function syncXGeometry(focusWindow)", HOST)
        self.assertIn("function activateApp(index", HOST)
        self.assertNotIn("SocialIdentityStore", HOST)
        for banned in ("sendMessage(", "startLogin(", "logout(", "Process {", "Timer {"):
            self.assertNotIn(banned, POLICY + STORE)


if __name__ == "__main__":
    unittest.main()
