import QtQuick
import "../../components"
import "CpuPlusQueueRecovery.js" as Recovery

// Read-only and unmounted. Host must atomically clear inventory on owner loss,
// selection change or timeout; no display data grants an unlock.
Column {
    id: root
    objectName: "cpuplusQueueRecoveryPane"
    property var hostStatus: null
    property var inventory: null
    readonly property var view: Recovery.project(inventory)
    spacing: 5
    GohuText {
        width: parent.width
        text: "AUTO // STARTUP & RECOVERY"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: Recovery.gate(root.hostStatus)
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.view ? "PENDING REQUEST // " + (root.view.pendingId || "NONE REPORTED")
            + "\n" + (root.view.truncated ? "PARTIAL RECENT INVENTORY" : "RECENT INVENTORY REPORTED")
            : "RECOVERY INVENTORY UNAVAILABLE"
        color: Colors.cyan
        textFormat: Text.PlainText
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.view !== null
        text: root.view && root.view.prepared
            ? "PREPARED ACTION // " + root.view.prepared.actionId
                + "\n" + root.view.prepared.kind + " // DO NOT REPLAY"
            : "NO PREPARED ACTION REPORTED // NOT PROOF OF NONCOMMIT"
        color: Colors.orange
        font.pixelSize: 10
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.view ? root.view.recent : []
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: body.implicitHeight + 8
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.kind + " // " + (modelData.state==="COMMITTED"
                        ? "LOCAL INTENT COMMITTED" : "PREPARED // UNRESOLVED")
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: "ACTION // " + modelData.actionId
                        + "\nEXPECTED // " + (modelData.expectedId || "NEW REQUEST")
                        + "\nRESULT // " + (modelData.resultId || "NOT RECORDED")
                        + (modelData.target===null ? "" : "\nTARGET // "+modelData.target+" GiB"
                            + "\nEXPIRY // "+Recovery.utc(modelData.expiry))
                        + "\nPREPARED // "+Recovery.utc(modelData.preparedAt)
                        + (modelData.committedAt===null?"":"\nCOMMITTED // "+Recovery.utc(modelData.committedAt))
                    textFormat: Text.PlainText
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: "ADJUSTMENT OUTCOME // UNVERIFIED\nLocal commit records queue intent only. Missing records do not establish noncommit. No retry, unlock or acknowledgment is available."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
