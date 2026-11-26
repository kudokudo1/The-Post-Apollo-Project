import QtQuick
import Quickshell
import "services/kill" as KillBackend

// No widget, real process probe or process mutation. Fixture timer only.
ShellRoot {
    id: root
    QtObject {
        id: first
        readonly property var store: KillBackend.KillStore
        readonly property var rows: store.rows
    }
    QtObject {
        id: second
        readonly property var store: KillBackend.KillStore
        readonly property var rows: store.rows
    }
    // Run after the shell event loop starts, not during component loading.
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: root.verifyStore()
    }
    function verifyStore() {
        const sample = [{_taskRecord: true, pid: 4321, startTicks: 98765, comm: "synthetic"}];
        first.store.publishSnapshot(sample);
        if (first.store !== second.store
                || first.store.telemetry !== second.store.telemetry
                || first.rows.length !== 1 || second.rows.length !== 1
                || first.rows[0].startTicks !== second.rows[0].startTicks
                || first.store.telemetry.snapshotLoading
                || first.store.telemetry.miniProbeLoading
                || first.store.telemetry.detailProbeLoading) {
            console.error("KILL_STORE_NATIVE_FAIL");
        } else {
            console.log("KILL_STORE_NATIVE_PASS");
        }
        Qt.quit();
    }
}
