"""Offline contracts for Identity Center tabs inside existing USER // SETTINGS.

Static checks only. Does not claim live Quickshell/Sway rendering, backend
authentication, organization memberships or production authorization.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()


class IdentityCenterSettingsSectionsContracts(unittest.TestCase):
    def test_one_original_settings_window_footer_and_header(self):
        self.assertEqual(HOST.count("FloatingWindow {"), 1)
        self.assertIn("id: settingsPage", SELECTOR)
        self.assertIn("id: settingsHeader", SELECTOR)
        self.assertIn('text: "USER // SETTINGS"', SELECTOR)
        self.assertEqual(SELECTOR.count('text: "USER // SETTINGS"'), 1)
        self.assertIn('label: "USER // SETTINGS"', SELECTOR)
        self.assertIn("onTriggered: appSelector.settingsOpen = !appSelector.settingsOpen",
                      SELECTOR)
        self.assertNotIn("FloatingWindow {", SECTIONS)
        self.assertNotIn("PopupWindow {", SECTIONS)
        self.assertNotIn("PanelWindow {", SECTIONS)

    def test_all_five_sections_are_selectable_inside_same_workspace(self):
        ids = re.findall(r'\{\s*id: "([^"]+)", label: "([^"]+)"\s*\}', SECTIONS)
        self.assertEqual(ids, [
            ("PROFILE", "PROFILE"),
            ("ORGANIZATIONS", "ORGANIZATIONS"),
            ("CONNECTED ACCOUNTS", "CONNECTED ACCOUNTS"),
            ("SECURITY", "SECURITY"),
            ("SOCIAL LAYOUT", "SOCIAL LAYOUT"),
        ])
        self.assertIn('property string settingsSection: "SOCIAL LAYOUT"', SELECTOR)
        self.assertIn("id: identityCenterSettingsSections", SELECTOR)
        self.assertIn("activeSection: appSelector.settingsSection", SELECTOR)
        self.assertIn("appSelector.settingsSection = section;", SELECTOR)
        self.assertIn("onTriggered: sections.sectionRequested(modelData.id)", SECTIONS)
        self.assertIn("selected: sections.activeSection === modelData.id", SECTIONS)
        self.assertIn("flickableDirection: Flickable.HorizontalFlick", SECTIONS)
        self.assertIn("clip: true", SECTIONS)

    def test_original_social_editors_remain_and_default_on_open(self):
        first = SELECTOR.index("onSettingsOpenChanged:")
        second = SELECTOR.index("if (settingsOpen) {", first)
        self.assertIn('settingsSection = "SOCIAL LAYOUT";',
                      SELECTOR[second:second + 280])
        for part in (
            "id: settingsLegacyLayoutRow",
            'visible: appSelector.settingsSection === "SOCIAL LAYOUT"',
            "top: settingsHeader.bottom",
            "anchors.topMargin: identityCenterSettingsSections.navigationHeight",
            "id: settingsIdentityPane",
            "id: settingsEditorPane",
            "id: settingsFamilyPane",
            "id: settingsAppPane",
            "SocialIdentityStore.createIdentity(",
            "SocialAccountDetailsStore.saveContact(",
            "SocialIdentityStore.moveAppToFamily(",
        ):
            self.assertIn(part, SELECTOR, part)
        self.assertLess(SELECTOR.index("id: settingsHeader"),
                        SELECTOR.index("id: identityCenterSettingsSections"))
        self.assertLess(SELECTOR.index("id: identityCenterSettingsSections"),
                        SELECTOR.index("id: settingsLegacyLayoutRow"))
        self.assertIn("settingsWorkspaceParent: messagingContent.contentItem", HOST)

    def test_organization_switcher_is_truthful_and_disabled(self):
        self.assertIn('text: "ACTIVE ORGANIZATION // NONE VERIFIED"', SECTIONS)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        start = SECTIONS.index('label: "SWITCH ORGANIZATION // UNAVAILABLE"')
        self.assertIn("interactive: false", SECTIONS[start:start + 220])
        self.assertIn('text: "NOT CONNECTED // TRUSTED BACKEND REQUIRED"', SECTIONS)
        self.assertIn("Portfolio views never grant rights", SECTIONS)
        self.assertNotRegex(SECTIONS, r'\b(?:llc_a|llc_b|nonprofit-test|identity-1)\b')
        self.assertNotIn("onTriggered: sections.switch", SECTIONS)

    def test_preview_has_no_credential_or_storage_side_effects(self):
        for forbidden in (
            "Process {", "FileView {", "HttpRequest",
            "Quickshell.Io", "Qt.openUrlExternally(",
            ".createIdentity(", ".saveContact(", ".setAccountLabel(",
            "appActivated(", "session_token", "accessToken:",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, SECTIONS)
        self.assertIn('visible: sections.isPreviewSection', SECTIONS)
        self.assertIn('activeSection !== "SOCIAL LAYOUT"', SECTIONS)
        self.assertIn("No verified Post-Apollo person session", SECTIONS)
        self.assertIn("No authorized organizations or portfolios", SECTIONS)
        self.assertIn("not connected", SECTIONS.lower())

    def test_existing_host_keyboard_and_app_rail_stay_untouched(self):
        self.assertIn("if (appSelector.settingsOpen) {", HOST)
        self.assertIn("Qt.Key_Escape", HOST)
        self.assertIn("appSelector.settingsOpen = false;", HOST)
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);",
                      SELECTOR)
        self.assertIn("messagingWindow.activateApp(index);", HOST)


if __name__ == "__main__":
    unittest.main()
