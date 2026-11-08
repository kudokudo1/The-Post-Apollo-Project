// HOSPITAL // Durable Room continuity projection. READ ONLY.
// Nothing here predicts a dead browser chat, grants authority, estimates
// work from elapsed time, or manufactures missing checkpoints.
function str(v) { return String(v === undefined || v === null ? "" : v).trim(); }
function upper(v) { return str(v).toUpperCase(); }
function rows(v) { return Array.isArray(v) ? v : []; }
function latest(v) { const a = rows(v); return a.length ? a[a.length - 1] : null; }
function excerpt(v, limit) {
    const s = str(v);
    const max = Math.max(60, Number(limit) || 600);
    return s.length > max ? s.slice(0, max) + " … [PREVIEW TRUNCATED]" : s;
}
function checklist(markdown) {
    const lines = str(markdown).split(/\r?\n/);
    const items = [];
    for (let i = 0; i < lines.length; ++i) {
        const m = lines[i].match(/^\s*(?:(?:[-*+]|\d+[.)])\s*)?\[([ xX])\]\s+(.+)$/);
        if (m) items.push({done: upper(m[1]) === "X", label: str(m[2])});
    }
    const done = items.filter(function(v) {return v.done;}).length;
    return {
        items: items,
        done: done,
        total: items.length,
        percent: items.length ? Math.round(100 * done / items.length) : null,
        evidence: items.length ? "COUNTED CHECKBOXES // NOT VERIFIED COMPLETION"
            : "NO PARSEABLE CHECKLIST // NO PROGRESS MEASUREMENT"
    };
}
function openSession(s) {
    if (!s) return false;
    const state = upper(s.status);
    return Number(s.activePid || 0) > 0
        || (!str(s.endedAt) && ["COMPLETE", "ENDED", "FAILED"].indexOf(state) === -1);
}
function recovery(roomId, sessions, sessionsLoaded) {
    if (!sessionsLoaded)
        return {label:"SESSION DATA UNVERIFIED", severity:2,
            detail:"Refresh the PX registry; no replacement decision is justified.", action:"VERIFY SESSION REGISTRY"};
    const roomSessions = rows(sessions).filter(function(s) {
        return str((s || {}).roomId) === roomId;
    });
    const current = roomSessions.filter(openSession);
    if (current.length > 1)
        return {label:"SESSION OWNERSHIP COLLISION", severity:3,
            detail:"Multiple nonterminal Sessions are recorded for one Room. Reconcile ownership before any command.",
            action:"REVIEW SESSION COLLISION"};
    if (!current.length) {
        const prior = roomSessions.length ? roomSessions[0] : null;
        const failed = prior && (upper(prior.status) === "FAILED" || str(prior.lastError));
        return {label:failed ? "LAST SESSION FAILED // RECOVERY REVIEW"
                           : "NO ACTIVE SESSION // ROOM PERSISTS",
            severity:failed ? 3 : 1,
            detail:failed ? "Work records remain in the Room. Inspect the failure before attaching another Doctor."
                          : "Durable Room data can be read without a running Doctor. Replacement is not automatic.",
            action:"REVIEW HANDOFF AND ATTACHMENT"};
    }
    const active = current[0], state = upper(active.status);
    if (Number(active.activePid || 0) > 0 || state === "OPERATING" || state === "THINKING")
        return {label:"OPERATING RECORDED // LIVE UNVERIFIED", severity:1,
            detail:"PX has operating evidence; this is not a heartbeat. Do not start a competing Session.",
            action:"CHECK EXACT SESSION STATUS"};
    if (state === "PAUSED" || state === "REVIEW")
        return {label:state + " // MANUAL REVIEW", severity:2,
            detail:"Deliberate hold preserved. Continuation needs the appropriate authorized release.",
            action:"REVIEW HOLD AND OWNER"};
    if (state === "WAITING") {
        const ok = str(active.lastExitCode) === "0" && !str(active.lastError);
        return {label:ok ? "PRIOR TURN COMPLETE // WAITING" : "WAITING // OUTCOME UNVERIFIED",
            severity:ok ? 0 : 2,
            detail:ok ? "Previous PX exit succeeded. Operator may request a new turn after fresh permission checks."
                      : "Inspect the last error/exit before continuation.",
            action:ok ? "REVIEW NEXT ASSIGNMENT ACTION" : "INSPECT PX STATUS"};
    }
    return {label:state === "IDLE" ? "SESSION REGISTERED // LIVE UNVERIFIED"
                                  : "SESSION STATE UNVERIFIED // " + state,
        severity:state === "IDLE" ? 0 : 2,
        detail:"A saved Session record does not prove its Provider is reachable.",
        action:"CHECK EXACT SESSION STATUS"};
}
function project(args) {
    const a = args || {}, expected = str(a.roomId);
    const snap = a.snapshot || {};
    const room = snap.room || {};
    if (!a.loaded || !expected || str(room.id) !== expected)
        return {verified:false, label:"ROOM SNAPSHOT NOT VERIFIED",
            roomId:expected, recovery:recovery(expected,a.sessions,a.sessionsLoaded),
            progress:checklist(""), decisions:[], next:{source:"NONE",body:"No verified Room snapshot."}};
    const assignmentId = str(room.assignmentId);
    const assignment = rows(snap.assignments).filter(function(v) {
        return str((v || {}).roomId) === expected && str(v.id) === assignmentId;
    })[0] || null;
    const reports = rows(snap.reports);
    const handoff = latest(reports.filter(function(v) {
        return upper((v || {}).kind) === "HANDOFF";
    }));
    const checkpoint = latest(snap.checkpoints);
    const report = latest(reports);
    const decisions = rows(snap.roomChart).concat(rows(snap.patientChart))
        .filter(function(v) {
            return upper((v || {}).status) === "ACTIVE"
                && str(v.authorRole).toLowerCase() === "operator";
        })
        .slice(0, 12);
    const progress = checklist(assignment ? assignment.checklist : "");
    let next = {source:"NO RECORDED NEXT ACTION",
                body:"Review the current Assignment or request a HANDOFF report."};
    if (assignment && str(assignment.openQuestions))
        next = {source:"ASSIGNMENT // OPEN QUESTIONS",body:str(assignment.openQuestions)};
    else if (progress.items.some(function(v) {return !v.done;}))
        next = {source:"ASSIGNMENT // FIRST UNCHECKED ITEM",
            body:progress.items.filter(function(v) {return !v.done;})[0].label};
    else if (handoff)
        next = {source:"LATEST HANDOFF // READ BEFORE ACTING",body:str(handoff.body)};
    return {
        verified:true, roomId:expected, repository:str(room.repository),
        patientId:str(room.patientId), branch:str(room.branch),
        assignment:assignment,
        assignmentLinked:!!assignment,
        checkpoint:checkpoint, handoff:handoff, report:report,
        progress:progress, decisions:decisions, next:next,
        recovery:recovery(expected,a.sessions,a.sessionsLoaded),
        counts:{reports:reports.length,checkpoints:rows(snap.checkpoints).length,
            activeRoomChart:rows(snap.roomChart).length,
            activePatientChart:rows(snap.patientChart).length},
        source:"PX DURABLE ROOM / ASSIGNMENT / CHECKPOINT / REPORT / CHART",
        claim:"RECORDS ONLY // NO PROVIDER HEARTBEAT OR AUTOMATIC RECOVERY"
    };
}
