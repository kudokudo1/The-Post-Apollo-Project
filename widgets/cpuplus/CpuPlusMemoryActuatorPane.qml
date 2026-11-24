import QtQuick
import QtQuick.Controls as Controls
import Quickshell.Io
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
                text: "MEMORY EXPANSION // PREVIEW ONLY"
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.magenta
                font.pixelSize: 12
            }
            GohuText {
                text: "ADDITIONAL DISK SWAP // " + root.stagedGiB + " GiB"
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.yellow
                font.pixelSize: 12
            }
            Controls.Slider {
                width: parent.width
                from: 0
                to: 64
                stepSize: 4
                snapMode: Controls.Slider.SnapAlways
                value: root.stagedGiB
                onMoved: root.stagedGiB = Math.round(value)
            }
            GohuText {
                width: parent.width
                text: root.sample ? "PROJECTED TOTAL SWAP // "
                      + root.gib(root.sample.swap + root.stagedGiB * 1048576)
                      : "PROJECTED TOTAL SWAP // UNAVAILABLE"
                color: Colors.cyan
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "Would reserve " + root.stagedGiB
                      + " GiB of disk storage. Not physical RAM. Storage eligibility, free space and authorization are not checked in this preview."
                color: Colors.white
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "APPLY // HOLD — NO SYSTEM WRITES"
                color: Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
        }
    }
    NeonScrollBar { flickable: scroll; visible: root.visible && scrollable }
}
