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
function digest(v) { return typeof v==="string" && /^[0-9a-f]{64}$/.test(v); }
function equal(a,b) {
    if (a===b) return true;
    if (!a || !b || typeof a!=="object" || typeof b!=="object"
        || Array.isArray(a)!==Array.isArray(b)) return false;
    return exact(a,Object.keys(b)) && Object.keys(b).every(k=>equal(a[k],b[k]));
}
function reviewValue(r,recoveryRow) {
    if (!exact(r,["version","review_id","owner_id","action_id","snapshot","review_digest",
        "reviewed_at_ms","can_execute","startup_unlock"]) || r.version!==1
        || !uuid(r.review_id) || !uuid(r.owner_id) || !uuid(r.action_id)
        || !digest(r.review_digest) || !Number.isSafeInteger(r.reviewed_at_ms) || r.reviewed_at_ms<0
        || r.can_execute!==false || r.startup_unlock!==false) return false;
    const s=r.snapshot;
    if (!exact(s,["version","record","pending_request_id","pending_digest","adjustment_outcome","can_execute","startup_unlock"])
        || s.version!==1 || (s.pending_request_id!==null && !uuid(s.pending_request_id))
        || !digest(s.pending_digest) || s.adjustment_outcome!=="UNVERIFIED"
        || s.can_execute!==false || s.startup_unlock!==false) return false;
    let view;
    try { view=recoveryRow(s.record); } catch (_) { return false; }
    return !!view && view.actionId===r.action_id && s.record.message.owner_id!==r.owner_id;
}
function receiptValue(r,recoveryRow) {
    return exact(r,["version","review","acknowledged_at_ms","disposition","adjustment_outcome","can_execute","startup_unlock"])
        && r.version===1 && reviewValue(r.review,recoveryRow)
        && Number.isSafeInteger(r.acknowledged_at_ms)
        && r.acknowledged_at_ms>=r.review.reviewed_at_ms
        && r.acknowledged_at_ms-r.review.reviewed_at_ms<60000
        && r.disposition==="REVIEW_ACKNOWLEDGED_ONLY" && r.adjustment_outcome==="UNVERIFIED"
        && r.can_execute===false && r.startup_unlock===false;
}
function dispositionValue(r,recoveryRow) {
    return exact(r,["version","review","dismissed_at_ms","disposition","adjustment_outcome","can_execute","startup_unlock"])
        && r.version===2 && reviewValue(r.review,recoveryRow)
        && r.review.snapshot.record.state==="PREPARED"
        && Number.isSafeInteger(r.dismissed_at_ms) && r.dismissed_at_ms>=r.review.reviewed_at_ms
        && r.dismissed_at_ms-r.review.reviewed_at_ms<60000
        && r.disposition==="LOCAL_PREPARATION_DISMISSED" && r.adjustment_outcome==="UNVERIFIED"
        && r.can_execute===false && r.startup_unlock===false;
}
function dispositionInventoryValue(v,recoveryRow,limit) {
    if (!exact(v,["version","recent","truncated","prepared","pending_request_id","startup_unlock","adjustment_outcome","can_execute"])
        || v.version!==2 || v.startup_unlock!==false || v.adjustment_outcome!=="UNVERIFIED" || v.can_execute!==false
        || typeof v.truncated!=="boolean" || !Array.isArray(v.recent) || v.recent.length>limit
        || (v.truncated && v.recent.length!==limit)
        || (v.pending_request_id!==null && !uuid(v.pending_request_id))) return false;
    let last=Infinity,open=null;
    const ids=new Set();
    for (const entry of v.recent) {
        if (!exact(entry,["record","disposition"])) return false;
        const view=recoveryRow(entry.record);
        if (!view || view.ordinal>=last || ids.has(view.actionId)) return false;
        last=view.ordinal;ids.add(view.actionId);
        if (entry.disposition!==null) {
            if (!dispositionValue(entry.disposition,recoveryRow)
                || !equal(entry.record,entry.disposition.review.snapshot.record)) return false;
        } else if (view.state==="PREPARED") {
            if (open) return false;
            open=entry.record;
        }
    }
    const unresolved=v.prepared===null?null:recoveryRow(v.prepared);
    if (v.prepared!==null && (!unresolved || unresolved.state!=="PREPARED")) return false;
    if (open) return equal(open,v.prepared);
    return !unresolved || (v.truncated && unresolved.ordinal<last && !ids.has(unresolved.actionId));
}
function initial(consumer) {
    return {session:consumer.initial(),projection:null,history:null,historyRead:null,
        recoveryRead:null,inventory:null,localAction:null,
        buffer:"",phase:"STOPPED",sequence:0,generation:0,startupLocked:true,
        mode:"LEGACY",stage:null,reviewEnabled:false,reviewFlow:null,reviewReceipt:null,reviewLost:null,
        checkpointRequired:false,checkpointWait:null,notificationEnabled:false,lastNoticeSequence:0,
        dispositionEnabled:false,dispositionConnectPending:false,dispositionInventory:null,
        dispositionLost:null,dispositionReceipt:null,retentionProof:null,retentionPending:false,
        awaitingStatus:false,publicationRequired:false,failure:null};
}
function start(state,consumer,generation,mode="LEGACY",reviewEnabled=false,checkpointRequired=false,notificationEnabled=false,dispositionEnabled=false) {
    if (state.retentionPending || (state.phase!=="STOPPED" && state.phase!=="FAILED")
        || !positive(generation) || generation<=state.generation
        || !["LEGACY","STAGED"].includes(mode) || typeof reviewEnabled!=="boolean"
        || typeof checkpointRequired!=="boolean" || typeof notificationEnabled!=="boolean"
        || typeof dispositionEnabled!=="boolean"
        || (dispositionEnabled && (!reviewEnabled || !checkpointRequired))
        || (state.dispositionLost && !dispositionEnabled)
        || ((reviewEnabled || checkpointRequired) && mode!=="STAGED")) return state;
    return Object.assign({},initial(consumer),{
        generation,mode,reviewEnabled,checkpointRequired,notificationEnabled,reviewLost:state.reviewLost,
        dispositionEnabled,dispositionLost:state.dispositionLost,
        session:consumer.disconnect(state.session),phase:"HELLO"});
}
function stop(state,consumer,reason,generation) {
    if (generation!==state.generation || !["HELLO","CONNECTED"].includes(state.phase)) return state;
    return Object.assign({},initial(consumer),{
        generation,reviewLost:state.reviewFlow?.phase==="WAIT_ACK"
            ? state.reviewFlow.review : state.reviewLost,
        dispositionLost:state.reviewFlow?.phase==="WAIT_DISMISS" ? state.reviewFlow.review : state.dispositionLost,
        session:consumer.disconnect(state.session),phase:reason?"FAILED":"STOPPED",
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
    if (state.recoveryRead || state.reviewFlow) waits.push("RECOVERY");
    if (state.buffer) waits.push("PARTIAL_FRAME");
    return waits;
}
function context(state) {
    if (!state.session.ownerId && !state.session.pending && !state.session.unresolved) return null;
    // Startup inventory is a separate lock, not a fabricated unresolved action.
    // Keep pending/unknown state even when the projection is invalid.
    const session=state.startupLocked || state.historyRead || state.recoveryRead || state.reviewFlow || state.reviewLost
        ? Object.assign({},state.session,{nextActionSequence:null,prepared:null})
        : state.session;
    return {state:session,projection:state.projection,startupLocked:state.startupLocked,
        historyPending:!!state.historyRead,phase:state.phase,waiting:waiting(state),failure:state.failure,
        recoveryPending:!!(state.recoveryRead || state.reviewFlow),
        actionStage:state.checkpointWait?.record.kind==="ACTION"?"WAIT_CHECKPOINT":state.stage?state.stage.phase:null};
}
function recoveryContext(state) {
    // Atomic snapshot for DOC 2's read-only pane. This metadata is not
    // authority, and a missing response is never evidence of noncommit.
    return {hostStatus:{phase:state.phase,startupLocked:state.startupLocked,
        historyPending:!!(state.historyRead || state.recoveryRead || state.reviewFlow),
        actionPending:!!state.session.pending,unresolved:!!state.session.unresolved},
        inventory:state.inventory,localAction:state.localAction,
        recoveryPending:!!(state.recoveryRead || state.reviewFlow)};
}
// Separate additive interface; existing DOC 2 recoveryContext stays stable.
function reviewContext(state) {
    const flow=state.reviewFlow;
    return {phase:state.checkpointWait?.record.kind==="REVIEW_ACK"?"WAIT_CHECKPOINT":
        flow?flow.phase:state.reviewLost?"ACK_UNKNOWN":"IDLE",
        review:flow?.phase==="REVIEW_READY" && !state.awaitingStatus && !state.publicationRequired
            ? flow.review:null,
        reviewSequence:flow?.phase==="REVIEW_READY"?flow.sequence:null,
        receipt:state.reviewReceipt,unknownReviewId:state.reviewLost?.review_id||null,
        canAcknowledge:canAck(state),startupLocked:state.startupLocked,canExecute:false};
}
function canAck(state) {
    const f=state.reviewFlow, status=state.session.status;
    return state.phase==="CONNECTED" && state.reviewEnabled && state.startupLocked
        && f?.phase==="REVIEW_READY" && !state.buffer && !state.awaitingStatus && !state.publicationRequired
        && !!status && (status.requestId!==null || status.state==="IDLE REPORTED")
        && status.requestId===f.review.snapshot.pending_request_id;
}
function takeDispositionConnect(state,generation) {
    const no={state,frame:null};
    if (generation!==state.generation || state.phase!=="CONNECTED" || !state.dispositionEnabled
        || !state.dispositionConnectPending || state.buffer || !state.publicationRequired) return no;
    return {state:Object.assign({},state,{dispositionConnectPending:false}),
        frame:JSON.stringify({version:1,kind:"CONNECT_DISPOSITION",owner_id:state.session.ownerId})+"\n"};
}
function packet(state,p,consumer,project,historyProject,recoveryProject,recoveryRow,offerNotice) {
    const fail=reason=>stop(state,consumer,reason,state.generation);
    if (!p || typeof p!=="object" || Array.isArray(p) || !safe(p) || p.version!==1 || p.can_execute!==false) return fail("INVALID_PACKET");
    // A retention proof is one fresh history response, not a cached UI receipt.
    if (state.retentionProof) state=Object.assign({},state,{retentionProof:null});
    if (state.phase==="HELLO") {
        if (!exact(p,["version","kind","owner_id","can_execute"]) || p.kind!==(state.dispositionEnabled?"HELLO_DISPOSITION":"HELLO") || !uuid(p.owner_id)
            || p.owner_id===state.session.previousOwnerId)
            return fail("INVALID_HELLO");
        return Object.assign({},state,{phase:"CONNECTED",session:consumer.connect(state.session,p.owner_id),
            publicationRequired:true,dispositionConnectPending:state.dispositionEnabled});
    }
    if (state.dispositionConnectPending) return fail("DISPOSITION_CONNECT_REQUIRED");
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
            projection:null,history:null,inventory:null,localAction:null,dispositionInventory:null,
            awaitingStatus:true,publicationRequired:true});
    }
    if (p.kind==="NOTIFICATION") {
        const n=p.notice;
        if (!state.notificationEnabled
            || !exact(p,["version","kind","owner_id","can_execute","status_sequence","notice"])
            || !positive(p.status_sequence) || p.status_sequence!==state.sequence
            || !exact(n,["version","event_id","request_id","kind","code","observed_at","target_gib",
                "original_actual_kib","delivery_state","can_execute","checked_at_ms","valid_before_wall_ms"])
            || n.version!==1 || n.can_execute!==false || n.delivery_state!=="ATTEMPT_RESERVED"
            || !uuid(n.request_id) || !["DEFERRED","ATTENTION","READY_ADVISORY","EXPIRED","CANCELLED"].includes(n.kind)
            || n.event_id!=="apollo-cpu-memory-"+n.request_id+"-"+n.kind.toLowerCase().replace(/_/g,"-"))
            return fail("INVALID_NOTIFICATION");
        if (state.lastNoticeSequence>=p.status_sequence) return state;
        // Consume this publication's offer even if the host is busy or
        // no sink exists. A dropped alert is preferable to stale/replayed
        // advice. Notification sink is synchronous and never receives a
        // queue operation, raw source or authority.
        const next=Object.assign({},state,{lastNoticeSequence:p.status_sequence});
        const status=state.projection?.status;
        if (state.awaitingStatus || state.publicationRequired || state.session.pending
            || state.reviewFlow || state.historyRead || state.recoveryRead || !status)
            return next;
        const terminal=["EXPIRED","CANCELLED"].includes(n.kind);
        const matches=terminal ? status.state==="IDLE" && status.request_id===null
            : status.request_id===n.request_id && status.code===n.code
              && status.target_gib===n.target_gib && status.original_actual_kib===n.original_actual_kib;
        if (matches && typeof offerNotice==="function") {
            try { offerNotice(JSON.parse(JSON.stringify(n))); } catch (_) {}
        }
        return next;
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
    if (p.kind==="RECOVERY_REVIEW" || p.kind==="RECOVERY_ACK" || p.kind==="RECOVERY_REVIEW_HISTORY") {
        const f=state.reviewFlow;
        const fields=["version","kind","owner_id","sequence","next_action_sequence","can_execute"];
        if (!state.reviewEnabled || !state.startupLocked || !f || state.session.pending
            || state.awaitingStatus || state.publicationRequired || !state.session.status
            || p.next_action_sequence!==state.session.nextActionSequence) return fail("UNEXPECTED_REVIEW");
        const advanced={sequence:p.sequence,session:Object.assign({},state.session,{sequence:p.sequence,prepared:null})};
        if (p.kind==="RECOVERY_REVIEW") {
            if (f.phase!=="WAIT_REVIEW" || !exact(p,fields.concat(["review"]))
                || !reviewValue(p.review,recoveryRow) || p.review.owner_id!==state.session.ownerId
                || p.review.action_id!==f.actionId) return fail("INVALID_REVIEW");
            return Object.assign({},state,advanced,{reviewFlow:{phase:"REVIEW_READY",review:p.review,sequence:p.sequence}});
        }
        if (p.kind==="RECOVERY_ACK") {
            if (f.phase!=="WAIT_ACK" || !exact(p,fields.concat(["receipt"]))
                || !receiptValue(p.receipt,recoveryRow) || !equal(p.receipt.review,f.review))
                return fail("INVALID_REVIEW_ACK");
            return Object.assign({},state,advanced,{reviewFlow:null,reviewReceipt:p.receipt});
        }
        if (f.phase!=="WAIT_RECEIPT" || !exact(p,fields.concat(["review_id","receipt"]))
            || p.review_id!==f.reviewId || (p.receipt!==null && (!receiptValue(p.receipt,recoveryRow)
                || p.receipt.review.review_id!==f.reviewId))) return fail("INVALID_REVIEW_HISTORY");
        if (state.reviewLost && p.receipt!==null && !equal(p.receipt.review,state.reviewLost))
            return fail("REVIEW_HISTORY_MISMATCH");
        return Object.assign({},state,advanced,{reviewFlow:null,reviewReceipt:p.receipt,
            reviewLost:p.receipt!==null ? null:state.reviewLost,
            retentionProof:p.receipt?.review?.snapshot?.record?.state==="COMMITTED"
                ? {generation:state.generation,ownerId:p.owner_id,sequence:p.sequence,
                    receipt:JSON.parse(JSON.stringify(p.receipt))} : null});
    }
    if (p.kind==="LOCAL_DISPOSITION" || p.kind==="LOCAL_DISPOSITION_HISTORY") {
        const f=state.reviewFlow;
        const fields=["version","kind","owner_id","sequence","next_action_sequence","can_execute"];
        if (!state.dispositionEnabled || !state.startupLocked || !f || state.session.pending
            || state.awaitingStatus || state.publicationRequired || !state.session.status
            || p.next_action_sequence!==state.session.nextActionSequence)
            return fail("UNEXPECTED_DISPOSITION");
        const advanced={sequence:p.sequence,session:Object.assign({},state.session,{sequence:p.sequence,prepared:null})};
        if (p.kind==="LOCAL_DISPOSITION") {
            if (f.phase!=="WAIT_DISMISS" || !exact(p,fields.concat(["receipt"]))
                || !dispositionValue(p.receipt,recoveryRow) || !equal(p.receipt.review,f.review))
                return fail("INVALID_DISPOSITION_RECEIPT");
            return Object.assign({},state,advanced,{reviewFlow:null,dispositionReceipt:p.receipt,
                projection:null,inventory:null,dispositionInventory:null,localAction:null,publicationRequired:true});
        }
        if (f.phase!=="WAIT_DISPOSITION" || !exact(p,fields.concat(["action_id","receipt"]))
            || p.action_id!==f.actionId || (p.receipt!==null &&
                (!dispositionValue(p.receipt,recoveryRow) || p.receipt.review.action_id!==f.actionId)))
            return fail("INVALID_DISPOSITION_HISTORY");
        if (state.dispositionLost && p.receipt!==null && !equal(p.receipt.review,state.dispositionLost))
            return fail("DISPOSITION_HISTORY_MISMATCH");
        return Object.assign({},state,advanced,{reviewFlow:null,dispositionReceipt:p.receipt,
            dispositionLost:p.receipt!==null?null:state.dispositionLost,
            retentionProof:p.receipt===null?null:{generation:state.generation,ownerId:p.owner_id,
                sequence:p.sequence,receipt:JSON.parse(JSON.stringify(p.receipt))}});
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
        let inventory=null, localAction=null, dispositionInventory=null;
        try {
            if (p.kind==="INVENTORY") {
                if (!exact(p,fields.concat(["inventory"])) || typeof recoveryProject!=="function")
                    return fail("INVALID_INVENTORY");
                if (state.dispositionEnabled) {
                    if (!dispositionInventoryValue(p.inventory,recoveryRow,read.limit))
                        return fail("INVALID_DISPOSITION_INVENTORY");
                    const observed=state.session.status;
                    if ((observed.requestId!==null || observed.state==="IDLE REPORTED")
                        && observed.requestId!==p.inventory.pending_request_id)
                        return fail("INVENTORY_STATUS_MISMATCH");
                    dispositionInventory=p.inventory;
                } else {
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
                }
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
        return Object.assign({},state,{sequence:p.sequence,recoveryRead:null,inventory,localAction,dispositionInventory,
            session:Object.assign({},state.session,{sequence:p.sequence,prepared:null})});
    }
    return fail("INVALID_KIND");
}
function feed(state,chunk,consumer,project,historyProject,generation,recoveryProject,recoveryRow,offerNotice) {
    if (generation!==state.generation || (state.phase!=="HELLO" && state.phase!=="CONNECTED")) return state;
    // No server reply can precede transmission. Conservatively terminate
    // even on a scheduled publication during local checkpoint IO; never
    // release a frame against a changed status or incomplete byte stream.
    if (state.checkpointWait && chunk!=="")
        return stop(state,consumer,"CHECKPOINT_CHANNEL_CHANGED",generation);
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
        next=packet(next,p,consumer,project,historyProject,recoveryProject,recoveryRow,offerNotice);
        if (next.phase==="FAILED") return next;
    }
    if (buffer.length>=MAX_FRAME) return stop(next,consumer,"FRAME_SIZE",generation);
    return Object.assign({},next,{buffer});
}
function confirm(state,intent,actionId,consumer) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.startupLocked || state.historyRead || state.recoveryRead
        || state.reviewFlow || state.reviewLost || state.dispositionLost || state.checkpointWait
        || (state.checkpointRequired && state.buffer)
        || state.awaitingStatus || state.publicationRequired || !state.projection || !uuid(actionId)
        || !exact(intent,["ownerId","statusSequence","actionSequence","kind","expectedId","targetGiB","expiresAt"])) return no;
    const prepared=consumer.prepare(state.session,intent.kind,intent.targetGiB,intent.expiresAt);
    if (!prepared.prepared || !Object.keys(intent).every(k=>intent[k]===prepared.prepared[k])) return no;
    const submitted=consumer.submit(prepared,actionId);
    if (!submitted.message) return no;
    const staged=state.mode==="STAGED" && submitted.message.kind!=="RECHECK";
    const transition={state:Object.assign({},state,{session:submitted.state,projection:null,history:null,inventory:null,localAction:null,
        awaitingStatus:false,stage:staged?{phase:"WAIT_PREPARED"}:null}),
        frame:JSON.stringify({version:1,kind:staged?"PREPARE_ACTION":"ACTION",message:submitted.message})+"\n"};
    return staged && state.checkpointRequired ? holdCheckpoint(state,transition) : transition;
}
function takeCommit(state,generation) {
    // Called by the transport only after feed has validated the complete
    // receipt. Publish returned state BEFORE writing. Never retry a failed
    // write or take a continuation from a recovered record.
    const no={state,frame:null};
    if (generation!==state.generation || state.phase!=="CONNECTED"
        || state.mode!=="STAGED" || state.checkpointWait || state.stage?.phase!=="RECEIPT_READY"
        || state.startupLocked || !state.session.pending || state.session.unresolved
        || state.buffer || state.awaitingStatus || state.publicationRequired) return no;
    const frame=JSON.stringify({version:1,kind:"COMMIT_ACTION",message:state.session.pending,
        prepared_sequence:state.stage.sequence,challenge:state.stage.challenge})+"\n";
    return {state:Object.assign({},state,{stage:{phase:"WAIT_COMMIT"}}),frame};
}
function readHistory(state,requestId) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.historyRead || state.recoveryRead || state.reviewFlow || state.session.pending
        || state.awaitingStatus || state.publicationRequired || !uuid(requestId) || !state.session.status) return no;
    return {state:Object.assign({},state,{history:null,historyRead:{requestId}}),
        frame:JSON.stringify({version:1,kind:"HISTORY",owner_id:state.session.ownerId,request_id:requestId})+"\n"};
}
function readRecovery(state,kind,value) {
    const no={state:state,frame:null};
    if (state.phase!=="CONNECTED" || state.historyRead || state.recoveryRead || state.reviewFlow
        || state.session.pending || state.awaitingStatus || state.publicationRequired
        || !state.session.status) return no;
    let request;
    if (kind==="INVENTORY" && positive(value) && value<=(state.dispositionEnabled?4:16)) request={kind,limit:value};
    else if (kind==="LOCAL_ACTION" && uuid(value)) request={kind,actionId:value};
    else return no;
    const message={version:1,kind,owner_id:state.session.ownerId};
    if (kind==="INVENTORY") message.limit=value;
    else message.action_id=value;
    return {state:Object.assign({},state,{recoveryRead:request,inventory:null,localAction:null,dispositionInventory:null,history:null,
        session:Object.assign({},state.session,{prepared:null})}),frame:JSON.stringify(message)+"\n"};
}
function reviewAvailable(state) {
    return state.phase==="CONNECTED" && state.mode==="STAGED" && state.reviewEnabled
        && state.startupLocked && !state.reviewFlow && !state.historyRead && !state.recoveryRead
        && !state.session.pending && !state.awaitingStatus && !state.publicationRequired
        && !state.buffer && !!state.session.status;
}
function beginReview(state,actionId) {
    const no={state,frame:null};
    if (!reviewAvailable(state) || state.reviewLost || state.dispositionLost || !uuid(actionId)) return no;
    return {state:Object.assign({},state,{reviewFlow:{phase:"WAIT_REVIEW",actionId},reviewReceipt:null}),
        frame:JSON.stringify({version:1,kind:"RECOVERY_REVIEW",owner_id:state.session.ownerId,action_id:actionId})+"\n"};
}
function acknowledgeReview(state,selection,generation,recoveryRow) {
    const no={state,frame:null};
    if (generation!==state.generation || !canAck(state)
        || !exact(selection,["reviewId","digest","sequence"])) return no;
    const f=state.reviewFlow,r=f.review;
    if (selection.reviewId!==r.review_id || selection.digest!==r.review_digest || selection.sequence!==f.sequence) return no;
    const transition={state:Object.assign({},state,{reviewFlow:{phase:"WAIT_ACK",review:r,sequence:f.sequence},reviewReceipt:null}),
        frame:JSON.stringify({version:1,kind:"RECOVERY_ACK",owner_id:state.session.ownerId,
            review_id:r.review_id,review_digest:r.review_digest,review_sequence:f.sequence})+"\n"};
    return state.checkpointRequired ? holdCheckpoint(state,transition,recoveryRow) : transition;
}
function readReviewReceipt(state,reviewId) {
    const no={state,frame:null};
    if (!reviewAvailable(state) || !uuid(reviewId)
        || (state.reviewLost && state.reviewLost.review_id!==reviewId)) return no;
    return {state:Object.assign({},state,{reviewFlow:{phase:"WAIT_RECEIPT",reviewId},reviewReceipt:null,retentionProof:null}),
        frame:JSON.stringify({version:1,kind:"RECOVERY_REVIEW_HISTORY",owner_id:state.session.ownerId,review_id:reviewId})+"\n"};
}
function canDismiss(state) {
    return state.dispositionEnabled && state.checkpointRequired && !state.reviewLost && !state.dispositionLost
        && canAck(state) && state.reviewFlow.review.snapshot.record.state==="PREPARED";
}
function dispositionContext(state) {
    const f=state.reviewFlow;
    return {enabled:state.dispositionEnabled,phase:state.checkpointWait?.record.kind==="REVIEW_DISMISS"?"WAIT_CHECKPOINT":
        f?f.phase:state.dispositionLost?"DISMISS_UNKNOWN":"IDLE",
        review:f?.phase==="REVIEW_READY" && !state.awaitingStatus && !state.publicationRequired?f.review:null,
        reviewSequence:f?.phase==="REVIEW_READY"?f.sequence:null,
        inventory:state.dispositionInventory,receipt:state.dispositionReceipt,
        unknownActionId:state.dispositionLost?.action_id||null,canDismiss:canDismiss(state),
        startupLocked:state.startupLocked,canExecute:false};
}
function dismissReview(state,selection,generation,recoveryRow) {
    const no={state,frame:null};
    if (generation!==state.generation || !canDismiss(state)
        || !exact(selection,["reviewId","digest","sequence"])) return no;
    const f=state.reviewFlow,r=f.review;
    if (selection.reviewId!==r.review_id || selection.digest!==r.review_digest || selection.sequence!==f.sequence) return no;
    const transition={state:Object.assign({},state,{reviewFlow:{phase:"WAIT_DISMISS",review:r,sequence:f.sequence},dispositionReceipt:null}),
        frame:JSON.stringify({version:1,kind:"RECOVERY_DISMISS",owner_id:state.session.ownerId,
            review_id:r.review_id,review_digest:r.review_digest,review_sequence:f.sequence})+"\n"};
    return holdCheckpoint(state,transition,recoveryRow);
}
function readDispositionReceipt(state,actionId) {
    const no={state,frame:null};
    if (!state.dispositionEnabled || !reviewAvailable(state) || !uuid(actionId)
        || (state.dispositionLost && state.dispositionLost.action_id!==actionId)) return no;
    return {state:Object.assign({},state,{reviewFlow:{phase:"WAIT_DISPOSITION",actionId},dispositionReceipt:null,retentionProof:null}),
        frame:JSON.stringify({version:1,kind:"DISPOSITION_HISTORY",owner_id:state.session.ownerId,action_id:actionId})+"\n"};
}
// R6e: consume only a fresh history proof accepted by the canonical owner
// feed. Trusted wrapper owns the LOAD result and explicit selection, must
// publish stopped state, terminate its exact child and await exit before IO.
// No queue frame, unlock, replay, or caller-supplied receipt argument.
function takeRetentionAdvance(state,selection,loaded,generation,consumer,recoveryRow) {
    const no={state,request:null,frame:null};
    const proof=state.retentionProof;
    const committed=proof?.receipt?.version===1;
    if (generation!==state.generation || !reviewAvailable(state) || !state.dispositionEnabled
        || !state.checkpointRequired || state.reviewLost || state.dispositionLost
        || state.checkpointWait || !proof || proof.generation!==generation
        || proof.ownerId!==state.session.ownerId || proof.sequence!==state.sequence
        || (committed ? (!equal(proof.receipt,state.reviewReceipt) || !receiptValue(proof.receipt,recoveryRow)
            || proof.receipt.review.snapshot.record.state!=="COMMITTED")
            : (!equal(proof.receipt,state.dispositionReceipt) || !dispositionValue(proof.receipt,recoveryRow)))
        || !safe(selection) || !exact(selection,["storageGeneration","actionId","reviewDigest","sequence"])
        || selection.sequence!==proof.sequence || selection.actionId!==proof.receipt.review.action_id
        || selection.reviewDigest!==proof.receipt.review.review_digest
        || !safe(loaded) || !exact(loaded,["version","kind","snapshot","can_execute"])
        || loaded.version!==1 || loaded.kind!=="CHECKPOINT_GENERATION_LOADED" || loaded.can_execute!==false)
        return no;
    const snapshot=loaded.snapshot;
    if (!exact(snapshot,["generation","checkpoint","sealed","receipt","startup_unlock","can_execute"])
        || !Number.isSafeInteger(snapshot.generation) || snapshot.generation<0
        || snapshot.generation!==selection.storageGeneration || snapshot.startup_unlock!==false
        || snapshot.can_execute!==false || typeof snapshot.sealed!=="boolean"
        || (snapshot.sealed?!equal(snapshot.receipt,proof.receipt):snapshot.receipt!==null))
        return no;
    const restored=restoreCheckpoint(consumer,snapshot.checkpoint,recoveryRow);
    if (!restored || (committed ? (!!restored.dispositionLost || !restored.reviewLost
            || !equal(restored.reviewLost,proof.receipt.review))
            : (!restored.dispositionLost || !equal(restored.dispositionLost,proof.receipt.review)))
        || !equal(restored.session.unresolved,state.session.unresolved)) return no;
    const request={version:1,generation:snapshot.generation,receipt:JSON.parse(JSON.stringify(proof.receipt))};
    // Retire this controller instance before storage. Only a fresh verified
    // LOAD may construct another locked state; the wrapper owns monotonic
    // process generation across that reconstruction.
    return {state:Object.assign({},stop(state,consumer,null,generation),{retentionPending:true}),
        request,frame:null};
}
// R3q: bounded durable checkpoint contract. The actual storage adapter
// must save the exact returned record before emitting the associated frame.
// No storage or IO performed by this controller.
function checkpointMessage(m) {
    return exact(m,["version","owner_id","action_id","action_sequence","kind",
        "expected_request_id","target_gib","expires_at"]) && m.version===1
        && uuid(m.owner_id) && uuid(m.action_id) && positive(m.action_sequence)
        && m.action_sequence<Number.MAX_SAFE_INTEGER
        && ["QUEUE","REPLACE","CANCEL","EXPIRE"].includes(m.kind)
        && (m.kind==="QUEUE"?m.expected_request_id===null:uuid(m.expected_request_id))
        && (["QUEUE","REPLACE"].includes(m.kind)
            ? positive(m.target_gib) && m.target_gib>=4 && m.target_gib<=64 && m.target_gib%4===0 && positive(m.expires_at)
            : m.target_gib===null && m.expires_at===null);
}
function checkpointForFrame(transition,recoveryRow) {
    if (!transition || !transition.state || typeof transition.frame!=="string") return null;
    const s=transition.state;
    if (s.phase!=="CONNECTED" || s.mode!=="STAGED") return null;
    let p;
    try { p=JSON.parse(transition.frame); } catch (_) { return null; }
    if (!safe(p) || JSON.stringify(p)+"\n"!==transition.frame || p.version!==1) return null;
    if (p.kind==="PREPARE_ACTION" && s.stage?.phase==="WAIT_PREPARED"
        && exact(p,["version","kind","message"]) && checkpointMessage(p.message)
        && equal(p.message,s.session.pending))
        return {version:1,kind:"ACTION",message:JSON.parse(JSON.stringify(p.message))};
    if (((p.kind==="RECOVERY_ACK" && s.reviewFlow?.phase==="WAIT_ACK")
        || (p.kind==="RECOVERY_DISMISS" && s.dispositionEnabled && s.reviewFlow?.phase==="WAIT_DISMISS"))
        && exact(p,["version","kind","owner_id","review_id","review_digest","review_sequence"])) {
        const r=s.reviewFlow.review;
        if (reviewValue(r,recoveryRow) && p.owner_id===s.session.ownerId
            && r.owner_id===p.owner_id && r.review_id===p.review_id && r.review_digest===p.review_digest
            && positive(p.review_sequence) && p.review_sequence===s.reviewFlow.sequence)
            return {version:1,kind:p.kind==="RECOVERY_DISMISS"?"REVIEW_DISMISS":"REVIEW_ACK",review:JSON.parse(JSON.stringify(r))};
    }
    return null;
}
function holdCheckpoint(previous,transition,recoveryRow) {
    const record=checkpointForFrame(transition,recoveryRow);
    if (!record) return {state:previous,frame:null};
    // Publish this state before starting the one-shot save process. No
    // transport frame is returned until the successful exit is correlated.
    return {state:Object.assign({},transition.state,{checkpointWait:{
        record:JSON.parse(JSON.stringify(record)),frame:transition.frame}}),
        checkpoint:JSON.parse(JSON.stringify(record)),frame:null};
}
function finishCheckpoint(state,result,generation,consumer,recoveryRow) {
    const no={state,frame:null};
    if (generation!==state.generation || state.phase!=="CONNECTED" || !state.checkpointWait) return no;
    const held=state.checkpointWait;
    // Wrapper must supply result only after observing successful helper
    // exit and bounded stdout; null represents failed/unknown IO.
    const fail=()=>({state:stop(state,consumer,"CHECKPOINT_UNAVAILABLE",generation),frame:null});
    if (!result || !safe(result) || !exact(result,["version","kind","record","can_execute"])
        || result.version!==1 || result.kind!=="CHECKPOINT_SAVED" || result.can_execute!==false
        || !equal(result.record,held.record) || state.buffer
        || state.awaitingStatus || state.publicationRequired) return fail();
    const record=checkpointForFrame({state,frame:held.frame},recoveryRow);
    if (!record || !equal(record,held.record)) return fail();
    // Consume before writing. Repeated callback against current state has
    // no frame; stale generations never release one.
    return {state:Object.assign({},state,{checkpointWait:null}),frame:held.frame};
}
function restoreCheckpoint(consumer,snapshot,recoveryRow) {
    // Only for a fresh shell before start(). Corrupt or mismatched evidence
    // returns null; caller must refuse startup. Empty evidence stays locked.
    if (!safe(snapshot) || ![1,2].includes(snapshot?.version)
        || !exact(snapshot,["version","action","acknowledgment","startup_unlock","can_execute"].concat(snapshot.version===2?["dismissal"]:[]))
        || snapshot.startup_unlock!==false || snapshot.can_execute!==false) return null;
    const a=snapshot.action,b=snapshot.acknowledgment,z=snapshot.version===2?snapshot.dismissal:null;
    if (snapshot.version===2 && (!exact(z,["version","kind","review"]) || z.version!==1
        || z.kind!=="REVIEW_DISMISS" || !reviewValue(z.review,recoveryRow)
        || z.review.snapshot.record.state!=="PREPARED")) return null;
    if (a!==null && (!exact(a,["version","kind","message"]) || a.version!==1
        || a.kind!=="ACTION" || !checkpointMessage(a.message))) return null;
    if (b!==null && (!exact(b,["version","kind","review"]) || b.version!==1
        || b.kind!=="REVIEW_ACK" || !reviewValue(b.review,recoveryRow))) return null;
    const old=b!==null?b.review.snapshot.record.message:null;
    const dismissed=z!==null?z.review.snapshot.record.message:null;
    if (a!==null && old!==null && !equal(a.message,old)) return null;
    const s=initial(consumer),m=a!==null?a.message:old!==null?old:dismissed;
    if (dismissed!==null && !equal(dismissed,m)) return null;
    return Object.assign({},s,{reviewLost:b!==null?JSON.parse(JSON.stringify(b.review)):null,
        dispositionLost:z!==null?JSON.parse(JSON.stringify(z.review)):null,
        session:Object.assign({},s.session,{unresolved:m?JSON.parse(JSON.stringify(m)):null,
            previousOwnerId:z!==null?z.review.owner_id:b!==null?b.review.owner_id:m?m.owner_id:null,
            feedback:m?"OUTCOME UNKNOWN // RECONCILE":"NOT CONNECTED"})});
}
// Deliberately no public startup unlock or action-reconciliation release.
// Complete durable inventory / lost action correlation is a prerequisite for
// those transitions. In this slice a trusted fixture can inject reviewed
// startup state; production stays locked even if the Python child is healthy.
