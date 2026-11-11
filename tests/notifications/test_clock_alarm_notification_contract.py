"""Clock alarm -> Notifications: exact resource routing without policy bypass."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/AlarmManagerService.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
PRODUCER = (ROOT / "services/notifications/ClockAlarmNotificationProducer.qml").read_text()
POLICY = (ROOT / "services/notifications/ClockAlarmNotificationPolicy.js").read_text()
SCOPE = (ROOT / "services/notifications/NotificationScopePolicy.js").read_text()
NOTICE = (ROOT / "services/notifications/NotificationsService.qml").read_text()
ROUTE = (ROOT / "services/notifications/ApolloNotificationRoute.js").read_text()
MODULE = (ROOT / "services/notifications/qmldir").read_text()
POPUP = (ROOT / "modules/Notifications.qml").read_text()


class ClockAlarmNotifications(unittest.TestCase):
    def test_existing_scheduler_only_emits_real_ring_occurrences(self):
        self.assertIn("signal alarmFired(int alarmId, double startedMs)", SERVICE)
        self.assertIn("if (r.started.length)", SERVICE)
        self.assertIn("alarmFired(row.id, row.ringStartedAtMs)", SERVICE)
        self.assertIn("function announceRestoredRinging()", SERVICE)
        self.assertIn("Qt.callLater(manager.announceRestoredRinging)", SERVICE)
        self.assertNotIn("NotificationsService.pushRich", SERVICE)
        self.assertNotIn("notify-send", SERVICE + PRODUCER)

    def test_single_producer_uses_existing_policy_instead_of_new_daemon(self):
        self.assertIn("ClockAlarmNotificationProducer 1.0 ClockAlarmNotificationProducer.qml", MODULE)
        self.assertEqual(SHELL.count("ClockAlarmNotificationProducer {}"), 1)
        self.assertIn("target: AlarmManagerService", PRODUCER)
        self.assertIn("producer.deliver(alarmId, startedMs)", PRODUCER)
        self.assertIn("AlarmNotice.payload(alarm, startedMs)", PRODUCER)
        self.assertIn("NotificationsService.pushRich(event)", PRODUCER)
        self.assertIn("history.get(i).id ||", PRODUCER)
        self.assertNotIn("Process {", PRODUCER)
        self.assertNotIn("FileView {", PRODUCER)
        self.assertIn("function shouldBlockNotification(entry)", NOTICE)
        self.assertIn("function shouldSuppressScoped(entry)", NOTICE)
        self.assertIn("function isFavoriteForNotification(entry)", NOTICE)
        self.assertIn("function isSnoozedForNotification(entry)", NOTICE)
        self.assertIn("const options = scopeOptionsFor(entry);", NOTICE)

    def test_notification_popup_opens_exact_saved_alarm_without_window_spawn(self):
        self.assertIn('id === "clock-alarm" && event === "alarm-rang"', ROUTE)
        self.assertIn('text(ctx.resourceId) === "alarm-" + alarmId', ROUTE)
        self.assertIn('return { widget: "time", view: "alarm", alarmId: alarmId };', ROUTE)
        self.assertIn('widget === "time" && route.view === "alarm"', SHELL)
        self.assertIn("timewWindow.openNotificationAlarm(route.alarmId)", SHELL)
        self.assertIn("function openNotificationAlarm(alarmId)", TIMEW)
        self.assertIn("!AlarmManagerService.findAlarm(alarmId)", TIMEW)
        self.assertIn("if (!alarmPlaceholderPane.choose(alarmId))", TIMEW)
        self.assertIn('toolsView = "alarm";', TIMEW)
        self.assertIn("menuOpen = true;", TIMEW)
        self.assertNotIn("execDetached", PRODUCER)
        self.assertIn("NotificationsService.hasApolloDestination(", POPUP)
        self.assertIn("NotificationsService.requestApolloDestination(", POPUP)
        self.assertIn("focusable: false", POPUP)

    def test_metadata_does_not_use_title_or_note_to_identify_alarm(self):
        self.assertIn('resourceId: resource', POLICY)
        self.assertIn('resourceLabel: label', POLICY)
        self.assertIn('alarmId: a.id', POLICY)
        self.assertIn('eventType: EVENT_TYPE', POLICY)
        self.assertIn('origin: "apollo"', POLICY)
        self.assertIn('domain: "system"', POLICY)
        self.assertIn('ringStartedAtMs: startedMs', POLICY)
        self.assertNotIn("a.note", POLICY)
        self.assertIn("const resourceId", SCOPE) if "const resourceId" in SCOPE else self.assertIn("let resourceId =", SCOPE)


if __name__ == "__main__":
    unittest.main()
