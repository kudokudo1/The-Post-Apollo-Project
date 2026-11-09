// HOSPITAL // Replacement Doctor recovery preflight, READ ONLY.
// Registered Doctor/Provider and durable Room evidence are inspection inputs,
// never staff authorization, provider reachability, automatic death detection
// or permission to create/rebind any Session.
function v(x) { return String(x === undefined || x === null ? "" : x).trim(); }
function u(x) { return v(x).toUpperCase(); }
function arr(x) { return Array.isArray(x) ? x : []; }
function id(x) { return v((x || {}).id || (x || {}).sessionId); }
function open(s) {
    if (!s) return false;
    return Number(s.activePid || 0) > 0 ||
        (!v(s.endedAt) && ["ENDED", "COMPLETE", "FAILED"].indexOf(u(s.status)) < 0);
}
function find(rows, wanted) {
    const key = v(wanted);
    return arr(rows).filter(function(row) { return id(row) === key; })[0] || null;
}
function preview(a) {
    const source = a || {};
    const roomId = v(source.roomId);
    const overview = source.overview || {};
    const snapshot = source.snapshot || {};
    const room = snapshot.room || {};
    const sessions = arr(source.sessions);
    const doctorId = v(source.doctorId);
    const providerId = v(source.providerId);
    const doctors = arr(source.doctors);
    const providers = arr(source.providers);
    const blockers = [], actions = [], evidence = [], warnings = [];
    const registeredDoctorId = v(room.doctorId);
    const linkedAssignment = overview.assignment || null;
    const assignmentId = v(room.assignmentId);
    const verified = overview.verified === true
        && v(overview.roomId) === roomId && roomId && v(room.id) === roomId;
    function block(s) { blockers.push(s); }
    function task(s) { actions.push(s); }
    function warn(s) { warnings.push(s); }
    function detail(label, value) { evidence.push({label:label, value:value}); }

    detail("ROOM", roomId || "NOT SELECTED");
    detail("PATIENT", v(room.repository) || "UNKNOWN");
    detail("BRANCH", v(room.branch) || "UNKNOWN");
    detail("BED", v(room.bedPath) || "UNKNOWN");
    detail("ASSIGNMENT", assignmentId || "NONE LINKED");
    detail("CURRENT DOCTOR", registeredDoctorId || "NONE REGISTERED");
    detail("PROPOSED DOCTOR", doctorId || "NOT SELECTED");
    detail("PROPOSED PROVIDER", providerId || "NOT SELECTED");

    if (!verified) block("Cannot verify the pinned persistent Room evidence");
    if (!v(room.patientId) || !v(room.repository) || !v(room.branch) || !v(room.bedPath))
        block("Room Patient, repository, branch or Bed is incomplete");
    if (!linkedAssignment || v(linkedAssignment.id) !== assignmentId
            || v(linkedAssignment.roomId) !== roomId
            || u(linkedAssignment.status) !== "ACTIVE")
        block("A linked ACTIVE Assignment is required; do not create or alter one");
    if (source.sessionsLoaded !== true)
        block("PX Session registry has not been verified");
    if (source.doctorsLoaded !== true || source.providersLoaded !== true)
        block("Doctor and Provider directories must be verified");
    if (v(source.sourceError))
        block("PX directory/source error: " + v(source.sourceError).slice(0,120));
    if (v(source.roomData && source.roomData.roomDoctorId)
            && registeredDoctorId
            && v(source.roomData.roomDoctorId) !== registeredDoctorId)
        block("Room Doctor identity differs between roster and PX briefing");

    const doctor = find(doctors, doctorId);
    if (!doctor) block("Choose an existing registered successor Doctor");
    else if (u(doctor.status) !== "ACTIVE")
        block("Selected Doctor is not ACTIVE");
    if (doctorId && registeredDoctorId && doctorId === registeredDoctorId)
        block("Select a different Doctor to replace the current Room Doctor");
    const provider = find(providers, providerId);
    if (!provider) block("Choose a registered PX Provider");
    else if (provider.available !== true)
        block("Selected PX Provider is not listed as available");
    if (providerId === "int1-fake")
        block("Synthetic-only Provider requires a separate fixture-only assignment");

    const sameRoom = sessions.filter(function(s) {
        return v((s || {}).roomId) === roomId && open(s);
    });
    if (sameRoom.length > 1)
        block("Multiple nonterminal Sessions are registered in this Room");
    else if (sameRoom.length === 1) {
        const s = sameRoom[0];
        if (Number(s.activePid || 0) > 0 || u(s.status) === "OPERATING"
                || u(s.status) === "THINKING")
            block("Current Room Session has active/operating evidence; cannot replace");
        else
            block("Current Room Session still claims this Room; verify release first");
        detail("CURRENT SESSION", id(s) + " // " + u(s.status));
    } else {
        detail("CURRENT SESSION", "NO OPEN SESSION RECORDED");
        warn("No open Session in PX does not prove an external browser chat died");
    }
    const bed = v(room.bedPath);
    if (bed && sessions.some(function(s) {
        if (!open(s) || v(s.roomId) === roomId) return false;
        const otherRoom = find(source.rooms, v(s.roomId));
        return !!otherRoom && v(otherRoom.bedPath) === bed;
    })) block("Another Room has an open PX Session on the same recorded Bed");
    if (doctorId && sessions.some(function(s) {
        return open(s) && v(s.roomId) !== roomId && v(s.doctorId) === doctorId;
    })) block("Selected Doctor has an open Session in another Room; review ownership");

    const checkpoint = overview.checkpoint || null;
    const handoff = overview.handoff || null;
    const decisions = arr(overview.decisions);
    detail("LAST HANDOFF", handoff ? "#" + v(handoff.id) : "NONE");
    detail("LAST CHECKPOINT", checkpoint ? "#" + v(checkpoint.id) : "NONE");
    detail("APPROVED CHART", String(decisions.length) + " visible in Room briefing");
    if (!handoff) {
        if (checkpoint)
            warn("Checkpoint is saved but no explicit HANDOFF report exists");
        else
            block("No checkpoint or HANDOFF report exists for replacement continuity");
    }
    if (source.roomsLoaded !== true)
        block("Room registry not verified; cross-Room Bed occupancy cannot be excluded");

    task("Preserve the existing Room ID, Patient and ACTIVE Assignment");
    task("Review last HANDOFF and approved decisions with successor");
    task("Verify live Git worktree and branch, not just stored Bed labels");
    task("Verify prior Doctor/Session release and staffing ownership");
    task("Obtain operator authority for explicit Doctor/Provider transfer");
    task("Atomically create a fresh Session and PX successor context");
    task("Verify successor STATUS and first authorized report; do not auto-GO");

    return {
        roomId: roomId, assignmentId: assignmentId,
        previousDoctorId: registeredDoctorId,
        successorDoctorId: doctorId, providerId: providerId,
        selectedDoctorName: doctor ? v(doctor.name) : "",
        selectedProviderName: provider ? v(provider.name) : "",
        evidence:evidence, blockers:blockers, warnings:warnings, actions:actions,
        contextAvailable:verified && !!linkedAssignment,
        previewable:verified && blockers.length === 0,
        status:!verified ? "ROOM EVIDENCE UNVERIFIED"
            : blockers.length ? "RECOVERY PREVIEW // NEEDS INTERVENTION"
            : "SUCCESSOR CANDIDATE // AUTHORITATIVE TRANSFER PENDING",
        mutationAuthorized:false,
        operatorApprovalRequired:true,
        source:"PX DURABLE ROOM + REGISTERED DOCTOR/PROVIDER READS",
        disclaimer:"NO ROOM MUTATION // NO NEW SESSION // NO WORKER START // NO BROWSER ATTACHMENT"
    };
}
// Exact PX succession request contract, READ ONLY. This never grants authority.
// A list of Sessions is not ordered by the SQLite insertion rowid used by PX;
// multiple historical Sessions therefore require a newer authoritative check,
// rather than guessing the predecessor from a display order.
function successionContract(a) {
    const source = a || {};
    const plan = source.plan || {};
    const room = (source.snapshot || {}).room || {};
    const sameRoom = arr(source.sessions).filter(function(s) {
        return v((s || {}).roomId) === v(plan.roomId);
    });
    const blockers = [];
    function block(message) { blockers.push(message); }
    if (source.sessionsLoaded !== true)
        block("PX Session registry not verified for the transfer");
    if (plan.previewable !== true || plan.mutationAuthorized !== false)
        block("Recovery preview has blockers or is not safely read-only");
    if (!v(plan.roomId) || v(room.id) !== v(plan.roomId)
            || !v(room.providerId) || !v(room.doctorId)
            || !v(room.assignmentId) || !v(room.repository)
            || !v(room.branch) || !v(room.bedPath))
        block("Pinned Room, previous staffing, Assignment or Git Bed is incomplete");
    if (sameRoom.length === 0)
        block("No recorded predecessor Session; cannot construct a PX succession request");
    else if (sameRoom.length > 1)
        block("Multiple historical Room Sessions; latest insertion order must be verified by PX");
    const previous = sameRoom.length === 1 ? sameRoom[0] : null;
    if (previous) {
        if (!id(previous))
            block("Recorded predecessor has no exact Session ID");
        if (["COMPLETE", "ENDED", "FAILED"].indexOf(u(previous.status)) < 0
                || !v(previous.endedAt) || Number(previous.activePid || 0) !== 0
                || !Number.isFinite(Number(previous.activePid || 0)))
            block("Predecessor Session has not been explicitly released");
        if (v(previous.doctorId) !== v(room.doctorId)
                || v(previous.providerId) !== v(room.providerId))
            block("Predecessor Doctor/Provider differs from pinned Room staffing");
        if (v(previous.workingDirectory) !== v(room.bedPath))
            block("Predecessor Session Bed differs from pinned Room Bed");
    }
    const ready = blockers.length === 0;
    return {
        readyForAuthorityCheck: ready,
        previousSessionId: previous ? id(previous) : "",
        previousDoctorId: v(room.doctorId),
        previousProviderId: v(room.providerId),
        blockers: blockers,
        pinnedRequest: ready ? {
            roomId: v(plan.roomId),
            previousSessionId: id(previous),
            previousDoctorId: v(room.doctorId),
            previousProviderId: v(room.providerId),
            successorDoctorId: v(plan.successorDoctorId),
            successorProviderId: v(plan.providerId),
            assignmentId: v(plan.assignmentId),
            repository: v(room.repository),
            branch: v(room.branch),
            bedPath: v(room.bedPath)
        } : null,
        // A freshly minted new Session ID, caller-authenticated permission,
        // PX command capability and last-moment database check are still absent.
        mutationAuthorized: false,
        status: ready
            ? "PREDECESSOR PINNED // OPERATOR AUTHORITY NOT VERIFIED"
            : "ATOMIC SUCCESSION PRECONDITIONS NOT SATISFIED",
        disclaimer: "NO SUCCESSION SUBMITTED // SESSION RELEASE IS RECORDED, NOT A LIVE BROWSER HEARTBEAT"
    };
}

