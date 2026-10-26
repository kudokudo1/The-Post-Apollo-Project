.pragma library

// M11f PURE, UNMOUNTED acceptance model for a FUTURE OS-owned writer gate.
// Evidence inputs are SYNTHETIC and CAN BE FORGED. Never load this module
// in ApolloHubTodoStore or use mock eligibility as real writer authority.
var VERSION=1;
var MARK="M11E_SYNTHETIC_ONLY";

function state() {
    return {version:VERSION,phase:"BOOT_LOCKED",reason:"",owner:null,
        confirmedRaw:null,revision:-1,sequence:1,stageId:null,
        stagedRaw:null,freezeRequested:false,committed:0};
}
function copy(s) {
    return {version:s.version,phase:s.phase,reason:s.reason,
        owner:s.owner===null?null:{
            writerId:s.owner.writerId,sessionId:s.owner.sessionId,
            epoch:s.owner.epoch,sourceHash:s.owner.sourceHash},
        confirmedRaw:s.confirmedRaw,revision:s.revision,
        sequence:s.sequence,stageId:s.stageId,stagedRaw:s.stagedRaw,
        freezeRequested:s.freezeRequested,committed:s.committed};
}
function output(s,allowed,reason) {
    return {accepted:allowed===true,reason:reason||"",state:s,
        mockOnly:true,mockStageEligible:eligible(s),
        productionWriteAuthorized:false,sqliteWriteAuthorized:false,
        migrationAuthorized:false,remoteWriteAuthorized:false};
}
function eligible(s) {
    return s.phase==="MOCK_READY" && !s.freezeRequested
        && s.stageId===null && s.stagedRaw===null;
}
function hash(value) {
    return typeof value==="string" && /^[0-9a-f]{64}$/.test(value);
}
function token(value) {
    return typeof value==="string"
        && /^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(value);
}
function fields(x, expected) {
    if (!x || typeof x!=="object" || Array.isArray(x)
            || Object.keys(x).length!==expected.length)
        return false;
    return expected.every(function(key) {
        return Object.prototype.hasOwnProperty.call(x,key);
    });
}
function fixture(raw) {
    if (typeof raw!=="string" || raw.length===0 || raw.length>2048)
        return null;
    try {
        var obj=JSON.parse(raw);
        if (!fields(obj,["fixture","revision","counter","marker"])
                || obj.fixture!==MARK || obj.marker!=="sample"
                || !Number.isSafeInteger(obj.revision)
                || obj.revision<0 || obj.revision>1000000
                || obj.counter!==obj.revision) return null;
        return obj;
    } catch(e) {return null;}
}
function fault(s,why) {
    var n=copy(s);
    n.phase="RECOVERY_REVIEW";
    n.reason=why;
    n.stageId=null;
    n.stagedRaw=null;
    n.freezeRequested=true;
    // Last fully confirmed bytes remain observable for read-only review.
    return output(n,false,why);
}
function reviewMockOwner(s,e) {
    if (s.phase!=="BOOT_LOCKED") return output(s,false,"NOT_BOOT_LOCKED");
    var keys=["writerId","sessionId","epoch","sourceHash","hostPhase",
        "flockObserved","callbackQueueDrained","sourceStable","confirmedRaw"];
    if (!fields(e,keys) || !token(e.writerId) || !token(e.sessionId)
            || e.writerId===e.sessionId || !Number.isSafeInteger(e.epoch)
            || e.epoch<0 || e.epoch>=1000000000
            || !hash(e.sourceHash) || e.hostPhase!=="JSON_ACTIVE"
            || e.flockObserved!==true || e.callbackQueueDrained!==true
            || e.sourceStable!==true)
        return fault(s,"MISSING_MOCK_OWNER_EVIDENCE");
    var doc=fixture(e.confirmedRaw);
    if (doc===null) return fault(s,"INVALID_SYNTHETIC_SOURCE");
    var n=copy(s);
    n.phase="MOCK_READY";
    n.owner={writerId:e.writerId,sessionId:e.sessionId,
        epoch:e.epoch,sourceHash:e.sourceHash};
    n.confirmedRaw=e.confirmedRaw;
    n.revision=doc.revision;
    return output(n,true,"MOCK_REVIEW_ONLY");
}
function proposeStage(s,raw) {
    if (!eligible(s)) return output(s,false,"MOCK_ADMISSION_CLOSED");
    var proposed=fixture(raw);
    if (proposed===null || proposed.revision!==s.revision+1)
        return output(s,false,"INVALID_SYNTHETIC_INCREMENT");
    if (s.sequence>=1000000000) return fault(s,"STAGE_SEQUENCE_EXHAUSTED");
    var n=copy(s);
    n.phase="MOCK_RESERVING";
    n.stageId="mock-stage-"+s.sequence;
    n.sequence++;
    n.stagedRaw=raw;
    return output(n,true,"WAIT_FOR_DURABLE_RESERVATION");
}
function match(s,r,kind,keys) {
    return fields(r,keys) && r.kind===kind && s.owner!==null
        && r.writerId===s.owner.writerId
        && r.sessionId===s.owner.sessionId && r.epoch===s.owner.epoch
        && r.stageId===s.stageId;
}
function acceptReservation(s,receipt) {
    if (s.phase!=="MOCK_RESERVING" || s.stageId===null)
        return output(s,false,"NO_RESERVED_STAGE");
    if (!match(s,receipt,"reserve",["kind","writerId","sessionId",
            "epoch","stageId","persisted","sourceHash"])
            || receipt.persisted!==true
            || receipt.sourceHash!==s.owner.sourceHash)
        return fault(s,"STALE_OR_UNVERIFIED_RESERVATION");
    var n=copy(s);
    n.phase="MOCK_SAVING";
    return output(n,true,"DISPATCH_SIMULATED_FILEVIEW_ONLY");
}
function onSaved(s) {
    if (s.phase!=="MOCK_SAVING") return fault(s,"UNEXPECTED_SAVE_CALLBACK");
    var n=copy(s);
    n.phase="MOCK_VERIFYING";
    return output(n,true,"WAIT_FOR_READBACK");
}
function verifyReadback(s,raw) {
    if (s.phase!=="MOCK_VERIFYING") return fault(s,"UNEXPECTED_READBACK");
    var observed=fixture(raw);
    if (observed===null || raw!==s.stagedRaw
            || observed.revision!==s.revision+1)
        return fault(s,"READBACK_NOT_MATCHED");
    var n=copy(s);
    n.phase="MOCK_SETTLING";
    return output(n,true,"WAIT_FOR_DURABLE_SETTLE");
}
function acceptSettle(s,receipt) {
    if (s.phase!=="MOCK_SETTLING")
        return output(s,false,"NO_SETTLING_STAGE");
    if (!match(s,receipt,"settle",["kind","writerId","sessionId",
            "epoch","stageId","persisted","readbackMatched"])
            || receipt.persisted!==true || receipt.readbackMatched!==true)
        return fault(s,"STALE_OR_UNVERIFIED_SETTLE");
    var n=copy(s),doc=fixture(n.stagedRaw);
    n.confirmedRaw=n.stagedRaw;
    n.revision=doc.revision;
    n.stagedRaw=null;
    n.stageId=null;
    n.committed++;
    n.phase=n.freezeRequested?"MOCK_FREEZING":"MOCK_READY";
    return output(n,true,"SETTLED_MOCK_ONLY");
}
function requestFreeze(s) {
    if (s.phase==="MOCK_FROZEN" || s.phase==="MOCK_FREEZING"
            || s.phase==="RECOVERY_REVIEW")
        return output(s,false,"ALREADY_CLOSED");
    if (s.phase!=="MOCK_READY" && s.phase!=="MOCK_RESERVING"
            && s.phase!=="MOCK_SAVING"
            && s.phase!=="MOCK_VERIFYING" && s.phase!=="MOCK_SETTLING")
        return output(s,false,"FREEZE_NOT_AVAILABLE");
    var n=copy(s);
    n.freezeRequested=true;
    if (n.phase==="MOCK_READY") n.phase="MOCK_FREEZING";
    return output(n,true,"ADMISSION_CLOSED_WAIT_DURABLE_FREEZE");
}
function acceptFreeze(s,receipt) {
    if (s.phase!=="MOCK_FREEZING" || !s.freezeRequested
            || s.stageId!==null)
        return output(s,false,"SAVE_NOT_DRAINED");
    if (!fields(receipt,["kind","writerId","sessionId",
            "epoch","persisted","pendingStage","sourceHash"])
            || s.owner===null || receipt.kind!=="freeze"
            || receipt.writerId!==s.owner.writerId
            || receipt.sessionId!==s.owner.sessionId
            || receipt.epoch!==s.owner.epoch
            || receipt.persisted!==true || receipt.pendingStage!==false
            || !hash(receipt.sourceHash))
        return fault(s,"FREEZE_NOT_DURABLY_WITNESSED");
    var n=copy(s);
    n.phase="MOCK_FROZEN";
    return output(n,true,"FROZEN_MOCK_ONLY");
}
function failedCallback(s) {return fault(s,"SAVE_OR_LOAD_FAILED");}
function restart(s) {
    var n=copy(s);
    n.phase="RECOVERY_REVIEW";
    n.reason="NEW_PROCESS_REQUIRES_REVIEW";
    n.stageId=null;
    n.stagedRaw=null;
    n.freezeRequested=true;
    return output(n,false,n.reason);
}
