import QtQuick
import Quickshell
import qs.services.notifications
import "NotificationsPersistenceHealthPolicy.js" as StoragePolicy

// Observes existing FileView status exposed by NotificationsService.
// It never retries a save, reads/writes storage, or bypasses DND/snooze.
// If history itself is unwritable, the warning can be displayed in-session
// but must not be described as successfully persisted.
Scope {
    id: producer
    property var state: StoragePolicy.initial()

    function observe(area, status) {
        if (!NotificationsService.historyReady)
            return;
        const next = StoragePolicy.transition(producer.state, area, status);
        producer.state = next.state;
        if (!next.event)
            return;
        const restored = next.event === "restored";
        const label = area === "history" ? "HISTORY"
                    : area === "policy" ? "DND / SNOOZE SETTINGS"
                    : "FAVORITE SOURCES";
        NotificationsService.pushRich({
            "source": "NOTIFICATIONS",
            "sourceId": "notifications-storage-health",
            "category": "internal",
            "severity": restored ? "normal" : "warning",
            "title": "NOTIFICATIONS // " + label
                     + (restored ? " STORAGE RESTORED"
                                 : " STORAGE ERROR"),
            "message": restored
                ? "The " + label + " store reported a successful load or save."
                : "The " + label + " store reported a load or save error."
                  + " Changes may not survive a restart. Review Notifications Hub.",
            "tags": ["notifications", "system", "storage-health", area],
            "context": {
                "eventType": "notification-" + area + "-"
                           + (restored ? "storage-restored" : "storage-error"),
                "origin": "apollo",
                "domain": "system",
                "store": area,
                "observedAtUtc": new Date().toISOString()
            }
        });
    }
    function scan() {
        if (!NotificationsService.historyReady)
            return;
        producer.observe("history", NotificationsService.historyStatus);
        if (NotificationsService.policyReady)
            producer.observe("policy", NotificationsService.policyStatus);
        if (NotificationsService.favoritesReady)
            producer.observe("favorites", NotificationsService.favoritesStatus);
    }

    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.scan(); }
        function onHistoryStatusChanged() {
            producer.observe("history", NotificationsService.historyStatus);
        }
        function onPolicyStatusChanged() {
            if (NotificationsService.policyReady)
                producer.observe("policy", NotificationsService.policyStatus);
        }
        function onFavoritesStatusChanged() {
            if (NotificationsService.favoritesReady)
                producer.observe("favorites", NotificationsService.favoritesStatus);
        }
        function onPolicyReadyChanged() { producer.scan(); }
        function onFavoritesReadyChanged() { producer.scan(); }
    }
    Component.onCompleted: producer.scan()
}
