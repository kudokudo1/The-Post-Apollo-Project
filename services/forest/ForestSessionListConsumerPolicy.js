// ForestW // LIST_SESSIONS V1 (proposed) PRESENTATION-ONLY consumer.
// Parses already-delivered objects. THIS DOES NOT AUTHENTICATE THEIR SOURCE.
// The separate Forest Core / Connections protected host must authenticate the
// caller, independently scope owner and Tree, and authorize title disclosure.
// No database, socket, subprocess, encryption key, token or inference here.
var SCHEMA = "postapollo.forest.list-sessions-ui.v1";
var TREE_KEYS = ["CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH"];
var MAX_SESSIONS = 100;
var MAX_FRAME_CHARS = 65536;
var KEY = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;
var RID = /^[A-Za-z0-9_-]{16,96}$/;

function _exact(obj, keys) {
    if (!obj || typeof obj !== "object" || Array.isArray(obj))
        return false;
    const actual = Object.keys(obj);
    return actual.length === keys.length
        && actual.every(k => keys.indexOf(k) >= 0);
}
function _safeInt(n, positive) {
    return typeof n === "number" && isFinite(n)
        && Math.floor(n) === n && n <= Number.MAX_SAFE_INTEGER
        && n >= (positive ? 1 : 0);
}
function _utf8Length(s) {
    try {
        // URL-encoded bytes are two hex digits; literal ASCII is one byte.
        return encodeURIComponent(s).replace(/%[0-9a-fA-F]{2}|[^%]/g, "x").length;
    } catch (e) {
        return Infinity; // invalid surrogate
    }
}
function _hold(reason) {
    return {
        state: "UNAVAILABLE", reason: reason, sessions: [],
        // Strictly non-authority even if every supplied field matches.
        sourceAuthenticated: false, permissionGranted: false,
        canReadSession: false, safeActions: []
    };
}

// Correlation is NOT a security token, session grant, or proof of user intent.
function beginList(treeKey, requestId, generation) {
    if (TREE_KEYS.indexOf(treeKey) < 0 || typeof requestId !== "string"
            || !RID.test(requestId) || !_safeInt(generation, true))
        return _hold("INVALID_REQUEST");
    return {
        state: "PENDING", requestId: requestId, treeKey: treeKey,
        generation: generation, sessions: [],
        sourceAuthenticated: false, permissionGranted: false,
        canReadSession: false, safeActions: []
    };
}
function clearList() {
    return _hold("DISCONNECTED");
}

// Only the independently authenticated native host can eventually decide
// WHETHER a packet may reach ForestW. This function merely checks structure.
// A valid forged packet still confers NO authority and is not live chat.
function consumeList(pending, frame, currentTreeKey, currentGeneration) {
    if (!_exact(pending, ["state", "requestId", "treeKey", "generation",
                          "sessions", "sourceAuthenticated",
                          "permissionGranted", "canReadSession", "safeActions"])
            || pending.state !== "PENDING"
            || pending.sourceAuthenticated !== false
            || pending.permissionGranted !== false
            || pending.canReadSession !== false
            || !Array.isArray(pending.safeActions)
            || pending.safeActions.length !== 0
            || TREE_KEYS.indexOf(pending.treeKey) < 0
            || !RID.test(pending.requestId)
            || !_safeInt(pending.generation, true)
            || pending.treeKey !== currentTreeKey
            || pending.generation !== currentGeneration)
        return _hold("STALE_OR_UNAUTHORIZED_VIEW");
    const frameKeys = ["schema", "action", "requestId", "treeKey",
                       "generation", "status", "complete", "sessions"];
    if (!_exact(frame, frameKeys) || frame.schema !== SCHEMA
            || frame.action !== "LIST_SESSIONS"
            || frame.requestId !== pending.requestId
            || frame.treeKey !== pending.treeKey
            || frame.generation !== pending.generation
            || frame.status !== "READ_ONLY"
            || frame.complete !== true
            || !Array.isArray(frame.sessions)
            || frame.sessions.length > MAX_SESSIONS)
        return _hold("INVALID_RESPONSE");
    // A final size cap is defensive; the future trusted host must separately
    // impose a wire-byte cap and reject duplicate JSON object keys.
    try {
        if (JSON.stringify(frame).length > MAX_FRAME_CHARS)
            return _hold("INVALID_RESPONSE");
    } catch (e) {
        return _hold("INVALID_RESPONSE");
    }
    const ids = Object.create(null);
    const result = [];
    const recordKeys = ["session_id", "tree_key", "title", "state", "revision",
                        "created_at_ms", "updated_at_ms"];
    for (let i = 0; i < frame.sessions.length; i++) {
        const row = frame.sessions[i];
        if (!_exact(row, recordKeys)
                || typeof row.session_id !== "string" || !KEY.test(row.session_id)
                || typeof row.tree_key !== "string" || row.tree_key !== pending.treeKey
                || typeof row.title !== "string" || !row.title
                || _utf8Length(row.title) > 160
                || /[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]/.test(row.title)
                || ["OPEN", "PAUSED", "ARCHIVED"].indexOf(row.state) < 0
                || !_safeInt(row.revision, false)
                || !_safeInt(row.created_at_ms, true)
                || !_safeInt(row.updated_at_ms, true)
                || row.updated_at_ms < row.created_at_ms
                || ids[row.session_id])
            return _hold("INVALID_RESPONSE"); // no partial publication
        ids[row.session_id] = true;
        if (row.state === "OPEN")
            result.push({
                session_id: row.session_id,
                title: row.title,
                revision: row.revision,
                updated_at_ms: row.updated_at_ms
            });
    }
    result.sort((a, b) => b.updated_at_ms - a.updated_at_ms
        || (a.session_id < b.session_id ? -1 : a.session_id > b.session_id ? 1 : 0));
    return {
        state: "STRUCTURALLY_VALID_NOT_AUTHENTICATED",
        reason: "",
        sessions: result,
        // Never promote a data field into a trusted connection or grant.
        sourceAuthenticated: false, permissionGranted: false,
        canReadSession: false, safeActions: []
    };
}
