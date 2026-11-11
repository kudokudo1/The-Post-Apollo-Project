pragma Singleton
import QtQuick
import Quickshell
import qs.services.notifications
import qs.services.time
import "ClockAlarmNotificationActionPolicy.js" as ActPolicy

// Only the transient live popup may issue a direct alarm action. Saved
// notification history remains informational. This service re-resolves the
// stored notification ID and exact current ring immediately before actuation.
Scope {
    id: controls

    function activeEntry(eventId) {
        const id = String(eventId || "");
        if (id === "") return null;
        const model = NotificationsService.activeNotifications;
        for (let i = 0; i < model.count; i++) {
            const entry = model.get(i);
            if (String(entry.id || "") === id)
                return entry;
        }
        return null;
    }

    function optionsFor(eventId) {
        const entry = activeEntry(eventId);
        if (!entry) return [];
        const id = entry.context ? entry.context.alarmId : 0;
        const row = AlarmManagerService.findAlarm(id);
        if (!ActPolicy.liveOccurrence(entry, row, Date.now()))
            return [];
        return [
            {identifier: "stop", label: "STOP"},
            {identifier: "snooze", label: "SNOOZE 5M"}
        ];
    }

    function dispatch(eventId, operation) {
        if (!ActPolicy.validAction(operation))
            return false;
        const entry = activeEntry(eventId);
        if (!entry) return false;
        const alarmId = entry.context ? entry.context.alarmId : 0;
        const row = AlarmManagerService.findAlarm(alarmId);
        const verified = ActPolicy.liveOccurrence(entry, row, Date.now());
        if (!verified) return false;

        // Second witness check is inside the single AlarmManager owner, so
        // a stale popup cannot silence a later occurrence with the same ID.
        const ok = operation === "stop"
            ? AlarmManagerService.stopOccurrence(
                  verified.alarmId, verified.startedMs)
            : AlarmManagerService.snoozeOccurrence(
                  verified.alarmId, verified.startedMs);
        if (ok)
            NotificationsService.dismissPopup(eventId); // history retained
        return ok;
    }
}
