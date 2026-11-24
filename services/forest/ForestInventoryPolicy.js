// Forest B0 // Pure, fail-closed model-list validation. No network or storage.
function parseInventory(raw) {
    var bad = { valid: false, status: "UNAVAILABLE", reason: "INVALID_RESPONSE", models: [] };
    if (typeof raw !== "string" || raw.length < 2 || raw.length > 1048576)
        return bad;
    var value;
    try { value = JSON.parse(raw); } catch (e) { return bad; }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.schema_version !== 1 || value.provider !== "ollama"
            || value.generation_enabled !== false || value.tools_enabled !== false
            || value.sessions_enabled !== false || !Array.isArray(value.models)
            || value.models.length > 256 || value.model_count !== value.models.length
            || !Array.isArray(value.capabilities))
        return bad;
    if (value.status === "UNAVAILABLE") {
        if (value.models.length !== 0 || value.capabilities.length !== 0
                || typeof value.reason !== "string"
                || !/^[A-Z0-9_]{1,64}$/.test(value.reason))
            return bad;
        return { valid: true, status: "UNAVAILABLE", reason: value.reason, models: [] };
    }
    if (value.status !== "REACHABLE" || value.capabilities.length !== 1
            || value.capabilities[0] !== "list_models")
        return bad;
    var seen = Object.create(null);
    var models = [];
    for (var i = 0; i < value.models.length; i++) {
        var m = value.models[i];
        if (!m || typeof m !== "object" || Array.isArray(m)
                || typeof m.name !== "string"
                || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(m.name)
                || seen[m.name] || typeof m.size_bytes !== "number"
                || !isFinite(m.size_bytes) || m.size_bytes < 0
                || Math.floor(m.size_bytes) !== m.size_bytes)
            return bad;
        seen[m.name] = true;
        models.push({ name: m.name, size_bytes: m.size_bytes });
    }
    return { valid: true, status: "REACHABLE", reason: "", models: models };
}

/*
 * Process callback barrier. No model list is public until stdout, stderr
 * and QProcess::NormalExit have all completed for this scan. Mirrors the
 * principle of HospitalDoctorDirectoryExitPolicy without sharing ownership.
 */
