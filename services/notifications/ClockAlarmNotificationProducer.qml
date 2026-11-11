import QtQuick
import Quickshell
import qs.services.notifications
import qs.services.time
import "ClockAlarmNotificationPolicy.js" as AlarmNotice

// One-way, read-only fanout from the durable Clock scheduler. All mute,
// DND, block, ZZ, favorite, popup and history decisions remain owned by
// NotificationsService, using app + exact RESOURCE + EVENT scopes.
Scope {
    id: producer

    function containsId(model, eventId) {
        for (let i = 0; i < model.count; i++) {
            if (String(model.get(i).id || "") === eventId)
                return true;
        }
        return false;
    }
    function deliver(alarmId, startedMs) {
        const alarm = AlarmManagerService.findAlarm(alarmId);
        const event = AlarmNotice.payload(alarm, startedMs);
        if (!event) {
            AlarmManagerService.reportNotificationOutcome(
                alarmId, startedMs, "INVALID EVENT PAYLOAD");
            return;
        }

        // The receipt shows what the *existing* Notifications service did:
        // blocked-before-history, retained-only, or actively queued popup.
        // It must never bypass DND, BLOCK, ZZ or other shared policy.
        try {
            const history = NotificationsService.notifications;
            if (containsId(history, event.id)) {
                AlarmManagerService.reportNotificationOutcome(
                    alarmId, startedMs, "ALREADY IN HISTORY");
                return;
            }

            NotificationsService.pushRich(event);
            const recorded = containsId(history, event.id);
            const active = containsId(
                NotificationsService.activeNotifications, event.id);
            let result = "NO HISTORY // NOT ACCEPTED";
            if (recorded)
                result = active ? "POPUP QUEUED" : "HISTORY ONLY";
            else if (!NotificationsService.policyReady)
                result = "POLICY STILL LOADING";
            else if (NotificationsService.policyStatus === "parse-error"
                    || NotificationsService.policyStatus === "load-error")
                result = "NOTIFICATION POLICY ERROR";
            else if (NotificationsService.shouldBlockNotification(event))
                result = "BLOCKED BY NOTIFICATION POLICY";

            AlarmManagerService.reportNotificationOutcome(
                alarmId, startedMs, result);
        } catch (error) {
            AlarmManagerService.reportNotificationOutcome(
                alarmId, startedMs, "NOTIFICATION BRIDGE ERROR");
            console.warn("Clock alarm: notification delivery failed");
        }
    }

    Connections {
        target: AlarmManagerService
        function onAlarmFired(alarmId, startedMs) {
            producer.deliver(alarmId, startedMs);
        }
    }
}
