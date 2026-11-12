.pragma library

// P1 // Owner-local draft records only. Never store authentication material.
// Pure policy: no network, filesystem, provider, or identity side effects.
var VERSION = 1;
var MAX_DRAFTS = 100;
var MAX_TITLE = 120;
var MAX_BODY = 10000;
var MAX_FILE_LENGTH = 1500000;
var MAX_SEQUENCE = 1000000000;

function emptyDocument() {
    return {version: VERSION, nextId: 1, drafts: []};
}
function plain(value) {
    return value !== null && typeof value === "object"
        && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
}
function exactly(value, keys) {
    if (!plain(value)) return false;
    var have = Object.keys(value).sort();
    var want = keys.slice().sort();
    return have.length === want.length && have.every(function(k, i) {
        return k === want[i];
    });
}
function integer(value, low, high) {
    return typeof value === "number" && isFinite(value)
        && Math.floor(value) === value && value >= low && value <= high;
}
function cleanTitle(value) {
    return typeof value === "string" && value === value.trim()
        && value.length > 0 && value.length <= MAX_TITLE
        && !/[\x00-\x1f\x7f]/.test(value);
}
function cleanBody(value) {
    return typeof value === "string" && value.length <= MAX_BODY
        && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value);
}
function validDraft(draft) {
    return exactly(draft, ["id", "title", "body", "createdAtMs", "updatedAtMs"])
        && typeof draft.id === "string" && /^d[1-9][0-9]*$/.test(draft.id)
        && integer(Number(draft.id.slice(1)), 1, MAX_SEQUENCE)
        && cleanTitle(draft.title) && cleanBody(draft.body)
        && integer(draft.createdAtMs, 1, Number.MAX_SAFE_INTEGER)
        && integer(draft.updatedAtMs, draft.createdAtMs, Number.MAX_SAFE_INTEGER);
}
function validate(doc) {
    if (!plain(doc)) return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== VERSION) return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!exactly(doc, ["version", "nextId", "drafts"]))
        return {ok:false, reason:"UNKNOWN_FIELDS"};
    if (!integer(doc.nextId, 1, MAX_SEQUENCE))
        return {ok:false, reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.drafts) || doc.drafts.length > MAX_DRAFTS)
        return {ok:false, reason:"INVALID_DRAFT_LIST"};
    var ids = {};
    var highest = 0;
    for (var i = 0; i < doc.drafts.length; i++) {
        var draft = doc.drafts[i];
        if (!validDraft(draft)) return {ok:false, reason:"INVALID_DRAFT"};
        if (Object.prototype.hasOwnProperty.call(ids, draft.id))
            return {ok:false, reason:"DUPLICATE_DRAFT_ID"};
        ids[draft.id] = true;
        highest = Math.max(highest, Number(draft.id.slice(1)));
    }
    if (highest >= doc.nextId) return {ok:false, reason:"SEQUENCE_REWIND"};
    if (JSON.stringify(doc).length > MAX_FILE_LENGTH)
        return {ok:false, reason:"DOCUMENT_TOO_LARGE"};
    return {ok:true, reason:""};
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length > MAX_FILE_LENGTH)
        return {ok:false, reason:"INVALID_SOURCE"};
    var doc;
    try { doc = JSON.parse(raw); }
    catch (e) { return {ok:false, reason:"MALFORMED_JSON"}; }
    var check = validate(doc);
    return check.ok ? {ok:true, document:doc} : check;
}
function saveDraft(doc, id, title, body, now) {
    var check = validate(doc);
    if (!check.ok) return check;
    if (typeof title !== "string" || typeof body !== "string")
        return {ok:false, reason:"INVALID_INPUT"};
    var clean = title.trim();
    if (!cleanTitle(clean) || !cleanBody(body))
        return {ok:false, reason:"INVALID_INPUT"};
    if (!integer(now, 1, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TIME"};
    if (typeof id !== "string") return {ok:false, reason:"INVALID_DRAFT_ID"};
    var next = {version:VERSION, nextId:doc.nextId, drafts:doc.drafts.map(function(d) {
        return {id:d.id, title:d.title, body:d.body,
                createdAtMs:d.createdAtMs, updatedAtMs:d.updatedAtMs};
    })};
    if (id === "") {
        if (next.drafts.length >= MAX_DRAFTS || next.nextId >= MAX_SEQUENCE)
            return {ok:false, reason:"CAPACITY_REACHED"};
        id = "d" + next.nextId++;
        next.drafts.push({id:id, title:clean, body:body, createdAtMs:now, updatedAtMs:now});
    } else {
        var target = next.drafts.filter(function(d) { return d.id === id; })[0];
        if (!target) return {ok:false, reason:"UNKNOWN_DRAFT"};
        if (now < target.updatedAtMs) return {ok:false, reason:"STALE_CLOCK"};
        target.title = clean;
        target.body = body;
        target.updatedAtMs = now;
    }
    var result = validate(next);
    return result.ok ? {ok:true, document:next, draftId:id} : result;
}
function view(state, doc, error) {
    var check = validate(doc);
    return {state:state, error:error || "", writable:(state === "ready" || state === "empty")
            && check.ok, drafts:check.ok ? doc.drafts.map(function(d) {
                return {id:d.id, title:d.title, body:d.body,
                        createdAtMs:d.createdAtMs, updatedAtMs:d.updatedAtMs};
            }) : []};
}
