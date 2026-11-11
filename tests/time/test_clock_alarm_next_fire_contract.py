"""Live-scheduling usability regression, not just timer/file existence."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
POLICY=(ROOT/"services/time/AlarmManagerPolicy.js").read_text(encoding="utf-8")
SERVICE=(ROOT/"services/time/AlarmManagerService.qml").read_text(encoding="utf-8")
PANE=(ROOT/"widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
NOTICE=(ROOT/"services/notifications/ClockAlarmNotificationProducer.qml").read_text(encoding="utf-8")

class AlarmNextFireContracts(unittest.TestCase):
    def test_one_time_date_is_next_actual_occurrence_not_blanket_tomorrow(self):
        self.assertIn("function suggestedOnceDate(hour, minute, nowMs)", POLICY)
        self.assertIn("dayAt(today, hour, minute) > nowMs", POLICY)
        self.assertIn("a.date || Policy.suggestedOnceDate(", PANE)
        self.assertIn("property bool onceDateExplicit: false", PANE)
        self.assertIn("onTextEdited: pane.onceDateExplicit = true", PANE)
        self.assertIn("function updateSuggestedOnceDate()", PANE)
        self.assertIn("onTextChanged: pane.updateSuggestedOnceDate()", PANE)
        self.assertIn("onceDateExplicit ? alarmDate.text.trim()", PANE)
        self.assertIn("Policy.suggestedOnceDate(hour, minute, Date.now())", PANE)

    def test_real_timer_test_does_not_fake_ringing_or_overwrite_existing_alarm(self):
        self.assertIn("function shortTestDueMs(nowMs)", POLICY)
        self.assertIn("function createShortTestAlarm(templateId)", SERVICE)
        self.assertIn("const created = Policy.create(document, now);", SERVICE)
        self.assertIn("const edited = Policy.update(created.document, created.id", SERVICE)
        self.assertIn('mode: "once", weekdays: []', SERVICE)
        self.assertIn("enabled: true, keepSaved: false", SERVICE)
        self.assertIn("template ? template.soundId", SERVICE)
        self.assertIn("if (!edited.ok || !saveDocument(edited.document))", SERVICE)
        self.assertIn('label: "TEST // 1-2 MIN"', PANE)
        self.assertIn("AlarmManagerService.createShortTestAlarm(selectedId)", PANE)
        self.assertIn("const r = Policy.tick(document, nowMs);", SERVICE)
        self.assertIn("alarmFired(row.id, row.ringStartedAtMs)", SERVICE)
        self.assertIn("NotificationsService.pushRich(event)", NOTICE)
        self.assertNotIn("alarmFired(", PANE)

    def test_saved_next_fire_and_diagnostics_are_visible(self):
        self.assertIn('text: "SAVED NEXT // " + AlarmManagerService.nextText(pane.selectedId)', PANE)
        self.assertIn('text: "TICK // " + (AlarmManagerService.lastSchedulerTickMs > 0', PANE)
        self.assertIn('new Date(AlarmManagerService.lastSchedulerTickMs).toLocaleTimeString()', PANE)
        self.assertIn("AlarmManagerService.audioState", PANE)
        self.assertIn('text: "STATUS // " + AlarmManagerService.feedback', PANE)
        self.assertIn("manager.lastSchedulerTickMs = manager.nowMs;", SERVICE)
        self.assertIn("function nextText(id)", SERVICE)
        self.assertIn('if (!a.enabled) return "DISABLED";', SERVICE)
        self.assertIn('if (a.ringing) return "RINGING";', SERVICE)
        self.assertNotIn("notify-send", SERVICE + PANE)
        self.assertNotIn("pkexec", SERVICE + PANE)

if __name__=="__main__":
    unittest.main()
