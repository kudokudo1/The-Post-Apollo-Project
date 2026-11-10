.pragma library

// ANGEL note recovery sidecar. This is not a second observation journal:
// it contains only the most recently staged note and its original row witness.
// Never replay a draft automatically. Before retrying, require an exact
// observation identity and unchanged original note to avoid lost updates.
var VERSION = 1;
var MAX_LENGTH = 4096;
var MAX_NOTE_LENGTH = 280;

function integer(value, min, max) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= min && value <= max;
}

function validNote(value) {
    return typeof value === "string" && value.length <= MAX_NOTE_LENGTH
           && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value);
}

function emptyDocument() {
    return {version: VERSION, draft: null};
}

function validDraft(draft) {
    return !!draft && typeof draft === "object" && !Array.isArray(draft)
           && typeof draft.id === "string" && /^a[1-9][0-9]*$/.test(draft.id)
           && typeof draft.digits === "string"
           && /^[0-9]{1,8}$/.test(draft.digits)
           && integer(draft.observedAtMs, 1, Number.MAX_SAFE_INTEGER)
           && integer(draft.stagedAtMs, 1, Number.MAX_SAFE_INTEGER)
           && validNote(draft.before)
           && validNote(draft.after);
}

function parse(raw) {
    if (typeof raw !== "string" || raw.length < 2 || raw.length > MAX_LENGTH)
        return {ok: false, reason: "INVALID_DRAFT_FILE"};
    var document;
    try { document = JSON.parse(raw); }
    catch (error) { return {ok: false, reason: "INVALID_DRAFT_JSON"}; }
    if (!document || typeof document !== "object" || Array.isArray(document)
            || document.version !== VERSION)
        return {ok: false, reason: "UNSUPPORTED_DRAFT"};
    if (document.draft !== null && !validDraft(document.draft))
        return {ok: false, reason: "INVALID_DRAFT"};
    return {ok: true, document: document};
}

function create(row, text, stagedAtMs) {
    if (!row || typeof row !== "object" || !validNote(text)
            || !integer(stagedAtMs, 1, Number.MAX_SAFE_INTEGER))
        return {ok: false, reason: "INVALID_NOTE_DRAFT"};
    var draft = {
        id: row.id,
        digits: row.digits,
        observedAtMs: row.observedAtMs,
        before: row.note || "",
        after: text.trim(),
        stagedAtMs: stagedAtMs
    };
    if (!validDraft(draft))
        return {ok: false, reason: "INVALID_NOTE_DRAFT"};
    var document = {version: VERSION, draft: draft};
    if (JSON.stringify(document).length > MAX_LENGTH)
        return {ok: false, reason: "DRAFT_TOO_LARGE"};
    return {ok: true, document: document};
}

// The result is read-only. 'recoverable' is permission to OFFER a retry,
// not permission to automatically overwrite anything.
function disposition(draft, observations) {
    if (!draft)
        return "none";
    if (!validDraft(draft) || !Array.isArray(observations))
        return "invalid";
    var row = observations.find(function(candidate) {
        return candidate && candidate.id === draft.id;
    });
    if (!row)
        return "missing";
    if (row.digits !== draft.digits
            || row.observedAtMs !== draft.observedAtMs)
        return "identity-conflict";
    var current = row.note || "";
    if (current === draft.after)
        return "already-saved";
    return current === draft.before ? "recoverable" : "conflict";
}
