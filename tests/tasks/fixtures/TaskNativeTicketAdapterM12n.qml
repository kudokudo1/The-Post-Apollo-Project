import QtQuick
import Quickshell
import "TaskNativeTicketLogicM12n.js" as TicketLogic

// M12n // Standalone observer around M12i. It is NOT a new FileView, host,
// protected production store, or a durable ticket journal. Its only native
// write request is via the existing M12i lab's increment() method.
Scope {
    id: bridge
    required property var nativeLab
    property var currentTicket: null
    property int ticketSequence: 0
    property string lastRefusal: "NOT_REQUESTED"
    property int outOfBandReceipts: 0
    property int seenReceipts: 0
    readonly property bool productionWriterAuthorized: false
    readonly property bool realTaskDataAccessAuthorized: false
    readonly property bool independentlyAuthenticatedNativeStage: false
    readonly property bool durableTicketsImplemented: false
    readonly property bool realNativeTestObservedByCI: false
    readonly property bool canStartTicket:
        nativeLab !== null && nativeLab.canIncrement &&
        (currentTicket === null ||
         currentTicket.state === "CONFIRMED" ||
         currentTicket.state === "REVIEW_REQUIRED" ||
         currentTicket.state === "REJECTED")

    function observation() {
        return {counter:nativeLab.counter,
                receipts:nativeLab.settledCount,
                epoch:nativeLab.epoch,
                phase:nativeLab.phase,
                fileState:nativeLab.fileState,
                pendingStage:nativeLab.pendingStage,
                status:nativeLab.status,
                connected:nativeLab.connected};
    }

    function refresh() {
        if (nativeLab === null) return;
        if (nativeLab.settledCount > seenReceipts) {
            if (!currentTicket ||
                    currentTicket.state === "CONFIRMED" ||
                    currentTicket.state === "REVIEW_REQUIRED" ||
                    currentTicket.state === "REJECTED")
                outOfBandReceipts += nativeLab.settledCount - seenReceipts;
            seenReceipts = nativeLab.settledCount;
        } else if (nativeLab.settledCount < seenReceipts) {
            seenReceipts = nativeLab.settledCount;
            // New lab instance, never certify an earlier session ticket.
        }
        if (currentTicket !== null)
            currentTicket = TicketLogic.observe(currentTicket, observation());
    }

    function requestTicket() {
        if (!canStartTicket) {
            lastRefusal = "OWNER_OR_PREVIOUS_TICKET_NOT_READY";
            return false;
        }
        var ticket = TicketLogic.begin(
            ++ticketSequence, nativeLab.counter, nativeLab.settledCount,
            nativeLab.epoch);
        if (ticket === null) {
            lastRefusal = "INVALID_NATIVE_BASELINE";
            return false;
        }
        currentTicket = ticket;
        if (!nativeLab.increment()) {
            currentTicket = {
                ticketId:ticket.ticketId,state:"REJECTED",
                reason:"M12I_ADMISSION_REFUSED",stageId:"",
                baselineCounter:ticket.baselineCounter,
                baselineReceipts:ticket.baselineReceipts,
                baselineEpoch:ticket.baselineEpoch
            };
            lastRefusal = "M12I_ADMISSION_REFUSED";
            return false;
        }
        var armed = TicketLogic.arm(currentTicket,nativeLab.pendingStage);
        if (armed === null) {
            lastRefusal = "NATIVE_STAGE_CORRELATION_FAILED";
            nativeLab.reject("M12N_NATIVE_STAGE_CORRELATION_FAILED");
            currentTicket = {
                ticketId:ticket.ticketId,state:"REVIEW_REQUIRED",
                reason:lastRefusal,stageId:"",
                baselineCounter:ticket.baselineCounter,
                baselineReceipts:ticket.baselineReceipts,
                baselineEpoch:ticket.baselineEpoch
            };
            return false;
        }
        currentTicket = armed;
        lastRefusal = "";
        refresh();
        return true;
    }

    Connections {
        target: bridge.nativeLab
        function onPhaseChanged() {bridge.refresh();}
        function onFileStateChanged() {bridge.refresh();}
        function onStatusChanged() {bridge.refresh();}
        function onCounterChanged() {bridge.refresh();}
        function onSettledCountChanged() {bridge.refresh();}
        function onPendingStageChanged() {bridge.refresh();}
        function onConnectedChanged() {bridge.refresh();}
        function onEpochChanged() {bridge.refresh();}
    }

    PanelWindow {
        visible: true
        implicitWidth: 480
        implicitHeight: 290
        focusable: true
        exclusiveZone: 0
        anchors { top: true; right: true }
        color: "#1B0623"
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#C74EC7"
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 9
                Text {
                    text: "M12n // NATIVE SAVE TICKET BRIDGE"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    width:parent.width
                    wrapMode:Text.WordWrap
                    text:"ISOLATED M12i FIXTURE ONLY // NOT THE LIVE TASKS STORE"
                    color:"#F2BE4E"
                    font.pixelSize:11
                }
                Rectangle {
                    width:190;height:32
                    color: button.pressed ? "#C74EC7" : "#1B0623"
                    border.color:bridge.canStartTicket ? "#55CFCA" : "#6C6975"
                    Text {
                        anchors.centerIn:parent
                        text:"TICKET INCREMENT"
                        font.pixelSize:11
                        color:bridge.canStartTicket ? "#DCF3FA" : "#9994A3"
                    }
                    MouseArea {
                        id:button
                        anchors.fill:parent
                        enabled:bridge.canStartTicket
                        onClicked:bridge.requestTicket()
                    }
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"TICKET: " +
                         (bridge.currentTicket ? bridge.currentTicket.ticketId : "NONE")
                    color:"#DCF3FA";font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"STATE: " +
                         (bridge.currentTicket ? bridge.currentTicket.state : "NOT_STARTED")
                    color:"#55CFCA";font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"REASON: " +
                         (bridge.currentTicket && bridge.currentTicket.reason ?
                          bridge.currentTicket.reason : bridge.lastRefusal)
                    color:"#F2BE4E";font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"OUT-OF-BAND RECEIPTS OBSERVED: " + bridge.outOfBandReceipts
                    color:bridge.outOfBandReceipts > 0 ? "#F2BE4E" : "#DCF3FA"
                    font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"CONFIRMED = M12i synthetic host receipt + UI ready. " +
                         "Not a trusted native callback origin, production save, " +
                         "or durable ticket across a crash."
                    color:"#F2BE4E";font.pixelSize:10
                }
            }
        }
    }
}
