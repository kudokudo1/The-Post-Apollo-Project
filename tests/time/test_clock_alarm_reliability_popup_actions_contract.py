"""Clock alarm occurrence receipts and exact live popup controls."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "services/time/AlarmManagerPolicy.js").read_text()
SERVICE = (ROOT / "services/time/AlarmManagerService.qml").read_text()
UI = (ROOT / "widgets/AlarmManagerPane.qml").read_text()
POPUP = (ROOT / "modules/Notifications.qml").read_text()
ACTION_POLICY = (ROOT / "services/notifications/ClockAlarmNotificationActionPolicy.js").read_text()
ACTION_SERVICE = (ROOT / "services/notifications/ClockAlarmNotificationActions.qml").read_text()
MODULE = (ROOT / "services/notifications/qmldir").read_text()
NOTIFICATIONS = (ROOT / "services/notifications/NotificationsService.qml").read_text()

class AlarmReliabilityActions(unittest.TestCase):
    def test_durable_receipts_compatible_with_old_v2_storage(self):
        for token in ('lastEventKind', 'lastEventAtMs', 'lastExpectedAtMs',
                      'lastFiredAtMs', 'lastMissedAtMs'):
            self.assertIn(token, POLICY)
        self.assertIn('EVENT_KINDS = ["none", "fired", "missed", "stopped", "snoozed", "expired"]', POLICY)
        self.assertIn('if (late > MAX_LATE_MS)', POLICY)
        self.assertIn('a.lastFiredDay = due;', POLICY)
        self.assertIn('a.lastEventKind = "missed";', POLICY)
        self.assertIn('a.lastEventKind = "fired";', POLICY)
        self.assertIn('function lastEventText(id)', SERVICE)
        self.assertIn('text: "LAST // " + AlarmManagerService.lastEventText(pane.selectedId)', UI)

    def test_only_current_matching_live_ring_can_be_stopped_from_popup(self):
        self.assertIn('ClockAlarmNotificationActions 1.0 ClockAlarmNotificationActions.qml', MODULE)
        self.assertIn('function liveOccurrence(entry, alarm, nowMs)', ACTION_POLICY)
        self.assertIn('a.ringStartedAtMs !== ringMs', ACTION_POLICY)
        self.assertIn('ctx.resourceId !== "alarm-" + alarmId', ACTION_POLICY)
        self.assertIn('ringMs > nowMs || nowMs - ringMs >= 15 * 60 * 1000', ACTION_POLICY)
        self.assertIn('function optionsFor(eventId)', ACTION_SERVICE)
        self.assertIn('const entry = activeEntry(eventId);', ACTION_SERVICE)
        self.assertIn('NotificationsService.activeNotifications', ACTION_SERVICE)
        self.assertIn('ActPolicy.liveOccurrence(entry, row, Date.now())', ACTION_SERVICE)
        self.assertIn('function stopOccurrence(id, startedMs)', SERVICE)
        self.assertIn('function snoozeOccurrence(id, startedMs)', SERVICE)
        self.assertIn('a.ringStartedAtMs === startedMs', SERVICE)
        self.assertIn('NotificationsService.dismissPopup(eventId)', ACTION_SERVICE)
        self.assertNotIn('NotificationsService.pushRich', ACTION_SERVICE)
        self.assertNotIn('setDnd(', ACTION_SERVICE)
        self.assertNotIn('setBlock(', ACTION_SERVICE)

    def test_popup_reuses_native_buttons_and_does_not_steal_focus(self):
        self.assertIn('focusable: false', POPUP)
        self.assertIn('WlrLayershell.keyboardFocus: WlrKeyboardFocus.None', POPUP)
        self.assertIn('readonly property var popupActions:', POPUP)
        self.assertIn('clockAlarmActions.length > 0 ? clockAlarmActions : externalActions', POPUP)
        self.assertIn('model: notificationCard.popupActions', POPUP)
        self.assertIn('visible: notificationCard.popupActions.length > 0', POPUP)
        self.assertIn('ClockAlarmNotificationActions.dispatch(', POPUP)
        self.assertIn('NotificationsService.invokeExternalAction(', POPUP)
        self.assertIn('NotificationService', 'NotificationService') # compatibility marker
        self.assertIn('function requestApolloDestination(eventId)', NOTIFICATIONS)
        self.assertNotIn('Window {', ACTION_SERVICE)
        self.assertNotIn('Process {', ACTION_SERVICE)

if __name__ == "__main__":
    unittest.main()
