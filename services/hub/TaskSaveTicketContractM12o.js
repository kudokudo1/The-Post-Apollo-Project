.pragma library
// TASKS M12o // disabled-only UI ticket reconciliation contract.
// PURE QML-compatible JavaScript, deliberately NOT imported into the live
// TASKS singleton or its four consumers. No persistence or host authority.
// Every "CONFIRMED" in this model requires an explicit *synthetic* fixture
// receipt AND an independently supplied matching complete view. This is
// not cryptographic proof or a production native callback.

var OPERATIONS = {
    "HUB": ["addTask", "renameTask", "setTaskDone", "removeTask"],
    "DETAILS": ["updateTaskDetails"],
    "PLANNER": ["addTask", "updateTaskDetails"],
    "PROJECTS": ["createProject", "renameProject", "deleteProject",
                 "assignTaskProject"]
};
var TERMINAL = ["CONFIRMED", "REJECTED", "BLOCKED", "REVIEW_REQUIRED"];
var PENDING = ["QUEUED", "PREPARING", "WRITING", "VERIFYING"];

function copy(x) {
    return JSON.parse(JSON.stringify(x));
}
function isView(x) {
    return x && typeof x === "object" && !Array.isArray(x)
        && (x.state === "ready" || x.state === "empty")
        && typeof x.writable === "boolean"
        && Array.isArray(x.items) && Array.isArray(x.projects)
        && typeof x.total === "number" && typeof x.remaining === "number";
}
function validTicketId(x) {
    return typeof x === "string" && /^m12o-[A-Za-z0-9._:-]{8,80}$/.test(x);
}
function supported(surface, method) {
    return Object.prototype.hasOwnProperty.call(OPERATIONS, surface)
        && OPERATIONS[surface].indexOf(method) >= 0;
}
function begin(surface, method, ticketId, baseline, expected, draft) {
    if (!supported(surface, method) || !validTicketId(ticketId) ||
            !isView(baseline) || !isView(expected) ||
            JSON.stringify(baseline) === JSON.stringify(expected) ||
            draft === undefined) return null;
    return {
        ticketId:ticketId, surface:surface, method:method, state:"QUEUED",
        disposition:"KEEP_DRAFT", reason:"",
        baseline:copy(baseline), expected:copy(expected), draft:copy(draft)
    };
}
function withState(ticket, state, reason) {
    var next = copy(ticket);
    next.state = state;
    next.reason = reason || "";
    next.disposition = state === "CONFIRMED" ? "CLEAR_DRAFT" : "KEEP_DRAFT";
    return next;
}
function reconcile(ticket, event, observedSnapshot) {
    if (!ticket || typeof ticket !== "object") return null;
    if (TERMINAL.indexOf(ticket.state) >= 0) return copy(ticket);

    // An event for a different save may never acknowledge this ticket.
    // A malformed/unrecognized event is ignored, never trusted as success.
    if (!event || typeof event !== "object" ||
            event.ticketId !== ticket.ticketId ||
            typeof event.state !== "string") return copy(ticket);

    if (event.state === "REJECTED" || event.state === "BLOCKED" ||
            event.state === "REVIEW_REQUIRED")
        return withState(ticket, event.state, "SAVE_NOT_CONFIRMED");

    if (event.state === "CONFIRMED") {
        // Explicitly test-only. The future real API needs independently
        // approved source/receipt authority, not a boolean or a self-report.
        if (event.evidence !== "SYNTHETIC_READBACK_RECEIPT")
            return withState(ticket, "REVIEW_REQUIRED", "UNVERIFIED_COMPLETION");
        if (!isView(observedSnapshot) ||
                JSON.stringify(observedSnapshot) !== JSON.stringify(ticket.expected))
            return withState(ticket, "REVIEW_REQUIRED", "COMPLETION_SNAPSHOT_MISMATCH");
        return withState(ticket, "CONFIRMED", "");
    }

    if (PENDING.indexOf(event.state) >= 0) {
        // Do not regress visible pending state on out-of-order callbacks.
        var positions = {"QUEUED":0,"PREPARING":1,"WRITING":2,"VERIFYING":3};
        if (positions[event.state] > positions[ticket.state])
            return withState(ticket, event.state, "");
    }
    return copy(ticket);
}
