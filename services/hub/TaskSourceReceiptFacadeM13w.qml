import QtQuick
import Quickshell
import "TaskSaveTicketContractM12o.js" as ExistingTicket
import "TaskSourceReceiptReviewPolicyM13w.js" as SourceReview

// TASKS M13w // Never-mounted, fail-closed *interface shape* only.
// This does not attach to ApolloHubTodoStore, shell.qml or any widget.
// No FileView/Process, no network/Secret Service, no source path, no writer.
// All production authority is literal false, not a runtime opt-in toggle.
Scope {
    id: facade

    readonly property bool enabled: false
    readonly property bool productionWriterAuthorized: false
    readonly property bool sourceOwnerAuthenticated: false
    readonly property bool nativeCallbackAuthenticated: false
    readonly property bool realTaskDataAccessAuthorized: false
    readonly property bool durableReceiptAuthenticated: false
    readonly property bool consentAuthenticated: false
    readonly property bool draftRecoveryEnabled: false
    readonly property var consumerSurfaces: ["HUB","DETAILS","PLANNER","PROJECTS"]

    // Same admission boundary as the existing disabled M12o facade.
    // No synthetic ticket or caller flags can turn this into a real save.
    function submit(surface, method, draft) {
        return {admitted:false, ticketId:"", state:"BLOCKED",
                disposition:"KEEP_DRAFT", reason:"M13W_DISABLED_NO_WRITER"};
    }

    // Inspection is explicitly synthetic and has no side effects.
    // All results retain the draft and refuse real save acknowledgment.
    function inspectSynthetic(surface, method, ticketId, before, after,
                              draftMetadata, sourcePin, evidence, snapshot) {
        var ticket = ExistingTicket.begin(surface,method,ticketId,
                                          before,after,draftMetadata);
        return SourceReview.inspectSynthetic(ticket,sourcePin,evidence,snapshot);
    }
}
