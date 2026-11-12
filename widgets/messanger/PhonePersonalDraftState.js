// P42: pure, ephemeral PHONE Personal editor draft state. NO persistence.
// The BlueFerry row ID is only an in-memory selection guard, never a vault key.
function empty() {
    return { contactId: "", favorite: null, note: null, changed: false };
}

function validContactId(value) {
    return typeof value === "string" && value.length > 0 && value.length <= 256;
}

function start(contactId) {
    if (!validContactId(contactId))
        return empty();
    return { contactId: contactId, favorite: null, note: null, changed: false };
}

function sameSelection(state, contactId) {
    return state !== null && typeof state === "object"
        && validContactId(contactId) && state.contactId === contactId
        && (state.favorite === null || typeof state.favorite === "boolean")
        && (state.note === null || typeof state.note === "string");
}

function withFavorite(state, contactId, requested) {
    if (!sameSelection(state, contactId) || typeof requested !== "boolean")
        return empty();
    return {
        contactId: contactId,
        favorite: requested,
        note: state.note,
        changed: true
    };
}

function withNote(state, contactId, requested) {
    // Empty string intentionally means "clear note" in a DRAFT, NOT delete.
    if (!sameSelection(state, contactId) || typeof requested !== "string"
            || requested.length > 4096 || requested.indexOf("\u0000") >= 0)
        return empty();
    return {
        contactId: contactId,
        favorite: state.favorite,
        note: requested,
        changed: true
    };
}

function summary(state, contactId) {
    if (!sameSelection(state, contactId))
        return "NO ACTIVE DRAFT";
    if (state.changed !== true)
        return "NO CHANGE PROPOSED";
    var parts = [];
    if (state.favorite !== null)
        parts.push(state.favorite ? "FAVORITE ON (DRAFT)" : "FAVORITE OFF (DRAFT)");
    if (state.note !== null)
        parts.push("NOTE CHANGE (DRAFT)");
    return parts.join(" // ") + " // NOT SAVED";
}

// Deliberately no write/commit/save/submit method, no storage or IPC.
