import QtQuick
import "../../components"
import "CpuPlusQueuePresentation.js" as QueueView

// R1 display seam only. Production caller supplies null until transport review.
Column {
    id: root
    objectName: "cpuplusQueuePane"
    required property var observedDiskKiB
    required property int capacityTargetGiB
    property var runtimeProjection: null
    readonly property var display: QueueView.project(runtimeProjection)
    spacing: 6
    GohuText {
        width: parent.width
        text: "AUTO // DEFERRED ADJUSTMENTS"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: "NOTIFY ONLY // PROTECTED EXECUTION HOLD"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: [
            {label:"OBSERVED MANAGED DISK",value:QueueView.gib(root.observedDiskKiB),accent:Colors.cyan},
            {label:"CAP TARGET // NOT QUEUED",value:root.capacityTargetGiB + " GiB",accent:Colors.yellow},
            {label:"QUEUE STATUS",value:root.display.state,accent:Colors.orange},
            {label:"ADJUSTMENT OUTCOME",value:root.display.outcome,accent:Colors.orange}
        ]
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: tileBody.implicitHeight + 8
            color: Colors.black
            border.width: 1
            border.color: modelData.accent
            Column {
                id: tileBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.label
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: modelData.value
                    textFormat: Text.PlainText
                    color: modelData.accent
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: root.display.reason
        color: Colors.white
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Column {
        width: parent.width
        spacing: 4
        visible: root.display.requestId !== null
        GohuText {
            width: parent.width
            text: "REQUEST // " + (root.display.requestId || "")
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "AT REQUEST // " + QueueView.gib(root.display.originalActualKiB)
                + "\nREQUESTED TARGET // " + root.display.targetGiB + " GiB"
                + "\nLAST CHECK // " + QueueView.timestamp(root.display.checkedAt)
                + "\nEXPIRY // " + QueueView.timestamp(root.display.expiresAt)
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: root.display.scheduled ? "NEXT CHECK // OWNER REPORTED SCHEDULE"
                : "NEXT CHECK // NOT SCHEDULED IN REPORT"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }
    GohuText {
        width: parent.width
        visible: root.display.notificationIssue
        text: "NOTIFICATION STAGING ISSUE // DELIVERY UNVERIFIED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "QUEUE / REPLACE / CANCEL / RECHECK // TRANSPORT NOT CONNECTED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "Queue reports are historical advisory evidence, not current readiness or authority. The capacity slider alone never creates a request. No automatic adjustment or notification delivery is connected."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
