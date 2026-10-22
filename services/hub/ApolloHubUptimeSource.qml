import QtQuick
import Quickshell
import Quickshell.Io
import "ApolloHubUptimePolicy.js" as UptimePolicy

// One tiny, local, read-only Linux boot-uptime source per Hub bridge.
// No process launch, CPU++ telemetry duplication, shell boot guessing, or
// privileged/write API. Does not watch-change a dynamically generated file.
Scope {
    id: uptime

    property string raw: ""
    property double observedAtMs: 0
    property double nowMs: Date.now()
    property bool loadError: false

    FileView {
        id: uptimeFile
        path: "/proc/uptime"
        watchChanges: false
        printErrors: false

        onLoaded: {
            // Completed read establishes one coherent value and timestamp.
            const observedNow = Date.now();
            uptime.raw = uptimeFile.text();
            uptime.loadError = false;
            uptime.nowMs = observedNow;
            uptime.observedAtMs = observedNow;
        }
        onLoadFailed: function(error) {
            uptime.raw = "";
            uptime.observedAtMs = 0;
            uptime.loadError = true;
            uptime.nowMs = Date.now();
        }
    }

    Timer {
        interval: 60000
        repeat: true
        running: true
        // Nonblocking procfs file refresh, NOT process or hardware polling.
        onTriggered: uptimeFile.reload()
    }

    readonly property var snapshot: UptimePolicy.snapshot(
        raw, observedAtMs, nowMs, loadError)
}
