// Hospital // First-job activation in the existing Surgery manager.
// This is a source-based operator review gate, not authenticated PX authority.
// It only permits DRAFT READ-only jobs in an unoccupied Room, and never launches AI.
function textValue(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}
function rows(value) {
    return Array.isArray(value) ? value : [];
}
function upper(value) {
    return textValue(value).toUpperCase();
}
function terminalReleased(session) {
    const status = upper(session.status);
    const pid = Number(session.activePid || 0);
    return ["COMPLETE", "FAILED", "ENDED"].indexOf(status) >= 0
        && !!textValue(session.endedAt)
        && Number.isFinite(pid) && pid === 0;
}
function review(source) {
    const a = source || {};
    const roomId = textValue(a.roomId);
    const selectedId = textValue(a.assignmentId);
    const blocks = [];
    function hold(msg) { blocks.push(msg); }
    if (!a.roomsLoaded || !a.sessionsLoaded)
        hold("Room / Session registry not verified");
    if (!a.assignmentsLoaded || a.assignmentsLoading)
        hold("Assignment list not verified for this Room");
    if (textValue(a.registryError) || textValue(a.assignmentError))
        hold("PX registry or Assignment source reported an error");
    const roomMatches = rows(a.rooms).filter(r =>
        textValue(r.id || r.roomId) === roomId);
    if (!roomId || roomMatches.length !== 1)
        hold("Choose one registered Room");
    const room = roomMatches.length === 1 ? roomMatches[0] : {};
    const linkedId = textValue(room.assignmentId);
    if (linkedId)
        hold("Room already has an active Assignment; use ORDERS to replace it");
    const assignments = rows(a.assignments);
    if (assignments.some(r => textValue(r.roomId) !== roomId))
        hold("Foreign Room Assignment in the loaded list");
    if (assignments.some(r => upper(r.status) === "ACTIVE"))
        hold("Another ACTIVE Assignment is recorded for this Room");
    const matches = assignments.filter(r => textValue(r.id) === selectedId);
    if (!selectedId || matches.length !== 1)
        hold("Choose one saved Assignment");
    const assignment = matches.length === 1 ? matches[0] : {};
    if (upper(assignment.status) !== "DRAFT")
        hold("Only a saved DRAFT Assignment may be activated here");
    if (!textValue(assignment.goal) || !textValue(assignment.title))
        hold("Selected Assignment is missing its title or goal");
    const permissions = rows(assignment.permissions).map(upper);
    if (permissions.length !== 1 || permissions[0] !== "READ")
        hold("First-job activation here requires READ-only permission");
    if (rows(a.sessions).some(s =>
        textValue(s.roomId) === roomId && !terminalReleased(s)))
        hold("Room has a Session not explicitly released; cannot activate here");
    return {
        ready: blocks.length === 0,
        blockers: blocks,
        roomId: roomId,
        assignmentId: selectedId,
        title: textValue(assignment.title),
        goal: textValue(assignment.goal),
        status: upper(assignment.status),
        permissions: permissions,
        authorityVerified: false,
        launchesProvider: false,
        createsSession: false,
        mutationAuthorized: false
    };
}
