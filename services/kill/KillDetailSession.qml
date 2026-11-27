import QtQuick
import Quickshell

// One exact selected-detail stream per session. Store supplies independent
// consumer sessions during donor comparison.
Scope {
    id: root
    required property var graph
    required property var state
    required property var rows
    property bool collectionAllowed: true
    property bool cpuActive: false
    property bool donorActive: false
    property string cpuTarget: ""
    property string donorTarget: ""
    property bool ready: false
    property var resourceEvidence: null

    function identity(row) {
        if (!row || row._taskRecord !== true) return "";
        const pid=Number(row.pid), birth=Number(row.startTicks);
        const comm=String(row.comm || "");
        if (!Number.isSafeInteger(pid) || pid<=1
                || !Number.isSafeInteger(birth) || birth<=0 || !comm) return "";
        return JSON.stringify([pid,birth,comm]);
    }
    readonly property string requestedKey: !collectionAllowed ? "" : cpuActive ? cpuTarget : donorActive ? donorTarget : ""
    readonly property var currentEntry: {
        if (!requestedKey) return null;
        const expected=JSON.parse(requestedKey);
        return rows.find(row => row && row._taskRecord === true
            && Number(row.pid)===expected[0] && Number(row.startTicks)===expected[1]
            && String(row.comm || "")===expected[2]) || null;
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
        resourceEvidence = null;
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
        // Same identity-bound selected-detail sample; no new collector.
        resourceEvidence = {key:activeKey,niceValue:sample.niceValue === undefined ? null : sample.niceValue,
            cpuMask:typeof sample.cpuMask === "string" ? sample.cpuMask : ""};
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
