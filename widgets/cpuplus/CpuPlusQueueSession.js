// DOC 2 R3d: shell-session coordinator, not a Process launcher.
// All operations are pure transitions. Caller commits returned state BEFORE
// writing a frame, and closes the exact child on stop. No automatic replay.
// The unmounted reference has no production startup/recovery approval path.
const LIMIT=16384;
function exact(o,keys) {
    return o !== null && typeof o === "object" && !Array.isArray(o)
        && Object.keys(o).length===keys.length && keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));
}
function uuid(v) {return typeof v==="string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);}
function positive(v) {return Number.isSafeInteger(v)&&v>0;}
function safe(v,depth=0) {
    if(depth>12)return false;
    if(v===null||typeof v==="boolean")return true;
    if(typeof v==="number")return Number.isSafeInteger(v)&&v>=0;
    if(typeof v==="string")return v.length<=1024 && /^[\x20-\x7e]*$/.test(v);
    if(Array.isArray(v))return v.length<=64&&v.every(x=>safe(x,depth+1));
    return typeof v==="object"&&Object.keys(v).length<=64&&Object.keys(v).every(k=>
        k.length<=128&&/^[\x20-\x7e]*$/.test(k)&&safe(v[k],depth+1));
}
function decode(line) {
    // DOC 4 emits compact ASCII JSON. Exact round trip rejects duplicate keys,
    // alternate numeric spellings and noncanonical escape encodings. This is a
    // post-frame guard, NOT a byte-bounded stdout reader.
    if(typeof line!=="string"||!line.length||line.length>=LIMIT||!/^[\x20-\x7e]+$/.test(line))return null;
    try {
        const p=JSON.parse(line);
        return safe(p)&&JSON.stringify(p)===line&&p&&p.version===1&&p.can_execute===false?p:null;
    }catch(_){return null;}
}
function initial(C,fixtureStartupReconciled=false) {
    return {generation:0,active:false,hello:false,awaitingStatus:false,
        session:C.initial(),projection:null,historyPending:null,history:null,
        startupHold:fixtureStartupReconciled!==true,reason:"NOT CONNECTED"};
}
function result(state,frame=null,stop=false){return {state,frame,stop};}
function begin(s,generation) {
    if(s.active||!positive(generation)||generation<=s.generation)return s;
    return Object.assign({},s,{generation,active:true,hello:false,awaitingStatus:false,
        projection:null,historyPending:null,history:null,reason:"AWAIT HELLO"});
}
function stopSession(s,C,reason) {
    return result(Object.assign({},s,{active:false,hello:false,awaitingStatus:false,
        session:C.disconnect(s.session),projection:null,historyPending:null,history:null,reason}),null,true);
}
function disconnect(s,generation,C,reason="OWNER LOST") {
    return s.active&&generation===s.generation?stopSession(s,C,reason):result(s);
}
function context(s) {
    const c=s.session;
    if(!c.ownerId&&!c.pending&&!c.unresolved)return null;
    // Preserve pending/unresolved transitions even when projection is absent.
    const blocked=s.startupHold||!!s.historyPending;
    return {state:blocked?Object.assign({},c,{status:null,prepared:null}):c,
        projection:!blocked&&c.status?s.projection:null};
}
function receive(s,generation,line,C,project,historyProject) {
    if(!s.active||generation!==s.generation)return result(s);
    const p=decode(line);
    if(!p)return stopSession(s,C,"INVALID FRAME");
    const control=["version","kind","owner_id","can_execute"];
    if(p.kind==="HELLO") {
        if(s.hello||!exact(p,control)||!uuid(p.owner_id)||p.owner_id===s.session.previousOwnerId)
            return stopSession(s,C,"INVALID HELLO");
        return result(Object.assign({},s,{hello:true,session:C.connect(s.session,p.owner_id),reason:"AWAIT PUBLICATION"}));
    }
    const c=s.session;
    if(!s.hello||p.owner_id!==c.ownerId)return stopSession(s,C,"OWNER MISMATCH");
    if(p.kind==="INVALIDATE") {
        if(!exact(p,control)||s.awaitingStatus)return stopSession(s,C,"INVALID INVALIDATE");
        // A scheduled publication can race a submitted action; do not convert
        // a pending request to unknown merely because the owner invalidated.
        return result(Object.assign({},s,{awaitingStatus:true,session:C.invalidate(c,"STATUS INVALIDATED"),
            projection:null,reason:"AWAIT STATUS"}));
    }
    if(!positive(p.sequence)||p.sequence<=c.sequence)return stopSession(s,C,"STALE OR INVALID SEQUENCE");
    if(p.kind==="STATUS") {
        if(!s.awaitingStatus||!p.projection||p.projection.notification_candidate!==null)
            return stopSession(s,C,"UNEXPECTED STATUS");
        // Validate even when pending; Consumer deliberately discards a
        // publication during pending, so use an independent sanitized probe.
        const probe=C.acceptStatus(Object.assign({},c,{pending:null}),p,project);
        if(!probe.status)return stopSession(s,C,"INVALID STATUS");
        const next=C.acceptStatus(c,p,project);
        return result(Object.assign({},s,{awaitingStatus:false,session:next,
            projection:next.status?p.projection:null,reason:next.feedback}));
    }
    if(p.kind==="ACTION") {
        if(!c.pending||s.awaitingStatus)return stopSession(s,C,"UNEXPECTED ACTION");
        const next=C.acceptAction(c,p);
        if(next.sequence!==p.sequence||next.pending||next.feedback==="INVALID RESPONSE // RECONCILE"
            ||next.feedback==="UNMATCHED RESPONSE // RECONCILE")
            return stopSession(s,C,"INVALID ACTION RESPONSE");
        return result(Object.assign({},s,{session:next,projection:null,history:null,reason:next.feedback}));
    }
    if(p.kind==="DETAIL") {
        if(!s.historyPending||s.awaitingStatus||c.pending||typeof historyProject!=="function")
            return stopSession(s,C,"UNEXPECTED HISTORY");
        const pending=s.historyPending;
        let view=null;
        try{view=historyProject(p,c.ownerId,pending.requestId,Math.max(pending.floor,c.sequence));}catch(_){}
        if(!view||view.canExecute!==false||view.outcome!=="UNVERIFIED")
            return stopSession(s,C,"INVALID HISTORY");
        // DETAIL shares the owner's global response sequence. Do not reset
        // action sequencing or let it revive a stale status.
        if(c.nextActionSequence!==null&&p.next_action_sequence!==c.nextActionSequence)
            return stopSession(s,C,"HISTORY ACTION SEQUENCE MISMATCH");
        return result(Object.assign({},s,{session:Object.assign({},c,{sequence:p.sequence,prepared:null}),
            historyPending:null,history:{envelope:p,ownerId:c.ownerId,requestId:pending.requestId,
                sequenceFloor:Math.max(pending.floor,c.sequence),view},reason:"HISTORY REPORTED"}));
    }
    return stopSession(s,C,"UNKNOWN FRAME");
}
function submitIntent(s,intent,actionId,C) {
    if(!s.active||!s.hello||s.startupHold||s.awaitingStatus||s.historyPending||!s.projection||!uuid(actionId)
        ||!exact(intent,["ownerId","statusSequence","actionSequence","kind","expectedId","targetGiB","expiresAt"]))
        return result(s);
    const p=C.prepare(s.session,intent.kind,intent.targetGiB,intent.expiresAt);
    if(!p.prepared||!Object.keys(intent).every(k=>p.prepared[k]===intent[k]))return result(s);
    const sent=C.submit(p,actionId);
    if(!sent.message)return result(s);
    return result(Object.assign({},s,{session:sent.state,projection:null,history:null,reason:"ACTION PENDING"}),
        JSON.stringify({version:1,kind:"ACTION",message:sent.message})+"\n");
}
function requestHistory(s,requestId) {
    if(!s.active||!s.hello||s.awaitingStatus||!s.session.status||s.session.pending||s.historyPending||!uuid(requestId))
        return result(s);
    return result(Object.assign({},s,{historyPending:{requestId,floor:s.session.sequence},history:null,
        reason:"HISTORY PENDING"}),
        JSON.stringify({version:1,kind:"HISTORY",owner_id:s.session.ownerId,request_id:requestId})+"\n");
}
// No acknowledgment or startup-unlock method. Durable restart reconciliation
// and explicit operator review must be designed before deployment.
