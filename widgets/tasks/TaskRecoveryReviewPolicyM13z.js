.pragma library

// TASKS M13z // read-only save-review presentation, NOT a source connector.
// M13y inspects DISPOSABLE SQLite/JSON only. The real TASKS source is NOT
// inspected by this QML policy, and every state retains the user's draft.
// All labels are authored here. No untrusted source payload is echoed.
var SCENARIOS = {
    baseline: {
        classification: "RESERVED_SOURCE_STILL_AT_BASELINE",
        sourcePosition: "BASELINE",
        pendingStagePresent: true,
        label: "SOURCE STILL UNCHANGED",
        headline: "SAVE MAY NOT HAVE REACHED THE FILE",
        explanation: "The simulated source still matches its pre-save bytes. This is not permission to replay the edit: a crash or competing write can leave an uncertain result."
    },
    expected: {
        classification: "RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED",
        sourcePosition: "EXPECTED",
        pendingStagePresent: true,
        label: "NEW BYTES // UNSETTLED RECEIPT",
        headline: "CHANGE APPEARS, BUT CONFIRMATION IS MISSING",
        explanation: "The simulated source contains expected new bytes. The journal still has a reserved stage, so the editor must not treat this as a confirmed save."
    },
    settled: {
        classification: "SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED",
        sourcePosition: "LAST_SETTLED",
        pendingStagePresent: false,
        label: "RECEIPT SETTLED / UI NOT ACKNOWLEDGED",
        headline: "SOURCE AND JOURNAL AGREE; UI ACK IS LOST",
        explanation: "The simulated journal settled and the saved bytes match. This does not prove the original UI saw the acknowledgment or that its draft can be cleared."
    }
};
var M13Y_FALSE_FLAGS = [
    "realTaskDataRead","productionActivation","nativeCallbackAuthenticated",
    "hostAuthenticated","sourceOwnerAuthenticated","consentAuthenticated",
    "captureAuthorized","previewAuthorized","deleteAuthorized",
    "restoreAuthorized","keyReleaseAuthorized","taskWriteAuthorized",
    "automaticReplayAuthorized","savedAcknowledged","clearDraftAuthorized"
];
var M13Y_KEYS = [
    "classification","lastSettledRevision","pendingStagePresent",
    "sourcePosition","draftDisposition","lastConfirmedDisplay",
    "nextAction","fixtureOnly","journalReadOnly"
].concat(M13Y_FALSE_FLAGS);

function sameKeys(value,keys) {
    if(!value || typeof value!=="object" || Array.isArray(value))return false;
    var actual=Object.keys(value).sort();
    var expected=keys.slice().sort();
    return JSON.stringify(actual)===JSON.stringify(expected);
}
function safe(stage,context) {
    return {
        origin:context,
        title:stage ? stage.label : "SAVE STATE NOT VERIFIED",
        headline:stage ? stage.headline : "NO TRUSTED SOURCE OBSERVATION",
        explanation:stage ? stage.explanation
            : "No live source journal is connected. The existing TASKS editors remain the only local unsaved-change indicators.",
        draftStatus:"KEEP UNSAVED DRAFT",
        displayStatus:"KEEP LAST CONFIRMED VIEW",
        nextStep:"MANUAL REVIEW ONLY",
        canReplay:false,canRestore:false,canClearDraft:false,
        canDeleteCheckpoint:false,canWriteTasks:false,
        nativeSaveAcknowledged:false,encryptedRecoveryEnabled:false,
        liveSourceEvidenceConnected:false,readTaskData:false,
        keyReleaseAuthorized:false
    };
}
function current() {
    // Literal no-provider default. Never consume caller assertions here.
    return safe(null,"LIVE // SOURCE REVIEW NOT CONNECTED");
}
function example(id) {
    // The selector changes VISUAL EXAMPLES, never the source or any draft.
    if(typeof id!=="string" || !Object.prototype.hasOwnProperty.call(SCENARIOS,id))
        return safe(null,"EXAMPLE // UNKNOWN CASE");
    return safe(SCENARIOS[id],"EXAMPLE ONLY // NOT A LIVE SAVE");
}
function syntheticResult(report) {
    // M13y returns a fixture-only redacted frame. Projection is useful for
    // offline UI-contract tests, but is NEVER wired to the live TASKS menu.
    var invalid=safe(null,"SYNTHETIC FIXTURE // UNVERIFIED");
    if(!sameKeys(report,M13Y_KEYS)
            || report.fixtureOnly!==true || report.journalReadOnly!==true
            || report.draftDisposition!=="KEEP_DRAFT"
            || report.lastConfirmedDisplay!=="KEEP_LAST_CONFIRMED"
            || report.nextAction!=="OPERATOR_REVIEW_ONLY"
            || typeof report.lastSettledRevision!=="number"
            || !isFinite(report.lastSettledRevision)
            || report.lastSettledRevision<0
            || report.lastSettledRevision>1000000
            || Math.floor(report.lastSettledRevision)!==report.lastSettledRevision)
        return invalid;
    for(var j=0;j<M13Y_FALSE_FLAGS.length;j++)
        if(report[M13Y_FALSE_FLAGS[j]]!==false)return invalid;
    var ids=["baseline","expected","settled"];
    for(var k=0;k<ids.length;k++){
        var match=SCENARIOS[ids[k]];
        if(report.classification===match.classification
                && report.sourcePosition===match.sourcePosition
                && report.pendingStagePresent===match.pendingStagePresent)
            return safe(match,"SYNTHETIC FIXTURE ONLY // NOT LIVE");
    }
    return invalid;
}
