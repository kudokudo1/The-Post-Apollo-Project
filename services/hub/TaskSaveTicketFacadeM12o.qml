import QtQuick
import Quickshell
import "TaskSaveTicketContractM12o.js" as TicketContract

// TASKS M12o // Unmounted, disabled-only public API shape.
// DO NOT import from shell.qml or ApolloHubTodoStore.qml.
// This facade has NO FileView, Process, network, storagePath, or mutation
// authority. It cannot be enabled by a runtime property or incoming message.
Scope {
    id: facade
    readonly property bool enabled: false
    readonly property bool productionWriterAuthorized: false
    readonly property bool realTaskDataAccessAuthorized: false
    readonly property bool ticketCompletionAuthorityVerified: false
    readonly property bool nativeTicketAccepted: false
    readonly property bool exposesTicketProtocolOnly: true
    readonly property var consumerSurfaces: ["HUB", "DETAILS", "PLANNER", "PROJECTS"]

    // The future production API will return a ticket identifier on actual
    // admission. This disabled facade can NEVER admit anything.
    function submit(surface, method, draft) {
        return {admitted:false, ticketId:"", state:"BLOCKED",
                disposition:"KEEP_DRAFT",
                reason:"M12O_DISABLED_NO_WRITER"};
    }

    // Pure, test-only contract inspection. Does not run a mutation.
    function previewSynthetic(surface, method, ticketId, before, after, draft) {
        return TicketContract.begin(surface, method, ticketId,
                                    before, after, draft);
    }

    function reconcileSynthetic(ticket, event, snapshot) {
        return TicketContract.reconcile(ticket, event, snapshot);
    }
}
