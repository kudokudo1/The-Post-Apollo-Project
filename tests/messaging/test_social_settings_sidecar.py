"""Offline source contracts for the Social USER // SETTINGS wide sidecar.

The existing Social FloatingWindow must own this UI. No additional toplevel,
Sway geometry resize/move, provider session changes or desktop activation
may follow from this source-only feature. Live compositor verification is
still required to certify stacking, input and focus.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
SELECTOR=(ROOT/"widgets/messanger/AppSelector.qml").read_text()
HOST=(ROOT/"widgets/messanger/MessagingW.qml").read_text()
FRAME=(ROOT/"components/WindowPanelFrame.qml").read_text()
SURFACE=(ROOT/"components/SurfaceFrame.qml").read_text()


class SocialSettingsSidecarContracts(unittest.TestCase):
    def test_existing_window_and_stable_geometry_dimensions(self):
        self.assertEqual(HOST.count("FloatingWindow {"), 1)
        self.assertIn('title: "QS_SOCIAL_MENU"', HOST)
        self.assertIn('width: messagingWindow.sharedPanelWidth', HOST)
        self.assertIn('height: messagingWindow.sharedPanelHeight', HOST)
        self.assertIn('property int appSelectorWidth: 110', HOST)
        self.assertIn('property int contactListWidth: 200', HOST)
        self.assertIn('property int settingsSidecarPreferredWidth: 400', HOST)
        self.assertIn('readonly property int settingsSidecarWidth:', HOST)
        self.assertIn('sharedPanelWidth - appSelectorWidth', HOST)
        self.assertIn('settingsOverlayParent: messagingContent.contentItem', HOST)
        self.assertIn('settingsOverlayWidth: messagingWindow.settingsSidecarWidth', HOST)
        self.assertIn('readonly property Item contentItem: surface.contentItem', FRAME)
        self.assertIn('default property alias contentData: surface.contentData', FRAME)
        self.assertIn('default property alias contentData: contentHost.data', SURFACE)
        self.assertIn('readonly property Item contentItem: contentHost', SURFACE)

    def test_sidecar_is_a_sibling_not_a_second_window(self):
        self.assertIn('property Item settingsOverlayParent: null', SELECTOR)
        self.assertIn('property int settingsOverlayWidth: 400', SELECTOR)
        self.assertIn('id: settingsPage', SELECTOR)
        self.assertIn('parent: appSelector.settingsOverlayParent', SELECTOR)
        self.assertIn('? appSelector.settingsOverlayParent : appSelector', SELECTOR)
        self.assertIn('left: appSelector.settingsOverlayParent ? appSelector.right : parent.left',
                      SELECTOR)
        self.assertIn('bottom: appSelector.settingsOverlayParent ? parent.bottom', SELECTOR)
        self.assertIn('Math.min(appSelector.settingsOverlayWidth', SELECTOR)
        self.assertIn('parent.width - appSelector.width', SELECTOR)
        self.assertIn('z: 8', SELECTOR)
        self.assertIn('color: Colors.black', SELECTOR)
        self.assertIn('border.color: Colors.cyan', SELECTOR)
        self.assertIn('visible: appSelector.settingsOpen', SELECTOR)
        self.assertNotIn('FloatingWindow {', SELECTOR)
        self.assertNotIn('PanelWindow {', SELECTOR)
        self.assertNotIn('PopupWindow {', SELECTOR)

    def test_input_mask_is_bounded_and_restored(self):
        mask=HOST.split('id: socialWindow',1)[1].split('// GEOMETRY HELPERS',1)[0]
        self.assertEqual(mask.count('mask: Region {'), 1)
        self.assertIn('width: messagingWindow.menuOpen', mask)
        self.assertIn('? (appSelector.settingsOpen',mask)
        self.assertIn('Math.min(socialWindow.width,',mask)
        self.assertIn('messagingWindow.appSelectorWidth',mask)
        self.assertIn('messagingWindow.settingsSidecarWidth',mask)
        self.assertIn(
            'messagingWindow.externalSelected ? messagingWindow.appSelectorWidth : socialWindow.width',
            mask)
        self.assertIn(': 0',mask)  # Closed menu is fully click-through.
        # Width never exceeds the shared window, including minimum-sized cases.
        for shared in (311, 410, 510, 1210):
            sidecar=max(1,min(400, shared-110))
            expanded=min(shared, 110+sidecar)
            self.assertGreaterEqual(expanded,110)
            self.assertLessEqual(expanded,shared)
            self.assertEqual(110, min(shared, 110))  # original external mask

    def test_background_launcher_is_visible_but_not_actionable(self):
        self.assertIn('visible: !appSelector.settingsOpen || !!appSelector.settingsOverlayParent',
                      SELECTOR)
        self.assertIn('enabled: !appSelector.settingsOpen', SELECTOR)
        self.assertIn('interactive: visible && appSelector.identitySnapshot.writable', SELECTOR)
        self.assertIn('&& !appSelector.settingsOpen', SELECTOR)
        self.assertIn('appSelector.appActivated(buttonContainer.modelData.serviceIndex);',
                      SELECTOR)
        self.assertIn('label: "USER // SETTINGS"', SELECTOR)
        self.assertEqual(SELECTOR.count('id: settingsFooter'),1)
        self.assertIn('onTriggered: appSelector.settingsOpen = !appSelector.settingsOpen',
                      SELECTOR)
        self.assertIn('if (appSelector.settingsOpen) {', HOST)  # block Tab/Enter.

    def test_external_stacking_is_focus_only_and_reversible(self):
        self.assertIn('socialWindow.requestActivate()',HOST)
        self.assertIn('discordRaiseDelay.stop();',HOST)
        self.assertIn('xRaiseDelay.stop();',HOST)
        self.assertIn('|| appSelector.settingsOpen)',HOST)
        self.assertIn('messagingWindow.raiseDiscord();', HOST)
        self.assertIn('messagingWindow.raiseX();',HOST)
        self.assertIn('appSelector.settingsOpen = false;',HOST)
        # Session storage, account switching and platform helpers are not edited.
        self.assertNotIn('SocialIdentityStore',HOST)
        self.assertIn('providerDesktopManaged: false',HOST)
        self.assertIn('function syncDiscordGeometry(focusWindow)',HOST)
        self.assertIn('function syncXGeometry(focusWindow)',HOST)


if __name__=="__main__":
    unittest.main()
