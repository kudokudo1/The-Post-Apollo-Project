.pragma library

// M11e disposable FileView event policy. NOT a production admission gate.
// Its READY state allows writes to ONE synthetic test fixture ONLY. No OS
// writer lock, durable epoch, migration, GitHub API, or real task schema.
var MAX_BYTES = 2048;
var MARK = "M11E_SYNTHETIC_ONLY";

function idle() {
    return {phase:"UNARMED",reason:"",document:null,confirmedRaw:"",
        pending:null,pendingRaw:"",nextToken:1,activeToken:null,
        freezeRequested:false,readExpectation:null,completed:0};
}
function clone(s) {
    return {phase:s.phase,reason:s.reason,document:s.document,
        confirmedRaw:s.confirmedRaw,pending:s.pending,pendingRaw:s.pendingRaw,
        nextToken:s.nextToken,activeToken:s.activeToken,
        freezeRequested:s.freezeRequested,readExpectation:s.readExpectation,
        completed:s.completed};
}
function blocked(s, why) {
    var n=clone(s);
    n.phase="RECOVERY_REVIEW";
    n.reason=why;
    n.pending=null;
    n.pendingRaw="";
    n.activeToken=null;
    n.readExpectation=null;
    n.freezeRequested=true;
    // Preserve last confirmed data; never publish a speculative write.
    return n;
}
function fieldsExact(obj, names) {
    if (!obj || typeof obj!=="object" || Array.isArray(obj)) return false;
    if (Object.keys(obj).length !== names.length) return false;
    for (var i=0;i<names.length;i++)
        if (!Object.prototype.hasOwnProperty.call(obj,names[i]))
            return false;
    return true;
}
function decode(raw) {
    if (typeof raw!=="string" || raw.length<1 || raw.length>MAX_BYTES)
        return null;
    try {
        var v=JSON.parse(raw);
        if (!fieldsExact(v,["fixture","revision","counter","marker"])
                || v.fixture!==MARK || v.marker!=="sample"
                || !Number.isSafeInteger(v.revision) || v.revision<0
                || v.revision>1000000
                || !Number.isSafeInteger(v.counter) || v.counter<0
                || v.counter>1000000
                || v.counter!==v.revision)
            return null;
        return v;
    } catch (e) {return null;}
}
function start(s) {
    if (s.phase!=="UNARMED") return {accepted:false,state:s};
    var n=clone(s);
    n.phase="LOADING";
    n.reason="";
    n.readExpectation=null;
    return {accepted:true,state:n};
}
function onLoaded(s, raw) {
    if (s.phase!=="LOADING" && s.phase!=="VERIFYING")
        return blocked(s,"UNEXPECTED_LOAD_CALLBACK");
    var value=decode(raw);
    if (value===null) return blocked(s,"INVALID_TEST_FILE");
    if (s.phase==="LOADING") {
        if (s.readExpectation!==null && raw!==s.readExpectation)
            return blocked(s,"RELOAD_SOURCE_DRIFT");
        var ready=clone(s);
        ready.phase=ready.freezeRequested?"FROZEN":"READY";
        ready.reason="";
        ready.document=value;
        ready.confirmedRaw=raw;
        ready.readExpectation=null;
        return ready;
    }
    // FileView.onSaved alone is not proof that the exact staged text was
    // subsequently read from the file. Both bytes and value must match.
    if (s.activeToken===null || s.pending===null
            || raw!==s.pendingRaw || value.revision!==s.pending.revision
            || value.counter!==s.pending.counter)
        return blocked(s,"POST_SAVE_READBACK_MISMATCH");
    var committed=clone(s);
    committed.phase=committed.freezeRequested?"FROZEN":"READY";
    committed.reason="";
    committed.document=value;
    committed.confirmedRaw=raw;
    committed.pending=null;
    committed.pendingRaw="";
    committed.activeToken=null;
    committed.completed+=1;
    return committed;
}
function onLoadFailed(s) {
    return blocked(s,"FILE_LOAD_FAILED");
}
function requestStage(s) {
    if (s.phase!=="READY" || s.freezeRequested || !s.document)
        return {accepted:false,state:s};
    var value={fixture:MARK,revision:s.document.revision+1,
        counter:s.document.counter+1,marker:"sample"};
    if (value.revision>1000000)
        return {accepted:false,state:blocked(s,"FIXTURE_COUNTER_EXHAUSTED")};
    var raw=JSON.stringify(value)+"\n";
    var n=clone(s);
    n.phase="SAVING";
    n.pending=value;
    n.pendingRaw=raw;
    n.activeToken=n.nextToken;
    n.nextToken++;
    return {accepted:true,raw:raw,token:n.activeToken,state:n};
}
function onSaved(s) {
    if (s.phase!=="SAVING" || s.activeToken===null
            || s.pending===null || s.pendingRaw==="")
        return blocked(s,"UNEXPECTED_SAVE_CALLBACK");
    var n=clone(s);
    n.phase="VERIFYING";
    return n;
}
function onSaveFailed(s) {
    return blocked(s,"FILE_SAVE_FAILED");
}
function requestReload(s) {
    if (s.phase!=="READY" || s.freezeRequested)
        return {accepted:false,state:s};
    var n=clone(s);
    n.phase="LOADING";
    n.readExpectation=s.confirmedRaw;
    return {accepted:true,state:n};
}
function requestFreeze(s) {
    if (s.phase==="FROZEN") return {accepted:false,state:s};
    if (s.phase==="READY") {
        var n=clone(s);
        n.phase="FROZEN";
        n.freezeRequested=true;
        return {accepted:true,state:n};
    }
    if (s.phase==="SAVING" || s.phase==="VERIFYING") {
        var pending=clone(s);
        pending.freezeRequested=true;
        return {accepted:true,state:pending};
    }
    // There is no safe partial loading checkpoint in this standalone demo.
    return {accepted:false,state:s};
}
function writable(s) {
    return s.phase==="READY" && !s.freezeRequested
        && s.pending===null && s.activeToken===null;
}