function beginScan() {
    return {
        stdoutSeen: false, stderrSeen: false, exitSeen: false,
        stagedStatus: "", stagedReason: "", stagedModels: [],
        exitCode: -999, exitStatus: -999, error: "",
        complete: false, accepted: false,
        status: "CHECKING", reason: "", models: []
    };
}
function cloneScan(s) {
    return {
        stdoutSeen: s.stdoutSeen, stderrSeen: s.stderrSeen,
        exitSeen: s.exitSeen, stagedStatus: s.stagedStatus,
        stagedReason: s.stagedReason, stagedModels: s.stagedModels,
        exitCode: s.exitCode, exitStatus: s.exitStatus, error: s.error,
        complete: s.complete, accepted: s.accepted,
        status: s.status, reason: s.reason, models: s.models
    };
}
function finishScan(s) {
    if (!s.stdoutSeen || !s.stderrSeen || !s.exitSeen)
        return s;
    s.complete = true;
    // QProcess::NormalExit is 0; a crash with an exit code of 0 is failure.
    if (s.exitStatus !== 0 || s.error) {
        s.status = "UNAVAILABLE";
        s.reason = s.error || "BACKEND_EXIT";
    } else if (s.stagedStatus === "REACHABLE" && s.exitCode === 0) {
        s.status = "REACHABLE";
        s.reason = "";
        s.accepted = true;
        s.models = s.stagedModels;
    } else if (s.stagedStatus === "UNAVAILABLE" && s.exitCode === 2) {
        s.status = "UNAVAILABLE";
        s.reason = s.stagedReason;
        s.accepted = true;
    } else {
        s.status = "UNAVAILABLE";
        s.reason = "INVALID_RESPONSE";
    }
    // Never publish staged model names on failure.
    s.stagedModels = [];
    return s;
}
function captureStdoutScan(state, raw) {
    if (!state || state.complete)
        return state;
    var s = cloneScan(state);
    if (s.stdoutSeen) {
        s.error = "DUPLICATE_STDOUT";
        return finishScan(s);
    }
    s.stdoutSeen = true;
    var response = parseInventory(raw);
    if (!response.valid) {
        s.error = "INVALID_RESPONSE";
    } else {
        s.stagedStatus = response.status;
        s.stagedReason = response.reason;
        s.stagedModels = response.models;
    }
    return finishScan(s);
}
function captureStderrScan(state, raw) {
    if (!state || state.complete)
        return state;
    var s = cloneScan(state);
    if (s.stderrSeen) {
        s.error = "DUPLICATE_STDERR";
        return finishScan(s);
    }
    s.stderrSeen = true;
    if (String(raw || "").trim().length > 0)
        s.error = "BACKEND_STDERR";
    return finishScan(s);
}
function captureExitScan(state, code, exitStatus) {
    if (!state || state.complete)
        return state;
    var s = cloneScan(state);
    if (s.exitSeen) {
        s.error = "DUPLICATE_EXIT";
        return finishScan(s);
    }
    s.exitSeen = true;
    if (typeof code !== "number" || typeof exitStatus !== "number"
            || !isFinite(code) || !isFinite(exitStatus)) {
        s.error = "BACKEND_EXIT";
    } else {
        s.exitCode = code;
        s.exitStatus = exitStatus;
        if (exitStatus !== 0 || (code !== 0 && code !== 2))
            s.error = "BACKEND_EXIT";
    }
    return finishScan(s);
}

// Display-only comparison of provider-reported model artifact bytes from
// the same successful B0 inventory. No free-space, deduplication, intelligence,
// allocation, memory, or model-form inference is made from these numbers.
function diskComparison(status, models) {
    var unknown = { observed: false, largest: 0, sizes: Object.create(null) };
    if (status !== "REACHABLE" || !Array.isArray(models)
            || models.length > 256)
        return unknown;
    var sizes = Object.create(null);
    var largest = 0;
    for (var i = 0; i < models.length; i++) {
        var entry = models[i];
        if (!entry || typeof entry.name !== "string"
                || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(entry.name)
                || sizes[entry.name] !== undefined
                || !Number.isSafeInteger(entry.size_bytes) || entry.size_bytes < 0)
            return unknown;
        sizes[entry.name] = entry.size_bytes;
        largest = Math.max(largest, entry.size_bytes);
    }
    return { observed: true, largest: largest, sizes: sizes };
}

function artifactSizeLabel(bytes) {
    if (!Number.isSafeInteger(bytes) || bytes < 0)
        return "?";
    if (bytes >= 1073741824)
        return (bytes / 1073741824).toFixed(2) + " GiB";
    if (bytes >= 1048576)
        return (bytes / 1048576).toFixed(1) + " MiB";
    if (bytes >= 1024)
        return (bytes / 1024).toFixed(1) + " KiB";
    return String(bytes) + " B";
}

function diskProfile(comparison, name) {
    var unknown = { observed: false, label: "?", ratio: 0, comparable: false };
    if (!comparison || comparison.observed !== true
            || !comparison.sizes || typeof name !== "string"
            || !Object.prototype.hasOwnProperty.call(comparison.sizes, name))
        return unknown;
    var bytes = comparison.sizes[name];
    if (!Number.isSafeInteger(bytes) || bytes < 0
            || !Number.isSafeInteger(comparison.largest)
            || comparison.largest < bytes)
        return unknown;
    return {
        observed: true,
        label: artifactSizeLabel(bytes),
        comparable: comparison.largest > 0,
        ratio: comparison.largest > 0 ? bytes / comparison.largest : 0
    };
}
