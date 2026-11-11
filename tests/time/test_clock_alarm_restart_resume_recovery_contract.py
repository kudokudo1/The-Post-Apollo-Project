"""Clock restart/resume policy: no duplicate rings, bounded missed-day recovery."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
POLICY=(ROOT/"services/time/AlarmManagerPolicy.js").read_text(encoding="utf-8")
SERVICE=(ROOT/"services/time/AlarmManagerService.qml").read_text(encoding="utf-8")
PANE=(ROOT/"widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
POPUP=(ROOT/"services/notifications/ClockAlarmNotificationProducer.qml").read_text(encoding="utf-8")


class ClockRecoveryContracts(unittest.TestCase):
    def test_policy_persists_exact_arming_and_processed_due_cursors(self):
        for item in ("armedAtMs", "lastProcessedDueMs"):
            self.assertIn(item, POLICY)
        self.assertIn("function latestUnprocessedWeeklyDue(a, nowMs, pausedThroughDate)", POLICY)
        self.assertIn("a.lastFiredDay = dayKey(previous);", POLICY)
        self.assertIn("nowMs - previous <= MAX_LATE_MS", POLICY)
        self.assertIn("var yesterday = dateOffset(nowMs, -1);", POLICY)
        self.assertIn("var daysBack = 1; daysBack <= 7; daysBack++", POLICY)
        self.assertIn("a.lastProcessedDueMs = previous;", POLICY)
        self.assertIn('a.lastEventKind = "missed";', POLICY)
        self.assertIn("a.armedAtMs = nowMs;", POLICY)
        self.assertIn("const pausedThroughDate = a.pausedUntilDate;", POLICY)
        self.assertIn("if (a.armedAtMs > nowMs && !a.ringing) return;", POLICY)

    def test_clock_samples_wall_time_during_file_restore_and_timer_callback(self):
        self.assertIn("const prior = lastSchedulerTickMs;", SERVICE)
        self.assertIn("manager.nowMs = Date.now();", SERVICE)
        self.assertIn("manager.lastSchedulerTickMs = manager.nowMs;", SERVICE)
        self.assertIn("const resumedAfterGap = gapMs > 5000;", SERVICE)
        self.assertIn("const r = Policy.tick(document, manager.nowMs);", SERVICE)
        self.assertIn("onTriggered: manager.checkDue()", SERVICE)
        self.assertIn("Qt.callLater(manager.checkDue);", SERVICE)
        self.assertIn("Qt.callLater(manager.announceRestoredRinging);", SERVICE)
        self.assertIn("property bool recoveryNoteworthy: false", SERVICE)
        self.assertIn('lastRecoveryText = (restarting ? "RESTART" : "TIMER GAP")', SERVICE)

    def test_popup_policy_and_operator_stop_remain_unchanged(self):
        self.assertIn("alarmFired(alarmId, startedMs)", SERVICE)
        self.assertIn("reportRingOccurrence(row.id, row.ringStartedAtMs)", SERVICE)
        self.assertIn("function stopOccurrence(id, startedMs)", SERVICE)
        self.assertIn("function snoozeOccurrence(id, startedMs)", SERVICE)
        self.assertIn("NotificationsService.pushRich(event);", POPUP)
        self.assertIn("id: alarmList", PANE)
        self.assertIn("clip: true", PANE)
        self.assertIn("visible: AlarmManagerService.recoveryNoteworthy", PANE)
        self.assertIn('text: "RECOVERY // " + AlarmManagerService.lastRecoveryText', PANE)
        self.assertIn("id: listRail", PANE)
        self.assertNotIn("notify-send", SERVICE)
        self.assertNotIn("systemctl", SERVICE)

if __name__ == "__main__":
    unittest.main()
