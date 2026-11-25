import QtQuick
import "../../components"
import "CpuPlusQueueRecovery.js" as Recovery

// Read-only. Canonical host owns correlation and clears data on loss/timeout.
// Legacy standalone fixture inputs remain supported; atomic mode never falls back.
Column {
    id: root
    objectName: "cpuplusQueueRecoveryPane"
    property var hostStatus: null
    property var inventory: null
    property bool atomicMode: false
    property var recoveryContext: null
    // Host supplies this from its exact read gate; it revalidates every signal.
    property bool readAvailable: false
    property Item footerTarget: null
    property string lookupText: ""
    signal recoveryReadRequested(string kind, var value)
    readonly property var snapshot: atomicMode ? Recovery.context(recoveryContext) : null
    readonly property var effectiveHost: atomicMode ? (snapshot ? snapshot.host : null) : hostStatus
    readonly property var view: atomicMode ? (snapshot ? snapshot.inventory : null) : Recovery.project(inventory)
    readonly property var localView: snapshot ? snapshot.localAction : null
    readonly property bool canRead: atomicMode && Recovery.canRead(recoveryContext,readAvailable)
    function requestRead(kind,value) {
        if (!visible || !atomicMode || !Recovery.canRead(recoveryContext,readAvailable)) return;
        if (kind==="INVENTORY" && value===16) recoveryReadRequested(kind,value);
        else if (kind==="LOCAL_ACTION" && Recovery.uuid(value)) recoveryReadRequested(kind,value);
    }
    spacing: 5
    GohuText {
        width: parent.width
        text: "AUTO // STARTUP & RECOVERY"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: Recovery.gate(root.effectiveHost)
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.view ? "PENDING REQUEST // " + (root.view.pendingId || "NONE REPORTED")
            + "\n" + (root.view.truncated ? "PARTIAL RECENT INVENTORY" : "RECENT INVENTORY REPORTED")
            : root.snapshot && root.snapshot.readPending ? "RECOVERY READ PENDING"
            : root.localView ? "EXACT ACTION LOOKUP // INVENTORY NOT DISPLAYED"
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
    GohuText {
        width: parent.width
        visible: root.localView !== null
        text: root.localView ? "LOOKUP ACTION // "+root.localView.actionId
            + (root.localView.missing ? "\nNO RECORD REPORTED // NOT PROOF OF NONCOMMIT" : "\nEXACT LOCAL RECORD REPORTED") : ""
        color: Colors.orange
        textFormat: Text.PlainText
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.localView ? (root.localView.record ? [root.localView.record] : [])
            : root.view ? root.view.recent : []
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
    Column {
        parent: root.footerTarget || root
        objectName: "cpuplusRecoveryReadControls"
        visible: root.atomicMode
        width: parent.width
        spacing: 3
        GohuText {
            width: parent.width
            text: "ACTION UUID // EXACT LOOKUP"
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
                color: Colors.white
                font.pixelSize: 10
                maximumLength: 36
                selectByMouse: true
                clip: true
                text: root.lookupText
                onTextEdited: root.lookupText=text
            }
        }
        Row {
            width: parent.width
            spacing: 3
            ActionButton {
                objectName: "cpuplusRecoveryInventoryRead"
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 26
                label: "INVENTORY"
                contentPadding: 2
                available: root.canRead
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.requestRead("INVENTORY",16)
            }
            ActionButton {
                objectName: "cpuplusRecoveryActionRead"
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 26
                label: "LOOKUP"
                contentPadding: 2
                available: root.canRead && Recovery.uuid(root.lookupText)
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.requestRead("LOCAL_ACTION",root.lookupText)
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
