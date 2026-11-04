"use strict";
/*
 * TASKS M13p // FAKE-ONLY, unmounted Settings/Connections permission contract.
 *
 * A shared Settings broker may eventually own explicit user opt-in and
 * installation-scoped OS key operations, while TASKS owns only draft editing.
 * A keyring probe, Social label, toggle, fake host receipt or caller-supplied
 * role cannot establish permission. All outputs deny REAL authority.
 *
 * No I/O, OS credential access, account lookup, desktop import, QML call,
 * key release, real draft data, persistence or actual authorization.
 */
const NO_POWER=Object.freeze({
    productionActivation:false,
    hostAuthenticated:false,
    callerAuthenticated:false,
    userConsentAuthenticated:false,
    keyringUnlocked:false,
    keyReleaseAuthorized:false,
    canCaptureDraft:false,
    canDecryptDraft:false,
    canPreviewDraft:false,
    canPersistDraft:false,
    canRestoreDraft:false,
    canDeleteDraft:false,
    canWriteTaskSource:false,
    realGrantActive:false
});
const OPS=Object.freeze({
    CAPTURE: Object.freeze({
        scope:"tasks.draft.capture.encrypted",label:"SAVE ENCRYPTED DRAFT",
        action:"Capture only unfinished TASKS editor content",
        requires:"EXPLICIT_TASKS_OPT_IN_AND_TRUSTED_HOST",
        consent:"Opt in to encrypted unfinished-draft storage"
    }),
    PREVIEW: Object.freeze({
        scope:"tasks.draft.preview.unlocked",label:"UNLOCK DRAFT PREVIEW",
        action:"Preview a recoverable draft, never overwrite TASKS",
        requires:"SEPARATE_UNLOCK_AND_EDITOR_REVIEW",
        consent:"Unlock and review this recovery candidate"
    }),
    CLEAR: Object.freeze({
        scope:"tasks.draft.clear.encrypted",label:"DELETE ENCRYPTED DRAFT",
        action:"Clear one scoped encrypted checkpoint",
        requires:"EXPLICIT_DELETION_AND_FRESH_SOURCE_REVIEW",
        consent:"Confirm deletion of this encrypted checkpoint"
    })
});
const keys=["CAPTURE","PREVIEW","CLEAR"];
const allowed=new Set(keys.map(k=>OPS[k].scope));
const exact=(x,required)=>x&&typeof x==="object"&&!Array.isArray(x)
    &&Object.keys(x).sort().join(",")===required.slice().sort().join(",");
