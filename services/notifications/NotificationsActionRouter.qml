pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    function route(actionId, context) {
        switch (actionId) {
        case "open-resource":
            break;
        case "limit-resource":
            break;
        case "kill-resource":
            break;
        default:
            break;
        }
    }
}
