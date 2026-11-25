import QtQuick
import "../../components"
import "CpuPlusQueueHistory.js" as History

// Standalone read-only view. Caller owns correlation, timeout, owner loss and
// global sequence watermark. No implicit read or reconciliation approval.
Column {
    id: root
    objectName: "cpuplusQueueHistoryPane"
    property var envelope: null
    property string expectedOwner: ""
    property string expectedRequest: ""
    property var sequenceFloor: null
    readonly property var detail: History.project(envelope,expectedOwner,expectedRequest,sequenceFloor)
    spacing: 5
    GohuText {
        width: parent.width
        text: "REQUEST HISTORY // LOCAL REPORT"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: root.detail ? "INTENT // " + root.detail.state + "\nADJUSTMENT OUTCOME // UNVERIFIED"
            : "HISTORY UNAVAILABLE // SELECT EXACT REQUEST"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.detail !== null
        text: root.detail ? "REQUEST // " + root.detail.requestId
            + "\nAT REQUEST // " + History.gib(root.detail.originalKiB)
            + "\nTARGET // " + root.detail.targetGiB + " GiB"
            + "\nCREATED // " + History.utc(root.detail.requestedAt)
            + "\nEXPIRY // " + History.utc(root.detail.expiresAt)
            + "\nCHANGED // " + History.utc(root.detail.changedAt)
            + (root.detail.replacedBy ? "\nREPLACED BY // " + root.detail.replacedBy : "") : ""
        textFormat: Text.PlainText
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.detail !== null
        text: root.detail && root.detail.events.length ? "NOTIFICATION HISTORY" : "NO NOTIFICATION CANDIDATES RECORDED"
        color: Colors.magenta
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.detail ? root.detail.events : []
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: eventBody.implicitHeight + 8
            border.width: 1
            border.color: Colors.cyan
            color: Colors.black
            Column {
                id: eventBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                GohuText {
                    width: parent.width
                    text: modelData.kind + "\n" + modelData.code + "\n" + History.utc(modelData.observedAt)
                    textFormat: Text.PlainText
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: modelData.delivery
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    GohuText {
        width: parent.width
        visible: root.detail !== null
        text: root.detail && root.detail.evidenceAt !== null
            ? "UNBOUND EVIDENCE // " + History.utc(root.detail.evidenceAt) + "\nNOT VERIFIED FOR REQUEST"
            : "NO WITHDRAWAL EVIDENCE RECORDED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "History describes recorded intent and advisory observations. It does not prove delivery, kernel completion or permission. A lost action must be reconciled explicitly; never replay automatically."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
