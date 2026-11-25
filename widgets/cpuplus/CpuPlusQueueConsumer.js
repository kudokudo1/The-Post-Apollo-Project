// DOC 2 R2b: local consumer state for DOC 4's proposed in-process envelope.
// No IPC, runtime owner, timer, clock conversion, persistence or authority.
// Host must supply a trusted connection epoch and the reviewed R2a projector.
// All state transitions are immutable; only submit() returns a client message.
const MAX_SAFE = Number.MAX_SAFE_INTEGER;
function uuid(value) {
    return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
}
function positive(value) { return Number.isSafeInteger(value) && value > 0; }
function exact(value,keys) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        && Object.keys(value).length === keys.length
        && keys.every(k=>Object.prototype.hasOwnProperty.call(value,k));
}
function initial() {
    return {ownerId:null, previousOwnerId:null, sequence:0, nextActionSequence:null, status:null,
        prepared:null, pending:null, unresolved:null, feedback:"NOT CONNECTED"};
}
function invalidate(state, feedback) {
    return Object.assign({},state,{status:null,prepared:null,nextActionSequence:null,feedback:feedback});
}
function uncertain(state, feedback) {
    return Object.assign({},invalidate(state,feedback),{
        unresolved:state.pending || state.unresolved,pending:null});
}
function connect(state, ownerId) {
    if (!uuid(ownerId)) return disconnect(state);
    if (state.ownerId === ownerId) return state;
    // Only the transport lifecycle may call connect; a reply cannot choose its
    // own trusted owner. A lost in-flight action survives owner replacement.
    const lost=uncertain(state,"FRESH STATUS REQUIRED");
    return Object.assign({},initial(),{ownerId:ownerId,previousOwnerId:ownerId,
        sequence:state.previousOwnerId === ownerId ? state.sequence : 0,unresolved:lost.unresolved,
        feedback:lost.unresolved ? "OUTCOME UNKNOWN // RECONCILE" : "FRESH STATUS REQUIRED"});
}
function disconnect(state) {
    const lost=uncertain(state,"NOT CONNECTED");
    return Object.assign({},initial(),{previousOwnerId:state.ownerId || state.previousOwnerId,
        sequence:state.sequence,unresolved:lost.unresolved,
        feedback:lost.unresolved ? "OWNER LOST // RECONCILE" : "NOT CONNECTED"});
}
function timeout(state) {
    return uncertain(state,state.pending || state.unresolved
        ? "OUTCOME UNKNOWN // RECONCILE" : "STATUS UNAVAILABLE");
}
function metadata(state,packet,kind,fields) {
    if (!state.ownerId || !packet || packet.owner_id !== state.ownerId) return "IGNORE";
    if (!positive(packet.sequence)) return "INVALID";
    if (packet.sequence <= state.sequence) return "IGNORE";
    if (!exact(packet,["version","owner_id","sequence","next_action_sequence","kind","can_execute"].concat(fields))
        || packet.version !== 1 || packet.kind !== kind || packet.can_execute !== false
        || !positive(packet.next_action_sequence)) return "INVALID";
    return "OK";
}
function acceptStatus(state,packet,projector) {
    const check=metadata(state,packet,"STATUS",["projection"]);
    if (check === "IGNORE") return state;
    if (check !== "OK") return uncertain(state,"INVALID STATUS // RECONCILE");
    const advanced=Object.assign({},state,{sequence:packet.sequence,prepared:null});
    if (state.pending) {
        // An unsolicited STATUS is not an action reply. Ordered delivery is
        // required; if the reply is lost the host must signal timeout.
        return invalidate(advanced,"ACTION PENDING");
    }
    let view;
    try { view=projector(packet.projection); } catch (_) { view=null; }
    const raw=packet.projection && packet.projection.status;
    if (!view || !raw || !["IDLE REPORTED","WAITING REPORTED","UNKNOWN","READY REPORTED // RECHECK REQUIRED"].includes(view.state)
        || view.canExecute !== false || view.outcome !== "UNVERIFIED"
        || raw.can_execute !== false || packet.projection.can_execute !== false
        || packet.projection.adjustment_outcome !== "UNVERIFIED"
        || view.requestId !== raw.request_id || (view.requestId !== null && !uuid(view.requestId))
        || (view.state === "IDLE REPORTED" && view.requestId !== null)
        || (view.state === "WAITING REPORTED" && view.requestId === null))
        return uncertain(advanced,"INVALID STATUS // RECONCILE");
    // Retain only sanitized display output, never raw request identity data,
    // receipt, notification candidate or Linux inode/device integers.
    const status={state:view.state,requestId:view.requestId,targetGiB:view.targetGiB,
        code:raw.code,outcome:"UNVERIFIED",canExecute:false};
    return Object.assign({},advanced,{status:status,nextActionSequence:packet.next_action_sequence,
        feedback:advanced.unresolved ? "OUTCOME UNKNOWN // RECONCILE" : "STATUS REPORTED"});
}
function prepare(state,kind,target,expires) {
    if (!state.ownerId || !state.status || state.pending || state.unresolved
        || !positive(state.nextActionSequence) || state.nextActionSequence >= MAX_SAFE
        || !["QUEUE","REPLACE","CANCEL","EXPIRE","RECHECK"].includes(kind)) return state;
    const id=state.status.requestId;
    if (kind === "QUEUE" ? state.status.state !== "IDLE REPORTED" || id !== null : !uuid(id))
        return state;
    if (kind === "EXPIRE" && state.status.code !== "EXPIRY_RECONCILIATION_REQUIRED") return state;
    if (kind === "QUEUE" || kind === "REPLACE") {
        if (!positive(target) || target < 4 || target > 64 || target%4 !== 0 || !positive(expires)) return state;
    } else if (target !== null || expires !== null) return state;
    return Object.assign({},state,{prepared:{ownerId:state.ownerId,statusSequence:state.sequence,
        actionSequence:state.nextActionSequence,kind:kind,expectedId:id,targetGiB:target,expiresAt:expires},
        feedback:"CONFIRM EXPLICIT INTENT"});
}
function cancelPreparation(state) {
    return Object.assign({},state,{prepared:null,feedback:state.status ? "STATUS REPORTED" : state.feedback});
}
function submit(state,actionId) {
    const p=state.prepared;
    if (!p || !state.status || state.pending || state.unresolved || !uuid(actionId)
        || p.ownerId !== state.ownerId || p.statusSequence !== state.sequence
        || p.actionSequence !== state.nextActionSequence || p.expectedId !== state.status.requestId)
        return {state:state,message:null};
    // The host supplies a fresh action UUID. Never synthesize retries here.
    const message={version:1,owner_id:p.ownerId,action_id:actionId,action_sequence:p.actionSequence,
        kind:p.kind,expected_request_id:p.expectedId,target_gib:p.targetGiB,expires_at:p.expiresAt};
    return {state:Object.assign({},invalidate(state,"ACTION PENDING"),{pending:Object.assign({},message)}),
        message:message};
}
function acceptAction(state,packet) {
    const check=metadata(state,packet,"ACTION",["action_id","action_sequence","disposition","code","result","invalidate"]);
    if (check === "IGNORE") return state;
    if (check !== "OK") return uncertain(state,"INVALID RESPONSE // RECONCILE");
    const advanced=Object.assign({},state,{sequence:packet.sequence});
    const p=state.pending;
    if (!p || packet.action_id !== p.action_id || packet.action_sequence !== p.action_sequence
        || packet.next_action_sequence !== p.action_sequence + 1 || packet.invalidate !== true)
        return uncertain(advanced,"UNMATCHED RESPONSE // RECONCILE");
    if (packet.disposition === "UNKNOWN" && packet.code === "RECONCILE_REQUIRED" && packet.result === null)
        return uncertain(advanced,"OUTCOME UNKNOWN // RECONCILE");
    if (packet.disposition === "REFUSED" && packet.code === "STALE_REQUEST" && packet.result === null)
        return Object.assign({},invalidate(advanced,"REFUSED // FRESH STATUS REQUIRED"),{pending:null});
    if (packet.disposition === "REPORTED" && packet.code === "READ_STATUS_REQUIRED"
        && packet.result && packet.result.version === 1 && packet.result.can_execute === false
        && packet.result.adjustment_outcome === "UNVERIFIED") {
        // Raw result is intentionally not parsed, stored or rendered. A
        // separately reviewed JS-safe response codec is required for real IPC.
        return Object.assign({},invalidate(advanced,"REPORTED // FRESH STATUS REQUIRED"),{pending:null});
    }
    return uncertain(advanced,"INVALID RESPONSE // RECONCILE");
}
function acknowledgeReconciliation(state) {
    // Explicit UI action only, after operator has read fresh status/history.
    // This does not prove success/failure or resend the unresolved message.
    if (!state.unresolved || !state.status || state.pending) return state;
    return Object.assign({},state,{unresolved:null,feedback:"RECONCILIATION ACKNOWLEDGED"});
}
