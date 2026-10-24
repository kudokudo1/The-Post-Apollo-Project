.pragma library

// M10o: PURE, UNMOUNTED TASKS writer-handoff design contract.
// NOT a writer, lock, authorization token, Quickshell host, migration,
// or replacement for ApolloHubTodoStore. This module never grants SQLite
// writes. External witness booleans are simulated evidence, not proof.
var VERSION=1;
var PHASES=["JSON_ACTIVE","FREEZE_REQUESTED","JSON_QUIESCED",
            "SHADOW_VERIFIED","AWAITING_OPERATOR","RECOVERY_REVIEW"];
var STATE_KEYS=["version","phase","sessionId","writerId","sequence",
                "sourceSha256","shadowModelSha256","reason"];
var REVIEW_FIELDS=["legacyWriterQuiescenceReviewed",
    "exclusiveNewWriterReviewed","hostRuntimeAcceptanceReviewed",
    "sqliteOnlineBackupReviewed","restartRecoveryReviewed",
    "rollbackProcedureReviewed"];

function failure(reason) {
    return {ok:false,reason:reason,writeReady:false,
        sqliteWriteAuthorized:false,liveChangePerformed:false};
}
function object(x) {
    return x!==null && typeof x==="object" && !Array.isArray(x);
}
function exactKeys(x,fields) {
    if(!object(x)) return false;
    var got=Object.keys(x);
    if(got.length!==fields.length) return false;
    for(var i=0;i<fields.length;i++)
        if(!Object.prototype.hasOwnProperty.call(x,fields[i])) return false;
    return true;
}
function identity(x) {
    return typeof x==="string" && /^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(x);
}
function hash(x) {
    return typeof x==="string" && /^[a-f0-9]{64}$/.test(x);
}
function valid(s) {
    return exactKeys(s,STATE_KEYS) && s.version===VERSION
        && PHASES.indexOf(s.phase)>=0 && identity(s.sessionId)
        && identity(s.writerId)
        && Number.isSafeInteger(s.sequence)
        && s.sequence>=0 && s.sequence<1000000000
        && (s.sourceSha256===null || hash(s.sourceSha256))
        && (s.shadowModelSha256===null || hash(s.shadowModelSha256))
        && typeof s.reason==="string" && s.reason.length<=80
        && (s.phase==="JSON_ACTIVE" || s.phase==="FREEZE_REQUESTED"
            || s.sourceSha256!==null)
        && (s.phase!=="SHADOW_VERIFIED" && s.phase!=="AWAITING_OPERATOR"
            || s.shadowModelSha256!==null)
        && (s.phase!=="JSON_ACTIVE" || s.sequence===0
            && s.sourceSha256===null && s.shadowModelSha256===null);
}
function clone(s) {
    return {version:s.version,phase:s.phase,sessionId:s.sessionId,
        writerId:s.writerId,sequence:s.sequence,
        sourceSha256:s.sourceSha256,shadowModelSha256:s.shadowModelSha256,
        reason:s.reason};
}
function begin(sessionId,writerId) {
    if(!identity(sessionId) || !identity(writerId)
            || sessionId===writerId)
        return failure("INVALID_IDENTITIES");
    return {ok:true,reason:"",writeReady:false,
        sqliteWriteAuthorized:false,liveChangePerformed:false,
        state:{version:VERSION,phase:"JSON_ACTIVE",sessionId:sessionId,
            writerId:writerId,sequence:0,sourceSha256:null,
            shadowModelSha256:null,reason:""}};
}
function response(s) {
    return {ok:true,reason:"",writeReady:false,
        sqliteWriteAuthorized:false,liveChangePerformed:false,state:s};
}
function gate(s) {
    if(!valid(s)) return {ok:false,reason:"INVALID_STATE",
        legacyStagePermittedByContract:false,sqliteWriteAuthorized:false,
        writeReady:false};
    // This is a *simulated* legacy-stage gate. An actual QML host must
    // call it before EVERY entry into ApolloHubTodoStore.stage() and must
    // persist/recover its gate state; M10o does not do that.
    return {ok:true,reason:"",legacyStagePermittedByContract:
        s.phase==="JSON_ACTIVE",sqliteWriteAuthorized:false,
        writeReady:false};
}
function checkTransition(s,sessionId,expectedSequence,phase) {
    if(!valid(s)) return "INVALID_STATE";
    if(s.sessionId!==sessionId) return "STALE_SESSION";
    if(s.sequence!==expectedSequence) return "STALE_SEQUENCE";
    if(s.phase!==phase) return "UNEXPECTED_PHASE";
    if(s.sequence>=999999999) return "SEQUENCE_EXHAUSTED";
    return "";
}
function requestFreeze(s,sessionId,expectedSequence) {
    var reason=checkTransition(s,sessionId,expectedSequence,"JSON_ACTIVE");
    if(reason) return failure(reason);
    var n=clone(s);
    n.phase="FREEZE_REQUESTED";
    n.sequence++;
    // A prospective QML integration must atomically stop admitting new
    // stage() calls BEFORE acknowledging requestFreeze.
    return response(n);
}
function observeDrain(s,sessionId,expectedSequence,evidence) {
    var reason=checkTransition(s,sessionId,expectedSequence,"FREEZE_REQUESTED");
    if(reason) return failure(reason);
    if(!object(evidence) || evidence.writerId!==s.writerId
            || evidence.stageGateClosed!==true)
        return failure("LEGACY_STAGE_GATE_NOT_CLOSED");
    if(evidence.saveFailed===true)
        return fault(s,sessionId,expectedSequence,"LEGACY_SAVE_FAILED");
    if(evidence.pendingSave===true || evidence.saveCallbacksSettled!==true)
        return failure("WAIT_FOR_PENDING_SAVE");
    if(evidence.storageState!=="ready" && evidence.storageState!=="empty")
        return failure("LEGACY_STORE_NOT_SETTLED");
    if(!hash(evidence.diskSha256) || !hash(evidence.secondReadSha256)
        || evidence.diskSha256!==evidence.secondReadSha256)
        return failure("SOURCE_READBACK_UNSTABLE");
    var n=clone(s);
    n.phase="JSON_QUIESCED";
    n.sequence++;
    n.sourceSha256=evidence.diskSha256;
    return response(n);
}
function verifyShadow(s,sessionId,expectedSequence,evidence) {
    var reason=checkTransition(s,sessionId,expectedSequence,"JSON_QUIESCED");
    if(reason) return failure(reason);
    if(!object(evidence) || evidence.sourceSha256!==s.sourceSha256
            || !hash(evidence.candidateModelSha256)
            || evidence.sqliteRevision!==0
            || evidence.sqliteBackupRevision!==0
            || evidence.shadowModelSha256!==evidence.candidateModelSha256
            || evidence.sqliteBackupModelSha256!==evidence.candidateModelSha256
            || evidence.blockedOperations!==0
            || evidence.legacyWriterStillQuiesced!==true)
        return failure("SHADOW_PARITY_OR_FREEZE_NOT_PROVEN");
    var n=clone(s);
    n.phase="SHADOW_VERIFIED";
    n.sequence++;
    n.shadowModelSha256=evidence.candidateModelSha256;
    return response(n);
}
function prepareReview(s,sessionId,expectedSequence,evidence) {
    var reason=checkTransition(s,sessionId,expectedSequence,"SHADOW_VERIFIED");
    if(reason) return failure(reason);
    if(!object(evidence)) return failure("MISSING_REVIEW_EVIDENCE");
    for(var i=0;i<REVIEW_FIELDS.length;i++)
        if(evidence[REVIEW_FIELDS[i]]!==true)
            return failure("REVIEW_GATE_OPEN_"+REVIEW_FIELDS[i]);
    // This phase deliberately does NOT mean SQLITE_ACTIVE. Only a
    // separately authorized, implemented host may ever switch writers.
    var n=clone(s);
    n.phase="AWAITING_OPERATOR";
    n.sequence++;
    return response(n);
}
function fault(s,sessionId,expectedSequence,why) {
    if(!valid(s)) return failure("INVALID_STATE");
    if(s.sessionId!==sessionId || s.sequence!==expectedSequence)
        return failure("STALE_OR_UNEXPECTED_SESSION");
    if(typeof why!=="string" || !/^[A-Z0-9_]{1,80}$/.test(why))
        return failure("INVALID_FAULT_REASON");
    var n=clone(s);
    n.phase="RECOVERY_REVIEW";
    n.reason=why;
    n.sequence++;
    return response(n);
}
function restartFromCheckpoint(raw) {
    // Deserializing a checkpoint NEVER revives permission to write. Even an
    // old JSON_ACTIVE snapshot is untrusted across process identity changes.
    var original;
    try {
        original=JSON.parse(raw);
    } catch(e) {
        return failure("INVALID_CHECKPOINT_JSON");
    }
    if(!valid(original)) return failure("INVALID_CHECKPOINT_STATE");
    if(original.sequence>=999999999) return failure("SEQUENCE_EXHAUSTED");
    var n=clone(original);
    n.phase="RECOVERY_REVIEW";
    n.reason="SESSION_RESTART_REQUIRES_INSPECTION";
    n.sequence++;
    return response(n);
}
function checkpoint(s) {
    if(!valid(s)) return failure("INVALID_STATE");
    return {ok:true,reason:"",writeReady:false,
        sqliteWriteAuthorized:false,liveChangePerformed:false,
        raw:JSON.stringify(s)};
}
function inspect(s) {
    var g=gate(s);
    if(!g.ok) return g;
    return {ok:true,phase:s.phase,sourceSha256:s.sourceSha256,
        candidateModelSha256:s.shadowModelSha256,
        legacyStagePermittedByContract:g.legacyStagePermittedByContract,
        sqliteWriteAuthorized:false,writeReady:false,
        activationAvailable:false,requiresOperator:true};
}
