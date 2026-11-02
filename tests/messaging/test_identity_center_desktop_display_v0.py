"""Static safety contracts for staged Social Organizations display-only input.

No live Quickshell render, OAuth desktop host, API session or data activation.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
UI = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
HOST = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
ADAPTER = (ROOT / "services/identity/desktop_context_projection_v0.py").read_text()


class IdentityCenterDesktopDisplayTests(unittest.TestCase):
    def test_existing_social_settings_navigation_is_unchanged(self):
        for section in ("PROFILE", "ORGANIZATIONS", "CONNECTED ACCOUNTS",
                        "SECURITY", "SOCIAL LAYOUT"):
            self.assertIn('label: "' + section + '"', UI)
        self.assertIn('property string activeSection: "SOCIAL LAYOUT"', UI)
        self.assertIn("id: identityCenterSettingsSections", HOST)
        self.assertIn('visible: appSelector.settingsSection === "SOCIAL LAYOUT"', HOST)

    def test_display_input_is_null_and_not_an_authenticated_host(self):
        self.assertIn("property var organizationDisplaySnapshot: null", UI)
        self.assertIn('organizationDisplaySnapshot.status === "READY"', UI)
        self.assertIn("organizationDisplaySnapshot.canSwitchOrganization === false", UI)
        self.assertIn("Array.isArray(organizationDisplaySnapshot.organizations)", UI)
        self.assertNotIn("organizationDisplaySnapshot:", HOST)
        self.assertNotIn("onOrganizationDisplaySnapshotChanged", UI)

    def test_switcher_remains_disabled_even_with_projected_memberships(self):
        start = UI.index('label: "SWITCH ORGANIZATION // UNAVAILABLE"')
        self.assertIn("interactive: false", UI[start:start + 240])
        self.assertIn('text: "ACTIVE ORGANIZATION // NONE VERIFIED"', UI)
        self.assertIn("Display data is not proof of permission.", UI)
        self.assertNotIn("onTriggered: sections.selectOrganization", UI)

    def test_organizations_are_displayed_only_in_the_organizations_page(self):
        self.assertIn('visible: sections.activeSection === "ORGANIZATIONS"', UI)
        self.assertIn('visible: sections.organizationDisplayReady', UI)
        self.assertIn('visible: !sections.organizationDisplayReady', UI)
        self.assertIn("organizationDisplaySnapshot.organizations", UI)
        self.assertIn("organizationDisplaySnapshot.portfolios", UI)
        self.assertIn('text: "MEMBERSHIPS // READ-ONLY DISPLAY"', UI)
        self.assertIn("modelData.scopeGrants.length", UI)

    def test_no_credential_storage_network_process_or_browser(self):
        for prohibited in (
            "Process {", "FileView {", "HttpRequest", "XMLHttpRequest",
            "Authorization:", "Bearer ", "accessToken", "refreshToken",
            "id_token", "Qt.openUrlExternally", "SessionAdapter",
            "role: \"admin\"", "Socket", "LocalStorage",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, UI)
        self.assertNotIn("requests.", ADAPTER)
        self.assertNotIn("urllib.request", ADAPTER)
        self.assertNotIn("subprocess", ADAPTER)
        self.assertNotIn("keyring", ADAPTER)

    def test_no_new_settings_window_or_side_effect(self):
        self.assertNotIn("FloatingWindow {", UI)
        self.assertNotIn("PopupWindow {", UI)
        self.assertNotIn("writeFile(", UI)
        self.assertNotIn("createIdentity(", UI)
        self.assertNotIn("saveContact(", UI)
        self.assertIn('text: "NOT CONNECTED // TRUSTED BACKEND REQUIRED"', UI)


if __name__ == "__main__":
    unittest.main()
