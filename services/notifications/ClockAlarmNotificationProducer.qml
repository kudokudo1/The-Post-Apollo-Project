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

    function deliver(alarmId, startedMs) {
        const alarm = AlarmManagerService.findAlarm(alarmId);
        const event = AlarmNotice.payload(alarm, startedMs);
        if (!event)
            return;

        // A persisted ring can be re-observed after a Quickshell restart.
        // Same event ID means no second saved card or repeated popup.
        const history = NotificationsService.notifications;
        for (let i = 0; i < history.count; i++) {
            if (String(history.get(i).id || "") === event.id)
                return;
        }
        NotificationsService.pushRich(event);
    }

    Connections {
        target: AlarmManagerService
        function onAlarmFired(alarmId, startedMs) {
            producer.deliver(alarmId, startedMs);
        }
    }
}
