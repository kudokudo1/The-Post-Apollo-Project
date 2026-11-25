// UI2 R4b local public fixture consumer. No transport, authority or history I/O.
const SCHEMA = "postapollo.forest.public-runtime-status.v1";
const CORR = ["requestId","viewKey","generation"];
const UNIT = [...CORR,"sequence","kind","statusPacket"];
const FLAGS = ["sourceAuthenticated","permissionGranted","productionAuthority","modelExecutionPermitted"];
const PACKET = ["schema","status","safeActions",...FLAGS];
const LABELS = Object.freeze({
    REQUEST_PENDING:"REQUEST PENDING",
    PREPARING:"PREPARING",
    GENERATING:"GENERATING",
    STOP_REQUESTED:"STOP REQUESTED // OUTCOME PENDING",
    LOCAL_COMMIT_RECORDED:"LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED",
    UNKNOWN_HOLD:"UNKNOWN HOLD // NO AUTOMATIC RETRY"
});
function own(o,k) { return Object.prototype.hasOwnProperty.call(o,k); }
function record(o) { return o !== null && typeof o === "object" && !Array.isArray(o); }
function exact(o,keys) {
    return record(o) && Object.keys(o).length === keys.length && keys.every(k=>own(o,k));
}
function token(v) { return typeof v === "string" && v.length === 32 && /^[0-9a-f]{32}$/.test(v); }
function positive(v) { return Number.isSafeInteger(v) && v > 0; }
function correlation(o) {
    if (!record(o) || !CORR.every(k=>own(o,k)) || !token(o.requestId)
        || !token(o.viewKey) || o.requestId === o.viewKey || !positive(o.generation))
        return null;
    return {requestId:o.requestId,viewKey:o.viewKey,generation:o.generation};
}
function same(a,b) { return a !== null && b !== null && CORR.every(k=>a[k]===b[k]); }
function packetOK(p) {
    return exact(p,PACKET) && p.schema===SCHEMA && typeof p.status==="string"
        && own(LABELS,p.status) && FLAGS.every(k=>p[k]===false)
        && Array.isArray(p.safeActions) && p.safeActions.length===0;
}
// Exact R4 transition paths, including conservative early UNKNOWN_HOLD.
function allowed(previous,next) {
    if (next==="UNKNOWN_HOLD") return previous!=="LOCAL_COMMIT_RECORDED" && previous!=="UNKNOWN_HOLD";
    switch(previous) {
    case "": return next==="REQUEST_PENDING";
    case "REQUEST_PENDING": return next==="PREPARING" || next==="STOP_REQUESTED";
    case "PREPARING": return next==="GENERATING" || next==="STOP_REQUESTED";
    case "GENERATING": return next==="STOP_REQUESTED" || next==="LOCAL_COMMIT_RECORDED";
    case "STOP_REQUESTED": return next==="LOCAL_COMMIT_RECORDED";
    default: return false;
    }
}
function createConsumer() {
    let active=null, sequence=0, status="", state="CLOSED";
    // Bounded local reuse fence. A new host-owned consumer lifetime is required
    // on exhaustion, with independently fresh tokens; no automatic replacement.
    const used=Object.create(null);
    let count=0;
    function snapshot() {
        return {state,status,label:status ? LABELS[status] : "",
            sourceAuthenticated:false,permissionGranted:false,
            productionAuthority:false,modelExecutionPermitted:false,
            sendEnabled:false,stopEnabled:false,safeActions:[]};
    }
    function clear(next) {
        active=null; sequence=0; status=""; state=next;
        return snapshot();
    }
    function open(ref,current) {
        const a=exact(ref,CORR)?correlation(ref):null;
        const b=exact(current,CORR)?correlation(current):null;
        clear("CLOSED");
        if (!same(a,b) || used[a.requestId] || used[a.viewKey] || count>=1024)
            return clear("UNAVAILABLE");
        used[a.requestId]=true;used[a.viewKey]=true;count++;
        active=a;state="ATTACHED";return snapshot();
    }
    function observe(current) {
        if (active && !same(active,exact(current,CORR)?correlation(current):null))
            return clear("CLOSED");
        return snapshot();
    }
    function invalidate(ref) {
        // Owner's INVALIDATED result is scoped; old clear cannot affect new view.
        if (active && same(active,exact(ref,CORR)?correlation(ref):null))
            return clear("UNAVAILABLE");
        return snapshot();
    }
    function receive(unit,current) {
        observe(current);
        if (!active) return snapshot();
        const incoming=correlation(unit);
        // Uncorrelatable input cannot mutate a newer view; owner clears a known
        // affected lifetime separately. Never open a view from an incoming unit.
        if (!same(active,incoming)) return snapshot();
        if (!exact(unit,UNIT) || !positive(unit.sequence)
            || sequence>=Number.MAX_SAFE_INTEGER || unit.sequence!==sequence+1)
            return clear("UNAVAILABLE");
        if (unit.kind==="WITHDRAW" && unit.statusPacket===null)
            return clear("CLOSED");
        if (unit.kind!=="STATUS" || !packetOK(unit.statusPacket)
            || !allowed(status,unit.statusPacket.status))
            return clear("UNAVAILABLE");
        sequence=unit.sequence;status=unit.statusPacket.status;
        state="DISPLAYING";return snapshot();
    }
    return {open,observe,invalidate,receive,close:()=>clear("CLOSED")};
}
