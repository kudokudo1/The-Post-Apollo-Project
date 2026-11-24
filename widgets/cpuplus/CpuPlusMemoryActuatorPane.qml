import QtQuick
import QtQuick.Controls as Controls
import Quickshell.Io
import qs.services.memory
import "../../components"
import "CpuPlusMemorySnapshot.js" as Snapshot

// Demand-loaded by SYSTEM memory/swap selection. No privileged operations.
Item {
    id: root
    property var sample: null
    property string status: "READING"
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property var pendingSample: null
    function finish() {
        if (!received || !exited) return;
        sample = exitOk ? pendingSample : null;
        status = sample ? "OBSERVED" : "UNAVAILABLE";
    }
    property int stagedGiB: 16
    property bool initializedTarget: false
    readonly property var capacity: Snapshot.capacityPlan(sample, stagedGiB)
    function adoptActual() {
        if (!sample || initializedTarget) return;
        const plan = Snapshot.capacityPlan(sample, stagedGiB);
        if (!plan) return;
        if (plan.active) stagedGiB = Math.max(4, Math.min(64, Math.round(plan.actualGiB / 4) * 4));
        initializedTarget = true;
    }
    onSampleChanged: adoptActual()
    function gib(kib) { return (kib / 1048576).toFixed(2) + " GiB"; }
    function refresh() {
        if (probe.running || (status === "READING" && (received || exited))) return;
        received = false;
        exited = false;
        exitOk = false;
        pendingSample = null;
        sample = null;
        status = "READING";
        probe.running = true;
    }
    Component.onCompleted: refresh()
    Connections {
        target: MemoryOperation
        function onRevisionChanged() { root.refresh(); }
    }
    Timer {
        interval: 10000
        repeat: true
        running: root.visible
        onTriggered: root.refresh()
    }
    Process {
        id: probe
        running: false
        command: ["/usr/bin/cat", "/proc/meminfo", "/proc/swaps",
                  "/proc/pressure/memory", "/proc/sys/vm/swappiness"]
        stdout: StdioCollector {
            onStreamFinished: {
                root.pendingSample = Snapshot.parseSnapshot(this.text);
                root.received = true;
                root.finish();
            }
        }
        onExited: function(code, exitStatus) {
            root.exited = true;
            root.exitOk = code === 0 && exitStatus === 0;
            root.finish();
        }
    }
    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.implicitHeight + 18)
        Column {
            id: body
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 17)
            spacing: 10
            GohuText {
                text: "MEMORY // LIVE DIAGNOSTICS"
                color: Colors.magenta
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.WordWrap
            }
            GohuText {
                text: "SOURCE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 10
            }
            ActionButton {
                width: parent.width
                height: 30
                label: "REFRESH"
                available: !probe.running
                onLeftClicked: root.refresh()
            }
            Repeater {
                model: root.sample ? [
                    "PHYSICAL // " + root.gib(root.sample.total),
                    "AVAILABLE // " + root.gib(root.sample.available),
                    "SWAP USED // " + root.gib(root.sample.swap - root.sample.free)
                        + " / " + root.gib(root.sample.swap),
                    "PRESSURE SOME / FULL (10s) // " + root.sample.some.toFixed(2)
                        + "% / " + root.sample.full.toFixed(2) + "%",
                    "SWAPPINESS // " + root.sample.swappiness
                ] : []
                delegate: GohuText {
                    required property string modelData
                    width: body.width
                    text: modelData
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
            Repeater {
                model: root.sample ? root.sample.rows : []
                delegate: GohuText {
                    required property var modelData
                    width: body.width
                    textFormat: Text.PlainText
                    text: modelData.kind + " // " + modelData.name + "\n"
                          + root.gib(modelData.used) + " / " + root.gib(modelData.size)
                          + " // PRIORITY " + modelData.priority
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
            Rectangle { width: parent.width; height: 1; color: Colors.cyan }
            GohuText {
                text: "MANAGED DISK SWAP // CAPACITY"
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.magenta
                font.pixelSize: 12
            }
            GohuText {
                text: "TARGET CAPACITY // " + root.stagedGiB + " GiB"
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.yellow
                font.pixelSize: 12
            }
            GohuText {
                width: parent.width
                text: root.capacity ? "ACTUAL ACTIVE // " + root.gib(root.capacity.actualKiB) : "ACTUAL ACTIVE // UNAVAILABLE"
                color: Colors.cyan
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            Controls.Slider {
                width: parent.width
                enabled: root.capacity !== null && !MemoryOperation.busy
                from: 0
                to: 64
                stepSize: 4
                snapMode: Controls.Slider.SnapAlways
                value: root.stagedGiB
                onMoved: root.stagedGiB = Math.round(value)
            }
            GohuText {
                width: parent.width
                text: root.capacity ? "PROJECTED TOTAL SWAP // "
                      + root.gib(root.capacity.projectedKiB)
                      : "PROJECTED TOTAL SWAP // UNAVAILABLE"
                color: Colors.cyan
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: !root.capacity ? "WAITING FOR LIVE CAPACITY"
                    : root.capacity.direction === "unchanged" ? "TARGET MATCHES ACTIVE CAPACITY"
                    : root.capacity.direction === "expand" && root.capacity.baseActive && !root.capacity.extensionActive
                        ? "EXPANSION // ADD SEPARATE TEMPORARY SWAP"
                    : root.capacity.active ? "PREVIEW ONLY // RESIZE NOT AVAILABLE YET"
                    : "Would reserve " + root.stagedGiB + " GiB of storage. Not physical RAM."
                color: Colors.white
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            ActionButton {
                visible: root.capacity !== null && root.capacity.active && root.capacity.direction !== "unchanged"
                width: parent.width
                height: 30
                label: "RESET TARGET TO ACTIVE"
                onLeftClicked: root.stagedGiB = Math.max(4, Math.min(64, Math.round(root.capacity.actualGiB / 4) * 4))
            }
            CpuPlusSwapComposition {
                width: parent.width
                sample: root.sample
                capacity: root.capacity
            }
            CpuPlusMemoryAddControl {
                width: parent.width
                stagedGiB: root.stagedGiB
                sample: root.sample
            }
        }
    }
    NeonScrollBar { flickable: scroll; visible: root.visible && scrollable }
}
