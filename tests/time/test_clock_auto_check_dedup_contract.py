"""Clock: read-only automatic checks reuse recent attempts and cached errors."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "services/time/TimeAutoCheckPolicy.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")
DOCK = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
COMPACT = (ROOT / "widgets/TimeSettingsCompact.qml").read_text(encoding="utf-8")


class ClockAutoCheckDedupContracts(unittest.TestCase):
    def test_dock_underline_uses_open_magenta_with_yellow_closed(self):
        underline = DOCK.split("id: timeDifferenceUnderline", 1)[1].split(
            "onRightClicked:", 1
        )[0]
        self.assertIn("visible: TimeSettings.dockTimeUnderlined(", underline)
        # Both the stroke and its drop shadow must change together.
        self.assertEqual(underline.count(
            "color: clockButton.open ? Colors.magenta : Colors.yellow"), 2)
        self.assertIn("requestedVisible: timeDifferenceUnderline.visible", underline)

    def test_one_cooldown_gates_reload_open_and_interval(self):
        self.assertIn("var MIN_AUTOMATIC_GAP_MS = 15 * 60 * 1000;", POLICY)
        self.assertIn("function canStartAutomaticCheck(", POLICY)
        self.assertIn("if (!triggerEnabled(doc, trigger)", POLICY)
        self.assertIn('trigger === "interval" && !isDue(', POLICY)
        self.assertIn("Math.max(saved, session, reference)", POLICY)
        self.assertIn("nowMs - recent >= MIN_AUTOMATIC_GAP_MS", POLICY)
        self.assertIn("referenceLastAttemptAtMs", SERVICE)
        self.assertIn("referenceLastAttemptAtMs = Date.now();", SERVICE)
        self.assertIn("AutoCheck.canStartAutomaticCheck(active, reason, now,", SERVICE)
        self.assertIn("autoLastStartedAtMs = now;", SERVICE)
        self.assertIn("AutoCheck.withAttempt(active, now)", SERVICE)
        self.assertIn('timeSettings.maybeAutoCheckTime("reload")', SERVICE)
        self.assertIn('return maybeAutoCheckTime("clock-open")', SERVICE)
        self.assertIn("onTriggered: timeSettings.maybeAutoCheckTime()", SERVICE)
        self.assertIn("if (menuOpen)", TIMEW)
        self.assertIn("TimeSettings.checkOnClockOpened();", TIMEW)

    def test_same_measurement_owner_no_privilege_escalation(self):
        schedule = SERVICE.split("function maybeAutoCheckTime(trigger) {", 1)[1].split(
            "function completeAutoReferenceIfReady()", 1
        )[0]
        self.assertIn("checkTimeAccuracy()", schedule)
        self.assertIn("referenceChecking || authSessionActive", schedule)
        self.assertIn("resyncAuthPending || resyncProcess.running", schedule)
        for forbidden in ("requestResync(", "prepareResync(", "resyncProcess.exec(",
                          "pkexec", "requestTimezone("):
            self.assertNotIn(forbidden, schedule)
        self.assertIn('"measure"', SERVICE)

    def test_details_refresh_from_result_not_extra_host_query(self):
        complete = SERVICE.split("function completeAutoReferenceIfReady() {", 1)[1].split(
            "Timer {", 1
        )[0]
        self.assertIn("referenceOffsetMs / 1000", complete)
        self.assertIn("referenceUncertaintyMs / 1000", complete)
        self.assertIn("OUT OF SYNC // OFFSET ", complete)
        self.assertIn("UNCERTAINTY ", complete)
        self.assertIn("UNAVAILABLE // ", complete)
        self.assertNotIn("checkTimeAccuracy()", complete)
        self.assertNotIn("referenceProcess.exec", complete)
        self.assertIn("TimeSettings.autoCheckResult", COMPACT)
        self.assertIn("TimeSettings.referenceMessage", COMPACT)


if __name__ == "__main__":
    unittest.main()
