// HOSPITAL // Guided worker attachment candidate, PREVIEW ONLY.
// This policy has no write functions or provider execution. Only durable PX
// records and explicit operator-selected IDs may contribute to a candidate.
function textValue(v) {
    return String(v === undefined || v === null ? "" : v).trim();
}
function status(v) { return textValue(v).toUpperCase(); }
function terminal(v) {
    const x = status(v);
    return x === "COMPLETE" || x === "ENDED" || x === "FAILED";
}
function idOf(row) { return textValue((row || {}).id || (row || {}).sessionId); }
function findById(rows, wanted) {
    const id = textValue(wanted);
    if (!id || !Array.isArray(rows)) return null;
    for (let i = 0; i < rows.length; ++i)
        if (idOf(rows[i]) === id) return rows[i];
    return null;
}
function openSession(s) {
    return !!s && !textValue(s.endedAt) && !terminal(s.status);
}
function plan(input) {
    const a = input || {};
    const room = a.room || {};
    const id = textValue(room.roomId);
    const patient = textValue(room.patientId);
    const repo = textValue(room.repository);
    const branch = textValue(room.branch);
    const bed = textValue(room.bedPath);
    const assignmentId = textValue(a.assignmentId);
    const doctorId = textValue(a.doctorId);
    const providerId = textValue(a.providerId);
    const assignments = Array.isArray(a.assignments) ? a.assignments : [];
    const doctors = Array.isArray(a.doctors) ? a.doctors : [];
    const providers = Array.isArray(a.providers) ? a.providers : [];
    const sessions = Array.isArray(a.sessions) ? a.sessions : [];
    const rooms = Array.isArray(a.rooms) ? a.rooms : [];
    const errors = [];
    const notices = [];
    const facts = [];

    function stop(x) { errors.push(x); }
    function note(x) { notices.push(x); }
    function fact(k,v) { facts.push({label:k, value:v}); }

    fact("ROOM", id || "MISSING");
    fact("PATIENT", repo || "MISSING");
    fact("BRANCH", branch || "MISSING");
    fact("BED", bed || "MISSING");
    fact("ASSIGNMENT", assignmentId || "NOT SELECTED");
    fact("DOCTOR", doctorId || "NOT SELECTED");
    fact("PROVIDER", providerId || "NOT SELECTED");

    if (!id) stop("No registered Room ID");
    if (!repo || !patient) stop("Room Patient identity is incomplete");
    if (!branch) stop("Room Git branch is missing");
    if (!bed) stop("Room has no registered Bed");
    if (!a.roomsLoaded || !a.sessionsLoaded)
        stop("PX Rooms/Sessions snapshot is not complete");
    if (!a.assignmentsLoaded)
        stop("Assignment list has not been verified for this Room");
    if (!a.doctorsLoaded || !a.providersLoaded)
        stop("Doctor/Provider directory not yet loaded");
    if (textValue(a.loadError))
        stop("PX read failed: " + textValue(a.loadError).slice(0,130));

    // A selection must be a record owned by the current Room, never just
    // a title or an ID supplied by a different Room.
    const assignment = findById(assignments, assignmentId);
    if (!assignment) stop("Select an existing Assignment from this Room");
    else {
        if (textValue(assignment.roomId) !== id)
            stop("Selected Assignment belongs to another Room");
        if (textValue(assignment.patientId) &&
                textValue(assignment.patientId) !== patient)
            stop("Assignment Patient differs from Room Patient");
        if (status(assignment.status) !== "ACTIVE")
            stop("Selected Assignment is not ACTIVE; no auto-activation");
        if (textValue(room.assignmentId) !== assignmentId)
            stop("Room currently links another Assignment; review ownership");
        if (!textValue(assignment.goal) || !textValue(assignment.title))
            note("Assignment title or goal incomplete; review contract");
    }
    const doctor = findById(doctors, doctorId);
    if (!doctor) stop("Choose an existing Doctor from the Hospital directory");
    else if (status(doctor.status) !== "ACTIVE")
        stop("Chosen Doctor is not ACTIVE");
    if (doctor && textValue(room.roomDoctorId) &&
            textValue(room.roomDoctorId) !== doctorId)
        stop("Doctor change requires separate staffing approval");
    const provider = findById(providers, providerId);
    if (!provider) stop("Choose an existing registered PX Provider");
    else if (provider.available !== true)
        stop("Selected Provider is not reported available");
    if (providerId === "int1-fake")
        stop("Fake-only provider requires separate synthetic authorization");
    if (provider && textValue(room.roomProviderId) &&
            textValue(room.roomProviderId) !== providerId)
        stop("Provider change requires separate staffing approval");

    const forRoom = sessions.filter(function(s) {
        return textValue((s || {}).roomId) === id;
    });
    const active = forRoom.filter(openSession);
    let mode = "NEW_SESSION_REVIEW";
    let sessionId = "";
    if (active.length > 1) {
        mode = "COLLISION";
        stop("Multiple nonterminal Sessions are registered for this Room");
    } else if (active.length === 1) {
        mode = "REUSE_SESSION_REVIEW";
        sessionId = idOf(active[0]);
        const s = active[0];
        if (!sessionId) stop("Existing Session has no stable ID");
        if (textValue(s.doctorId) !== doctorId)
            stop("Existing Session Doctor differs from selected Doctor");
        if (textValue(s.providerId) !== providerId)
            stop("Existing Session Provider differs from selected Provider");
        if (textValue(s.workingDirectory) !== bed)
            stop("Existing Session working directory differs from Room Bed");
        if (status(s.status) !== "IDLE")
            stop("Existing Session is not IDLE; do not overwrite its state");
        if (Number(s.activePid || 0) > 0)
            stop("Existing Session has a recorded active process");
        note("Reuse is only a proposed path; PX must verify live runtime state");
    } else {
        note("No open Session for this Room; new attachment would need authorization");
    }

    // A Bed used by another currently attached Room is an ownership conflict.
    for (let i = 0; i < rooms.length; ++i) {
        const other = rooms[i] || {};
        const otherId = textValue(other.id || other.roomId);
        if (!otherId || otherId === id ||
                textValue(other.bedPath) !== bed || !bed) continue;
        if (sessions.some(function(s) {
            return textValue((s || {}).roomId) === otherId && openSession(s);
        })) {
            stop("Another Room has an open Session on the same recorded Bed");
            break;
        }
    }
    if (mode === "NEW_SESSION_REVIEW" && textValue(room.sessionId))
        note("Roster has a historical Session; review recovery before replacement");
    fact("SESSION PATH", mode === "REUSE_SESSION_REVIEW"
        ? "REUSE " + sessionId
        : mode === "COLLISION" ? "COLLISION" : "NEW / REVIEW ONLY");

    return {
        roomId: id,
        assignmentId: assignmentId,
        doctorId: doctorId,
        providerId: providerId,
        bedPath: bed,
        sessionId: sessionId,
        sessionMode: mode,
        facts: facts,
        blockers: errors,
        notes: notices,
        reviewable: errors.length === 0,
        headline: errors.length ? "BLOCKED // REVIEW LINKS"
            : "PREVIEW CONSISTENT // NOT ATTACHED",
        mutationAuthorized: false,
        source: "READ-ONLY PX REGISTRY PREVIEW"
    };
}