const refusal=(status)=>({ok:false,status,...NO_POWER});
const safe=(status,extra)=>({ok:true,status,...extra,...NO_POWER});
const states=Object.freeze({
    PENDING: "AWAITING_FAKE_REVIEW",
    APPROVED: "FAKE_REVIEW_ACKNOWLEDGED",
    DENIED: "FAKE_REVIEW_DENIED",
    REVOKED: "FAKE_REVIEW_REVOKED",
    EXPIRED: "FAKE_REVIEW_EXPIRED",
    CANCELLED: "FAKE_REVIEW_CANCELLED"
});
const token=x=>typeof x==="string"&&/^FAKE_[A-Z0-9_]{8,40}$/.test(x);
const millis=x=>Number.isSafeInteger(x)&&x>0;
function requirement(scope){
    if(!allowed.has(scope))return refusal("UNREGISTERED_TASKS_SCOPE");
    const entry=OPS[keys.find(k=>OPS[k].scope===scope)];
    return safe("INTENDED_SCOPE_NOT_GRANTED",{
        feature:"tasks-draft-recovery",
        providerOwner:"connections-broker",
        consumerOwner:"tasks",
        settingsLocation:"CPU++ / SETTINGS / CONNECTIONS",
        taskLocation:"TASKS / RECOVERY",
        scope:entry.scope,label:entry.label,action:entry.action,
        requires:entry.requires,consentText:entry.consent,
        defaultOptIn:false,defaultNetworkSync:false
    });
}
function providerStatus(probe){
    // This is only a projection of C2a's read-only status.
    // "SERVICE_ACQUIRED" never means the collection is unlocked.
    const v=probe&&typeof probe.status==="string"?probe.status:"";
    const label=v==="SERVICE_ACQUIRED"
        ?"KEYRING FOUND / UNLOCK NOT VERIFIED"
        :v==="SERVICE_NOT_RUNNING"?"KEYRING SERVICE NOT RUNNING"
        :v==="SESSION_BUS_UNAVAILABLE"?"SESSION BUS UNAVAILABLE"
        :v==="DBUS_PROBE_TOOL_MISSING"?"D-BUS PROBE TOOL MISSING"
        :"KEYRING STATUS UNVERIFIED";
    return safe(v==="SERVICE_ACQUIRED"?"PROVIDER_PRESENT_ONLY":"PROVIDER_NOT_VERIFIED",{
        label,keyringPresent:v==="SERVICE_ACQUIRED",
        canApprove:false,grantEnabled:false
    });
}
function reviewRequest(input){
    if(!exact(input,["feature","scope","surface"]))
        return refusal("INVALID_REVIEW_DESCRIPTOR");
    if(input.feature!=="tasks-draft-recovery")
        return refusal("WRONG_FEATURE");
    if(input.surface!=="TASKS")
        return refusal("UNTRUSTED_CONSUMER_IDENTITY");
    const req=requirement(input.scope);
    if(!req.ok)return req;
    return safe("REVIEW_DISPLAY_ONLY_HOST_NOT_CONNECTED",{
        request:{feature:"tasks-draft-recovery",scope:req.scope,surface:"TASKS"},
        label:req.label,consentText:req.consentText,
        canApprove:false,disposition:"NO_SESSION_OR_KEY_ACCESS"
    });
}
function brokerDecision(input){
    const req=reviewRequest(input);
    if(!req.ok)return req;
    return refusal("TRUSTED_HOST_APPROVAL_NOT_CONNECTED");
}
function validFakeState(state) {
    return exact(state,["kind","scope","requestId","startedAtMs",
        "ttlMs","state","reason"])&&state.kind==="M13P_FAKE_REVIEW"
        &&allowed.has(state.scope)&&token(state.requestId)
        &&millis(state.startedAtMs)&&Number.isSafeInteger(state.ttlMs)
        &&state.ttlMs>0&&state.ttlMs<=300000
        &&Object.prototype.hasOwnProperty.call(states,state.state)
        &&state.reason===states[state.state];
}
function createFakeReview({scope,requestId,startedAtMs,ttlMs}={}){
    if(!allowed.has(scope)||!token(requestId)||!millis(startedAtMs)
        ||!Number.isSafeInteger(ttlMs)||ttlMs<1||ttlMs>300000)
        return refusal("INVALID_DISPOSABLE_REVIEW");
    return safe("SIMULATED_REVIEW_STARTED",{
        fakeState:{kind:"M13P_FAKE_REVIEW",scope,requestId,
            startedAtMs,ttlMs,state:"PENDING",reason:states.PENDING}
    });
}
function advanceFakeReview({fakeState,event,nowMs}={}){
    if(!validFakeState(fakeState)||!millis(nowMs)
        ||nowMs<fakeState.startedAtMs)
        return refusal("INVALID_FAKE_STATE_OR_CLOCK");
    const current=fakeState.state;
    // Both intermediate and terminal records are caller-authored and
    // NOT durable. No replay/rollback security assertion is made here.
    if(current==="EXPIRED"||current==="DENIED"||current==="REVOKED"
        ||current==="CANCELLED")
        return refusal("SIMULATED_TERMINAL_REVIEW");
    let next="";
    if(nowMs-fakeState.startedAtMs>=fakeState.ttlMs)
        next="EXPIRED";
    else if(current==="PENDING"&&event==="ACKNOWLEDGE")
        next="APPROVED";
    else if(current==="PENDING"&&event==="DENY")
        next="DENIED";
    else if(current==="PENDING"&&event==="CANCEL")
        next="CANCELLED";
    else if(current==="APPROVED"&&event==="REVOKE")
        next="REVOKED";
    else
        return refusal("SIMULATED_REVIEW_TRANSITION_REFUSED");
    return safe("FAKE_REVIEW_STATE_ONLY_NEVER_A_GRANT",{
        fakeState:{...fakeState,state:next,reason:states[next]},
        simulatedAcknowledged:next==="APPROVED"
    });
}
function displayFakeState(fakeState){
    if(!validFakeState(fakeState))
        return refusal("INVALID_SIMULATED_STATUS");
    return safe("SIMULATED_NOT_AUTHORIZED",{
        phase:fakeState.state,
        notice:fakeState.reason,
        // Deliberately no requestId, issuer, token or draft data.
        scope:fakeState.scope,
        label:"SIMULATED / HOST APPROVAL NOT CONNECTED"
    });
}
module.exports={requirement,providerStatus,reviewRequest,brokerDecision,
    createFakeReview,advanceFakeReview,displayFakeState,NO_POWER};
