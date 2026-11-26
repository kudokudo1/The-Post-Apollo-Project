import QtQuick
import Quickshell

// One selected-detail stream. CPU++ has priority during donor transition;
// two views of the same exact live process read the same history.
Scope {
    id: root
    required property var graph
    required property var state
    required property var rows
    property bool cpuActive: false
    property bool donorActive: false
    property string cpuTarget: ""
    property string donorTarget: ""
    property bool ready: false

    function identity(row) {
        if (!row || row._taskRecord !== true) return "";
        const pid=Number(row.pid), birth=Number(row.startTicks);
        const comm=String(row.comm || "");
        if (!Number.isSafeInteger(pid) || pid<=1
                || !Number.isSafeInteger(birth) || birth<=0 || !comm) return "";
        return JSON.stringify([pid,birth,comm]);
    }
    readonly property string requestedKey: cpuActive ? cpuTarget : donorActive ? donorTarget : ""
    readonly property var currentEntry: {
        if (!requestedKey) return null;
        return rows.find(row => identity(row) === requestedKey) || null;
    }
    readonly property string activeKey: identity(currentEntry)

    function matches(row) { return !!activeKey && identity(row) === activeKey; }
    function setCpuActive(active) {
        if (!active) cpuTarget="";
        cpuActive=!!active;
    }
    function selectCpu(row) { if (cpuActive) cpuTarget=identity(row); }
    function selectDonor(row) { donorTarget=identity(row); }

    // Reset even when the numeric PID was reused. Reset also invalidates
    // the in-flight probe generation in the original telemetry implementation.
    function rebind() {
        if (!ready) return;
        graph.clearDetailHistory();
        if (!currentEntry) return;
        graph.resetForSelection(currentEntry, graph.miniCpuHistory(currentEntry), true);
        refresh();
    }
    function refresh() {
        if (ready && currentEntry && state.taskHistoryPid===Number(currentEntry.pid))
            graph.refreshDetailProbe(currentEntry);
    }
    function accept(sample) {
        if (!sample || !currentEntry
                || Number(sample.pid)!==Number(currentEntry.pid)
                || Number(sample.startTicks)!==Number(currentEntry.startTicks)
                || state.taskHistoryPid!==Number(currentEntry.pid)) return false;
        graph.applyDetailProbe(sample,currentEntry);
        return true;
    }
    onActiveKeyChanged: rebind()
    Component.onCompleted: { ready=true; rebind(); }

    Timer {
        interval: 1000
        repeat: true
        running: root.ready && !!root.activeKey
        onTriggered: root.refresh()
    }
}
