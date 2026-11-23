import QtQuick
import "../components"

// Research M4b-T2: status-only presentation, not an authorization layer.
// Default stays a non-persistent preview. No Process, network or write signals.
Item {
    id: feedback
    property bool simulationOnly: true
    property bool readerConnected: false
    property string phase: "staged" // staged, inFlight, acknowledged, reviewRequired, refused
    property bool exactAcknowledgement: false
    property int acknowledgedRevision: -1

    signal reloadRequested()

    readonly property bool verifiedSave:
        !simulationOnly && phase === "acknowledged"
        && exactAcknowledgement && acknowledgedRevision >= 0
    readonly property bool unresolved:
        phase === "reviewRequired"
        || (phase === "acknowledged" && !verifiedSave)
    readonly property string headline: {
        if (simulationOnly) {
            if (phase === "inFlight")
                return "TEST DISPATCH IN FLIGHT // NO LIVE WRITE";
            if (phase === "acknowledged")
                return "TEST ACK RECEIVED // NOT SAVED TO LIVE STORAGE";
            if (phase === "reviewRequired")
                return "TEST OUTCOME UNKNOWN // KEEP DRAFT";
            if (phase === "refused")
                return "TEST REFUSED // NO LIVE WRITE";
            return "DISPOSABLE PREVIEW // NOT SAVED TO LIVE STORAGE";
        }
        if (verifiedSave) return "SAVED // EXACT ACK VERIFIED";
        if (phase === "inFlight") return "WRITE IN FLIGHT // DO NOT RESUBMIT";
        if (phase === "refused") return "REQUEST REFUSED // NO SAVE CLAIM";
        if (unresolved) return "OUTCOME UNKNOWN // KEEP DRAFT";
        return "WRITE NOT SUBMITTED";
    }
    readonly property string explanation: {
        if (simulationOnly)
            return "TEST RESULTS ARE NOT USER RECORDS // PRODUCTION WRITES DISABLED";
        if (verifiedSave)
            return "VERIFIED REVISION " + acknowledgedRevision + " // NO AUTO RETRY";
        if (phase === "inFlight")
            return "WAIT FOR THE ORIGINAL OUTCOME // A SECOND SUBMISSION IS BLOCKED";
        if (phase === "refused")
            return "KEEP THE EDITOR UNTIL THE REFUSAL IS VERIFIED";
        if (unresolved)
            return "KEEP THE DRAFT // RELOAD READ ONLY BEFORE ANY NEW ACTION";
        return "NO WRITE REQUEST WAS SENT";
    }
    readonly property color tone: verifiedSave ? Colors.cyan
        : unresolved || phase === "refused" ? Colors.red : Colors.orange

    implicitHeight: shell.height
    Rectangle {
        id: shell
        width: feedback.width
        height: detailColumn.implicitHeight + 20
        color: Colors.black
        border.width: 1
        border.color: feedback.tone

        Column {
            id: detailColumn
            x: 10
            y: 10
            width: Math.max(0, parent.width - 20)
            spacing: 8

            GohuText {
                width: parent.width
                text: "RESEARCH WRITE STATUS"
                color: Colors.white
                font.pixelSize: 11
                font.bold: true
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                text: feedback.headline
                color: feedback.tone
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                text: feedback.explanation
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
            ActionButton {
                width: 150
                height: 29
                label: "RELOAD READ ONLY"
                labelPixelSize: 9
                available: !feedback.simulationOnly && feedback.unresolved
                    && feedback.readerConnected
                onLeftClicked: feedback.reloadRequested()
            }
        }
    }
}
