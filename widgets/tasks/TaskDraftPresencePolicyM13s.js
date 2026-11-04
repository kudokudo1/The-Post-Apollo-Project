.pragma library

// TASKS M13s // status-only signals from two already-mounted editors.
// Neither drafts, task IDs nor saved TASKS JSON cross this boundary.
// This is NOT an encrypted backup, authorized capture or host receipt.
var STATES = {
    ready: "SOURCE // LOADED (REVISION NOT VERIFIED)",
    empty: "SOURCE // EMPTY (REVISION NOT VERIFIED)",
    saving: "SOURCE // SAVE PENDING (NOT CONFIRMED)",
    loading: "SOURCE // LOADING",
    error: "SOURCE // ERROR / REVIEW REQUIRED",
    unsupported: "SOURCE // UNSUPPORTED VERSION / REVIEW REQUIRED"
};

function view(signals) {
    var x = signals || {};
    var complete = typeof x.entryDirty === "boolean"
        && typeof x.detailsDirty === "boolean"
        && typeof x.entrySavePending === "boolean"
        && typeof x.detailsSavePending === "boolean";
    var pending = complete && (x.entrySavePending || x.detailsSavePending);
    var dirty = complete && (x.entryDirty || x.detailsDirty);
    var source = typeof x.sourceState === "string"
        && Object.prototype.hasOwnProperty.call(STATES, x.sourceState)
        ? STATES[x.sourceState] : "SOURCE // UNVERIFIED";
    var status = !complete ? "EDITOR STATUS // NOT VERIFIED"
        : pending ? "EDITOR SAVE // PENDING / NOT CONFIRMED"
        : dirty ? "UNSAVED EDITOR CHANGE // OBSERVED"
        : "NO UNSAVED CHANGES IN MONITORED EDITORS";
    var caution = !complete
        ? "No assertion about current editor contents is possible."
        : dirty
        ? "This is live memory only. It is NOT encrypted or recoverable after restart."
        : "Only NEW TASK / RENAME and TASK DETAILS are monitored. Other editors are not inspected.";
    return {
        status: status, explanation: caution, sourceStatus: source,
        scope: "MONITORED // TASK ENTRY + TASK DETAILS ONLY",
        otherScope: "PROJECT / PLANNER EDITORS // NOT INSPECTED",
        recoveryStatus: "ENCRYPTED RECOVERY // OFF",
        draftContentRead: false, draftContentShared: false,
        encrypted: false, checkpointPresent: false,
        captureEnabled: false, keyReleaseAuthorized: false,
        restoreAuthorized: false, writeAuthorized: false
    };
}
