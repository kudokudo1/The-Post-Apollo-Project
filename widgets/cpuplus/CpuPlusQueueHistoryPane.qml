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
    // Canonical host mode: caller publishes its current validated history
    // and read/display gates from one session snapshot, clearing on loss.
    // Legacy envelope fixture stays separate; no fallback in host mode.
    property bool hostMode: false
    property var hostHistory: null
    property bool historyAvailable: false
    property bool readAvailable: false
    property bool readPending: false
    property Item footerTarget: null
    property string lookupText: ""
    property string selectedRequest: ""
    signal historyReadRequested(string requestId)
    readonly property var detail: hostMode
        ? History.hostView(hostHistory,selectedRequest,historyAvailable && !readPending)
        : History.project(envelope,expectedOwner,expectedRequest,sequenceFloor)
    function requestRead() {
        if(!visible||!hostMode||!readAvailable||readPending||!History.uuid(lookupText))return;
        selectedRequest=lookupText;
        historyReadRequested(selectedRequest);
    }
    onLookupTextChanged: selectedRequest = ""
    onVisibleChanged: if (!visible) selectedRequest = ""
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
            : root.hostMode && root.readPending ? "HISTORY READ PENDING"
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
    Column {
        parent: root.footerTarget || root
        objectName: "cpuplusHistoryReadControls"
        visible: root.hostMode
        width: parent.width
        spacing: 3
        GohuText {
            width: parent.width
            text: "REQUEST UUID // EXACT HISTORY"
            color: Colors.cyan
            font.pixelSize: 10
        }
        Rectangle {
            width: parent.width
            height: 27
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 4
                text: root.lookupText
                color: Colors.white
                font.pixelSize: 10
                maximumLength: 36
                selectByMouse: true
                clip: true
                readOnly: root.readPending
                onTextEdited: root.lookupText=text
            }
        }
        ActionButton {
            objectName: "cpuplusHistoryRead"
            width: parent.width
            height: 26
            label: root.readPending ? "READING" : "READ HISTORY"
            contentPadding: 2
            available: root.hostMode && root.readAvailable && !root.readPending && History.uuid(root.lookupText)
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.requestRead()
        }
    }
    GohuText {
        width: parent.width
        text: "History describes recorded intent and advisory observations. It does not prove delivery, kernel completion or permission. A lost action must be reconciled explicitly; never replay automatically."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
