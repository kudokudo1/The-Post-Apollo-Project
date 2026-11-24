// DOC 2: display-only R1 projection. No transport, persistence, authority or
// shared clock yet. READY_ADVISORY is historical until an owner can invalidate
// it in the monitor's monotonic clock domain. Never compare it with Date.now().
function integer(value) {
    return Number.isSafeInteger(value) && value >= 0;
}
function nullableInteger(value) {
    return value === null || integer(value);
}
function uuid(value) {
    return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
}
function hasKeys(value, keys) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        && Object.keys(value).length === keys.length
        && keys.every(key => Object.prototype.hasOwnProperty.call(value,key));
}
function gib(kib) {
    return integer(kib) ? (kib / 1048576).toFixed(2) + " GiB" : "UNAVAILABLE";
}
function unknown(label) {
    return {state:label, reason:"No current queue observation.", requestId:null,
        originalActualKiB:null, targetGiB:null, checkedAt:null, expiresAt:null,
        scheduled:null, notificationIssue:false, outcome:"UNVERIFIED", canExecute:false};
}
function reasonFor(code) {
    const reasons = {
        NO_PENDING_REQUEST:"No pending request in the reported snapshot.",
        EXTENSION_OCCUPIED:"Extension still contains swap pages. Wait and recheck.",
        RAM_HEADROOM:"Available RAM is below the required reserve.",
        BASE_HEADROOM:"Remaining base swap is below the required reserve.",
        MEMORY_PRESSURE:"Memory pressure exceeds the advisory limit.",
        OPERATION_BUSY:"Another operation is in progress.",
        STABILITY_INTERVAL:"Waiting for the required observation interval.",
        CONTINUITY_REQUIRED:"More independent observations are required.",
        FRESH_AUTH_AND_ROOT_CHECK_REQUIRED:"Readiness was reported; fresh checks and separate authorization are required.",
        EXPIRY_RECONCILIATION_REQUIRED:"Request expiry requires explicit reconciliation.",
        SOURCE_CHANGED:"Observed allocation differs from the saved request.",
        BOOT_CHANGED:"Boot changed; request needs reconciliation.",
        OPERATION_AMBIGUOUS:"Operation state is uncertain. Do not replay.",
        OBSERVATION_UNAVAILABLE:"Independent observation is unavailable.",
        STALE_OBSERVATION:"Observation is no longer fresh.",
        OBSERVATION_ORDER_INVALID:"Observation order is invalid.",
        INVALID_OBSERVATION:"Observation failed validation.",
        CLOCK_ROLLBACK:"Clock changed unexpectedly.",
        CLOCK_UNAVAILABLE_OR_ROLLBACK:"Owner clock unavailable or changed.",
        QUEUE_UNAVAILABLE:"Queue storage is unavailable.",
        RUNTIME_UNAVAILABLE:"Runtime is unavailable.",
        REQUEST_CHANGED:"Request changed; re-read owner status.",
        BASE_OR_EXTENSION_INACTIVE:"Both managed allocations are not active.",
        UNEXPECTED_SWAP_IDENTITY:"Swap identity differs from expected evidence.",
        UNEXPECTED_CAPACITY:"Observed capacity differs from expected evidence.",
        UNSUPPORTED_TARGET:"Requested operation is outside this runtime slice."
    };
    return typeof code === "string" && Object.prototype.hasOwnProperty.call(reasons,code)
        ? reasons[code] : null;
}
function project(packet) {
    if (packet === null || packet === undefined) return unknown("NOT CONNECTED");
    if (!hasKeys(packet,["version","status","notification_candidate","notification_error",
        "adjustment_outcome","can_execute"]) || packet.version !== 1
        || packet.adjustment_outcome !== "UNVERIFIED" || packet.can_execute !== false)
        return unknown("UNSUPPORTED STATUS");
    const s = packet.status;
    if (!hasKeys(s,["version","request_id","target_gib","original_actual_kib","expires_at",
        "state","code","can_execute","last_checked_at","next_check_monotonic_ms",
        "ready_valid_before_monotonic_ms","transition"])
        || s.version !== 1 || s.can_execute !== false || typeof s.transition !== "boolean"
        || !["IDLE","WAITING","UNKNOWN","READY_ADVISORY"].includes(s.state)
        || !reasonFor(s.code) || !nullableInteger(s.last_checked_at)
        || !nullableInteger(s.next_check_monotonic_ms)
        || !nullableInteger(s.ready_valid_before_monotonic_ms)
        || !(packet.notification_error === null || typeof packet.notification_error === "string"))
        return unknown("INVALID STATUS");
    if (s.request_id === null) {
        if (s.target_gib !== null || s.original_actual_kib !== null || s.expires_at !== null
            || s.last_checked_at !== null || s.next_check_monotonic_ms !== null
            || s.ready_valid_before_monotonic_ms !== null
            || !["IDLE","UNKNOWN"].includes(s.state)
            || (s.state === "IDLE") !== (s.code === "NO_PENDING_REQUEST"))
            return unknown("INVALID STATUS");
    } else if (!uuid(s.request_id) || !integer(s.target_gib) || s.target_gib < 4
        || s.target_gib > 64 || s.target_gib % 4 !== 0 || !integer(s.original_actual_kib)
        || s.original_actual_kib <= s.target_gib * 1048576
        || !integer(s.expires_at) || s.expires_at <= 0 || s.state === "IDLE")
        return unknown("INVALID STATUS");
    if (s.state === "READY_ADVISORY") {
        if (!s.request_id || s.code !== "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED"
            || s.last_checked_at === null || s.last_checked_at >= s.expires_at
            || s.ready_valid_before_monotonic_ms === null
            || s.next_check_monotonic_ms !== s.ready_valid_before_monotonic_ms)
            return unknown("INVALID STATUS");
    } else if (s.ready_valid_before_monotonic_ms !== null
        || s.code === "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED") return unknown("INVALID STATUS");
    if (s.request_id !== null && s.code === "NO_PENDING_REQUEST") return unknown("INVALID STATUS");
    return {state:s.state === "READY_ADVISORY" ? "READY REPORTED // RECHECK REQUIRED"
        : s.state === "IDLE" ? "IDLE REPORTED"
        : s.state === "WAITING" ? "WAITING REPORTED" : "UNKNOWN",
        reason:reasonFor(s.code), requestId:s.request_id, originalActualKiB:s.original_actual_kib,
        targetGiB:s.target_gib, checkedAt:s.last_checked_at, expiresAt:s.expires_at,
        scheduled:s.next_check_monotonic_ms !== null, notificationIssue:packet.notification_error !== null,
        outcome:"UNVERIFIED", canExecute:false};
}
function timestamp(seconds) {
    // Invalid/out-of-range timestamps never render as a meaningful date.
    if (!integer(seconds) || seconds > 8640000000000) return "UNAVAILABLE";
    return new Date(seconds * 1000).toISOString();
}
