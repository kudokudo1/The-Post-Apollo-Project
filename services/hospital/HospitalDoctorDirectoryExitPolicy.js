// Hospital H1 // Doctor list process-event completion policy, READ ONLY.
// The roster must not see stdout before BOTH stdio streams and the exit
// result belong to the same completed request. No writes or PX fallback.
//
// A request stays busy until stdout, stderr and Process.exited are all
// observed, even after a failed exit. That prevents a new invocation on the
// same Quickshell Process/StdioCollector from accepting an old late callback.
// If a broken transport never closes a stream, it remains NOT READY.
// This policy never authorizes a Doctor action or an installed native client.

function begin() {
    return {
        stdoutSeen: false,
        stderrSeen: false,
        exitSeen: false,
        exitAccepted: false,
        staged: [],
        error: "",
        complete: false,
        accepted: false,
        records: []
    };
}

function clone(state) {
    return {
        stdoutSeen: state.stdoutSeen,
        stderrSeen: state.stderrSeen,
        exitSeen: state.exitSeen,
        exitAccepted: state.exitAccepted,
        staged: state.staged,
        error: state.error,
        complete: state.complete,
        accepted: state.accepted,
        records: state.records
    };
}

function finishIfComplete(next) {
    if (!next.stdoutSeen || !next.stderrSeen || !next.exitSeen)
        return next;
    next.complete = true;
    next.accepted = next.exitAccepted && !next.error;
    next.records = next.accepted ? next.staged : [];
    next.staged = []; // Erase rejected or published staging.
    if (!next.accepted && !next.error)
        next.error = "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER";
    return next;
}

function parseDirectory(raw) {
    const body = String(raw || "").trim();
    if (!body)
        throw new Error("EMPTY PROTECTED DOCTOR RESPONSE");
    const result = JSON.parse(body);
    if (!Array.isArray(result) || result.length > 250)
        throw new Error("INVALID PROTECTED DOCTOR DIRECTORY");

    const seen = {};
    return result.map(function(row) {
        if (!row || typeof row !== "object" || Array.isArray(row))
            throw new Error("INVALID PROTECTED DOCTOR ENTRY");
        const id = String(row.id || "").trim();
        if (!id || Object.prototype.hasOwnProperty.call(seen, id))
            throw new Error("INVALID PROTECTED DOCTOR ID");
        seen[id] = true;
        return {
            id: id,
            name: String(row.name || row.id || "DOCTOR").trim(),
            role: String(row.role || "DOCTOR").trim(),
            status: String(row.status || "ACTIVE").toUpperCase(),
            createdAt: String(row.createdAt || "").trim(),
            updatedAt: String(row.updatedAt || "").trim()
        };
    });
}

function captureStdout(state, text) {
    if (!state || state.complete)
        return state;
    const next = clone(state);
    if (next.stdoutSeen) {
        next.error = "DUPLICATE PROTECTED DOCTOR STDOUT";
        return finishIfComplete(next);
    }
    next.stdoutSeen = true;
    try {
        next.staged = parseDirectory(text);
    } catch (error) {
        next.staged = [];
        next.error = "HOSPITAL PROTECTED DOCTORS // "
            + String(error).slice(0, 220);
    }
    return finishIfComplete(next);
}

function captureStderr(state, text) {
    if (!state || state.complete)
        return state;
    const next = clone(state);
    if (next.stderrSeen) {
        next.error = "DUPLICATE PROTECTED DOCTOR STDERR";
        return finishIfComplete(next);
    }
    next.stderrSeen = true;
    const detail = String(text || "").trim();
    if (detail && !next.error)
        next.error = "HOSPITAL DOCTOR // "
            + detail.split("\n").pop().slice(0, 220);
    return finishIfComplete(next);
}

function captureExit(state, code, exitStatus) {
    if (!state || state.complete)
        return state;
    const next = clone(state);
    if (next.exitSeen) {
        next.error = "DUPLICATE PROTECTED DOCTOR EXIT";
        return finishIfComplete(next);
    }
    next.exitSeen = true;
    // QProcess::NormalExit is 0. Reject a crash even if exitCode is 0.
    next.exitAccepted = typeof code === "number" && code === 0
        && typeof exitStatus === "number" && exitStatus === 0;
    if (!next.exitAccepted && !next.error)
        next.error = "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER";
    return finishIfComplete(next);
}
