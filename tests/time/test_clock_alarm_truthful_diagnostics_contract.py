"""Prevent fake 'AUDIO // PLAYING' and expose notification intake receipts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/AlarmManagerService.qml").read_text(encoding="utf-8")
AUDIO = (ROOT / "services/time/AlarmAudioV2.qml").read_text(encoding="utf-8")
PRODUCER = (ROOT / "services/notifications/ClockAlarmNotificationProducer.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
NOTIFICATIONS = (ROOT / "services/notifications/NotificationsService.qml").read_text(encoding="utf-8")

class ClockAlarmTruthContracts(unittest.TestCase):
    def test_stopped_audio_is_not_reported_as_playing(self):
        self.assertIn('property string audioState: "IDLE"', SERVICE)
        self.assertIn('if (sourceId === "") {', SERVICE)
        self.assertIn('audioLoader.active = false;', SERVICE)
        self.assertIn('audioState = "IDLE";', SERVICE)
        self.assertIn('audioState = "QT STARTING";', SERVICE)
        self.assertIn('manager.audioState = "QT PLAYING";', SERVICE)
        self.assertIn('function onStopped()', SERVICE)
        self.assertIn('manager.audioState = "QT STOPPED";', SERVICE)
        self.assertIn("signal stopped()", AUDIO)
        self.assertIn("else\n                audio.stopped();", AUDIO)
        self.assertNotIn('manager.audioState = "PLAYING";', SERVICE)

    def test_actual_alarm_event_diagnostics_separate_from_audio_preview(self):
        self.assertIn('property int lastFiredAlarmId: 0', SERVICE)
        self.assertIn('property double lastFiredAtMs: 0', SERVICE)
        self.assertIn('property string notificationOutcome: "NO RING YET"', SERVICE)
        self.assertIn('function reportRingOccurrence(alarmId, startedMs)', SERVICE)
        self.assertIn('alarmFired(alarmId, startedMs);', SERVICE)
        self.assertIn('reportRingOccurrence(row.id, row.ringStartedAtMs);', SERVICE)
        self.assertIn('reportRingOccurrence(a.id, a.ringStartedAtMs);', SERVICE)
        self.assertIn('function reportNotificationOutcome(alarmId, startedMs, outcome)', SERVICE)
        self.assertIn('alarmId !== lastFiredAlarmId || startedMs !== lastFiredAtMs', SERVICE)
        self.assertIn('text: "RING #" + AlarmManagerService.lastFiredAlarmId', PANE)
        self.assertIn('AlarmManagerService.notificationOutcome', PANE)

    def test_notification_receipt_observes_existing_policy_not_override(self):
        self.assertIn('function containsId(model, eventId)', PRODUCER)
        self.assertIn('NotificationsService.pushRich(event);', PRODUCER)
        self.assertIn('NotificationsService.activeNotifications', PRODUCER)
        self.assertIn('NotificationsService.notifications', PRODUCER)
        self.assertIn('NotificationsService.policyReady', PRODUCER)
        self.assertIn('NotificationsService.shouldBlockNotification(event)', PRODUCER)
        for result in ('"POPUP QUEUED"', '"HISTORY ONLY"', '"ALREADY IN HISTORY"',
                       '"BLOCKED BY NOTIFICATION POLICY"', '"NOTIFICATION POLICY ERROR"',
                       '"INVALID EVENT PAYLOAD"', '"NOTIFICATION BRIDGE ERROR"'):
            self.assertIn(result, PRODUCER)
        self.assertIn('AlarmManagerService.reportNotificationOutcome(', PRODUCER)
        self.assertIn('if (policyStatus === "parse-error" || policyStatus === "load-error"', NOTIFICATIONS)
        self.assertNotIn('sourcePolicies.append', PRODUCER)
        self.assertNotIn('NotificationsService.setDnd(', PRODUCER)
        self.assertNotIn('NotificationsService.setBlock(', PRODUCER)

    def test_compact_tick_does_not_truncate_output_state_with_timezone_name(self):
        self.assertIn('Qt.formatDateTime(', PANE)
        self.assertIn('"h:mm:ss AP"', PANE)
        self.assertNotIn('new Date(AlarmManagerService.lastSchedulerTickMs).toLocaleTimeString()', PANE)
        self.assertIn('AlarmManagerService.audioState', PANE)
        self.assertIn('visible: AlarmManagerService.lastFiredAlarmId > 0', PANE)
        self.assertIn('height: Math.max(0, pane.height - y)', PANE)
        self.assertIn('id: alarmList', PANE)

if __name__ == "__main__":
    unittest.main()
