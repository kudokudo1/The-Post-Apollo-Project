.pragma library
// TASKS M13w // NEVER-MOUNTED, NEGATIVE-ONLY SOURCE RECEIPT REVIEW.
// Reuses M12o consumer ticket shape and M13v's synthetic source receipt.
// No I/O, Process, FileView, storage, keyring or actual caller authentication.
// SOURCE_MATCHED does NOT mean a task save is acknowledged or a draft cleared.

var ROUTES = {
    HUB:["addTask","renameTask","setTaskDone","removeTask"],
    DETAILS:["updateTaskDetails"],
    PLANNER:["addTask","updateTaskDetails"],
    PROJECTS:["createProject","renameProject","deleteProject","assignTaskProject"]
};
var MUST_REMAIN_FALSE = [
    "productionActivation","sourceTrusted","hostAuthenticated",
    "userConsentAuthenticated","keyReleaseAuthorized","captureAuthorized",
    "previewAuthorized","deleteAuthorized","restoreAuthorized",
    "taskWriteAuthorized","independentNativeCallbackAuthenticated",
    "sourceWritePerformed","pendingStageReplayAuthorized","realDraftDataRead",
    "durableUserSaveAcknowledged","automaticRecoveryAuthorized"
];

function exact(x, keys) {
    if (!x || typeof x!=="object" || Array.isArray(x)) return false;
    var a=Object.keys(x).sort(), b=keys.slice().sort();
    return JSON.stringify(a)===JSON.stringify(b);
}
function safeInt(x) {
    return typeof x==="number" && isFinite(x) && Math.floor(x)===x
        && x>=0 && x<=1000000;
}
function hash(x) { return typeof x==="string" && /^[a-f0-9]{64}$/.test(x); }
function stageId(x) {
    return typeof x==="string" && /^m13v-stage-[0-9]{6}$/.test(x);
}
function view(x) {
    return x && typeof x==="object" && !Array.isArray(x)
        && (x.state==="ready" || x.state==="empty")
        && typeof x.writable==="boolean"
        && Array.isArray(x.items) && Array.isArray(x.projects)
        && typeof x.total==="number" && typeof x.remaining==="number";
}
function safeResult(code, state) {
    return {
        status:code, state:state||"REVIEW_REQUIRED",
        lastConfirmedVisible:true, draftDisposition:"KEEP_DRAFT",
        draftPresentInResult:false, autoReplay:false, localSaved:false,
        sourceReceiptAuthenticated:false, userSaveAcknowledged:false,
        keyReleaseAuthorized:false, realGrantActive:false,
        canWriteTasks:false, canCapture:false, canPreview:false,
        canClear:false, canRestore:false
    };
}
function validTicket(ticket) {
    return ticket && typeof ticket==="object" && !Array.isArray(ticket)
        && typeof ticket.ticketId==="string"
        && /^m12o-[A-Za-z0-9._:-]{8,80}$/.test(ticket.ticketId)
        && Object.prototype.hasOwnProperty.call(ROUTES,ticket.surface)
        && ROUTES[ticket.surface].indexOf(ticket.method)>=0
        && ticket.state==="QUEUED" && ticket.disposition==="KEEP_DRAFT"
        && view(ticket.baseline) && view(ticket.expected)
        && ticket.draft!==undefined;
}
function expectedPin(pin,ticketId) {
    return exact(pin,["ticketId","stageId","ownerEpoch",
                      "baselineRevision","expectedSourceSha256"])
        && pin.ticketId===ticketId && stageId(pin.stageId)
        && safeInt(pin.ownerEpoch) && safeInt(pin.baselineRevision)
        && pin.baselineRevision<1000000 && hash(pin.expectedSourceSha256);
}
function inspectSynthetic(ticket,pin,evidence,snapshot) {
    if (!validTicket(ticket))
        return safeResult("TICKET_NOT_VERIFIED");
    if (!expectedPin(pin,ticket.ticketId))
        return safeResult("SOURCE_PIN_NOT_VERIFIED");
    if (evidence===null || evidence===undefined)
        return safeResult("WAITING_FOR_SOURCE_EVIDENCE","PENDING_REVIEW");
    // Only M13v's *explicit* synthetic fixture shape, not a fabricated
    // production approval or a QML-provided "authenticated:true" bit.
    var evidenceKeys=["status","fixtureOnly","receipt","independentlyReadBack"]
        .concat(MUST_REMAIN_FALSE);
    if (!exact(evidence,evidenceKeys)
            || evidence.status!=="SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED"
            || evidence.fixtureOnly!==true
            || evidence.independentlyReadBack!==true)
        return safeResult("UNTRUSTED_SOURCE_EVIDENCE");
    for (var i=0;i<MUST_REMAIN_FALSE.length;i++)
        if (evidence[MUST_REMAIN_FALSE[i]]!==false)
            return safeResult("UNTRUSTED_SOURCE_EVIDENCE");
    var r=evidence.receipt;
    if (!exact(r,["revision","stageId","sourceSha256","ownerEpoch"])
            || !safeInt(r.revision)
            || r.revision!==pin.baselineRevision+1
            || r.stageId!==pin.stageId || !hash(r.sourceSha256)
            || r.sourceSha256!==pin.expectedSourceSha256
            || r.ownerEpoch!==pin.ownerEpoch)
        return safeResult("STALE_OR_MISMATCHED_SOURCE_REVISION");
    if (!view(snapshot)
            || JSON.stringify(snapshot)!==JSON.stringify(ticket.expected))
        return safeResult("SAVED_SNAPSHOT_MISMATCH");
    // Even a perfectly source-consistent synthetic receipt has NO authority.
    // A future production host must separately authenticate and fence the
    // source and operator; this code will not "graduate" by changing a flag.
    return safeResult("SOURCE_MATCHED_SYNTHETIC_ONLY","NEEDS_TRUSTED_OWNER");
}
