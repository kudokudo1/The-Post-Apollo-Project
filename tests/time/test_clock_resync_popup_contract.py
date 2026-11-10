"""TimeW dynamic heading and non-navigating host-resync popover contracts.

Read-only source checks: no host time, timezone, NTP, RTC, Polkit or desktop
session is changed by this test suite.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
POPUP = (ROOT / "widgets/TimeResyncPopup.qml").read_text(encoding="utf-8")
SETTINGS = (ROOT / "widgets/TimeSettingsPane.qml").read_text(encoding="utf-8")
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")


class TimeResyncPopupContracts(unittest.TestCase):
    def test_heading_tracks_active_mode_without_changing_tab_names(self):
        for mode, name in (
            ("clock", "CLOCK"), ("calc", "CALC"), ("tools", "TOOLS"),
            ("machine", "MACHINE"), ("planned", "ANGEL"),
            ("settings", "SETTINGS"),
        ):
            self.assertIn(f'id: "{mode}", name: "{name}"', TIMEW)
        self.assertIn('selectedMode === "calc" ? "CALCULATOR" : selectedName', TIMEW)
        header = TIMEW.split("id: header", 1)[1].split(
            "id: stateIndicator", 1)[0]
        self.assertIn('text: "TIME // " + timew.headerModeName', header)
        self.assertNotIn('text: "TIME // W"', TIMEW)
        self.assertIn("fontSizeMode: Text.HorizontalFit", header)

    def test_resync_trigger_opens_in_place_with_no_actuation(self):
        sync = TIMEW.split("id: syncButton", 1)[1].split(
            "id: closeButton", 1)[0]
        self.assertIn("onLeftClicked: timew.toggleResyncPopup()", sync)
        self.assertNotIn("chooseMode(", sync)
        self.assertNotIn("requestResync(", sync)
        self.assertNotIn("prepareResync(", sync)
        toggle = TIMEW.split("function toggleResyncPopup() {", 1)[1].split(
            "function toggle() {", 1)[0]
        self.assertIn("resyncPopupOpen = true", toggle)
        self.assertIn("TimeSettings.prepareResync()", toggle)
        self.assertNotIn("TimeSettings.requestResync()", toggle)
        self.assertNotIn("chooseMode(", toggle)
        self.assertIn("resyncConfirmRequired = true", SERVICE)
        self.assertIn("if (!resyncConfirmRequired", SERVICE)

    def test_popup_uses_existing_confirm_and_readonly_actions(self):
        for label, action in (
            ('label: "CONFIRM RESYNC"', "TimeSettings.requestResync()"),
            ('label: "CANCEL"', "TimeSettings.cancelResync()"),
            ('label: "DIAGNOSE"', "TimeSettings.diagnoseResync()"),
            ('label: "CHECK TIME"', "TimeSettings.checkTimeAccuracy()"),
        ):
            self.assertIn(label, POPUP)
            self.assertIn(action, POPUP)
        self.assertIn("TimeSettings.resyncConfirmRequired", POPUP)
        self.assertIn("TimeSettings.resyncAuthPending", POPUP)
        self.assertIn("TimeSettings.authSessionActive", POPUP)
        self.assertIn("TimeSettings.referenceChecking", POPUP)
        self.assertIn("TimeSettings.diagnosticBusy", POPUP)
        self.assertIn("TimeSettings.resyncMessage", POPUP)
        self.assertIn("TimeSettings.diagnosticMessage", POPUP)
        self.assertIn("TimeSettings.referenceStatus", POPUP)
        self.assertIn("CONFIGURED TIME SERVERS", POPUP)
        self.assertIn("YOUR IP IS VISIBLE", POPUP)
        self.assertNotIn("Process {", POPUP)
        self.assertNotIn("resyncProcess.exec", POPUP)
        self.assertNotIn("pkexec", POPUP)
        self.assertNotIn("TimeSettings.requestResync()", TIMEW)

    def test_popover_stays_above_page_and_dismisses_safely(self):
        self.assertIn("TimeResyncPopup {", TIMEW)
        self.assertIn("z: 100", TIMEW)
        self.assertIn("syncButton.mapToItem(timewFrame, 0, 0)", TIMEW)
        self.assertIn("resyncPopup.mapToItem(timewFrame, 0, 0)", TIMEW)
        self.assertIn("visible: timew.menuOpen && timew.resyncPopupOpen", TIMEW)
        self.assertIn("onCloseRequested: timew.dismissResyncPopup()", TIMEW)
        self.assertIn("if (!onTrigger && !onPopup)", TIMEW)
        self.assertIn("timew.dismissResyncPopup()", TIMEW)
        self.assertIn("if (resyncPopupOpen)", TIMEW)
        self.assertIn("TimeSettings.cancelResync();", TIMEW)
        self.assertIn("width: 308", POPUP)
        self.assertIn("height: 320", POPUP)

    def test_popup_is_right_anchored_beneath_both_header_buttons(self):
        placement = TIMEW.split("TimeResyncPopup {", 1)[1].split(
            "onCloseRequested:", 1)[0]
        self.assertIn("const close = closeButton.mapToItem(timewFrame, 0, 0);",
                      placement)
        self.assertIn("const rightEdge = close.x + closeButton.width;", placement)
        self.assertIn("rightEdge - width", placement)
        self.assertIn("timewFrame.width - width - 8", placement)
        self.assertIn("Math.max(8, Math.min(", placement)
        self.assertIn("y: closeButton.mapToItem(timewFrame, 0, 0).y", placement)
        self.assertIn("+ closeButton.height + 7", placement)
        self.assertNotIn("at.x + syncButton.width - width", placement)
        # The outside-click detector still maps the popup's actual bounds.
        self.assertIn("resyncPopup.mapToItem(timewFrame, 0, 0)", TIMEW)
        self.assertIn("if (!onTrigger && !onPopup)", TIMEW)

    def test_popup_owns_glowing_border_and_background(self):
        self.assertIn('import "../components"', POPUP)
        self.assertIn("WindowPanelFrame {", POPUP)
        self.assertIn("fillColor: Colors.black", POPUP)
        self.assertIn("fillOpacity: 1.0", POPUP)
        self.assertIn("borderColor: Colors.yellow", POPUP)
        self.assertIn("borderWidth: 1", POPUP)
        self.assertIn("glowVisible: true", POPUP)
        self.assertIn("glowColor: Colors.yellow", POPUP)
        self.assertIn("closeGlowSpread: 6", POPUP)
        self.assertIn("closeGlowOpacity: 0.46", POPUP)
        self.assertIn("wideGlowSpread: 13", POPUP)
        self.assertIn("wideGlowOpacity: 0.18", POPUP)
        self.assertIn("clipContent: true", POPUP)
        self.assertNotIn("RectangularShadow {", POPUP)
        # No new subprocesses or clock writers may enter a visual-only patch.
        self.assertNotIn("Process {", POPUP)
        self.assertNotIn("pkexec", POPUP)

    def test_original_settings_and_host_security_owner_unchanged(self):
        self.assertIn('label: "CONFIRM RESYNC"', SETTINGS)
        self.assertIn("TimeSettings.requestResync()", SETTINGS)
        self.assertIn("TimeSettings.diagnoseResync()", SETTINGS)
        self.assertIn("TimeSettings.checkTimeAccuracy()", SETTINGS)
        self.assertIn("resyncAuthPending = true", SERVICE)
        self.assertIn('resyncStatus = "auth-preparing"', SERVICE)
        self.assertIn("resyncProcess.exec([", SERVICE)


if __name__ == "__main__":
    unittest.main()
