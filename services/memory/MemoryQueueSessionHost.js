// R3c host-owned protocol controller. No process launch, timers, files or
// authority. Host supplies trusted child channel, bounded chunks, deadlines,
// fresh UUIDs, and reviewed startup/recovery inventory. Never auto-resend.
const MAX_FRAME = 16384;
const MAX_CHUNK = 65536;
function exact(o, keys) {
    return o !== null && typeof o === "object" && !Array.isArray(o)
        && Object.keys(o).length === keys.length
        && keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));
}
function uuid(v) {
    return typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);
}
function positive(v) { return Number.isSafeInteger(v) && v > 0; }
function safe(v,depth=0) {
    if (depth>12) return false;
    if (v===null || typeof v==="boolean") return true;
    if (typeof v==="number") return Number.isSafeInteger(v) && v>=0;
    if (typeof v==="string") return v.length<=1024;
    if (Array.isArray(v)) return v.length<=64 && v.every(x=>safe(x,depth+1));
    return typeof v==="object" && Object.keys(v).length<=64
        && Object.keys(v).every(k=>k.length<=128 && safe(v[k],depth+1));
}
function initial(consumer) {
    return {session:consumer.initial(),projection:null,history:null,historyRead:null,
        buffer:"",phase:"STOPPED",sequence:0,startupLocked:true,
        awaitingStatus:false,failure:null};
}
function start(state,consumer) {
    if (state.phase!=="STOPPED" && state.phase!=="FAILED") return state;
    return Object.assign({},initial(consumer),{
        session:consumer.disconnect(state.session),phase:"HELLO"});
}
function stop(state,consumer,reason) {
    return Object.assign({},initial(consumer),{
        session:consumer.disconnect(state.session),phase:reason?"FAILED":"STOPPED",
        failure:reason||null});
}
function context(state) {
    if (!state.session.ownerId && !state.session.pending && !state.session.unresolved) return null;
    // Startup inventory is a separate lock, not a fabricated unresolved action.
    // Keep pending/unknown state even when the projection is invalid.
    const session=state.startupLocked || state.historyRead
        ? Object.assign({},state.session,{nextActionSequence:null,prepared:null})
        : state.session;
    return {state:session,projection:state.projection};
}
function packet(state,p,consumer,project,historyProject) {
    const fail=reason=>stop(state,consumer,reason);
    if (!safe(p) || p.version!==1 || p.can_execute!==false) return fail("INVALID_PACKET");
    if (state.phase==="HELLO") {
        if (!exact(p,["version","kind","owner_id","can_execute"]) || p.kind!=="HELLO" || !uuid(p.owner_id))
            return fail("INVALID_HELLO");
        return Object.assign({},state,{phase:"CONNECTED",session:consumer.connect(state.session,p.owner_id),
            awaitingStatus:true});
    }
    if (state.phase!=="CONNECTED" || p.owner_id!==state.session.ownerId) return fail("OWNER_MISMATCH");
    if (p.kind==="INVALIDATE") {
        if (!exact(p,["version","kind","owner_id","can_execute"])) return fail("INVALID_CONTROL");
        // Pending action may have been sent just before an owner timer fired.
        // Preserve pending until its correlated reply or explicit timeout.
        return Object.assign({},state,{session:consumer.invalidate(state.session,"FRESH STATUS REQUIRED"),
            projection:null,history:null,awaitingStatus:true});
    }
    if (!positive(p.sequence) || p.sequence<=state.sequence) return fail("SEQUENCE_MISMATCH");
    if (p.kind==="STATUS") {
        if (!state.awaitingStatus || p.projection?.notification_candidate!==null)
            return fail("UNEXPECTED_STATUS");
        const next=consumer.acceptStatus(state.session,p,project);
        if (next.sequence!==p.sequence || (!next.status && !next.pending))
            return fail("INVALID_STATUS");
        return Object.assign({},state,{session:next,sequence:p.sequence,
            projection:next.status?p.projection:null,awaitingStatus:false,history:null});
    }
    if (p.kind==="ACTION") {
        if (!state.session.pending || state.historyRead) return fail("UNEXPECTED_ACTION");
        const next=consumer.acceptAction(state.session,p);
        if (next.sequence!==p.sequence || next.pending
            || next.feedback==="INVALID RESPONSE // RECONCILE"
            || next.feedback==="UNMATCHED RESPONSE // RECONCILE") return fail("INVALID_ACTION");
        return Object.assign({},state,{session:next,sequence:p.sequence,projection:null,
            history:null,awaitingStatus:true});
    }
    if (p.kind==="DETAIL") {
        const read=state.historyRead;
        if (!read) return fail("UNEXPECTED_DETAIL");
        let view;
        try { view=historyProject(p,state.session.ownerId,read.requestId,state.sequence); }
        catch (_) { view=null; }
        if (!view || view.canExecute!==false || view.outcome!=="UNVERIFIED") return fail("INVALID_DETAIL");
        return Object.assign({},state,{sequence:p.sequence,history:view,historyRead:null});
    }
    return fail("INVALID_KIND");
}
function feed(state,chunk,consumer,project,historyProject) {
    if (state.phase!=="HELLO" && state.phase!=="CONNECTED") return state;
    if (typeof chunk!=="string" || chunk.length>MAX_CHUNK || /[^\x20-\x7e\n]/.test(chunk))
        return stop(state,consumer,"INVALID_CHUNK");
    // The Python encoder emits ASCII JSON lines. Bound retained partial
    // frames before parsing; upstream must bound raw reads too.
    let buffer=state.buffer+chunk, next=state;
    while (buffer.includes("\n")) {
        const i=buffer.indexOf("\n");
        if (!i || i>=MAX_FRAME) return stop(next,consumer,"FRAME_SIZE");
        let p;
        try { p=JSON.parse(buffer.slice(0,i)); }
        catch (_) { return stop(next,consumer,"INVALID_JSON"); }
        buffer=buffer.slice(i+1);
        next=packet(next,p,consumer,project,historyProject);
        if (next.phase==="FAILED") return next;
    }
    if (buffer.length>=MAX_FRAME) return stop(next,consumer,"FRAME_SIZE");
    return Object.assign({},next,{buffer});
}
function confirm(state,intent,actionId,consumer) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.startupLocked || state.historyRead
        || state.awaitingStatus || !state.projection || !uuid(actionId)
        || !exact(intent,["ownerId","statusSequence","actionSequence","kind","expectedId","targetGiB","expiresAt"])) return no;
    const prepared=consumer.prepare(state.session,intent.kind,intent.targetGiB,intent.expiresAt);
    if (!prepared.prepared || !Object.keys(intent).every(k=>intent[k]===prepared.prepared[k])) return no;
    const submitted=consumer.submit(prepared,actionId);
    if (!submitted.message) return no;
    return {state:Object.assign({},state,{session:submitted.state,projection:null,history:null,
        awaitingStatus:true}),frame:JSON.stringify({version:1,kind:"ACTION",message:submitted.message})+"\n"};
}
function readHistory(state,requestId) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.historyRead || state.session.pending
        || state.awaitingStatus || !uuid(requestId) || !state.session.status) return no;
    return {state:Object.assign({},state,{history:null,historyRead:{requestId}}),
        frame:JSON.stringify({version:1,kind:"HISTORY",owner_id:state.session.ownerId,request_id:requestId})+"\n"};
}
// Deliberately no public startup unlock or reconciliation acknowledgment.
// Complete durable inventory / lost action correlation is a prerequisite for
// those transitions. In this slice a trusted fixture can inject reviewed
// startup state; production stays locked even if the Python child is healthy.
