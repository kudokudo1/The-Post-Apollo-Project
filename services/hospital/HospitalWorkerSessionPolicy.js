// Verified registered Room and PX Session identity gates.
// These helpers do not infer that a ChatGPT browser tab is connected.
function clean(value) {
    return String(value === null || value === undefined ? "" : value).trim();
}

function roomMatches(roomData, roomId) {
    return !!clean(roomId) &&
        clean((roomData || {}).roomId) === clean(roomId);
}

function sessionMatches(roomData, roomId, sessionId) {
    const room = roomData || {};
    return roomMatches(room, roomId) &&
        !!clean(sessionId) &&
        clean(room.sessionId) === clean(sessionId) &&
        room.hasActiveSession === true;
}

function statusMatches(payload, sessionId) {
    const result = payload || {};
    const session = result.session || {};
    return !!clean(sessionId) &&
        clean(session.id || session.sessionId) === clean(sessionId);
}

function canIssueQuick(args) {
    const state = args || {};
    const command = clean(state.command).toUpperCase();
    const allow = [
        "GO", "CONTINUE", "STATUS", "REPORT",
        "CHECKLIST", "NEXT", "SUGGEST", "PAUSE"
    ];
    if (allow.indexOf(command) < 0 ||
            !state.active || !state.sessionMatches ||
            !state.runtimeStatusVerified ||
            !state.runtimeSessionMatches ||
            state.hasError || state.busy) {
        return false;
    }
    return !state.operating || command === "STATUS" || command === "PAUSE";
}
