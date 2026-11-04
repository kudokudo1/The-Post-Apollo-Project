pragma Singleton

import QtQuick
import "ConnectionsRequestDisplayPolicy.js" as DisplayPolicy

// C2g read-only host STATUS boundary. The real host has no registered,
// authenticated status channel yet. There is intentionally no Process,
// D-Bus subscriber, client-supplied setStatus(), or approval actuator here.
// In tests the pane may display an explicitly SIMULATED fixture, never a
// production grant. Later a trusted host adapter must own this singleton.
QtObject {
    id: statusBridge
    readonly property bool hostConnected: false
    readonly property bool hostAuthenticated: false
    readonly property bool canApprove: false
    readonly property var latestStatus: null

    function display(providerId) {
        return DisplayPolicy.project(latestStatus, providerId);
    }
}
