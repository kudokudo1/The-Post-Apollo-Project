.pragma library

// A FileView status describes an actual load/save outcome. Never interpret
// transient "saving", "loading", "clearing" or "new" as recovered.
// Deliberately do not propagate low-level error strings or file paths.
function initial() {
    return { history: "", policy: "", favorites: "" };
}
function transition(previous, area, status) {
    const prior = previous || initial();
    if (["history", "policy", "favorites"].indexOf(area) < 0)
        return { state: prior, event: "" };
    const value = String(status || "").toLowerCase();
    const failed = ["save-error", "load-error", "parse-error"].indexOf(value) >= 0;
    const succeeded = value === "saved" || value === "ready";
    if (!failed && !succeeded)
        return { state: prior, event: "" };
    const was = prior[area] || "";
    const now = failed ? "failed" : "healthy";
    if (now === was)
        return { state: prior, event: "" };
    const next = Object.assign({}, prior);
    next[area] = now;
    return { state: next,
             event: failed ? "unavailable"
                           : was === "failed" ? "restored" : "" };
}
