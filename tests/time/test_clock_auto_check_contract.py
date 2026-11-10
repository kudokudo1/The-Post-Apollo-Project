"""Clock automatic reference cadence and bounded dial security contracts.

Static checks assert that no background path may invoke privileged RESYNC.
The persisted cadence is tested separately through Node in the CI workflow.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text(encoding="utf-8")
DIAL = (ROOT / "components/SelectorDial.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/TimeAutoCheckPolicy.js").read_text(encoding="utf-8")


class ClockAutoReferenceContracts(unittest.TestCase):
    def test_cadence_is_separate_from_legacy_calibration(self):
        self.assertIn('"/time-auto-check-v1.json"', SERVICE)
        self.assertIn('"/time-settings-v1.json"', SERVICE)
        self.assertIn('import "TimeAutoCheckPolicy.js" as AutoCheck', SERVICE)
        self.assertIn('atomicWrites: true', SERVICE)
        self.assertIn('enabled: false, intervalHours: 6', POLICY)
        self.assertIn("var MAX_HOURS = 168;", POLICY)
        self.assertIn("var MIN_HOURS = 1;", POLICY)

    def test_background_only_measurement_no_privileged_actuation(self):
        schedule = SERVICE.split("function maybeAutoCheckTime() {", 1)[1].split(
            "function completeAutoReferenceIfReady()", 1
        )[0]
        self.assertIn("AutoCheck.isDue(", schedule)
        self.assertIn("checkTimeAccuracy()", schedule)
        self.assertIn("autoLastStartedAtMs = now", schedule)
        self.assertNotIn("requestResync(", schedule)
        self.assertNotIn("prepareResync(", schedule)
        self.assertNotIn("resyncProcess.exec(", schedule)
        self.assertNotIn("pkexec", schedule)
        self.assertIn('"measure"', SERVICE)
        self.assertIn('if (!resyncConfirmRequired', SERVICE)
        self.assertIn('resyncAuthPending = true', SERVICE)

    def test_background_timer_is_bounded_and_skips_conflicts(self):
        self.assertIn("interval: 60 * 1000", SERVICE)
        self.assertIn("repeat: true", SERVICE)
        self.assertIn("referenceChecking || authSessionActive", SERVICE)
        self.assertIn("resyncProcess.running", SERVICE)
        self.assertIn("autoCheckInFlight", SERVICE)
        self.assertIn("autoCheckResultSeen", SERVICE)
        self.assertIn("autoCheckExited", SERVICE)
        self.assertIn("autoResultDeadline", SERVICE)

    def test_radio_style_dial_is_bounded_hourly_with_true_day_marks(self):
        self.assertIn("SelectorDial {", PANE)
        self.assertIn('selectorMode: "continuous"', PANE)
        self.assertIn("minimumValue: 1", PANE)
        self.assertIn("maximumValue: 168", PANE)
        self.assertIn("valueStep: 1", PANE)
        self.assertIn("valueDecimals: 0", PANE)
        self.assertIn("snapContinuousToStep: true", PANE)
        self.assertIn(
            "numericReferenceValues: [1, 24, 48, 72, 96, 120, 144, 168]",
            PANE,
        )
        self.assertIn("property bool snapContinuousToStep: false", DIAL)
        self.assertIn("dialRoot.continuousDragRawAngle", DIAL)
        self.assertIn("dialRoot.finishFreePosition()", DIAL)
        self.assertIn("angleForValue(Number(numericReferenceValues[index]))", DIAL)

    def test_shared_dial_labels_are_readable_by_default(self):
        # Previous defaults were 6/7px markings and an 8px readout.
        # The defaults affect Radio and Git as well as Clock.
        self.assertIn("property int numericLabelPixelSize: 10", DIAL)
        self.assertIn("property int textLabelPixelSize: 8", DIAL)
        self.assertIn("property int readoutPixelSize: 11", DIAL)
        self.assertIn("dialRoot.numericLabelPixelSize", DIAL)
        self.assertIn("dialRoot.textLabelPixelSize", DIAL)
        self.assertIn("font.pixelSize: dialRoot.readoutPixelSize", DIAL)
        self.assertNotIn("font.pixelSize: dialRoot.optionCount() > 4 ? 6 : 7", DIAL)

    def test_clock_dial_captures_wheel_and_drag_without_page_flick(self):
        # Both nested mouse areas must block their Flickable ancestor from
        # stealing a click or rotary drag halfway through its gesture.
        self.assertIn("id: rotaryMouse", DIAL)
        self.assertGreaterEqual(DIAL.count("preventStealing: true"), 2)
        self.assertIn("WheelHandler {", DIAL)
        self.assertIn("target: null", DIAL)
        self.assertIn("PointerDevice.Mouse | PointerDevice.TouchPad", DIAL)
        self.assertIn("event.accepted = true;", DIAL)
        self.assertIn("dialRoot.stepIndex(event.angleDelta.y > 0 ? -1 : 1);", DIAL)
        self.assertIn("readonly property bool pointerOverDial:", DIAL)
        self.assertIn("id: dialHoverHandler", DIAL)
        self.assertIn("interactive: !(pane.showAutoTimeCheck && autoCheckDial.interactive", PANE)
        self.assertIn("autoCheckDial.pointerOverDial || autoCheckDial.dragging", PANE)
        # Approved bounds and nonwrapping behavior remain intact.
        self.assertIn("minimumValue: 1", PANE)
        self.assertIn("maximumValue: 168", PANE)
        self.assertIn("snapContinuousToStep: true", PANE)
        self.assertIn("function steppedValue(value)", DIAL)
        self.assertIn("dialRoot.finishFreePosition()", DIAL)

    def test_six_hour_stops_keep_endpoints_and_day_numbers(self):
        self.assertIn("numericDetentInterval: 6", PANE)
        self.assertIn("numericDetentOrigin: 0", PANE)
        self.assertIn("showNumericDetentTicks: true", PANE)
        self.assertIn("6H DETENTS // NO WRAP", PANE)
        self.assertIn("property real numericDetentInterval: 0", DIAL)
        self.assertIn("property bool showNumericDetentTicks: false", DIAL)
        self.assertIn("numericDetentOrigin", DIAL)
        self.assertIn("numericDetentInterval", DIAL)
        self.assertIn("Math.round((clamped - origin) / step)", DIAL)
        self.assertIn("Math.max(minimumValue, Math.min(maximumValue, upper))", DIAL)
        self.assertIn("Math.floor(", DIAL)
        self.assertIn("numericReferenceValues.indexOf(numericValue) < 0", DIAL)
        self.assertIn("color: detentTick.active ? Colors.orange : dialRoot.labelColor", DIAL)
        # The ratchet retains the special 1H endpoint, then 6H multiples.
        stops = [1] + list(range(6, 169, 6))
        self.assertEqual(stops[:4], [1, 6, 12, 18])
        self.assertEqual(stops[-1], 168)
        self.assertEqual(len(stops), 29)
        self.assertTrue(all(stops[i] < stops[i + 1] for i in range(len(stops) - 1)))
        for day in range(24, 169, 24):
            self.assertIn(day, stops)

    def test_numeric_markers_react_to_dial_angle(self):
        self.assertIn("function isOptionActive(index) {", DIAL)
        self.assertIn("Math.abs(visualAngle - angleForIndex(index)) <= 3.5", DIAL)
        self.assertIn('selectorMode === "continuous"', DIAL)
        self.assertIn("Colors.orange : dialRoot.markerColor", DIAL)
        self.assertIn("shadowColor: dialRoot.isOptionActive(optionMark.index)", DIAL)
        self.assertIn("shadowOpacity: dialRoot.optionGlowStrength(optionMark.index)", DIAL)
        self.assertIn("if (isOptionActive(index))", DIAL)

    def test_operator_controls_and_privacy_remain_visible(self):
        self.assertIn("setAutoCheckIntervalHours(", PANE)
        self.assertIn("setAutoCheckEnabled(", PANE)
        self.assertIn('"AUTO CHECK ON" : "AUTO CHECK OFF"', PANE)
        self.assertIn("One-shot RESYNC still requires confirmation and Polkit.", PANE)
        self.assertIn("They may see your IP.", PANE)
        self.assertIn("OUT OF SYNC // CONFIRM RESYNC MANUALLY", SERVICE)


if __name__ == "__main__":
    unittest.main()
