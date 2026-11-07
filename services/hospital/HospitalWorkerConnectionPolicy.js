// HOSPITAL // Registered Room-to-worker connection audit.
// This is evidence from durable PX records, not a provider heartbeat or
// browser ChatGPT attachment. Do not infer authorization from these labels.
function valueOf(input) {
    return String(input === undefined || input === null ? "" : input).trim();
}

function terminal(statusValue) {
    const status = valueOf(statusValue).toUpperCase();
    return status === "COMPLETE" || status === "ENDED" || status === "FAILED";
}

function inspect(roomValue) {
    const room = roomValue || {};
    const roomId = valueOf(room.roomId);
    const sessionId = valueOf(room.sessionId);
    const status = valueOf(room.sessionStatus).toUpperCase();
    const roomDoctor = valueOf(room.roomDoctorId);
    const doctor = valueOf(room.sessionDoctorId);
    const roomProvider = valueOf(room.roomProviderId);
    const provider = valueOf(room.sessionProviderId);
    const assignmentId = valueOf(room.assignmentId);
    const assignmentStatus = valueOf(room.assignmentStatus).toUpperCase();
    const roomBed = valueOf(room.bedPath);
    const sessionBed = valueOf(room.sessionWorkingDirectory);
    const ended = !!valueOf(room.sessionEndedAt);
    const validSession = !!sessionId && !ended && !terminal(status)
        && room.hasActiveSession === true;

    const checks = [];
    function add(label, ok, detail) {
        checks.push({label: label, ok: !!ok, detail: detail});
    }

    add("ROOM", !!roomId && !!valueOf(room.repository),
        valueOf(room.repository) || "Patient/repository not registered");
    add("DOCTOR", !!doctor && !!roomDoctor && doctor === roomDoctor,
        !roomDoctor ? "No Doctor bound to Room"
        : !doctor ? "Session has no Doctor"
        : doctor !== roomDoctor
          ? "Room Doctor and Session Doctor differ"
          : doctor);
    add("PROVIDER", !!provider && (!roomProvider || roomProvider === provider),
        !provider ? "PX Session has no Provider"
        : roomProvider && roomProvider !== provider
          ? "Room Provider and Session Provider differ"
          : provider + " // provider availability not probed");
    add("ASSIGNMENT", !!assignmentId &&
        (assignmentStatus === "ACTIVE" || !assignmentStatus),
        !assignmentId ? "No current Assignment linked to Room"
        : assignmentStatus === "ACTIVE"
          ? "ACTIVE // " + (valueOf(room.assignmentTitle) || assignmentId)
          : !assignmentStatus
            ? "Assignment " + assignmentId + " // status not exposed by PX"
            : assignmentStatus + " // not ACTIVE");
    add("BED", !!roomBed && !!sessionBed && roomBed === sessionBed,
        !roomBed ? "Room has no registered Bed"
        : !sessionBed ? "Session has no working directory"
        : roomBed !== sessionBed ? "Bed paths differ; PX must resolve them"
        : "Room Bed and Session directory agree as stored");
    add("SESSION", validSession,
        !sessionId ? "No registered PX Session"
        : ended || terminal(status)
          ? "Session ended or failed: " + (status || "ENDED")
          : status + " // persisted record, not a heartbeat");

    let code = "REGISTERED";
    let label = "ROUTE REQUIRES PROBE";
    let next = "Check exact PX Session status before requesting work.";
    if (!roomId) {
        code = "NO_ROOM"; label = "NO ROOM";
        next = "Register a durable Room identity first.";
    } else if (!sessionId) {
        code = "NO_SESSION"; label = "NO SESSION";
        next = "Attach an approved PX Session to this Room; browser tabs are external.";
    } else if (!validSession) {
        code = "ENDED_SESSION"; label = "SESSION NOT ACTIVE";
        next = "Review the finished/failed Session and approved recovery path.";
    } else if (!roomDoctor || !doctor) {
        code = "NO_DOCTOR"; label = "DOCTOR NOT LINKED";
        next = "Reconcile the Room Doctor and PX Session Doctor identities.";
    } else if (doctor !== roomDoctor) {
        code = "DOCTOR_MISMATCH"; label = "DOCTOR MISMATCH";
        next = "Review staffing/worker replacement; do not overwrite either ID.";
    } else if (!provider) {
        code = "NO_PROVIDER"; label = "NO PROVIDER";
        next = "Choose and verify an approved PX Provider for this Session.";
    } else if (roomProvider && provider !== roomProvider) {
        code = "PROVIDER_MISMATCH"; label = "PROVIDER MISMATCH";
        next = "Resolve the Room/Session Provider disagreement before dispatch.";
    } else if (provider === "int1-fake") {
        code = "FAKE_ONLY"; label = "FAKE-ONLY PROVIDER";
        next = "Requires its separately authorized synthetic execution path.";
    } else if (!roomBed || !sessionBed) {
        code = "NO_BED"; label = "BED NOT LINKED";
        next = "Verify the Room Bed and Session working directory.";
    } else if (roomBed !== sessionBed) {
        code = "BED_MISMATCH"; label = "BED NEEDS REVIEW";
        next = "Paths differ; PX must resolve the true worktree before execution.";
    } else if (!assignmentId) {
        code = "NO_ASSIGNMENT"; label = "NO ASSIGNMENT";
        next = "Create or activate a bounded Assignment for this Room.";
    } else if (assignmentStatus && assignmentStatus !== "ACTIVE") {
        code = "ASSIGNMENT_INACTIVE"; label = "ASSIGNMENT NOT ACTIVE";
        next = "Review Assignment status; do not auto-activate or override.";
    } else {
        code = "STRUCTURED";
        label = "PX PREFLIGHT NEEDED";
        next = !assignmentStatus
            ? "Assignment status is not exposed; PX must verify authority."
            : "Identity fields align; PX must still check provider, Bed and authority.";
    }

    const canRequestTurn = code === "STRUCTURED";
    return {
        code: code,
        label: label,
        next: next,
        checks: checks,
        canRequestTurn: canRequestTurn,
        hasRegisteredSession: !!sessionId,
        sessionId: sessionId,
        recordedAt: valueOf(room.statusRecordedAt),
        source: "PX ROOM / SESSION RECORDS",
        isProviderReachable: false,
        isBrowserChatConnected: false
    };
}

function allowsCommand(roomValue, commandValue) {
    const command = valueOf(commandValue).toUpperCase();
    if (command === "STATUS")
        return true; // px agent quick STATUS only reads recorded status.
    if (command === "PAUSE")
        return !!valueOf((roomValue || {}).sessionId);
    const turns = ["GO", "CONTINUE", "REPORT", "CHECKLIST", "NEXT", "SUGGEST"];
    return turns.indexOf(command) >= 0 && inspect(roomValue).canRequestTurn;
}

function countPending(rows) {
    const list = Array.isArray(rows) ? rows : [];
    let n = 0;
    for (let i = 0; i < list.length; ++i) {
        if (!inspect(list[i]).canRequestTurn)
            ++n;
    }
    return n;
}
