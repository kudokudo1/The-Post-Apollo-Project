// R3c reduced DETAIL presentation, aligned with DOC 4 #2577.
// The session host supplies the expected owner, requested ID and sequence
// floor from its outstanding HISTORY read. No history request or action here.
function exact(o,keys) {
    return o !== null && typeof o === "object" && !Array.isArray(o)
        && Object.keys(o).length === keys.length
        && keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));
}
function uuid(s) {
    return typeof s === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(s);
}
function count(v) { return Number.isSafeInteger(v) && v >= 0; }
function seconds(v) { return count(v) && v <= 8640000000000; }
function utc(v) { return seconds(v) ? new Date(v*1000).toISOString() : "UNAVAILABLE"; }
function gib(v) { return count(v) ? (v/1048576).toFixed(2)+" GiB" : "UNAVAILABLE"; }
function project(packet,ownerId,requestId,sequenceFloor) {
    if (!uuid(ownerId) || !uuid(requestId) || !count(sequenceFloor)
        || !exact(packet,["version","owner_id","sequence","next_action_sequence","kind","can_execute","detail"])
        || packet.version !== 1 || packet.kind !== "DETAIL" || packet.can_execute !== false
        || packet.owner_id !== ownerId || !count(packet.sequence) || packet.sequence <= sequenceFloor
        || !count(packet.next_action_sequence) || packet.next_action_sequence < 1) return null;
    const d=packet.detail;
    if (!exact(d,["version","request","notification_events","withdrawal_evidence","adjustment_outcome","can_execute"])
        || d.version !== 1 || d.can_execute !== false || d.adjustment_outcome !== "UNVERIFIED") return null;
    const r=d.request;
    if (!exact(r,["id","state","target_gib","original_actual_kib","requested_at","expires_at","changed_at","replaced_by"])
        || r.id !== requestId || !["QUEUED","CANCELLED","REPLACED","EXPIRED"].includes(r.state)
        || !count(r.target_gib) || r.target_gib > 64 || r.target_gib % 4
        || !count(r.original_actual_kib) || !seconds(r.requested_at) || !seconds(r.expires_at)
        || !seconds(r.changed_at) || r.expires_at <= r.requested_at || r.changed_at < r.requested_at
        || (r.state === "QUEUED" && r.changed_at !== r.requested_at)
        || (r.state === "EXPIRED" && r.changed_at < r.expires_at)
        || (r.state === "REPLACED" ? !uuid(r.replaced_by) || r.replaced_by === r.id : r.replaced_by !== null)) return null;
    const codes={
        DEFERRED:["BASE_OR_EXTENSION_INACTIVE","UNEXPECTED_SWAP_IDENTITY","UNEXPECTED_CAPACITY","UNSUPPORTED_TARGET",
            "EXTENSION_OCCUPIED","RAM_HEADROOM","BASE_HEADROOM","MEMORY_PRESSURE","OPERATION_BUSY","STABILITY_INTERVAL"],
        ATTENTION:["OBSERVATION_UNAVAILABLE","BOOT_CHANGED","SOURCE_CHANGED","OPERATION_AMBIGUOUS",
            "STALE_OBSERVATION","INVALID_OBSERVATION","OBSERVATION_ORDER_INVALID"],
        READY_ADVISORY:["FRESH_AUTH_AND_ROOT_CHECK_REQUIRED"],EXPIRED:["EXPIRED"],CANCELLED:["CANCELLED"]
    };
    if (!Array.isArray(d.notification_events) || d.notification_events.length > 5) return null;
    const seen=[],events=[];
    for (const e of d.notification_events) {
        if (!exact(e,["event_id","kind","code","observed_at","attempt_reserved_at_ms","delivery_outcome"])
            || !Object.prototype.hasOwnProperty.call(codes,e.kind) || !codes[e.kind].includes(e.code)
            || seen.includes(e.kind) || e.event_id !== "apollo-cpu-memory-"+r.id+"-"+e.kind.toLowerCase().replace(/_/g,"-")
            || !seconds(e.observed_at) || e.observed_at < r.requested_at) return null;
        const terminal=e.kind==="EXPIRED" || e.kind==="CANCELLED";
        if (terminal ? r.state!==e.kind || e.observed_at!==r.changed_at
            : e.observed_at>=r.expires_at || (r.state!=="QUEUED" && e.observed_at>r.changed_at)) return null;
        const attempt=e.attempt_reserved_at_ms;
        if (attempt===null ? e.delivery_outcome!=="NOT_RECORDED"
            : !count(attempt) || attempt<e.observed_at*1000 || e.delivery_outcome!=="UNKNOWN") return null;
        seen.push(e.kind);
        events.push({kind:e.kind==="READY_ADVISORY"?"READINESS REPORTED (HISTORICAL)":e.kind,
            code:e.code,observedAt:e.observed_at,delivery:attempt===null?"NO ATTEMPT RECORDED":"ATTEMPT RESERVED // DELIVERY UNKNOWN"});
    }
    const evidence=d.withdrawal_evidence;
    if (evidence!==null && (!exact(evidence,["state","observed_at","kernel_verified_for_request","can_execute"])
        || evidence.state!=="UNBOUND_EVIDENCE" || !seconds(evidence.observed_at)
        || evidence.observed_at<r.requested_at || evidence.kernel_verified_for_request!==false
        || evidence.can_execute!==false)) return null;
    return {requestId:r.id,state:r.state,targetGiB:r.target_gib,originalKiB:r.original_actual_kib,
        requestedAt:r.requested_at,expiresAt:r.expires_at,changedAt:r.changed_at,replacedBy:r.replaced_by,
        events:events,evidenceAt:evidence===null?null:evidence.observed_at,
        outcome:"UNVERIFIED",canExecute:false};
}
