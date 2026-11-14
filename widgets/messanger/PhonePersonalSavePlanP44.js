// P44 PHONE Personal in-memory save-intent planner. Not a save API.
// Each Favorite or Note change needs a separate one-use C5 approval and
// a fresh revision. A draft with both changes must NEVER be one broad grant.
var SCHEMA = "post-apollo.phone.personal-editor-intent.p43.v1";
var PLAN_SCHEMA = "post-apollo.phone.personal-save-plan.p44.v1";
var SELECTOR = /^[A-Za-z0-9:_-]{1,256}$/;

function planDraft(pending, selectedContactId) {
    var refused = { schema: PLAN_SCHEMA, status: "REFUSED", operations: [] };
    if (pending === null || typeof pending !== "object"
            || Array.isArray(pending) || typeof selectedContactId !== "string"
            || !SELECTOR.test(selectedContactId)
            || Object.keys(pending).sort().join(",")
               !== "changed,contactId,favorite,note"
            || pending.contactId !== selectedContactId
            || pending.changed !== true
            || !(pending.favorite === null || typeof pending.favorite === "boolean")
            || !(pending.note === null || typeof pending.note === "string"))
        return refused;
    if (pending.note !== null) {
        if (pending.note.length > 4096 || pending.note.indexOf("\u0000") >= 0)
            return refused;
        try {
            encodeURIComponent(pending.note); // refuses unpaired surrogates
        } catch (error) {
            return refused;
        }
    }
    var operations = [];
    if (pending.favorite !== null) {
        operations.push({
            schema: SCHEMA, action: "FAVORITE",
            selectedContactId: selectedContactId,
            favorite: pending.favorite
        });
    }
    if (pending.note !== null) {
        operations.push({
            schema: SCHEMA, action: "NOTE",
            selectedContactId: selectedContactId,
            note: pending.note
        });
    }
    if (operations.length === 0)
        return refused;
    // This plan is UNTRUSTED. It contains private draft text in memory;
    // never log, persist, hand to QML-readable saved state or auto-submit.
    return { schema: PLAN_SCHEMA, status: "UNTRUSTED_REVIEW_ONLY",
             operations: operations };
}
