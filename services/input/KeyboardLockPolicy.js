.pragma library

// One explicit startup preference per lock. "system" deliberately means
// no Post-Apollo override, NOT "remember the last physical keypress".
var VERSION = 1;
var MODES = ["system", "on", "off"];

function validMode(mode) {
    return typeof mode === "string" && MODES.indexOf(mode) !== -1;
}
function initialDocument() {
    return {version: VERSION, num: "system", caps: "system"};
}
function validDocument(document) {
    return !!document && typeof document === "object"
           && !Array.isArray(document)
           && document.version === VERSION
           && validMode(document.num) && validMode(document.caps);
}
function parse(raw) {
    var object;
    try { object = JSON.parse(String(raw)); }
    catch (_) { return {ok: false, reason: "INVALID_JSON"}; }
    if (!validDocument(object))
        return {ok: false, reason: "INVALID_DOCUMENT"};
    return {ok: true, document: {
        version: VERSION, num: object.num, caps: object.caps
    }};
}
function withMode(document, lockName, mode) {
    if (!validDocument(document) ||
            (lockName !== "num" && lockName !== "caps") || !validMode(mode))
        return {ok: false, reason: "INVALID_CHOICE"};
    return {ok: true, document: {
        version: VERSION,
        num: lockName === "num" ? mode : document.num,
        caps: lockName === "caps" ? mode : document.caps
    }};
}
