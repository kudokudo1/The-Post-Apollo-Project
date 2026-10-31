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

    def test_family_and_app_rows_have_inline_orange_order_arrows(self):
        family = SELECTOR.split("id: settingsFamilyPane", 1)[1].split(
            "id: settingsAppPane", 1
        )[0]
        app = SELECTOR.split("id: settingsAppPane", 1)[1].split(
            "// This entry point is always visible", 1
        )[0]

        # Both panes use up/name/down rows, not separate global actions
        # operating on a previously selected item.
        for source, row_id, label, writer in (
            (family, "familyOptionRow", "familyOptionRow.modelData.title",
             "SocialIdentityStore.reorderFamily("),
            (app, "organizationAppRow",
             "appSelector.messagingApps[", "SocialIdentityStore.reorderApp("),
        ):
            with self.subTest(row=row_id):
                row = source.split("id: " + row_id, 1)[1].split(
                    'text: "NO MATCH"' if row_id == "organizationAppRow"
                    else 'text: "NO FAMILIES"', 1
                )[0]
                self.assertIn('label: "↑"', row)
                self.assertIn('label: "↓"', row)
                self.assertLess(row.index('label: "↑"'), row.index(label))
                self.assertLess(row.index(label), row.index('label: "↓"'))
                self.assertEqual(row.count("accentColor: Colors.orange"), 2)
                self.assertEqual(row.count(writer), 2)
                self.assertIn('width: 28', row)
                self.assertIn('height: parent.height', row)
                self.assertIn('spacing: 3', row)
                self.assertIn('width: Math.max(1, ', row)
                self.assertNotIn('"FAMILY UP"', source)
                self.assertNotIn('"FAMILY DOWN"', source)
                self.assertNotIn('"APP UP"', source)
                self.assertNotIn('"APP DOWN"', source)

        # Arrows reorder their own explicit item IDs using persisted
        # indices, even when a different row is currently selected.
        self.assertIn("familyOptionRow.modelData.id, -1", family)
        self.assertIn("familyOptionRow.modelData.id, 1", family)
        self.assertIn("familyOptionRow.modelData.orderIndex > 0", family)
        self.assertIn("familyOptionRow.modelData.familyCount - 1", family)
        self.assertIn("familyEditorIdentityId ===", family)
        self.assertIn("!appSelector.familyCreatePending", family)
        self.assertIn("organizationAppRow.modelData.id, -1", app)
        self.assertIn("organizationAppRow.modelData.id, 1", app)
        self.assertIn("organizationAppRow.modelData.orderIndex > 0", app)
        self.assertIn("organizationAppRow.modelData.siblingCount - 1", app)
        self.assertIn("appSelector.familyIsSelected()", app)
        self.assertIn("organizationAppRow.modelData.familyId ===", app)
        self.assertIn("appSelector.editedFamilyId", app)
        self.assertIn("appSelector.editedAppId =", app)

        # Family removal remains a separate confirmed destructive action.
        removal = family.split(
            'label: appSelector.familyRemovalConfirmationMatches()', 1
        )[1].split("onTriggered:", 1)[0]
        self.assertIn('CONFIRM REMOVE" : "REMOVE FAMILY"', removal)
        self.assertIn('destructive: true', removal)
        self.assertIn('accentColor: Colors.red', removal)
        self.assertIn("familyRemovalConfirmationMatches()", family)
        self.assertIn("SocialIdentityStore.removeFamily(", family)
        self.assertIn("appSelector.selectedAppNeedsMove()", app)

    def test_operator_marked_settings_button_accents(self):
        # The marked actions use shared semantic states. The existing
        # ActionButton supplies matching idle text, border and glow from
        # accentColor without altering handlers or storage permissions.
        identity = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        family = SELECTOR.split("id: settingsFamilyPane", 1)[1].split(
            "id: settingsAppPane", 1
        )[0]
        app = SELECTOR.split("id: settingsAppPane", 1)[1].split(
            "// This entry point is always visible", 1
        )[0]

        for label, accent in (
            ('appSelector.creatingIdentity ? "CANCEL NEW" : "+ NEW ID"',
             "Colors.magenta"),
            ('"SAVE CONTACT"', "Colors.green"),
            ('"RELOAD DETAILS"', "Colors.yellow"),
        ):
            with self.subTest(label=label):
                button = identity.split("label: " + label, 1)[1].split(
                    "onTriggered:", 1
                )[0]
                self.assertIn("accentColor: " + accent, button)

        # The family-create action follows the same magenta new-item
        # identity while existing family reorder/rename stays orange.
        add_family = family.split('label: "+ FAMILY"', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn("accentColor: Colors.magenta", add_family)
        self.assertIn("familyNameInput.text.trim().length > 0", add_family)

        # The account picker is yellow/magenta at rest, then follows the
        # shared ActionButton selected-state rules when its list is expanded.
        picker = identity.split('label: appSelector.accountAppPickerOpen', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn('"▾ CHOOSE APP (32)"', picker)
        self.assertIn("idleFillColor: Colors.dark", picker)
        self.assertIn(
            "accentColor: appSelector.accountAppPickerOpen", picker,
        )
        self.assertIn("? Colors.magenta : Colors.orange", picker)
        self.assertIn("selected: appSelector.accountAppPickerOpen", picker)
        self.assertIn("interactive: appSelector.identitySnapshot.writable", picker)
        self.assertIn("labelPixelSize: 9", picker)
        self.assertIn("!appSelector.accountAppPickerOpen", identity)
        self.assertIn("visible: appSelector.accountAppPickerOpen", identity)

        edit = family.split(
            'label: appSelector.editingFamilies ? "CLOSE EDIT" : "EDIT FAMILIES"',
            1,
        )[1].split("onTriggered:", 1)[0]
        self.assertIn(
            "accentColor: appSelector.editingFamilies ? Colors.red : Colors.cyan",
            edit,
        )
        self.assertNotIn("destructive: true", edit)

        browser = family.split(
            '"USE LEGACY BROWSERS" : "USE ISOLATED BROWSERS"', 1
        )[1].split("onTriggered:", 1)[0]
        self.assertIn("accentColor: Colors.magenta", browser)
        self.assertIn(
            "appSelector.isolatedBrowserToggleAllowed", browser,
        )

        move = app.split('label: "MOVE HERE"', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn("accentColor: Colors.orange", move)
        self.assertIn("appSelector.selectedAppNeedsMove()", move)

        hide = app.split('label: appSelector.selectedAppOption()', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn("? \"SHOW APP\" : \"HIDE APP\"", hide)
        self.assertIn("!appSelector.selectedAppOption().hidden", hide)
        self.assertIn("? Colors.red : Colors.cyan", hide)
        self.assertNotIn("destructive: true", hide)
        self.assertIn("appSelector.selectedAppOption().familyId", hide)

        # The actions still reach their original, guarded operations.
        self.assertIn("SocialAccountDetailsStore.saveContact(", identity)
        self.assertIn("SocialAccountDetailsStore.refresh()", identity)
        self.assertIn("SocialIdentityStore.moveAppToFamily(", app)
        self.assertIn("SocialIdentityStore.setAppHidden(", app)

    def test_magenta_header_spans_workspace_above_all_three_columns(self):
        # The workspace is already rail-excluding via settingsPage's parent
        # and anchors. A single fixed header spans it above all scroll panes.
        settings = SELECTOR.split("id: settingsPage", 1)[1].split(
            "// This entry point is always visible", 1
        )[0]
        header = settings.split("id: settingsHeader", 1)[1].split(
            "id: settingsIdentityPane", 1
        )[0]
        self.assertIn("? appSelector.right : parent.left", settings)
        self.assertIn("anchors.left: parent.left", header)
        self.assertIn("anchors.right: parent.right", header)
        self.assertIn("anchors.top: parent.top", header)
        self.assertIn('text: "USER // SETTINGS"', header)
        self.assertIn("color: Colors.magenta", header)
        self.assertIn("border.color: Colors.magenta", header)
        self.assertIn("top: settingsHeader.bottom", header)
        self.assertLess(settings.index("id: settingsHeader"),
                        settings.index("id: settingsIdentityPane"))
        self.assertEqual(SELECTOR.count('text: "USER // SETTINGS"'), 1)
        # The header no longer scrolls with the narrow Identity column.
        identity_column = settings.split("id: settingsIdentityColumn", 1)[1].split(
            'text: "IDENTITIES"', 1
        )[0]
        self.assertNotIn("USER //", identity_column)
        self.assertIn("contentHeight: settingsIdentityColumn.height + 24", settings)
        self.assertIn("contentHeight: settingsColumn.height + 24", settings)
        self.assertIn("contentHeight: settingsAppsColumn.height + 24", settings)

    def test_updated_account_button_colors_and_labels_keep_actions(self):
        identity = SELECTOR.split("id: settingsIdentityPane", 1)[1].split(
            "id: settingsEditorPane", 1
        )[0]
        picker = identity.split("label: appSelector.accountAppPickerOpen", 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn("idleFillColor: Colors.dark", picker)
        self.assertIn("Colors.magenta : Colors.orange", picker)
        self.assertIn("selected: appSelector.accountAppPickerOpen", picker)

        save = identity.split('label: appSelector.accountSelectedEntryId === ""', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn('"+ ACCOUNT NAME" : "SAVE ACCOUNT NAME"', save)
        self.assertIn("accentColor: appSelector.accountSelectedEntryId", save)
        self.assertIn("? Colors.magenta : Colors.cyan", save)
        self.assertIn("SocialAccountDetailsStore.addAccountName(", identity)
        self.assertIn("SocialAccountDetailsStore.renameAccountName(", identity)

        signin = identity.split('label: "OPEN SIGN-IN WINDOW"', 1)[1].split(
            "onTriggered:", 1
        )[0]
        self.assertIn("accentColor: Colors.orange", signin)
        self.assertIn("appSelector.browserWindowActionAllowed", signin)
        self.assertIn("appSelector.browserAccountServiceSupported(", signin)
        self.assertIn("appSelector.browserOpenSignInRequested(", identity)

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
