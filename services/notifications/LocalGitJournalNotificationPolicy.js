.pragma library

// Present ONLY existing, post-operation journal records. A journal status is
// not independently verified Git repository state or proof of remote success.
function safeName(value, max) {
    return String(value || "").replace(/[^a-zA-Z0-9_ .:+\/-]/g, "")
           .trim().slice(0, max);
}
function repoLabel(raw) {
    const parts = String(raw || "").replace(/\\/g, "/").split("/");
    for (let i = parts.length - 1; i >= 0; --i) {
        const name = safeName(parts[i], 64);
        if (name && name !== "." && name !== "..")
            return name;
    }
    return "";
}
function payload(operationId, success, record) {
    const row = record || {};
    const id = String(operationId || "").trim();
    const status = String(row.status || "");
    const kind = safeName(row.kind, 72);
    const repo = repoLabel(row.repository);
    if (!id || id.length > 128 || id !== String(row.id || "")
            || !kind || !repo
            || (success !== true && success !== false)
            || (success && status !== "COMPLETE")
            || (!success && status !== "FAILED"))
        return null;
    return {
        id: "apollo-local-git-" + id,
        repository: repo,
        kind: kind,
        status: status,
        success: success,
        message: kind + " // " + repo + " // JOURNAL " + status
            + ". The operation journal recorded this outcome; "
            + "independent repository verification is not implied."
            + " Review Git Operations for evidence."
    };
}
