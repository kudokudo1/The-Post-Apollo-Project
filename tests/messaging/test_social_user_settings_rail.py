"""Offline source contracts for Social's first USER // SETTINGS rail slice.

These checks do not imply live Quickshell/Sway or credential integration.
Run: python3 -m unittest tests/messaging/test_social_user_settings_rail.py -v
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text(encoding="utf-8")
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text(encoding="utf-8")


class SocialUserSettingsRailContracts(unittest.TestCase):
    def test_catalog_indices_stay_unchanged(self):
        start = SELECTOR.index("property var messagingApps:")
        end = SELECTOR.index("// SIZE / PANEL", start)
        apps = re.findall(r'\bname:\s*"([^"]+)"', SELECTOR[start:end])
        self.assertEqual(apps, [
            "SESSIONS", "DISCORD", "TELEGRAM", "X", "INSTAGRAM",
            "FACEBOOK", "REDDIT", "THREADS", "PINTEREST",
            "TRUTH SOCIAL", "BLUESKY", "TUMBLR", "TIKTOK",
            "SNAPCHAT", "WHATSAPP", "MESSENGER", "LINKEDIN",
            "MASTODON", "NEXTDOOR", "STEAM CHAT", "ELEMENT",
            "GROUPME", "LEMON8", "QUORA", "PIXELFED", "ZALO",
            "SIGNAL", "WECHAT", "LINE", "VIBER", "KAKAOTALK",
            "BEREAL",
        ])
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);", SELECTOR)
        self.assertIn("messagingWindow.activateApp(index);", HOST)

    def test_settings_button_is_outside_scroll_and_never_activates_app(self):
        self.assertIn("property bool settingsOpen: false", SELECTOR)
        scroll = SELECTOR.index("    Flickable {\n        id: appScroll")
        footer = SELECTOR.index("    ActionButton {\n        id: settingsFooter")
        self.assertGreater(footer, scroll)
        self.assertIn("anchors.bottom: parent.bottom", SELECTOR[footer:footer + 220])
        self.assertIn('label: "USER // SETTINGS"', SELECTOR[footer:footer + 480])
        self.assertIn(
            "onTriggered: appSelector.settingsOpen = !appSelector.settingsOpen",
            SELECTOR[footer:footer + 550],
        )
        self.assertNotIn("appSelector.appActivated", SELECTOR[footer:footer + 600])
        self.assertIn("visible: !appSelector.settingsOpen", SELECTOR)

    def test_settings_page_and_status_do_not_hide_footer(self):
        self.assertIn("id: settingsPage", SELECTOR)
        self.assertIn("visible: appSelector.settingsOpen", SELECTOR)
        self.assertIn(
            "bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top",
            SELECTOR,
        )
        self.assertIn("anchors.bottom: settingsFooter.top", SELECTOR)
        self.assertIn('visible: appSelector.statusText !== ""', SELECTOR)
        self.assertIn("id: statusMessage", SELECTOR)

    def test_settings_keyboard_scope_and_reset(self):
        self.assertIn("if (appSelector.settingsOpen) {", HOST)
        scope_start = HOST.index("if (appSelector.settingsOpen) {")
        scope = HOST[scope_start:scope_start + 240]
        self.assertIn("Qt.Key_Escape", scope)
        self.assertIn("event.accepted = true", scope)
        self.assertIn("onSettingsOpenChanged:", HOST)
        self.assertIn("appSelector.settingsOpen = false;\n        setGeometryWatch(menuOpen)", HOST)
        self.assertIn("const count = appSelector.visibleAppIndices.length;", HOST)

    def test_external_input_mask_and_routing_unchanged(self):
        self.assertIn(
            "messagingWindow.externalSelected ? messagingWindow.appSelectorWidth : socialWindow.width",
            HOST,
        )
        self.assertIn("activeAppIndex === 0 || activeAppIndex === 2", HOST)
        self.assertIn("activeAppIndex === 1", HOST)
        # The in-rail slice introduces no credential, network or profile writes.
        first = SELECTOR.index("id: settingsPage")
        last = SELECTOR.index("id: statusMessage", first)
        settings = SELECTOR[first:last].lower()
        for forbidden in ("subprocess", "password", "token", "credential_store", "fileview"):
            self.assertNotIn(forbidden, settings)


if __name__ == "__main__":
    unittest.main()
