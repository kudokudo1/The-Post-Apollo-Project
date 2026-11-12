.pragma library

// Clock note-only recovery witness. A draft is NOT another alarm store.
// The real alarm document remains owned by AlarmManagerService; this sidecar
// never permits automatic replay, schedule activation, or conflict overwrite.
var VERSION = 1;
var MAX_BYTES = 4096;
var MAX_NOTE = 256;

function integer(n, lo, hi) {
    return typeof n === "number" && isFinite(n)
        && Math.floor(n) === n && n >= lo && n <= hi;
}
function validNote(n) {
    return typeof n === "string" && n.length <= MAX_NOTE
        && !/[\x00-\x1f\x7f]/.test(n);
}
function witness(row) {
    if (!row || !integer(row.id, 1, Number.MAX_SAFE_INTEGER - 1)
            || !integer(row.hour, 0, 23) || !integer(row.minute, 0, 59)
            || (row.mode !== "once" && row.mode !== "weekly")
            || !Array.isArray(row.weekdays)) return "";
    return JSON.stringify({id: row.id, hour: row.hour, minute: row.minute,
        mode: row.mode, date: row.date, weekdays: row.weekdays,
        armedAtMs: row.armedAtMs || 0});
}
function emptyDocument() { return {version: VERSION, draft: null}; }
function validDraft(d) {
    return d !== null && typeof d === "object" && !Array.isArray(d)
        && Object.keys(d).sort().join("|")
            === "after|before|id|stagedAtMs|witness"
        && integer(d.id, 1, Number.MAX_SAFE_INTEGER - 1)
        && integer(d.stagedAtMs, 1, Number.MAX_SAFE_INTEGER)
        && typeof d.witness === "string"
        && d.witness.length > 0 && d.witness.length < 512
        && validNote(d.before) && validNote(d.after)
        && d.before !== d.after;
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length < 2 || raw.length > MAX_BYTES)
        return {ok: false, reason: "INVALID_DRAFT_FILE"};
    var doc;
    try { doc = JSON.parse(raw); }
    catch (e) { return {ok: false, reason: "INVALID_DRAFT_JSON"}; }
    if (!doc || typeof doc !== "object" || Array.isArray(doc)
            || Object.keys(doc).sort().join("|") !== "draft|version"
            || doc.version !== VERSION
            || (doc.draft !== null && !validDraft(doc.draft)))
        return {ok: false, reason: "INVALID_DRAFT"};
    return {ok: true, document: doc};
}
function create(row, note, nowMs) {
    if (!row || !validNote(note)
            || !integer(nowMs, 1, Number.MAX_SAFE_INTEGER))
        return {ok: false, reason: "INVALID_NOTE"};
    var before = row.note || "";
    var after = note.trim();
    var d = {id: row.id, witness: witness(row),
        before: before, after: after, stagedAtMs: nowMs};
    if (!validDraft(d)) return {ok: false, reason: "INVALID_DRAFT"};
    var doc = {version: VERSION, draft: d};
    if (JSON.stringify(doc).length > MAX_BYTES)
        return {ok: false, reason: "DRAFT_TOO_LARGE"};
    return {ok: true, document: doc};
}
// A saved note may be recognized even if a simultaneous schedule edit also
// changed its witness. RETRY, however, requires an unchanged original row.
function disposition(d, doc) {
    if (!d) return "none";
    if (!validDraft(d) || !doc || !Array.isArray(doc.alarms))
        return "invalid";
    var row = doc.alarms.find(function(a) { return a && a.id === d.id; });
    if (!row) return "missing";
    var current = row.note || "";
    if (current === d.after) return "already-saved";
    if (current !== d.before) return "conflict";
    return witness(row) === d.witness ? "recoverable" : "identity-conflict";
}
