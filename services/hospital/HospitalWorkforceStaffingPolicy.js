// HOSPITAL // First-worker staffing plan, READ ONLY.
// A Room, Doctor, Provider and ACTIVE Assignment are identities, not execution.
// This module never modifies PX, assigns a Bed, launches an AI or grants authority.
function v(value) {
    return String(value === null || value === undefined ? "" : value).trim();
}
function upper(value) { return v(value).toUpperCase(); }
function rows(value) { return Array.isArray(value) ? value : []; }
function idOf(value) { return v((value || {}).id || (value || {}).roomId); }
function ended(session) {
    const state = upper(session.status);
    const pid = Number(session.activePid || 0);
    return ["COMPLETE", "FAILED", "ENDED"].indexOf(state) >= 0
        && !!v(session.endedAt) && Number.isFinite(pid) && pid === 0;
}
function plan(input) {
    const a = input || {}, blockers = [], notes = [];
    function stop(message) { blockers.push(message); }
    function note(message) { notes.push(message); }

    const roomId = v(a.roomId), doctorId = v(a.doctorId);
    const providerId = v(a.providerId);
    const allRooms = rows(a.rooms), sessions = rows(a.sessions);
    const doctors = rows(a.doctors), providers = rows(a.providers);
    const assignments = rows(a.assignments);
    const roomRows = allRooms.filter(r => idOf(r) === roomId);
    const room = roomRows.length === 1 ? roomRows[0] : {};
    const ownDoctorId = v(room.doctorId), ownProviderId = v(room.providerId);
    const assignmentId = v(room.assignmentId);
    const repository = v(room.repository), patientId = v(room.patientId);
    const branch = v(room.branch), bedPath = v(room.bedPath);

    if (a.roomsLoaded !== true || a.sessionsLoaded !== true)
        stop("Room and Session registry not verified");
    if (a.doctorsLoaded !== true || a.providersLoaded !== true)
        stop("Doctor and Provider directory not verified");
    if (a.assignmentsLoaded !== true || a.assignmentsLoading === true)
        stop("Assignment list not verified for the selected Room");
    if (v(a.sourceError)) stop("PX registry error: " + v(a.sourceError).slice(0,120));
    if (!roomId || roomRows.length !== 1)
        stop("Select one registered Room");
    if (!patientId || !repository)
        stop("Room Patient / repository identity missing");
    if (!branch || !bedPath)
        stop("Room Git branch or working Bed missing; configure and verify its Git worktree");
    if (!assignmentId)
        stop("Room has no ACTIVE Assignment; activate one READ-only job first");

    const matchedAssignments = assignments.filter(r => v(r.id) === assignmentId);
    if (assignments.some(r => v(r.roomId) !== roomId))
        stop("Assignment source contains records from another Room");
    if (!assignmentId || matchedAssignments.length !== 1)
        stop("Linked Assignment has not been verified for this Room");
    const assignment = matchedAssignments.length === 1
        ? matchedAssignments[0] : {};
    if (matchedAssignments.length === 1) {
        if (v(assignment.roomId) !== roomId
                || (v(assignment.patientId) && v(assignment.patientId) !== patientId))
            stop("Linked Assignment has different Room / Patient ownership");
        if (upper(assignment.status) !== "ACTIVE")
            stop("Linked Assignment is not ACTIVE");
        if (!v(assignment.title) || !v(assignment.goal))
            stop("Linked Assignment lacks a title or goal");
        const permissions = rows(assignment.permissions).map(upper);
        if (permissions.length !== 1 || permissions[0] !== "READ")
            stop("First-worker pilot requires an ACTIVE READ-only Assignment");
    }

    const chosenDoctors = doctors.filter(r => v(r.id) === doctorId);
    if (!doctorId || chosenDoctors.length !== 1)
        stop("Select one registered Doctor");
    else if (upper(chosenDoctors[0].status) !== "ACTIVE")
        stop("Selected Doctor is not ACTIVE");

    const chosenProviders = providers.filter(r => v(r.id) === providerId);
    if (!providerId || chosenProviders.length !== 1)
        stop("Select one registered AI Provider");
    else if (chosenProviders[0].available !== true)
        stop("Selected Provider is not available");
    if (providerId === "int1-fake")
        stop("Fake-only Provider is not authorized for this route");

    if (ownDoctorId && doctorId && ownDoctorId !== doctorId)
        stop("Room belongs to another Doctor; use the separate succession path");
    if (ownProviderId && providerId && ownProviderId !== providerId)
        stop("Room uses a different Provider; change requires separate authority");

    if (doctorId && allRooms.some(r => idOf(r) !== roomId
            && v(r.doctorId) === doctorId))
        stop("Doctor already owns another registered Room; release that staffing first");
    if (bedPath && allRooms.some(r => idOf(r) !== roomId
            && v(r.bedPath) === bedPath))
        stop("Git Bed already assigned to another Room");

    // Even a terminal-looking record is not released if it has no end-time
    // or still records a process ID. Never infer that a browser tab died.
    if (sessions.some(s => v(s.roomId) === roomId && !ended(s)))
        stop("Room has a Session not explicitly released");
    if (doctorId && sessions.some(s => v(s.roomId) !== roomId
            && v(s.doctorId) === doctorId && !ended(s)))
        stop("Doctor has an unreleased Session elsewhere");

    const needsStaffing = !!roomId && !!doctorId && !!providerId
        && (!ownDoctorId || !ownProviderId);
    const ready = blockers.length === 0;
    if (needsStaffing)
        note("Doctor/Provider choice is not yet registered as Room ownership");
    if (ready)
        note("Git branch, Bed path, authentication and live process state still require PX-side verification");

    return {
        readyForReview: ready,
        readyForAttachmentReview: ready && !needsStaffing,
        needsStaffingWrite: needsStaffing,
        blockers: blockers,
        notes: notes,
        roomId: roomId, patientId: patientId, repository: repository,
        branch: branch, bedPath: bedPath, assignmentId: assignmentId,
        assignmentTitle: v(assignment.title),
        doctorId: doctorId, doctorName: v((chosenDoctors[0] || {}).name),
        doctorRole: v((chosenDoctors[0] || {}).role),
        providerId: providerId, providerName: v((chosenProviders[0] || {}).name),
        currentDoctorId: ownDoctorId, currentProviderId: ownProviderId,
        authorizationVerified: false, mutationAuthorized: false,
        providerLaunched: false, sessionCreated: false,
        headline: !ready ? "STAFFING HOLD // INSPECT BLOCKERS"
            : needsStaffing ? "STAFFING PREPARED // ATOMIC PX AUTHORITY REQUIRED"
            : "LINKS MATCH // PX ATTACHMENT PREVIEW REQUIRED"
    };
}
