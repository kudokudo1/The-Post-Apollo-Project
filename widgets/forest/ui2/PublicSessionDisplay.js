// UI2.1: public disposable display projection, not an authentication boundary.
// Never feed these four-field records into the seven-field journal validator.
var SCHEMA = "postapollo.forest.public-session-display.v1";
var TREES = ["CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH"];
var KEY = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;
var REQUEST = /^[A-Za-z0-9_-]{16,96}$/;
function exact(o, keys) {
    return o !== null && typeof o === "object" && !Array.isArray(o)
        && Object.keys(o).length === keys.length
        && keys.every(k => Object.prototype.hasOwnProperty.call(o, k));
}
function integer(v, min) {
    return Number.isSafeInteger(v) && v >= min;
}
function textOK(s) {
    if (typeof s !== "string" || !s.trim()
        || /[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/.test(s))
        return false;
    try { return encodeURIComponent(s).replace(/%[0-9a-fA-F]{2}|[^%]/g, "x").length <= 160; }
    catch (_) { return false; }
}
function viewOK(v) {
    return exact(v, ["requestId", "treeKey", "generation"])
        && typeof v.requestId === "string" && REQUEST.test(v.requestId)
        && TREES.indexOf(v.treeKey) >= 0 && integer(v.generation, 1);
}
function unavailable() {
    return {state: "UNAVAILABLE", sessions: [], sourceAuthenticated: false,
        permissionGranted: false, safeActions: []};
}
function project(frame, requested, current) {
    if (!viewOK(requested) || !viewOK(current)
        || requested.requestId !== current.requestId
        || requested.treeKey !== current.treeKey
        || requested.generation !== current.generation
        || !exact(frame, ["schema", "requestId", "treeKey", "generation", "sessions"])
        || frame.schema !== SCHEMA || frame.requestId !== current.requestId
        || frame.treeKey !== current.treeKey || frame.generation !== current.generation
        || !Array.isArray(frame.sessions) || frame.sessions.length > 100)
        return unavailable();
    const seen = Object.create(null);
    const rows = [];
    for (const row of frame.sessions) {
        if (!exact(row, ["session_id", "title", "revision", "updated_at_ms"])
            || typeof row.session_id !== "string" || !KEY.test(row.session_id)
            || seen[row.session_id] || !textOK(row.title)
            || !integer(row.revision, 0) || !integer(row.updated_at_ms, 1))
            return unavailable();
        seen[row.session_id] = true;
        rows.push({session_id: row.session_id, title: row.title,
            revision: row.revision, updated_at_ms: row.updated_at_ms});
    }
    rows.sort((a,b) => b.updated_at_ms - a.updated_at_ms
        || (a.session_id < b.session_id ? -1 : a.session_id > b.session_id ? 1 : 0));
    return {state: "STRUCTURALLY_VALID_PUBLIC_FIXTURE", sessions: rows,
        sourceAuthenticated: false, permissionGranted: false, safeActions: []};
}
