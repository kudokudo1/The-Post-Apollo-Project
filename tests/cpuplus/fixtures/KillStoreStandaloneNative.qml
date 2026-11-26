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
        readonly property var graphState: store.graphState
    }
    QtObject {
        id: second
        readonly property var store: KillBackend.KillStore
        readonly property var rows: store.rows
        readonly property var graphState: store.graphState
    }
    // Run after the shell event loop starts, not during component loading.
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: root.verifyStore()
    }
    function verifyStore() {
        const sample = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 31, rss: 2048, mem: 3, elapsed: "00:05"}];
        first.store.graphVisible = true;
        first.store.publishSnapshot(sample);
        first.store.graphController.updateMiniCpuHistories(sample);
        first.store.graphController.updateMiniHunterMetricHistories(sample);
        first.graphState.taskMiniDisplayRevision += 1;
        const next = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 52, rss: 3072, mem: 4, elapsed: "00:06"}];
        const previous = second.graphState.taskMiniCpuHistories["pid:4321"];
        first.store.graphController.updateMiniCpuHistories(next);
        first.store.graphController.updateMiniHunterMetricHistories(next);
        first.graphState.taskMiniDisplayRevision += 1;
        if (first.store !== second.store
                || first.store.telemetry !== second.store.telemetry
                || first.graphState !== second.graphState
                || first.store.graphController !== second.store.graphController
                || previous.length !== 1 || previous[0] !== 31
                || second.graphState.taskMiniCpuHistories["pid:4321"].length !== 2
                || second.graphState.taskMiniCpuHistories["pid:4321"][1] !== 52
                || second.graphState.taskMiniHunterMetricHistories["mem:pid:4321"][1] !== 3
                || second.graphState.taskMiniDisplayRevision !== 2
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
