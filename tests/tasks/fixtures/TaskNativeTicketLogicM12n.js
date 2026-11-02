.pragma library
// M12n // PURE advisory ticket reducer for the existing isolated M12i native lab.
// Does not write files, reserve stages, authenticate QML events or grant
// production access. Host-confirmed synthetic receipt is stronger than
// onSaved(), but remains not an independently authenticated callback origin.

function _int(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= 0;
}

function begin(sequence, counter, receipts, epoch) {
    if (!_int(sequence) || sequence > 999999 ||
            !_int(counter) || !_int(receipts) || !_int(epoch))
        return null;
    return {ticketId:"m12n-native-ticket-" + String(sequence).padStart(6,"0"),
            state:"QUEUED",reason:"",stageId:"",baselineCounter:counter,
            baselineReceipts:receipts,baselineEpoch:epoch};
}

function arm(ticket, stageId) {
    if (!ticket || ticket.state !== "QUEUED" ||
            typeof stageId !== "string" ||
            !/^m12i-native-stage-[0-9]+$/.test(stageId))
        return null;
    return {ticketId:ticket.ticketId,state:"RESERVING",reason:"",
            stageId:stageId,baselineCounter:ticket.baselineCounter,
            baselineReceipts:ticket.baselineReceipts,
            baselineEpoch:ticket.baselineEpoch};
}

function _transition(t, state, reason) {
    return {ticketId:t.ticketId,state:state,reason:reason || "",
            stageId:t.stageId,baselineCounter:t.baselineCounter,
            baselineReceipts:t.baselineReceipts,baselineEpoch:t.baselineEpoch};
}

function observe(ticket, n) {
    if (!ticket) return null;
    if (ticket.state === "CONFIRMED" ||
            ticket.state === "REVIEW_REQUIRED" ||
            ticket.state === "REJECTED") return ticket;
    // The Quickshell signal can occur between increment() and arm(). Do
    // not infer native stage correlation until the call returns the stage.
    if (!ticket.stageId) return ticket;
    if (!n || !_int(n.counter) || !_int(n.receipts) ||
            !_int(n.epoch) || typeof n.phase !== "string" ||
            typeof n.fileState !== "string" ||
            typeof n.pendingStage !== "string" ||
            typeof n.status !== "string" ||
            typeof n.connected !== "boolean")
        return _transition(ticket,"REVIEW_REQUIRED","INVALID_NATIVE_OBSERVATION");

    if (n.phase === "RECOVERY_REVIEW" ||
            n.fileState === "RECOVERY_REVIEW" ||
            n.status.indexOf("HOST_EXITED") === 0 ||
            n.status.indexOf("STOPPED") === 0)
        return _transition(ticket,"REVIEW_REQUIRED","NATIVE_RECOVERY_REVIEW");

    if (n.epoch !== ticket.baselineEpoch)
        return _transition(ticket,"REVIEW_REQUIRED","UNEXPECTED_OWNER_EPOCH");

    if (n.receipts < ticket.baselineReceipts ||
            n.receipts > ticket.baselineReceipts + 1 ||
            n.counter < ticket.baselineCounter ||
            n.counter > ticket.baselineCounter + 1)
        return _transition(ticket,"REVIEW_REQUIRED","UNEXPECTED_COUNTER_OR_RECEIPTS");

    if (n.pendingStage !== "" && n.pendingStage !== ticket.stageId)
        return _transition(ticket,"REVIEW_REQUIRED","DIFFERENT_STAGE_OBSERVED");

    const incremented = (n.counter === ticket.baselineCounter + 1 &&
                         n.receipts === ticket.baselineReceipts + 1);
    const unadvanced = (n.counter === ticket.baselineCounter &&
                        n.receipts === ticket.baselineReceipts);
    if (!incremented && !unadvanced)
        return _transition(ticket,"REVIEW_REQUIRED","INCONSISTENT_COUNTER_AND_RECEIPTS");

    const settled = n.status === "TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED";
    if (incremented) {
        if (!settled || !n.connected || n.phase !== "JSON_ACTIVE" ||
                n.fileState !== "READY" || n.pendingStage !== "")
            return _transition(ticket,"SETTLING","");
        return _transition(ticket,"CONFIRMED","");
    }

    if (settled) {
        // A previous ticket's terminal status cannot confirm new work.
        // M12i changes it to SYNTHETIC_HOST_READY on reserve reply; until
        // that reply arrives, leave the new ticket pending.
        if (n.fileState === "READY" && n.pendingStage === "")
            return _transition(ticket,"RESERVING","");
    }
    if (!n.connected || n.phase !== "JSON_ACTIVE")
        return _transition(ticket,"REVIEW_REQUIRED","NATIVE_OWNER_UNAVAILABLE");
    if (n.fileState === "SAVING") return _transition(ticket,"WRITING","");
    if (n.fileState === "VERIFYING") return _transition(ticket,"VERIFYING","");
    if (n.fileState === "SETTLING") return _transition(ticket,"SETTLING","");
    if (n.fileState === "RESERVING" || n.fileState === "READY")
        return _transition(ticket,"RESERVING","");
    return _transition(ticket,"REVIEW_REQUIRED","UNEXPECTED_NATIVE_FILE_STATE");
}