function briefing(a) {
    const input = a || {};
    const p = preview(input);
    const o = input.overview || {};
    if (!p.contextAvailable)
        return "RECOVERY BRIEFING UNAVAILABLE // VERIFY ROOM AND ASSIGNMENT";
    const assignment = o.assignment || {};
    const handoff = o.handoff || {};
    const checkpoint = o.checkpoint || {};
    const decisions = arr(o.decisions).slice(0, 12);
    const lines = [
        "HOSPITAL // SUCCESSOR REVIEW BRIEFING // NOT AUTHORIZED",
        "ROOM // " + p.roomId,
        "PATIENT // " + v(o.repository),
        "ASSIGNMENT // #" + p.assignmentId + " // " + v(assignment.title),
        "GOAL // " + v(assignment.goal),
        "STATUS // " + v(assignment.status) + " // " + v(assignment.phase),
        "CURRENT DOCTOR // " + (p.previousDoctorId || "NONE"),
        "SUCCESSOR CANDIDATE // " + (p.successorDoctorId || "NOT SELECTED"),
        "PROVIDER CANDIDATE // " + (p.providerId || "NOT SELECTED"),
        "LAST HANDOFF // " + (handoff.id ? "#" + v(handoff.id) : "MISSING"),
        "HANDOFF PREVIEW // " + v(handoff.body).slice(0, 1400),
        "LAST CHECKPOINT // " + (checkpoint.id ? "#" + v(checkpoint.id) : "MISSING"),
        "CHECKPOINT PREVIEW // " + v(checkpoint.body).slice(0, 1200),
        "OPEN QUESTIONS // " + v(assignment.openQuestions).slice(0, 1000),
        "NEXT SAVED INPUT // " + v((o.next || {}).body).slice(0, 500),
        "APPROVED DECISIONS // " + decisions.length + " shown below"
    ];
    for (let i = 0; i < decisions.length; ++i)
        lines.push("DECISION #" + v(decisions[i].id) + " // "
            + v(decisions[i].title) + " // " + v(decisions[i].body).slice(0, 500));
    lines.push("ATTACHMENT BLOCKERS // " + p.blockers.join("; "));
    lines.push("NO PX TRANSFER HAS OCCURRED. FULL CONTEXT MUST BE REBUILT FROM CURRENT PX RECORDS AT EXECUTION.");
    return lines.join("\n");
}
