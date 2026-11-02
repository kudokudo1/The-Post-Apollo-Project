.pragma library
// TASKS M12p // Hub Mini's future ticket UI presenter.
// Pure, no filesystem, no writes. Unmounted in live behavior because
// ApolloHubTodoMini.ticketUiEnabled is a READONLY literal false.
// Use M12o reducer via explicit argument, not a second receipt authority.

var HUB_METHODS = {
    add:"addTask", rename:"renameTask", done:"setTaskDone", remove:"removeTask"
};
function copy(x) { return JSON.parse(JSON.stringify(x)); }

function begin(contract, kind, method, admission, baseline, draft) {
    if (!contract || typeof contract.begin !== "function" ||
            !Object.prototype.hasOwnProperty.call(HUB_METHODS,kind) ||
            HUB_METHODS[kind] !== method || !admission ||
            admission.admitted !== true ||
            typeof admission.ticketId !== "string" ||
            !admission.expected || !baseline ||
            typeof draft !== "object" || draft === null)
        return null;
    // The expected FULL view must come from the future coordinator's
    // admitted ticket; the Mini must never invent it from the old boolean.
    if (admission.baseline &&
            JSON.stringify(admission.baseline) !== JSON.stringify(baseline))
        return null;
    var t=contract.begin("HUB",method,admission.ticketId,
                         baseline,admission.expected,draft);
    if (!t) return null;
    return {kind:kind,ticket:t,bufferedReceipt:null};
}

function transition(pending, effect, status) {
    return {pending:pending,effect:effect,status:status};
}

function advance(contract, pending, event, observed) {
    if (!pending || !contract || typeof contract.reconcile !== "function")
        return transition(pending,"NONE","NO_TICKET");
    if (pending.ticket.state === "CONFIRMED" ||
            pending.ticket.state === "REVIEW_REQUIRED" ||
            pending.ticket.state === "BLOCKED" ||
            pending.ticket.state === "REJECTED")
        return transition(copy(pending),"NONE","TICKET_ALREADY_FINAL");

    var next=copy(pending);
    if (event && event.ticketId === next.ticket.ticketId) {
        if (event.state === "CONFIRMED" &&
                (!observed || observed.state === "saving" ||
                 observed.state === "loading")) {
            // Receipt came before the asynchronous store snapshot update.
            // Wait for a stable complete view before deciding any outcome.
            next.bufferedReceipt=copy(event);
            next.ticket=contract.reconcile(next.ticket,
                    {ticketId:next.ticket.ticketId,state:"VERIFYING"},observed);
            return transition(next,"KEEP_DRAFT","WAIT_FOR_CONFIRMED_SNAPSHOT");
        }
        next.ticket=contract.reconcile(next.ticket,event,observed);
        if (event.state === "CONFIRMED") next.bufferedReceipt=null;
    } else if (event && event.ticketId !== next.ticket.ticketId) {
        return transition(next,"KEEP_DRAFT","OTHER_TICKET");
    }

    if (next.bufferedReceipt && observed &&
            (observed.state === "ready" || observed.state === "empty")) {
        next.ticket=contract.reconcile(next.ticket,next.bufferedReceipt,observed);
        next.bufferedReceipt=null;
    }
    if (observed && (observed.state === "error" ||
                     observed.state === "unsupported") &&
            next.ticket.state !== "CONFIRMED" &&
            next.ticket.state !== "REVIEW_REQUIRED" &&
            next.ticket.state !== "BLOCKED" &&
            next.ticket.state !== "REJECTED") {
        next.ticket=contract.reconcile(next.ticket,
            {ticketId:next.ticket.ticketId,state:"REVIEW_REQUIRED"},observed);
        next.bufferedReceipt=null;
    }

    if (next.ticket.state === "CONFIRMED")
        return transition(next,"CLEAR_DRAFT","TICKET_AND_SNAPSHOT_CONFIRMED");
    if (next.ticket.state === "REJECTED" ||
            next.ticket.state === "BLOCKED" ||
            next.ticket.state === "REVIEW_REQUIRED")
        return transition(next,"KEEP_DRAFT_FINAL","SAVE_NOT_VERIFIED");
    return transition(next,"KEEP_DRAFT","AWAITING_TICKET_CONFIRMATION");
}
