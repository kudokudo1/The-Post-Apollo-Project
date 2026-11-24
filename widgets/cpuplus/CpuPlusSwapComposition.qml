import QtQuick
import "../../components"
import "CpuPlusMemorySnapshot.js" as Snapshot

// Read-only. The 24px square outlined track matches SystemMonitorView.
Column {
    id: root
    required property var sample
    required property var capacity
    property bool compact: false
    readonly property var composition: Snapshot.swapComposition(sample)
    readonly property var segments: composition ? composition.groups.filter(g => g.size > 0) : []
    spacing: compact ? 3 : 6

    function accent(id) {
        return id === "zram" ? Colors.cyan : id === "base" ? Colors.yellow
            : id === "extension" ? Colors.magenta : Colors.blue;
    }
    function amount(kib) {
        if (kib === 0) return "0 B";
        if (kib < 1024) return kib + " KiB";
        if (kib < 1048576) return (kib / 1024).toFixed(1) + " MiB";
        return (kib / 1048576).toFixed(2) + " GiB";
    }
    GohuText {
        width: parent.width
        text: root.compact ? "SWAP // USED / ACTIVE" : "SWAP // LIVE COMPOSITION"
        color: Colors.magenta
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: root.composition ? (root.compact ? root.amount(root.composition.used) + " / " + root.amount(root.composition.total)
              : "ACTIVE // " + root.amount(root.composition.total) + "   USED // " + root.amount(root.composition.used))
            : "SOURCE UNAVAILABLE"
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Rectangle {
        width: Math.max(0, parent.width - 10)
        anchors.horizontalCenter: parent.horizontalCenter
        height: 24
        color: Colors.black
        border.width: 1
        border.color: Colors.magenta
        clip: true
        Row {
            id: track
            anchors.fill: parent
            anchors.margins: 3
            spacing: 0
            Repeater {
                model: root.segments
                delegate: Item {
                    id: segment
                    required property var modelData
                    width: root.composition && root.composition.total > 0
                        ? track.width * modelData.size / root.composition.total : 0
                    height: track.height
                    clip: true
                    Rectangle {
                        anchors.fill: parent
                        color: root.accent(segment.modelData.id)
                        opacity: 0.22
                    }
                    Rectangle {
                        height: parent.height
                        width: parent.width * segment.modelData.used / segment.modelData.size
                        color: root.accent(segment.modelData.id)
                        opacity: 0.85
                    }
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.width: 1
                        border.color: root.accent(segment.modelData.id)
                    }
                }
            }
        }
    }
    GohuText {
        width: parent.width
        visible: !root.compact
        text: "BRIGHT = USED   DIM = AVAILABLE"
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: root.compact ? [] : root.segments
        delegate: Column {
            id: legend
            required property var modelData
            width: root.width
            spacing: 2
            GohuText {
                width: parent.width
                text: legend.modelData.label + " // " + (100 * legend.modelData.used / legend.modelData.size).toFixed(1) + "%"
                color: root.accent(legend.modelData.id)
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: root.amount(legend.modelData.used) + " USED / " + root.amount(legend.modelData.size)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }
    Flow {
        width: parent.width
        spacing: 5
        visible: root.compact
        Repeater {
            model: root.compact ? root.segments : []
            delegate: GohuText {
                required property var modelData
                text: modelData.label + " " + root.amount(modelData.size)
                color: root.accent(modelData.id)
                font.pixelSize: 10
            }
        }
    }
    GohuText {
        visible: root.composition !== null && !root.composition.capacityMatches
        width: parent.width
        text: "KERNEL TOTALS CHANGED DURING READ // REFRESH"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        visible: !root.compact && root.capacity !== null && root.capacity.direction !== "unchanged"
        width: parent.width
        text: root.capacity ? "TARGET PREVIEW // " + root.amount(root.capacity.projectedKiB)
            + " TOTAL; LIVE BAR UNCHANGED" : ""
        color: Colors.yellow
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: !root.compact
        text: "ZRAM CAPACITY IS LOGICAL COMPRESSED SWAP, NOT EXTRA PHYSICAL RAM."
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
