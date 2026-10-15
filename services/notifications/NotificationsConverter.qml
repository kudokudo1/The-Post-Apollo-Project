pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Notifications

Singleton {
    id: root

    // Freedesktop clients MAY provide a category hint. Keep the original
    // standard category (email.arrived, im.received, network.error, etc.)
    // so the hub can classify without guessing from message text.
    function categoryFor(notification) {
        const hints = notification.hints || {};
        const category = hints["category"];

        return typeof category === "string" && category.trim() !== ""
            ? category.trim().toLowerCase()
            : "generic";
    }

    // The QsNotification exposes the freedesktop urgency level as an enum.
    // Critical belongs in the Warning severity view regardless of its source.
    function severityFor(notification) {
        if (notification.urgency === NotificationUrgency.Critical)
            return "critical";

        if (notification.urgency === NotificationUrgency.Low)
            return "low";

        return "normal";
    }

    function convert(notification) {
        return {
            // A missing desktop entry is legitimate, especially for browsers.
            // Keep the sender's actual app name; policy keys continue to use
            // the original desktopEntry when one was provided.
            "source": String(notification.appName || notification.desktopEntry || "UNKNOWN APP"),
            "sourceId": String(notification.desktopEntry || ""),
            "title": notification.summary,
            "message": notification.body,
            "originalTitle": notification.summary,
            "originalMessage": notification.body,
            "appIcon": notification.appIcon,
            "image": notification.image,
            "category": root.categoryFor(notification),
            "severity": root.severityFor(notification)
        };
    }
}
