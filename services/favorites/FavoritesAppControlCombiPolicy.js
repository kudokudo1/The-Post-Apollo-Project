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

// Preserve the first live row for each watched identity. This is
// presentation-only: actual action targets still resolve live.
function firstFavoriteTaskRows(identities, rows, identityFor) {
    const first = Object.create(null);
    const wanted = Object.create(null);
    for (const identity of identities)
        wanted[identity] = true;
    let remaining = identities.length;
    for (let i = 0; i < rows.length && remaining > 0; i++) {
        const identity = identityFor(rows[i]);
        if (wanted[identity] && first[identity] === undefined) {
            first[identity] = rows[i];
            remaining--;
        }
    }
    return first;
}


// Local projection only. Provider reads remain lazy; no storage or execution
// authority is supplied. In COMBI mode only the cached catalog is read.
function buildLocalCatalog(inCombi, sources, owner) {
    const thermalSnapshot = inCombi ? [] : sources.thermalRows();
    const fanSnapshot = inCombi ? [] : sources.fanRows();
    const systemSnapshot = inCombi ? [] : sources.systemRows();
    const rows = [];
    const seen = ({});
    const preferredAppKeys = ({});
    const preferredRunKeys = ({});

    function pushUnique(record) {
        if (!record)
            return;

        const key = String(record._favoriteKey || record.id || record.name || "");
        if (!key || seen[key])
            return;

        seen[key] = true;
        rows.push(record);
    }

    if (inCombi) {
        const cached = sources.cachedRows();
        for (let i = 0; i < cached.length; i++)
            pushUnique(cached[i]);
    } else {
        const favoriteStore = sources.membership();
        for (let i = 0; i < favoriteStore.favoriteDetailActionKeys.length; i++) {
            const raw = String(favoriteStore.favoriteDetailActionKeys[i] || "");
            const first = raw.indexOf("|");
            const second = first >= 0 ? raw.indexOf("|", first + 1) : -1;
            if (first < 0 || second < 0)
                continue;

            const type = raw.slice(0, first);
            let context = "";
            try {
                context = decodeURIComponent(raw.slice(first + 1, second));
            } catch (error) {
                continue;
            }

            if (type === "app") preferredAppKeys[context] = true;
            else if (type === "run") preferredRunKeys[context] = true;
        }

        const apps = sources.apps();
        for (let i = 0; i < apps.length; i++) {
            const entry = apps[i];
            const appKey = owner.appEntryKey(entry);
            if (owner.isFavoriteItem(entry, owner.appsModeIndex)
                    || !!preferredAppKeys[appKey]) {
                pushUnique(owner.favoriteRecordForApp(entry));
            }
        }

        const runKeys = ({});
        for (let i = 0; i < favoriteStore.favoriteKeys.length; i++) {
            const key = String(favoriteStore.favoriteKeys[i] || "");
            if (owner.runFavoriteDataFromKey(key)) runKeys[key] = true;
        }
        for (const key in preferredRunKeys) runKeys[key] = true;
        for (const key in runKeys) {
            const data = owner.runFavoriteDataFromKey(key);
            if (data) pushUnique(owner.favoriteRecordForRunCommand(data.commandText, data.prefixMode));
        }

        const hiddenKeys = ({});
        for (let i = 0; i < favoriteStore.favoriteKeys.length; i++) {
            const key = String(favoriteStore.favoriteKeys[i] || "");
            if (key.indexOf("hidden:") === 0) hiddenKeys[key] = true;
        }
        for (const key in preferredAppKeys) {
            if (key.indexOf("hidden:") === 0) hiddenKeys[key] = true;
        }
        for (const key in hiddenKeys) {
            const command = key.slice(7);
            if (command) pushUnique(owner.favoriteRecordForApp(owner.hiddenCommandRecord(command)));
        }

        const thermalItems = thermalSnapshot.concat(fanSnapshot);
        for (let i = 0; i < thermalItems.length; i++) {
            const entry = thermalItems[i];
            if (owner.isFavoriteItem(entry, owner.thermalModeIndex)
                    || owner.monitorEntryHasBoxFavorite(entry, owner.thermalModeIndex)) {
                pushUnique(owner.favoriteRecordForModeItem(entry, owner.thermalModeIndex));
            }
        }

        for (let i = 0; i < systemSnapshot.length; i++) {
            const entry = systemSnapshot[i];
            if (owner.isFavoriteItem(entry, owner.systemModeIndex)
                    || owner.monitorEntryHasBoxFavorite(entry, owner.systemModeIndex)) {
                pushUnique(owner.favoriteRecordForModeItem(entry, owner.systemModeIndex));
            }
        }

        const windows = sources.windows();
        for (let i = 0; i < windows.length; i++) {
            const entry = windows[i];
            if (owner.isFavoriteItem(entry, owner.windowsModeIndex)) {
                pushUnique(owner.favoriteRecordForModeItem(entry, owner.windowsModeIndex));
            }
        }

        const taskIdentities = ({});

        for (let i = 0; i < favoriteStore.favoriteKeys.length; i++) {
            const identity = owner.taskIdentityFromFavoriteKey(
                favoriteStore.favoriteKeys[i]
            );
            if (identity)
                taskIdentities[identity] = true;
        }

        for (let i = 0; i < favoriteStore.favoriteTaskMetricKeys.length; i++) {
            const data = owner.taskMetricFavoriteData(
                favoriteStore.favoriteTaskMetricKeys[i]
            );
            if (data && data.identity)
                taskIdentities[data.identity] = true;
        }

        const watchedIdentities = Object.keys(taskIdentities);
        // Read taskRows only when the model actually contains task
        // favorites; otherwise this binding need not rebuild on telemetry.
        if (watchedIdentities.length > 0) {
            const first = firstFavoriteTaskRows(watchedIdentities, sources.taskRows(), owner.taskIdentity);
            for (const identity of watchedIdentities) {
                pushUnique(
                    owner.favoriteRecordForTaskIdentity(
                        identity,
                        first[identity] || null
                    )
                );
            }
        }

    }

    return rows;
}
