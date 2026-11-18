// HOSPITAL // Trash++ source-owned Room review (deny-only).
// A PX Room is a relational SQLite record, not a file or managed copy.
// Never infer safe Trash/Burn from a missing Session or a friendly label.
function str(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}
function inspect(inputValue) {
    const input = inputValue || {};
    const room = input.room || {};
    const roomId = str(input.pinnedRoomId);
    const recordedId = str(room.roomId);
    const rooms = Array.isArray(input.allRooms) ? input.allRooms : [];
    const sessions = Array.isArray(input.allSessions) ? input.allSessions : [];
    const sameRoom = !!roomId && roomId === recordedId;
    const registryMatch = input.roomsLoaded === true
        && rooms.some(function(r) {
            return str((r || {}).id || (r || {}).roomId) === roomId;
        });
    const sessionCount = input.sessionsLoaded === true
        ? sessions.filter(function(s) {
            return str((s || {}).roomId) === roomId;
        }).length : -1;
    const assignmentId = str(room.assignmentId);
    const assignmentStatus = str(room.assignmentStatus).toUpperCase();
    const blockers = [
        "HOSPITAL_SOURCE_OWNER_ADAPTER_UNAVAILABLE",
        "AUTHENTICATED_ROOM_REVISION_UNAVAILABLE",
        "RELATED_RECORD_DEPENDENCIES_UNVERIFIED",
        "RETENTION_AND_RECOVERY_UNVERIFIED",
        "BURN_AUTHORITY_AND_RECEIPT_UNAVAILABLE"
    ];
    if (!sameRoom)
        blockers.push("EXACT_ROOM_ID_MISMATCH");
    if (input.roomsLoaded !== true || !registryMatch)
        blockers.push("DURABLE_ROOM_REGISTRY_UNVERIFIED");
    if (input.sessionsLoaded !== true)
        blockers.push("SESSION_SNAPSHOT_UNVERIFIED");
    if (sessionCount > 0)
        blockers.push("LINKED_SESSION_HISTORY_PRESERVE");
    if (assignmentId)
        blockers.push("ASSIGNMENT_REFERENCE_REVIEW_REQUIRED");
    if (assignmentId && assignmentStatus === "ACTIVE")
        blockers.push("ACTIVE_ASSIGNMENT_HOLD");
    return {
        state: "DENY_ONLY_OWNER_REVIEW",
        source: "PX SQLITE ROOM RECORD",
        roomId: roomId,
        roomMatched: sameRoom,
        sessionCount: sessionCount,
        sessionSummary: sessionCount < 0
            ? "UNVERIFIED" : String(sessionCount) + " REGISTERED",
        assignmentSummary: assignmentId
            ? "#" + assignmentId + " // " + (assignmentStatus || "STATUS UNKNOWN")
            : "NONE LINKED (OTHERS NOT EXCLUDED)",
        blockers: blockers,
        trashAllowed: false,
        restoreAllowed: false,
        burnAllowed: false,
        enqueueAllowed: false,
        sourceMutationAllowed: false
    };
}
