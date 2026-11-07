// HOSPITAL // Evidence-backed attention labels for registered PX workers.
// Inputs are a saved Room/Session snapshot, NOT an authenticated heartbeat.
// No inference of "frozen", escalated, or operator approval from elapsed time.
function clean(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function oneLine(value, maxChars) {
    const text = clean(value).replace(/[\r\n\t\u0000-\u001f\u007f]+/g, " ")
        .replace(/\s+/g, " ");
    const limit = Math.max(16, Number(maxChars || 144));
    return text.length > limit ? text.slice(0, limit - 3) + "..." : text;
}

function describe(roomValue) {
    const room = roomValue || {};
    const status = clean(room.sessionStatus).toUpperCase();
    const id = clean(room.sessionId);
    const lastError = oneLine(room.sessionLastError, 160);
    const exitCode = room.sessionLastExitCode;
    const hasNonzeroExit = exitCode !== null && exitCode !== undefined
        && clean(exitCode) !== "" && Number(exitCode) !== 0;
    const ended = !!clean(room.sessionEndedAt);

    const result = {
        label: "UNKNOWN",
        reason: "No verified worker activity state available",
        severity: 0, // 0=informational, 1=watch, 2=attention, 3=stopped/error
        source: "PX SESSION RECORD",
        recordedAt: clean(room.statusRecordedAt),
        requiresReview: false,
        sessionId: id
    };

    if (!id || status === "NO SESSION") {
        result.label = "UNCONNECTED";
        result.reason = "No PX session is registered for this Room";
        return result;
    }
    if (status === "COMPLETE" || status === "ENDED") {
        result.label = "COMPLETE";
        result.reason = "PX session recorded completion; no active worker implied";
        return result;
    }
    if (status === "FAILED") {
        result.label = "STOPPED";
        result.severity = 3;
        result.reason = lastError || (hasNonzeroExit
            ? "PX last exit code " + clean(exitCode) : "PX session marked FAILED");
        return result;
    }
    if (ended) {
        result.label = "ENDED";
        result.reason = "Session has an end timestamp; no active worker implied";
        return result;
    }
    if (lastError || hasNonzeroExit) {
        result.label = "NEEDS ATTENTION";
        result.severity = 2;
        result.reason = lastError || "PX last exit code " + clean(exitCode);
        return result;
    }
    if (status === "REVIEW") {
        result.label = "NEEDS REVIEW";
        result.severity = 2;
        result.requiresReview = true;
        result.reason = "PX session marked REVIEW; inspect details before proceeding";
        return result;
    }
    if (status === "WAITING") {
        result.label = "WAITING";
        result.severity = 2;
        result.reason = "PX session marked WAITING; cause is not classified";
        return result;
    }
    if (status === "PAUSED") {
        result.label = "PAUSED";
        result.severity = 1;
        result.reason = "PX session is paused; no automatic continuation implied";
        return result;
    }
    if (status === "OPERATING" || status === "THINKING") {
        result.label = "WORKING";
        result.reason = "PX recorded " + status + "; heartbeat not verified";
        return result;
    }
    if (status === "IDLE") {
        result.label = "IDLE";
        result.reason = "PX session recorded IDLE; no new work dispatched";
        return result;
    }
    result.reason = "Unrecognized PX session state: " + (status || "UNKNOWN");
    return result;
}

function countAttention(rows) {
    const list = Array.isArray(rows) ? rows : [];
    let count = 0;
    for (let i = 0; i < list.length; ++i) {
        if (describe(list[i]).severity >= 2)
            count += 1;
    }
    return count;
}
