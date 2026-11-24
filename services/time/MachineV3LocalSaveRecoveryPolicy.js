.pragma library

// M11 display-only decoding. The caller must supply the active request token
// and selected original identity. No backend status becomes an action.
var KIND = "timew-local-save-recovery-ui-v1";
var DENIALS = ["protected_attempt_verified", "source_authenticated",
    "operator_selection_verified", "c5_spent_verified", "native_receipt_verified",
    "production_restore_allowed", "automatic_retry_allowed", "automatic_undo_allowed",
    "cross_database_atomic", "dispatch_execution_verified"];
var KEYS = ["kind", "request_id", "mode", "checkpoint_id", "status",
    "ordinary_status", "fractional_status", "fractional_attempt_id", "count",
    "intent_ids", "read_only", "local_data_only", "manual_review_required",
    "safe_actions"].concat(DENIALS);
var MATCH = "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED";
var EXACT = "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED";
var ORDINARY = ["PREPARED_HOLD", "DISPATCH_MARKED_UNKNOWN_HOLD",
    "ORIGINAL_SAVE_CONFLICT_HOLD", "ORIGINAL_SAVE_UNKNOWN_HOLD"];
var FRACTIONAL = [EXACT, "LEGACY_MATCH_LOCAL_EXACT_ABSENT",
    "CANDIDATE_CONFLICT_HOLD", "CHECKPOINT_CHANGED_HOLD",
    "LOCAL_EXACT_CONFLICT_HOLD", "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD"];

function uuid(value) {
    return typeof value === "string" && value.length === 36
        && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
}

function keys(data) {
    if (!data || typeof data !== "object" || Array.isArray(data))
        return false;
    var a = Object.keys(data).sort();
    var b = KEYS.slice().sort();
    return a.length === b.length && a.every(function(k, i) { return k === b[i]; });
}

function unavailable() {
    return {valid: false, status: "RECOVERY UNAVAILABLE // HOLD",
        ordinary: "UNKNOWN", fractional: "UNKNOWN", intentIds: [],
        detail: "Inspect original local records. Do not repeat Save."};
}

function display(status, ordinary, fractional, detail, ids) {
    return {valid: true, status: status, ordinary: ordinary,
        fractional: fractional, detail: detail, intentIds: ids || []};
}

function accept(data, requestId, mode, identity) {
    if (!uuid(requestId) || (mode !== "list" && mode !== "inspect")
            || (mode === "list" ? identity !== null : !uuid(identity))
            || !keys(data) || data.kind !== KIND
            || data.request_id !== requestId || data.mode !== mode
            || data.checkpoint_id !== identity || data.read_only !== true
            || data.local_data_only !== true || data.manual_review_required !== true
            || !Array.isArray(data.safe_actions) || data.safe_actions.length !== 0
            || !DENIALS.every(function(k) { return data[k] === false; })
            || !Array.isArray(data.intent_ids) || data.intent_ids.length > 64
            || data.count !== data.intent_ids.length)
        return unavailable();
    var o = data.ordinary_status, f = data.fractional_status;
    var a = data.fractional_attempt_id, s = data.status;
    if (a !== null && !uuid(a))
        return unavailable();
    if (s === "UNAVAILABLE_HOLD")
        return unavailable();
    if (mode === "list") {
        if (o !== null || f !== null || a !== null)
            return unavailable();
        var ids = data.intent_ids;
        for (var i = 0; i < ids.length; i++)
            if (!uuid(ids[i]) || (i > 0 && ids[i - 1] >= ids[i]))
                return unavailable();
        if (s === "NO_LOCAL_INTENTS_OBSERVED" && ids.length === 0)
            return display("NO LOCAL ATTEMPTS OBSERVED", "NOT INSPECTED", "NOT INSPECTED",
                "No coordinated intent seen in this read. This is not proof no Save happened.");
        if (s === "LOCAL_INTENTS_OBSERVED" && ids.length > 0)
            return display("LOCAL ATTEMPTS // READ ONLY", "NOT INSPECTED", "NOT INSPECTED",
                "Select an original attempt to inspect. No automatic retry.", ids.slice());
        return unavailable();
    }
    if (data.count !== 0)
        return unavailable();
    if (s === "COORDINATED_SAVE_UNKNOWN_HOLD" && o === null && f === null)
        return display("UNKNOWN // HOLD", "UNKNOWN", "UNKNOWN",
            "Original outcome unavailable. Do not repeat Save.");
    if (s === "ORDINARY_SAVE_UNRESOLVED_HOLD" && ORDINARY.indexOf(o) >= 0 && f === null) {
        var ordinary = o === "PREPARED_HOLD" ? "PREPARED // NO PAIR OBSERVED"
            : o === "DISPATCH_MARKED_UNKNOWN_HOLD" ? "MARKED // NO PAIR OBSERVED"
            : o === "ORIGINAL_SAVE_CONFLICT_HOLD" ? "CONFLICT" : "UNKNOWN";
        return display("ORDINARY SAVE // HOLD", ordinary, "NOT VERIFIED",
            "Ordinary Save unresolved. No automatic retry.");
    }
    if (o !== MATCH)
        return unavailable();
    if (s === "ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD" && a === null && f === null)
        return display("PARTIAL // HOLD", "LOCAL PAIR OBSERVED", "UNLINKED",
            "Ordinary checkpoint observed. Fractional attempt link unresolved.");
    if (s === "FRACTIONAL_LINK_CONFLICT_HOLD" && a !== null && f === null)
        return display("CONFLICT // HOLD", "LOCAL PAIR OBSERVED", "LINK CONFLICT",
            "Fractional attempt does not match its original link. Manual review.");
    if (s === "ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD"
            && a !== null && FRACTIONAL.indexOf(f) >= 0) {
        var fractional = f === "LEGACY_MATCH_LOCAL_EXACT_ABSENT" ? "NO ROWS OBSERVED"
            : f === EXACT ? "ROWS OBSERVED // UNRESOLVED"
            : f === "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD" ? "UNKNOWN" : "CONFLICT";
        return display("PARTIAL // HOLD", "LOCAL PAIR OBSERVED", fractional,
            "Fractional outcome unresolved. Do not repeat Save.");
    }
    if (s === "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED" && a !== null && f === EXACT)
        return display("LOCAL RECORDS OBSERVED // HOLD", "LOCAL PAIR OBSERVED", "LOCAL ROWS OBSERVED",
            "Local records only. Not authenticated execution or Restore authorization.");
    return unavailable();
}
