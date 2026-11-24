// Public M4 fixture page projection, not a transport or authorization boundary.
// Caller must supply only host-owned disposable public fixture data.
var SCHEMA = "postapollo.forest.public-history-display.v1";
var TREES = ["CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH"];
var KEY = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;
var REQUEST = /^[A-Za-z0-9_-]{16,96}$/;
var REF_KEYS = ["requestId", "treeKey", "generation", "sessionId",
                "revision", "after", "limit"];
function exact(o, keys) {
    return o !== null && typeof o === "object" && !Array.isArray(o)
        && Object.keys(o).length === keys.length
        && keys.every(k => Object.prototype.hasOwnProperty.call(o,k));
}
function integer(n, min) { return Number.isSafeInteger(n) && n >= min; }
function identifier(s, pattern) {
    // JS $ also matches before a trailing newline; require a full match.
    if (typeof s !== "string") return false;
    const match = pattern.exec(s);
    return match !== null && match[0] === s;
}
function utf8Length(s) {
    try { return encodeURIComponent(s).replace(/%[0-9a-fA-F]{2}|[^%]/g,"x").length; }
    catch (_) { return Infinity; }
}
function refOK(r) {
    return exact(r, REF_KEYS) && identifier(r.requestId,REQUEST)
        && TREES.indexOf(r.treeKey) >= 0 && integer(r.generation,1)
        && identifier(r.sessionId,KEY) && integer(r.revision,0)
        && integer(r.after,0) && r.after <= r.revision
        && integer(r.limit,1) && r.limit <= 16;
}
function unavailable() {
    return {state:"UNAVAILABLE", messages:[], complete:false, nextAfter:null,
        sourceAuthenticated:false, permissionGranted:false, safeActions:[]};
}
// Returns one page, never appends to existing history or issues a new request.
function project(frame, requested, current) {
    if (!refOK(requested) || !refOK(current)
        || REF_KEYS.some(k => requested[k] !== current[k])
        || !exact(frame,["schema","requestId","treeKey","generation",
                         "sessionId","revision","messages","complete"])
        || frame.schema !== SCHEMA
        || ["requestId","treeKey","generation","sessionId","revision"]
            .some(k => frame[k] !== current[k])
        || typeof frame.complete !== "boolean"
        || !Array.isArray(frame.messages) || frame.messages.length > current.limit
        || frame.messages.length > current.revision-current.after
        || (!frame.complete && frame.messages.length === 0)
        || (!frame.complete && frame.messages.length === current.revision-current.after))
        return unavailable();
    const seen = Object.create(null);
    const messages = [];
    const canonicalRows = [];
    for (let i=0; i<frame.messages.length; ++i) {
        const r = frame.messages[i];
        if (!exact(r,["turn_id","ordinal","role","text"])
            || !identifier(r.turn_id,KEY) || seen[r.turn_id]
            || !integer(r.ordinal,1) || r.ordinal !== current.after+i+1
            || (r.role !== "user" && r.role !== "assistant")
            || typeof r.text !== "string" || !r.text
            || r.text.length > 16000
            || /[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/.test(r.text)
            || utf8Length(r.text)>16000)
            return unavailable();
        seen[r.turn_id] = true;
        canonicalRows.push({turn_id:r.turn_id,ordinal:r.ordinal,role:r.role,text:r.text});
        messages.push({turnId:r.turn_id,ordinal:r.ordinal,
            direction:r.role === "user" ? "outgoing" : "incoming",body:r.text});
    }
    // Match M4's compact candidate JSON bound, not actual wire bytes.
    const bounded = {schema:SCHEMA,requestId:current.requestId,treeKey:current.treeKey,
        generation:current.generation,sessionId:current.sessionId,
        revision:current.revision,messages:canonicalRows,complete:frame.complete};
    if (utf8Length(JSON.stringify(bounded)) > 65536) return unavailable();
    return {state:"STRUCTURALLY_VALID_PUBLIC_FIXTURE",messages:messages,
        complete:frame.complete,nextAfter:frame.complete ? null : current.after+messages.length,
        sourceAuthenticated:false,permissionGranted:false,safeActions:[]};
}
