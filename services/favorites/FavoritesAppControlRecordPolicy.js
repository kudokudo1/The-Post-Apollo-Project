.pragma library

// Local AppControl FAVORITES/COMBI record presentation only.
//
// Owner-supplied keys, source records and callbacks are authoritative. Do not
// resolve providers, derive command execution authority, or persist these
// wrappers in the universal Favorites catalog. RUN command text and other
// source fields may be private.
//
// AppControl retains its application launcher. This policy only retains a
// callback supplied by that owner, exactly as the existing wrapper does.
function appRecord(entry, key, appsModeIndex, launchApplication) {
    return {
        _favoriteRecord: true,
        _favoriteType: "app",
        _favoriteKey: key,
        _sourceModeIndex: appsModeIndex,
        _sourceItem: entry,

        id: entry.id || key,
        name: entry.name || "APPLICATION",
        genericName: entry.genericName || "",
        comment: entry.comment || "",
        keywords: entry.keywords || "",
        icon: entry.icon || "",
        actions: entry.actions || [],
        command: entry.command || [],
        startupClass: entry.startupClass || "",

        execute: function() {
            launchApplication(entry);
        }
    };
}

// The RUN owner supplies the resolved prefix, provider row, stable key,
// prefix name and shell name. This policy neither parses nor runs commands.
function runRecord(sourceItem, key, resolvedPrefix, runModeIndex,
                   prefixName, shellName) {
    return {
        _favoriteRecord: true,
        _favoriteType: "run",
        _favoriteKey: key,
        _sourceModeIndex: runModeIndex,
        _sourceItem: sourceItem,
        _runPrefixMode: resolvedPrefix,

        id: key,
        label: sourceItem.label,
        name: sourceItem.name,
        commandText: sourceItem.commandText,
        genericName: sourceItem.genericName,
        comment: "FAVORITE • "
                 + prefixName
                 + " • "
                 + shellName.toUpperCase(),
        keywords: "",
        icon: "",
        actions: [],
        startupClass: ""
    };
}

// Local display records, including explicitly offline process placeholders.
function modeRecord(entry, key, modeIndex, modeName, onExecute) {
    const label = entry.label || entry.name || "OPTION";

    return {
        _favoriteRecord: true,
        _favoriteType: "mode",
        _favoriteKey: key,
        _sourceModeIndex: modeIndex,
        _sourceItem: entry,

        id: key,
        name: label,
        genericName: modeName,
        comment: "FAVORITE FROM " + modeName,
        keywords: "",
        icon: "",
        actions: [],
        command: [],
        startupClass: "",

        execute: function() {
            onExecute(modeName, label);
        }
    };
}

function taskRecord(identity, liveEntry, killModeIndex) {
    const normalized = String(identity || "").trim().toLowerCase();
    if (!normalized)
        return null;

    const source = liveEntry ? liveEntry : {
        _taskRecord: true,
        _taskOffline: true,
        id: "task-offline:" + normalized,
        pid: 0, ppid: 0, user: "", state: "OFFLINE",
        cpu: 0, mem: 0, rss: 0, vsz: 0, threads: 0,
        elapsed: "NOT RUNNING",
        comm: normalized, args: "", name: normalized, label: normalized
    };
    const key = "task|" + encodeURIComponent(normalized);
    return {
        _favoriteRecord: true,
        _favoriteType: "task",
        _favoriteKey: key,
        _sourceModeIndex: killModeIndex,
        _sourceItem: source,
        id: key,
        name: source.comm || normalized,
        genericName: "WATCHED PROCESS",
        comment: liveEntry
                 ? "KILL • RUNNING • PID " + String(source.pid || "?")
                 : "KILL • NOT RUNNING • FAVORITE RETAINED",
        keywords: "kill process task watched",
        icon: "", actions: [], command: [], startupClass: ""
    };
}
