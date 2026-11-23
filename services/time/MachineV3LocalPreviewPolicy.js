.pragma library

// TimeW M5 display-only decoding. Never return approval, actions, commands,
// selected native identity or a signed receipt from untrusted local data.
var MAX_ENTRIES = 512;
var ROOT_KEYS = [
    "kind", "checkpoint_id", "status", "count", "entries", "read_only",
    "data_origin", "source_authenticated", "operator_selection_verified",
    "c5_spent_verified", "native_receipt_verified",
    "exact_restore_verified", "restore_allowed", "native_action_allowed",
    "retry_allowed", "undo_allowed", "safe_actions"
];
var ENTRY_KEYS = [
    "capture_id", "checkpoint_window_key", "app_id", "output_id",
    "workspace_id", "saved_at_utc", "geometry", "observed_phase",
    "local_data_untrusted", "selected_window_identity_verified",
    "source_authenticated", "settled_frame_verified", "action_allowed"
];
var ROOT_DENIALS = [
    "source_authenticated", "operator_selection_verified",
    "c5_spent_verified", "native_receipt_verified",
    "exact_restore_verified", "restore_allowed", "native_action_allowed",
    "retry_allowed", "undo_allowed"
];
var AXES = ["x", "y", "width", "height"];

function unavailable() {
    return {valid: false, status: "LOCAL PREVIEW UNAVAILABLE // HOLD",
            count: 0, entries: []};
}

function _keys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return false;
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    if (actual.length !== wanted.length)
        return false;
    for (var i = 0; i < actual.length; i++)
        if (actual[i] !== wanted[i])
            return false;
    return true;
}

function _uuid(value, versionFour) {
    if (typeof value !== "string")
        return false;
    var expression = versionFour
        ? /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
        : /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    return expression.test(value);
}

function _label(value, maximum) {
    return typeof value === "string"
        && value.length > 0 && value.length <= maximum
        && /^[\x20-\x7e]+$/.test(value);
}

function _geometry(value) {
    if (!_keys(value, AXES))
        return null;
    var result = {};
    for (var i = 0; i < AXES.length; i++) {
        var axis = AXES[i];
        var reading = value[axis];
        if (!_keys(reading, ["decimal", "binary64_hex"])
                || typeof reading.decimal !== "string"
                || reading.decimal.length === 0
                || reading.decimal.length > 40
                || !/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-][0-9]+)?$/.test(reading.decimal)
                || typeof reading.binary64_hex !== "string"
                || reading.binary64_hex.length > 40
                || !/^-?0x[0-9a-f]+\.[0-9a-f]+p[+-][0-9]+$/.test(reading.binary64_hex))
            return null;
        result[axis] = {decimal: reading.decimal,
                        binary64_hex: reading.binary64_hex};
    }
    return result;
}

function accept(data, expectedCheckpoint) {
    if (!_uuid(expectedCheckpoint, true)
            || !_keys(data, ROOT_KEYS)
            || data.kind !== "timew-v3-local-exact-capture-preview-v1"
            || data.checkpoint_id !== expectedCheckpoint
            || data.read_only !== true
            || data.data_origin !== "CALLER_SUPPLIED_LOCAL_UNTRUSTED"
            || !Array.isArray(data.safe_actions)
            || data.safe_actions.length !== 0)
        return unavailable();

    for (var d = 0; d < ROOT_DENIALS.length; d++)
        if (data[ROOT_DENIALS[d]] !== false)
            return unavailable();

    if (typeof data.count !== "number" || !isFinite(data.count)
            || Math.floor(data.count) !== data.count
            || data.count < 0 || data.count > MAX_ENTRIES
            || !Array.isArray(data.entries)
            || data.entries.length !== data.count)
        return unavailable();

    if (!((data.status === "NO_LOCAL_CAPTURES" && data.count === 0)
            || (data.status === "LOCAL_CAPTURES_UNTRUSTED_HOLD"
                && data.count > 0)))
        return unavailable();

    var items = [];
    var seen = {};
    for (var i = 0; i < data.entries.length; i++) {
        var entry = data.entries[i];
        if (!_keys(entry, ENTRY_KEYS)
                || !_uuid(entry.capture_id, true)
                || !_uuid(entry.checkpoint_window_key, false)
                || !_label(entry.app_id, 128)
                || !_label(entry.output_id, 128)
                || !_label(entry.workspace_id, 128)
                || !_label(entry.saved_at_utc, 64)
                || entry.observed_phase !== "CURRENT_VALUE_ONLY"
                || entry.local_data_untrusted !== true
                || entry.selected_window_identity_verified !== false
                || entry.source_authenticated !== false
                || entry.settled_frame_verified !== false
                || entry.action_allowed !== false
                || seen[entry.capture_id] === true
                || seen[entry.checkpoint_window_key] === true)
            return unavailable();
        var g = _geometry(entry.geometry);
        if (g === null)
            return unavailable();
        seen[entry.capture_id] = true;
        seen[entry.checkpoint_window_key] = true;
        items.push({
            app_id: entry.app_id,
            output_id: entry.output_id,
            workspace_id: entry.workspace_id,
            capture_id: entry.capture_id,
            window_key: entry.checkpoint_window_key,
            saved_at_utc: entry.saved_at_utc,
            geometry: g
        });
    }

    // Keep this return shape display-only. No future caller can acquire
    // native permission by accidentally referencing a preview field.
    return {valid: true, status: data.status, count: data.count,
            entries: items};
}
