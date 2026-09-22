pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    function convert(notification) {
        return {
            "source": notification.appName,
            "sourceId": notification.desktopEntry,
            "title": notification.summary,
            "message": notification.body,
            "originalTitle": notification.summary,
            "originalMessage": notification.body,
            "appIcon": notification.appIcon,
            "image": notification.image
        };
    }
}
