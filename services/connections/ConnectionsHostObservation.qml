pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "ConnectionsHostStatusPolicy.js" as Policy

// C2i on-demand LOCAL HOST INSPECTION, not a trusted host-status feed.
// The C2g authenticated host boundary remains disconnected. A same-UID
// process could impersonate the inspected socket, so all observations
// are read-only, labeled UNVERIFIED and never become a broker grant.
Scope {
    id: inspection

    readonly property bool hostAuthenticated: false
    readonly property bool credentialActionsEnabled: false
    property bool checking: false
    property var observation: Policy.offline()
    property string rawResult: ""
    property bool replySeen: false
    readonly property bool observing: observation.status === "OBSERVED_UNVERIFIED"

    function inspect() {
        if (checking || host.running)
            return false;
        observation = Policy.offline();
        rawResult = "";
        replySeen = false;
        checking = true;
        host.exec([
            "python3", "-B",
            Quickshell.shellPath("services/connections/ConnectionsHostStatusInspect.py")
        ]);
        return true;
    }

    function acceptRaw(text) {
        if (!checking || replySeen || typeof text !== "string"
                || text.length > 1024) {
            replySeen = false;
            rawResult = "";
            return;
        }
        rawResult = text;
        replySeen = true;
    }

    function completed(code) {
        if (!checking)
            return;
        var source = null;
        if (code === 0 && replySeen) {
            try {
                source = JSON.parse(rawResult);
            } catch (error) {
                source = null;
            }
        }
        observation = Policy.project(source);
        rawResult = "";
        replySeen = false;
        checking = false;
    }

    Process {
        id: host
        running: false
        stdout: StdioCollector {
            onStreamFinished: inspection.acceptRaw(text)
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            inspection.completed(code);
        }
    }
}
