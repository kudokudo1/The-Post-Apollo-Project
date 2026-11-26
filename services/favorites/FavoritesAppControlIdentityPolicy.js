.pragma library

// AppControl donor identity compatibility, not a new universal identity schema.
// These helpers turn existing provider-owned process/metric/monitor values into
// legacy favorite keys. They DO NOT discover processes, authorize kills,
// mutate FavoritesStore, infer current liveness, or execute commands.
//
// Preserve original byte-level key formats. In particular, HUNTER rechecks
// task|<encoded comm identity> directly against FavoritesStore.favoriteKeys.

function sourceItem(entry) {
    if (entry && entry._favoriteRecord)
        return entry._sourceItem;
    return entry;
}

function taskIdentity(entry) {
    const source = sourceItem(entry) || entry;
    if (!source)
        return "";

    const comm = String(source.comm || source.name || source.label || "").trim();
    if (comm)
        return comm.toLowerCase();

    const args = String(source.args || "").trim();
    if (!args)
        return "";

    const first = args.split(/\s+/)[0] || "";
    const pieces = first.split("/");
    return String(pieces[pieces.length - 1] || first).toLowerCase();
}

function taskKey(entry) {
    const identity = taskIdentity(entry);
    return identity ? "task|" + encodeURIComponent(identity) : "";
}

function taskIdentityFromKey(key) {
    const raw = String(key || "");
    if (raw.indexOf("task|") !== 0)
        return "";
    try { return decodeURIComponent(raw.slice(5)); }
    catch (error) { return ""; }
}

function taskMetricKey(entry, metricId) {
    const identity = taskIdentity(entry);
    const id = String(metricId || "").trim().toLowerCase();
    if (!identity || !id)
        return "";
    return "taskmetric|" + encodeURIComponent(identity)
           + "|" + encodeURIComponent(id);
}

function taskMetricData(key) {
    const raw = String(key || "");
    if (raw.indexOf("taskmetric|") !== 0)
        return null;
    const parts = raw.split("|");
    if (parts.length < 3)
        return null;
    try {
        return {
            identity: decodeURIComponent(parts[1]),
            metricId: decodeURIComponent(parts.slice(2).join("|"))
        };
    } catch (error) { return null; }
}

// The original host obtains modeName from selectedControlModeIndex, not from
// the entry. Keep that host decision external, and accept only original modes.
function monitorBoxKey(entry, boxId, modeName) {
    if (!entry || !entry.id || !boxId)
        return "";
    if (modeName !== "thermal" && modeName !== "system")
        return "";
    return "watchbox|"
           + modeName
           + "|"
           + encodeURIComponent(String(entry.id))
           + "|"
           + encodeURIComponent(String(boxId));
}

function hasMonitorBoxFavorite(entry, modeName, keys) {
    if (!entry || !entry.id)
        return false;
    if (modeName !== "thermal" && modeName !== "system")
        return false;
    const prefix = "watchbox|"
                   + modeName
                   + "|"
                   + encodeURIComponent(String(entry.id))
                   + "|";

    for (let i = 0; i < keys.length; i++) {
        if (String(keys[i] || "").indexOf(prefix) === 0)
            return true;
    }
    return false;
}
