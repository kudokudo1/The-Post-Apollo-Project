.pragma library

// TASKS M15d // Choose ONE existing in-memory editor category for a
// future protected checkpoint. This policy never observes task text,
// IDs, descriptions, paths, credentials or checkpoint bytes.
// Current chooser is metadata-only and grants ZERO capture authority.
var SOURCE = {
    ready: "SAVED TASKS // LOADED (REVISION UNVERIFIED)",
    empty: "SAVED TASKS // EMPTY (REVISION UNVERIFIED)",
    saving: "SAVED TASKS // SAVE IN FLIGHT",
    loading: "SAVED TASKS // LOADING",
    error: "SAVED TASKS // ERROR",
    unsupported: "SAVED TASKS // UNSUPPORTED"
};
var TARGETS = ["none", "entry", "details"];
var KEYS = ["entryDirty", "detailsDirty", "entrySavePending",
            "detailsSavePending", "sourceState"];
function safe(state, selected, entry, details, explanation, sourceLabel) {
    return {
        state:state,
        selectedTarget:selected,
        sourceStatus:sourceLabel,
        entryAvailable:entry,
        detailsAvailable:details,
        statusLabel:state==="ENTRY_SELECTED" ? "SELECTED // NEW TASK / RENAME" :
            state==="DETAILS_SELECTED" ? "SELECTED // TASK DETAILS" :
            state==="BOTH_DIRTY_CHOOSE_ONE" ? "TWO UNSAVED DRAFTS // CHOOSE ONE" :
            state==="CHOOSE_EDITOR" ? "SELECT AN UNSAVED EDITOR" :
            state==="SAVE_IN_PROGRESS" ? "SAVE PENDING // SOURCE UNCONFIRMED" :
            state==="SOURCE_REVIEW_REQUIRED" ? "SOURCE NOT READY // REVIEW REQUIRED" :
            state==="SELECTED_EDITOR_CLEAN" ? "SELECTION STALE // EDITOR NOW CLEAN" :
            state==="NO_UNSAVED_EDITOR" ? "NO MONITORED UNSAVED DRAFT" :
            "DRAFT TARGET // NOT VERIFIED",
        explanation:explanation,
        scopeLabel:"ENTRY + DETAILS ONLY // PLANNER / PROJECTS NOT INSPECTED",
        captureStatus:"ENCRYPTED CAPTURE // NOT AUTHORIZED",
        targetIdentityVerified:false,
        realSourceRevisionVerified:false,
        encryptedStorageAuthorized:false,
        consentAuthenticated:false,
        keyReleaseAuthorized:false,
        captureAuthorized:false,
        previewAuthorized:false,
        draftClearingAuthorized:false,
        sourceWriteAuthorized:false,
        taskTextRead:false,
        taskTextTransferred:false,
        checkpointCreated:false
    };
}
function view(signals, selected) {
    var target = TARGETS.indexOf(selected)>=0 ? selected : "none";
    var refused = safe("UNVERIFIED","none",false,false,
        "The editor status is incomplete or untrusted. No draft target can be selected.",
        "SAVED TASKS // UNKNOWN");
    if (!signals || typeof signals!=="object" || Array.isArray(signals)
            || Object.keys(signals).sort().join(",")!==KEYS.slice().sort().join(",")
            || typeof signals.entryDirty!=="boolean"
            || typeof signals.detailsDirty!=="boolean"
            || typeof signals.entrySavePending!=="boolean"
            || typeof signals.detailsSavePending!=="boolean"
            || typeof signals.sourceState!=="string"
            || !Object.prototype.hasOwnProperty.call(SOURCE,signals.sourceState))
        return refused;
    var ready = signals.sourceState==="ready" || signals.sourceState==="empty";
    var label=SOURCE[signals.sourceState];
    var entry=ready && signals.entryDirty &&
        !signals.entrySavePending && !signals.detailsSavePending;
    var details=ready && signals.detailsDirty &&
        !signals.entrySavePending && !signals.detailsSavePending;
    if(signals.entrySavePending || signals.detailsSavePending
            || signals.sourceState==="saving")
        return safe("SAVE_IN_PROGRESS",target,false,false,
            "A save is pending. Do not assume a callback proves that the draft reached disk. Keep all in-memory edits.",
            label);
    if(!ready)
        return safe("SOURCE_REVIEW_REQUIRED",target,false,false,
            "The saved TASKS source is loading, in error or unsupported. Resolve its state before selecting a recovery candidate.",
            label);
    if(target==="entry" && !signals.entryDirty ||
            target==="details" && !signals.detailsDirty)
        return safe("SELECTED_EDITOR_CLEAN",target,entry,details,
            "The previously selected editor no longer reports unsaved changes. Rechoose a dirty editor instead of relying on a stale selection.",
            label);
    if(target==="entry")
        return safe("ENTRY_SELECTED",target,entry,details,
            "New-task/rename editor is chosen for a future checkpoint. The selection is only an in-memory label; no task title or body has left the editor.",
            label);
    if(target==="details")
        return safe("DETAILS_SELECTED",target,entry,details,
            "Task-details editor is chosen for a future checkpoint. No task ID, description, priority or due date has left the editor.",
            label);
    if(signals.entryDirty && signals.detailsDirty)
        return safe("BOTH_DIRTY_CHOOSE_ONE","none",entry,details,
            "Both monitored editors have unsaved changes. Explicitly select one. No automatic combination, overwrite or capture.",
            label);
    if(signals.entryDirty || signals.detailsDirty)
        return safe("CHOOSE_EDITOR","none",entry,details,
            "An unfinished edit is present. Select the matching editor before requesting any future encrypted capture.",
            label);
    return safe("NO_UNSAVED_EDITOR","none",false,false,
        "Neither monitored editor currently reports an unfinished draft. Other TASKS and Planner editor surfaces are outside this check.",
        label);
}
