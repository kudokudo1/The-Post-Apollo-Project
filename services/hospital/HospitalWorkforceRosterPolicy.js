// HOSPITAL // Registered workforce projection.
// Read-only. A Git branch is not a Doctor, and a PX session is not a
// ChatGPT browser conversation. Never invent attachment or heartbeat state.
function textValue(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function liveSession(session) {
    const status = textValue((session || {}).status).toUpperCase();
    return !session.endedAt
        && status !== "COMPLETE"
        && status !== "FAILED"
        && status !== "ENDED";
}

function latestSession(roomId, sessions) {
    const matches = (Array.isArray(sessions) ? sessions : []).filter(function(row) {
        return textValue((row || {}).roomId) === roomId;
    });
    matches.sort(function(a, b) {
        const aLive = liveSession(a) ? 1 : 0;
        const bLive = liveSession(b) ? 1 : 0;
        if (aLive !== bLive)
            return bLive - aLive;
        const aTime = textValue(a.updatedAt || a.startedAt).replace(" ", "T");
        const bTime = textValue(b.updatedAt || b.startedAt).replace(" ", "T");
        return bTime.localeCompare(aTime);
    });
    return matches.length > 0 ? matches[0] : null;
}

function doctorName(doctorId, doctors) {
    const id = textValue(doctorId);
    if (!id)
        return "UNASSIGNED";
    const rows = Array.isArray(doctors) ? doctors : [];
    for (let i = 0; i < rows.length; ++i) {
        if (textValue((rows[i] || {}).id) === id)
            return textValue(rows[i].name) || id;
    }
    return id;
}

function buildRoster(rooms, sessions, doctors) {
    const source = Array.isArray(rooms) ? rooms : [];
    const seen = {};
    const out = [];
    for (let i = 0; i < source.length; ++i) {
        const room = source[i] || {};
        const id = textValue(room.id || room.roomId);
        if (!id || seen[id])
            continue;
        seen[id] = true;

        const session = latestSession(id, sessions);
        const doctorId = textValue(
            (session && session.doctorId) || room.doctorId
        );
        const activeSession = session && liveSession(session);
        const rawStatus = session
            ? textValue(session.status).toUpperCase() || "UNKNOWN"
            : "NO SESSION";
        const roomName = textValue(
            room.displayName || room.team || room.id || room.roomId
        );
        out.push({
            roomId: id,
            name: roomName || id,
            nameIsFallback: !textValue(room.displayName),
            team: textValue(room.team),
            repository: textValue(room.repository),
            patientId: textValue(room.patientId),
            patientLabel: textValue(room.patientLabel),
            branch: textValue(room.branch),
            doctorId: doctorId,
            doctorName: doctorName(doctorId, doctors),
            // Preserve both ends. A matching fallback label is not proof
            // that Room staffing and the selected Session agree.
            roomDoctorId: textValue(room.doctorId),
            sessionDoctorId: session ? textValue(session.doctorId) : "",
            roomProviderId: textValue(room.providerId),
            sessionProviderId: session ? textValue(session.providerId) : "",
            providerId: textValue(
                (session && session.providerId) || room.providerId
            ),
            providerSessionId: session ? textValue(session.providerSessionId) : "",
            sessionWorkingDirectory: session ? textValue(session.workingDirectory) : "",
            bedPath: textValue(room.bedPath),
            sessionActivePid: session ? Number(session.activePid || 0) : 0,
            assignmentId: textValue(room.assignmentId),
            assignmentTitle: textValue(room.assignmentTitle),
            assignmentStatus: textValue(room.assignmentStatus).toUpperCase(),
            sessionId: session ? textValue(session.id || session.sessionId) : "",
            sessionStatus: rawStatus,
            hasActiveSession: !!activeSession,
            statusRecordedAt: session ? textValue(session.updatedAt) : "",
            sessionLastError: session ? textValue(session.lastError) : "",
            sessionLastExitCode: session && session.lastExitCode !== undefined
                ? session.lastExitCode : null,
            sessionEndedAt: session ? textValue(session.endedAt) : ""
        });
    }
    out.sort(function(a, b) {
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
            || a.roomId.localeCompare(b.roomId);
    });
    return out;
}
