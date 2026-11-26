.pragma library

// AppControl's local FAVORITES/COMBI catalog preparation, kept separate
// from the read-only cross-provider FavoritesUnifiedCatalog.
//
// Inputs must be ordinary records supplied by their original providers.
// This module may prepare UI search metadata but NEVER obtains filesystem
// truth, resolves a task/PID, executes an action, or changes favorite keys.
// _combiSearchText includes private owner fields and MUST NOT be exported to
// CPU++ or other universal Favorites projections.

function sourceItem(entry) {
    if (entry && entry._favoriteRecord)
        return entry._sourceItem;
    return entry;
}

function searchText(record) {
    if (!record)
        return "";
    const source = sourceItem(record) || record;
    // Intentional byte-for-byte donor field order and coercion.
    return ((record.name || "") + " "
            + (record.genericName || "") + " "
            + (record.comment || "") + " "
            + (record.keywords || "") + " "
            + (source.args || "") + " "
            + (source.commandText || "") + " "
            + (source.appName || "") + " "
            + (source.windowName || "") + " "
            + (source.tabTitle || "") + " "
            + (source.category || "") + " "
            + (source.role || "") + " "
            + (source.metric || "") + " "
            + String(source.pid || "")).toLowerCase();
}

function prepare(record) {
    if (!record)
        return null;
    // The donor attaches the field to the same local record. Do not clone
    // because AppControl relies on the original _sourceItem reference.
    record._combiSearchText = searchText(record);
    return record;
}

// The host remains responsible for sourcing provider records; this function
// only does local deduplication, ordering and structural signature generation.
// Preserve the donor comparator's Number(x || 0) and signature Number(x || -1)
// behavior exactly, including the handling of zero and absent source modes.
function buildStatic(records) {
    const rows = [];
    // Preserve the donor's legacy truthy-prototype key behavior exactly.
    // Any deduplication hardening is a separate, reviewed behavior change.
    const seen = ({});
    const input = records || [];
    for (let i = 0; i < input.length; i++) {
        const record = prepare(input[i]);
        if (!record)
            continue;
        const key = String(record._favoriteKey || record.id || record.name || "");
        if (!key || seen[key])
            continue;
        seen[key] = true;
        rows.push(record);
    }
    rows.sort(function(a,b) {
        const modeCompare = Number(a._sourceModeIndex || 0)
                          - Number(b._sourceModeIndex || 0);
        if (modeCompare !== 0)
            return modeCompare;
        return String(a.name || "").localeCompare(String(b.name || ""));
    });
    const signature = JSON.stringify(rows.map(function(entry) {
        return [
            Number(entry._sourceModeIndex || -1),
            String(entry.id || entry._favoriteKey || ""),
            String(entry.name || "")
        ];
    }));
    return {rows: rows, signature: signature};
}

// The donor's COMBI fast path uses a stable linear partition instead of
// sorting on every source/telemetry update. The caller supplies the *owner*
// membership predicate; this policy neither interprets nor invents IDs.
function partitionPinned(rows, isFavorite) {
    const pinned = [], ordinary = [];
    const input = rows || [];
    for (let i = 0; i < input.length; i++) {
        const entry = input[i];
        if (isFavorite(entry))
            pinned.push(entry);
        else
            ordinary.push(entry);
    }
    return pinned.concat(ordinary);
}


// The local COMBI process catalog is a presentation projection only.
// PROCESS owns live task identity and record materialization. The caller must
// supply those functions; this policy cannot kill, inspect procfs, or choose
// another task when a target disappears.
function buildTasks(tasks, identityFor, recordFor) {
    const rows = [];
    const seen = ({}); // Donor semantics, including reserved-object keys.
    const identities = [];
    const input = tasks || [];

    for (let i = 0; i < input.length; i++) {
        const task = input[i];
        const identity = identityFor(task);
        if (!identity || seen[identity])
            continue;

        seen[identity] = true;
        identities.push(identity);

        const record = prepare(recordFor(identity, task));
        if (record)
            rows.push(record);
    }

    identities.sort();
    const signature = identities.join("\\n");
    rows.sort(function(a, b) {
        return String(a.name || "").localeCompare(String(b.name || ""));
    });
    return {rows: rows, signature: signature};
}

// AppControl-local Favorites/COMBI visible-row projection. This deliberately
// does NOT reuse FavoritesSearchPolicy, which safely excludes sensitive
// command/path/task fields for CPU++'s universal view. COMBI searches those
// fields locally as it did before extraction. Never export these rows to
// another widget.
//
// Options are supplied by the AppControl UI. In particular, copied-submode
// visibility and starred membership remain owner-owned predicates.
function visibleRows(records, options) {
    const settings = options || {};
    const query = settings.query || "";
    const inCombi = !!settings.inCombi;
    const rows = (records || []).filter(function(entry) {
        if (settings.filterMode !== settings.filterAll
                && Number(entry._sourceModeIndex) !== settings.filterMode)
            return false;

        if (!settings.matchesCopiedSubmode(entry))
            return false;

        if (query.length === 0)
            return true;

        const haystack = inCombi && entry._combiSearchText
                       ? entry._combiSearchText
                       : searchText(entry);
        return haystack.indexOf(query) !== -1;
    });

    if (inCombi && query.length === 0)
        return partitionPinned(rows, settings.isFavorite);

    rows.sort(function(a, b) {
        if (inCombi) {
            const aFavorite = settings.isFavorite(a);
            const bFavorite = settings.isFavorite(b);
            if (aFavorite !== bFavorite)
                return aFavorite ? -1 : 1;
        }
        const modeCompare = a._sourceModeIndex - b._sourceModeIndex;
        if (modeCompare !== 0)
            return modeCompare;
        return String(a.name || "").localeCompare(String(b.name || ""));
    });
    return rows;
}
