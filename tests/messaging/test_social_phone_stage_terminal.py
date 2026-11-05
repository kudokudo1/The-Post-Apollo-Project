"""PHONE-only terminal viewport shares Weather's verified cutout pattern."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHONE = ROOT / "widgets/messanger/PhonePane.qml"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
WEATHER = ROOT / "widgets/weather/StationChassisCutout.qml"


class PhoneStageLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = PHONE.read_text()
        cls.social = SOCIAL.read_text()
        cls.weather = WEATHER.read_text()

    def test_phone_uses_existing_station_cutout_not_new_global_stage(self):
        self.assertIn('import "../weather" as WeatherStage', self.phone)
        self.assertIn('WeatherStage.StationChassisCutout {', self.phone)
        self.assertIn('id: stageProcess', self.phone)
        self.assertIn('PhoneStageDirector.py', self.phone)
        self.assertIn('"--sync"', self.phone)
        self.assertIn('"--close"', self.phone)
        self.assertIn('stageHoleActive', self.phone)
        self.assertIn('stageState === "ALIGNED"', self.phone)
        self.assertIn('stageHoleValid', self.phone)
        self.assertIn('holeWidth: phonePane.stageHoleWidth', self.phone)
        self.assertIn('holeHeight: phonePane.stageHoleHeight', self.phone)
        self.assertIn('panelOpacity: 1', self.phone)
        self.assertIn('holeWidth > 0', self.weather)
        self.assertNotIn('StationTerminal {', self.phone)

    def test_social_float_mask_removes_only_verified_phone_bay(self):
        self.assertIn('intersection: Intersection.Subtract', self.social)
        self.assertIn('x: messagingWindow.appSelectorWidth + phonePane.stageHoleX',
                      self.social)
        self.assertIn('y: phonePane.stageHoleY', self.social)
        self.assertIn(
            'width: phonePane.stageHoleActive ? phonePane.stageHoleWidth : 0',
            self.social)
        self.assertIn(
            'height: phonePane.stageHoleActive ? phonePane.stageHoleHeight : 0',
            self.social)
        self.assertIn('fillVisible: !phonePane.stageHoleActive',
                      self.social)
        self.assertIn('fillOpacity: 0.20', self.social)
        self.assertIn('id: phonePane', self.social)
        self.assertIn('title: "QS_SOCIAL_MENU"', self.social)

    def test_stage_is_never_opened_just_by_selecting_phone(self):
        self.assertIn('stageWanted = false;', self.phone)
        self.assertIn('if (!visible) closeStagedSetup();', self.phone)
        self.assertIn('if (selectedSection !== "DEVICE") closeStagedSetup();',
                      self.phone)
        self.assertIn('result.stageCandidate && result.target === "iphone"',
                      self.phone)
        self.assertIn('result.status === "OPEN_REQUESTED"', self.phone)
        self.assertIn('result.verifiedHole === true', self.phone)
        self.assertIn('phonePane.stageState = "ALIGNED"', self.phone)
        self.assertIn('stagePollCount > 40', self.phone)

    def test_terminal_appears_below_phone_controls_not_over_contact_list(self):
        self.assertIn('phoneChatFeed.x + 10', self.phone)
        self.assertIn('phoneChatFeed.y + stageBayTop', self.phone)
        self.assertIn('phoneChatFeed.height - stageBayTop - 12', self.phone)
        self.assertNotIn('setupHeader.height + setupColumn.implicitHeight + 24',
                         self.phone)
        self.assertIn('stageHoleWidth >= 200 && stageHoleHeight >= 120', self.phone)
        self.assertIn('stageHoleX + stageHoleWidth <= width', self.phone)
        self.assertIn('stageHoleY + stageHoleHeight <= height', self.phone)
        self.assertIn('height: 45 // Stable bay position', self.phone)
        self.assertIn('color: stageHoleActive ? "transparent" : Colors.black',
                      self.phone)
        self.assertIn('color: phonePane.stageHoleActive ? "transparent" : Colors.black',
                      self.phone)
        self.assertIn('visible: phonePane.selectedSection !== "DEVICE"', self.phone)
        self.assertIn('    ContactList {', self.phone)
        self.assertIn('    ChatFeed {', self.phone)
        self.assertIn('sendEnabled: false', self.phone)
        self.assertIn('conversations: []', self.phone)
        self.assertIn('messages: []', self.phone)

    def test_terminal_bay_is_independent_of_setup_content_height(self):
        self.assertIn('readonly property int stageBayTop:', self.phone)
        self.assertIn('setupHeader.height + 112', self.phone)
        self.assertIn('phoneChatFeed.height * 0.43', self.phone)
        self.assertIn('phoneChatFeed.y + stageBayTop', self.phone)
        self.assertIn('phoneChatFeed.height - stageBayTop - 12', self.phone)
        self.assertNotIn('stageHoleY: Math.round(\\n        phoneChatFeed.y + setupHeader.height + setupColumn.implicitHeight', self.phone)
        self.assertIn('phonePane.stageWanted && phonePane.stageHoleValid',
                      self.phone)
        self.assertIn('setupOverlay.height -', self.phone)
        self.assertIn('phonePane.stageBayTop + 8', self.phone)
        self.assertIn('clip: true', self.phone)
        self.assertIn('contentHeight: setupColumn.implicitHeight + 24',
                      self.phone)
        self.assertIn('stageHoleActive', self.phone)
        self.assertIn('intersection: Intersection.Subtract', self.social)

    def test_representative_panel_sizes_allow_lower_bay_without_scrolling_content(self):
        # Mirrors the source's 43% start plus a header safety minimum.
        for height in (400, 580, 700, 950):
            with self.subTest(feed_height=height):
                bay_top = max(60 + 112, round(height * 0.43))
                hole_height = round(height - bay_top - 12)
                scroll_height = bay_top - 8 - 60
                self.assertGreaterEqual(hole_height, 120)
                self.assertGreaterEqual(scroll_height, 100)
                self.assertLess(bay_top + hole_height, height)
        # Small windows are explicitly unsupported; don't render a fake hole.
        h = 280
        self.assertLess(h - max(60 + 112, round(h * 0.43)) - 12, 120)
        self.assertIn('if (!stageHoleValid) {', self.phone)
        self.assertIn('stageState = "UNAVAILABLE";', self.phone)

    def test_return_action_is_pinned_in_header_not_buried_below_scroll(self):
        start = self.phone.index('id: setupHeader')
        stop = self.phone.index('id: setupScroll', start)
        header = self.phone[start:stop]
        self.assertIn('id: stagedExitAction', header)
        self.assertIn('visible: phonePane.stageWanted', header)
        self.assertIn('? "RETURN TO PHONE" : "CLOSE SETUP"', header)
        self.assertIn('onTriggered: phonePane.closeStagedSetup()', header)
        self.assertEqual(self.phone.count('id: stagedExitAction'), 1)
        self.assertEqual(self.phone.count('onTriggered: phonePane.closeStagedSetup()'), 1)
        self.assertIn('if (installer) {', self.phone)

    def test_no_weather_host_or_shared_router_modifications(self):
        self.assertIn('WeatherStage.StationChassisCutout {', self.phone)
        self.assertNotIn('terminalView.openTerminal', self.phone)
        self.assertNotIn('messageRouter.sendMessage', self.phone)
        self.assertNotIn('SocialIdentityStore.', self.phone)
        self.assertIn('fillVisible: !phonePane.stageHoleActive', self.social)


if __name__ == "__main__":
    unittest.main()
