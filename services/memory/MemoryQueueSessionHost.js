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
    if (typeof v==="string") return v.length<=1024 && /^[\x20-\x7e]*$/.test(v);
    if (Array.isArray(v)) return v.length<=64 && v.every(x=>safe(x,depth+1));
    return typeof v==="object" && Object.keys(v).length<=64
        && Object.keys(v).every(k=>k.length<=128 && /^[\x20-\x7e]*$/.test(k) && safe(v[k],depth+1));
}
function initial(consumer) {
    return {session:consumer.initial(),projection:null,history:null,historyRead:null,
        recoveryRead:null,inventory:null,localAction:null,
        buffer:"",phase:"STOPPED",sequence:0,generation:0,startupLocked:true,
        mode:"LEGACY",stage:null,
        awaitingStatus:false,publicationRequired:false,failure:null};
}
function start(state,consumer,generation,mode="LEGACY") {
    if ((state.phase!=="STOPPED" && state.phase!=="FAILED")
        || !positive(generation) || generation<=state.generation
        || !["LEGACY","STAGED"].includes(mode)) return state;
    return Object.assign({},initial(consumer),{
        generation,mode,session:consumer.disconnect(state.session),phase:"HELLO"});
}
function stop(state,consumer,reason,generation) {
    if (generation!==state.generation || !["HELLO","CONNECTED"].includes(state.phase)) return state;
    return Object.assign({},initial(consumer),{
        generation,session:consumer.disconnect(state.session),phase:reason?"FAILED":"STOPPED",
        failure:reason||null});
}
// Independent caller-owned deadlines, not a timer or a polling interval.
// A wrapper must fence callbacks by generation AND the particular wait it
// armed, so an old timeout cannot stop a later action of the same kind.
function waiting(state) {
    if (!["HELLO","CONNECTED"].includes(state.phase)) return [];
    const waits=[];
    if (state.phase==="HELLO") waits.push("HELLO");
    if (state.awaitingStatus || state.publicationRequired) waits.push("PUBLICATION");
    if (state.session.pending) waits.push("ACTION");
    if (state.historyRead) waits.push("HISTORY");
    if (state.recoveryRead) waits.push("RECOVERY");
    if (state.buffer) waits.push("PARTIAL_FRAME");
    return waits;
}
function context(state) {
    if (!state.session.ownerId && !state.session.pending && !state.session.unresolved) return null;
    // Startup inventory is a separate lock, not a fabricated unresolved action.
    // Keep pending/unknown state even when the projection is invalid.
    const session=state.startupLocked || state.historyRead || state.recoveryRead
        ? Object.assign({},state.session,{nextActionSequence:null,prepared:null})
        : state.session;
    return {state:session,projection:state.projection,startupLocked:state.startupLocked,
        historyPending:!!state.historyRead,phase:state.phase,waiting:waiting(state),failure:state.failure,
        recoveryPending:!!state.recoveryRead,
        actionStage:state.stage?state.stage.phase:null};
}
function recoveryContext(state) {
    // Atomic snapshot for DOC 2's read-only pane. This metadata is not
    // authority, and a missing response is never evidence of noncommit.
    return {hostStatus:{phase:state.phase,startupLocked:state.startupLocked,
        historyPending:!!(state.historyRead || state.recoveryRead),
        actionPending:!!state.session.pending,unresolved:!!state.session.unresolved},
        inventory:state.inventory,localAction:state.localAction,
        recoveryPending:!!state.recoveryRead};
}
function packet(state,p,consumer,project,historyProject,recoveryProject,recoveryRow) {
    const fail=reason=>stop(state,consumer,reason,state.generation);
    if (!p || typeof p!=="object" || Array.isArray(p) || !safe(p) || p.version!==1 || p.can_execute!==false) return fail("INVALID_PACKET");
    if (state.phase==="HELLO") {
        if (!exact(p,["version","kind","owner_id","can_execute"]) || p.kind!=="HELLO" || !uuid(p.owner_id)
            || p.owner_id===state.session.previousOwnerId)
            return fail("INVALID_HELLO");
        return Object.assign({},state,{phase:"CONNECTED",session:consumer.connect(state.session,p.owner_id),
            publicationRequired:true});
    }
    if (state.phase!=="CONNECTED" || p.owner_id!==state.session.ownerId) return fail("OWNER_MISMATCH");
    // After a preparation receipt the server is waiting for our exact
    // continuation, not sending any additional frame until COMMIT.
    if (state.stage?.phase==="RECEIPT_READY") return fail("UNEXPECTED_STAGED_PACKET");
    if (p.kind==="INVALIDATE") {
        if (!exact(p,["version","kind","owner_id","can_execute"]) || state.awaitingStatus)
            return fail("INVALID_CONTROL");
        // Pending action may have been sent just before an owner timer fired.
        // Preserve pending until its correlated reply or explicit timeout.
        return Object.assign({},state,{session:consumer.invalidate(state.session,"FRESH STATUS REQUIRED"),
            projection:null,history:null,inventory:null,localAction:null,
            awaitingStatus:true,publicationRequired:true});
    }
    if (!positive(p.sequence) || p.sequence<=state.sequence) return fail("SEQUENCE_MISMATCH");
    if (p.kind==="STATUS") {
        if (!state.awaitingStatus || p.projection?.notification_candidate!==null)
            return fail("UNEXPECTED_STATUS");
        // Consumer intentionally discards STATUS while pending. Validate
        // the complete projection independently before that shortcut.
        const probe=consumer.acceptStatus(Object.assign({},state.session,{pending:null}),p,project);
        if (!probe.status || probe.sequence!==p.sequence) return fail("INVALID_STATUS");
        const next=consumer.acceptStatus(state.session,p,project);
        if (next.sequence!==p.sequence || (!next.status && !next.pending))
            return fail("INVALID_STATUS");
        return Object.assign({},state,{session:next,sequence:p.sequence,
            projection:next.status?p.projection:null,awaitingStatus:false,publicationRequired:false,history:null});
    }
    if (p.kind==="PREPARED_ACTION") {
        const pending=state.session.pending;
        const fields=["version","kind","owner_id","sequence","next_action_sequence","can_execute","record","challenge"];
        if (state.mode!=="STAGED" || state.stage?.phase!=="WAIT_PREPARED" || !pending
            || state.awaitingStatus || state.publicationRequired || !exact(p,fields)
            || p.next_action_sequence!==pending.action_sequence+1 || !uuid(p.challenge)
            || typeof recoveryRow!=="function") return fail("INVALID_PREPARED_RECEIPT");
        let view;
        try { view=recoveryRow(p.record); } catch (_) { view=null; }
        if (!view || view.state!=="PREPARED" || !exact(p.record.message,Object.keys(pending))
            || !Object.keys(pending).every(k=>p.record.message[k]===pending[k]))
            return fail("INVALID_PREPARED_RECEIPT");
        // Keep the original pending action; the receipt is not completion.
        return Object.assign({},state,{sequence:p.sequence,
            session:Object.assign({},state.session,{sequence:p.sequence,prepared:null}),
            stage:{phase:"RECEIPT_READY",sequence:p.sequence,challenge:p.challenge}});
    }
    if (p.kind==="ACTION") {
        if (state.stage && state.stage.phase!=="WAIT_COMMIT") return fail("PREMATURE_ACTION");
        if (!state.session.pending || state.historyRead || state.recoveryRead || state.awaitingStatus) return fail("UNEXPECTED_ACTION");
        const next=consumer.acceptAction(state.session,p);
        if (next.sequence!==p.sequence || next.pending
            || next.feedback==="INVALID RESPONSE // RECONCILE"
            || next.feedback==="UNMATCHED RESPONSE // RECONCILE") return fail("INVALID_ACTION");
        return Object.assign({},state,{session:next,sequence:p.sequence,projection:null,
            history:null,stage:null,publicationRequired:true});
    }
    if (p.kind==="DETAIL") {
        const read=state.historyRead;
        if (!read || state.awaitingStatus || state.publicationRequired || state.session.pending
            || !state.session.status || p.next_action_sequence!==state.session.nextActionSequence)
            return fail("UNEXPECTED_DETAIL");
        let view;
        try { view=historyProject(p,state.session.ownerId,read.requestId,state.sequence); }
        catch (_) { view=null; }
        if (!view || view.canExecute!==false || view.outcome!=="UNVERIFIED") return fail("INVALID_DETAIL");
        return Object.assign({},state,{sequence:p.sequence,history:view,historyRead:null,
            session:Object.assign({},state.session,{sequence:p.sequence,prepared:null})});
    }
    if (p.kind==="INVENTORY" || p.kind==="LOCAL_ACTION") {
        const read=state.recoveryRead;
        const fields=["version","owner_id","sequence","next_action_sequence","kind","can_execute"];
        if (!read || read.kind!==p.kind || state.historyRead || state.session.pending
            || state.awaitingStatus || state.publicationRequired || !state.session.status
            || p.next_action_sequence!==state.session.nextActionSequence)
            return fail("UNEXPECTED_RECOVERY");
        let inventory=null, localAction=null;
        try {
            if (p.kind==="INVENTORY") {
                if (!exact(p,fields.concat(["inventory"])) || typeof recoveryProject!=="function")
                    return fail("INVALID_INVENTORY");
                const view=recoveryProject(p.inventory);
                if (!view || view.canExecute!==false || view.startupLocked!==true
                    || view.outcome!=="UNVERIFIED" || view.recent.length>read.limit
                    || (p.inventory.truncated && view.recent.length!==read.limit))
                    return fail("INVALID_INVENTORY");
                // UNKNOWN may have no request ID; never interpret that as
                // absence. Only compare a concrete ID or explicit IDLE.
                const observed=state.session.status;
                if ((observed.requestId!==null || observed.state==="IDLE REPORTED")
                    && observed.requestId!==view.pendingId)
                    return fail("INVENTORY_STATUS_MISMATCH");
                inventory=p.inventory;
            } else {
                if (!exact(p,fields.concat(["action_id","record"])) || p.action_id!==read.actionId
                    || typeof recoveryRow!=="function") return fail("INVALID_LOCAL_ACTION");
                if (p.record!==null) {
                    const view=recoveryRow(p.record);
                    if (!view || view.actionId!==read.actionId) return fail("INVALID_LOCAL_ACTION");
                }
                localAction={actionId:read.actionId,record:p.record,
                    outcome:"UNVERIFIED",canExecute:false};
            }
        } catch (_) { return fail("INVALID_RECOVERY"); }
        return Object.assign({},state,{sequence:p.sequence,recoveryRead:null,inventory,localAction,
            session:Object.assign({},state.session,{sequence:p.sequence,prepared:null})});
    }
    return fail("INVALID_KIND");
}
function feed(state,chunk,consumer,project,historyProject,generation,recoveryProject,recoveryRow) {
    if (generation!==state.generation || (state.phase!=="HELLO" && state.phase!=="CONNECTED")) return state;
    if (typeof chunk!=="string" || chunk.length>MAX_CHUNK || /[^\x20-\x7e\n]/.test(chunk))
        return stop(state,consumer,"INVALID_CHUNK",generation);
    // The Python encoder emits ASCII JSON lines. Bound retained partial
    // frames before parsing; upstream must bound raw reads too.
    let buffer=state.buffer+chunk, next=state;
    while (buffer.includes("\n")) {
        const i=buffer.indexOf("\n");
        if (!i || i>=MAX_FRAME) return stop(next,consumer,"FRAME_SIZE",generation);
        const line=buffer.slice(0,i);
        let p;
        try {
            p=JSON.parse(line);
            // Exact compact ASCII roundtrip rejects duplicate keys, alternate
            // numeric forms and escape variants. All v1 wire fields are ASCII.
            if (!safe(p) || JSON.stringify(p)!==line)
                return stop(next,consumer,"NONCANONICAL_JSON",generation);
        } catch (_) { return stop(next,consumer,"INVALID_JSON",generation); }
        buffer=buffer.slice(i+1);
        next=packet(next,p,consumer,project,historyProject,recoveryProject,recoveryRow);
        if (next.phase==="FAILED") return next;
    }
    if (buffer.length>=MAX_FRAME) return stop(next,consumer,"FRAME_SIZE",generation);
    return Object.assign({},next,{buffer});
}
function confirm(state,intent,actionId,consumer) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.startupLocked || state.historyRead || state.recoveryRead
        || state.awaitingStatus || state.publicationRequired || !state.projection || !uuid(actionId)
        || !exact(intent,["ownerId","statusSequence","actionSequence","kind","expectedId","targetGiB","expiresAt"])) return no;
    const prepared=consumer.prepare(state.session,intent.kind,intent.targetGiB,intent.expiresAt);
    if (!prepared.prepared || !Object.keys(intent).every(k=>intent[k]===prepared.prepared[k])) return no;
    const submitted=consumer.submit(prepared,actionId);
    if (!submitted.message) return no;
    const staged=state.mode==="STAGED" && submitted.message.kind!=="RECHECK";
    return {state:Object.assign({},state,{session:submitted.state,projection:null,history:null,inventory:null,localAction:null,
        awaitingStatus:false,stage:staged?{phase:"WAIT_PREPARED"}:null}),
        frame:JSON.stringify({version:1,kind:staged?"PREPARE_ACTION":"ACTION",message:submitted.message})+"\n"};
}
function takeCommit(state,generation) {
    // Called by the transport only after feed has validated the complete
    // receipt. Publish returned state BEFORE writing. Never retry a failed
    // write or take a continuation from a recovered record.
    const no={state,frame:null};
    if (generation!==state.generation || state.phase!=="CONNECTED"
        || state.mode!=="STAGED" || state.stage?.phase!=="RECEIPT_READY"
        || state.startupLocked || !state.session.pending || state.session.unresolved
        || state.buffer || state.awaitingStatus || state.publicationRequired) return no;
    const frame=JSON.stringify({version:1,kind:"COMMIT_ACTION",message:state.session.pending,
        prepared_sequence:state.stage.sequence,challenge:state.stage.challenge})+"\n";
    return {state:Object.assign({},state,{stage:{phase:"WAIT_COMMIT"}}),frame};
}
function readHistory(state,requestId) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.historyRead || state.recoveryRead || state.session.pending
        || state.awaitingStatus || state.publicationRequired || !uuid(requestId) || !state.session.status) return no;
    return {state:Object.assign({},state,{history:null,historyRead:{requestId}}),
        frame:JSON.stringify({version:1,kind:"HISTORY",owner_id:state.session.ownerId,request_id:requestId})+"\n"};
}
function readRecovery(state,kind,value) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.historyRead || state.recoveryRead
        || state.session.pending || state.awaitingStatus || state.publicationRequired
        || !state.session.status) return no;
    let request;
    if (kind==="INVENTORY" && positive(value) && value<=16) request={kind,limit:value};
    else if (kind==="LOCAL_ACTION" && uuid(value)) request={kind,actionId:value};
    else return no;
    const message={version:1,kind,owner_id:state.session.ownerId};
    if (kind==="INVENTORY") message.limit=value;
    else message.action_id=value;
    return {state:Object.assign({},state,{recoveryRead:request,inventory:null,localAction:null,history:null,
        session:Object.assign({},state.session,{prepared:null})}),frame:JSON.stringify(message)+"\n"};
}
// Deliberately no public startup unlock or reconciliation acknowledgment.
// Complete durable inventory / lost action correlation is a prerequisite for
// those transitions. In this slice a trusted fixture can inject reviewed
// startup state; production stays locked even if the Python child is healthy.
