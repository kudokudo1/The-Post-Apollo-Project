.pragma library

// Read-only evidence evolution over exact-source dossier timelines.
//
// "First" and "last" here mean first/last archived presence in saved Weather
// snapshots. They do NOT claim provider discovery time, event onset, retraction,
// causation, or authoritative lifecycle status.

function text(value, limit) {
    const clean = String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    return clean.slice(0, Math.max(0, Number(limit) || 0));
}

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function relationKey(row) {
    if (!row)
        return "";
    const source = text(row.source, 48);
    const id = text(row.id, 120);
    if (!source)
        return "";
    if (id)
        return source + "|" + id;

    const lat = finite(row.latitude, NaN);
    const lon = finite(row.longitude, NaN);
    const title = text(row.title, 120);
    if (!isFinite(lat) || !isFinite(lon))
        return "";
    return source + "|@" + lat.toFixed(4) + "," + lon.toFixed(4)
           + "|" + title;
}

function lifecycleLabel(firstIndex, lastIndex, seenSnapshots, totalSnapshots) {
    const first = Number(firstIndex);
    const last = Number(lastIndex);
    const seen = Number(seenSnapshots);
    const total = Number(totalSnapshots);
    if (!isFinite(first) || !isFinite(last) || !isFinite(seen)
            || !isFinite(total) || total <= 0)
        return "UNKNOWN";

    const continuous = seen === (last - first + 1);
    const current = last === total - 1;
    if (!continuous)
        return "INTERMITTENT";
    if (first === 0 && current && seen === total)
        return "PERSISTENT";
    if (current)
        return "CURRENT / LATE";
    if (seen === 1)
        return "SINGLE SNAPSHOT";
    return "DROPPED";
}

function archivedOffsetHours(firstSavedMs, savedMs) {
    const first = finite(firstSavedMs, -1);
    const value = finite(savedMs, -1);
    if (first <= 0 || value < first)
        return -1;
    return (value - first) / 3600000;
}

function analyze(timeline) {
    const snapshots = timeline && Array.isArray(timeline.snapshots)
                    ? timeline.snapshots : [];
    const total = snapshots.length;
    const providers = {};
    const records = {};
    let additions = 0;
    let removals = 0;
    let maxChurn = 0;

    for (let i = 0; i < snapshots.length; i++) {
        const snapshot = snapshots[i] || {};
        const savedAtMs = Math.floor(finite(snapshot.savedAtMs, -1));
        const relations = Array.isArray(snapshot.relations)
                        ? snapshot.relations : [];
        const providerSeen = {};
        const recordSeen = {};

        if (i > 0) {
            const adds = Math.max(0, Number(snapshot.addedCount) || 0);
            const drops = Math.max(0, Number(snapshot.removedCount) || 0);
            additions += adds;
            removals += drops;
            maxChurn = Math.max(maxChurn, adds + drops);
        }

        for (let j = 0; j < relations.length; j++) {
            const row = relations[j] || {};
            const source = text(row.source, 48);
            const key = relationKey(row);
            if (!source || !key)
                continue;

            if (!providerSeen[source]) {
                providerSeen[source] = true;
                if (!providers[source]) {
                    providers[source] = {
                        source: source,
                        firstIndex: i,
                        lastIndex: i,
                        firstSavedMs: savedAtMs,
                        lastSavedMs: savedAtMs,
                        seenSnapshots: 0
                    };
                }
                const provider = providers[source];
                provider.lastIndex = i;
                provider.lastSavedMs = savedAtMs;
                provider.seenSnapshots++;
            }

            if (recordSeen[key])
                continue;
            recordSeen[key] = true;
            if (!records[key]) {
                records[key] = {
                    key: key,
                    source: source,
                    id: text(row.id, 120),
                    title: text(row.title, 180) || "UNTITLED RECORD",
                    mentionOnly: row.mentionOnly === true,
                    firstIndex: i,
                    lastIndex: i,
                    firstSavedMs: savedAtMs,
                    lastSavedMs: savedAtMs,
                    seenSnapshots: 0,
                    relationKinds: {}
                };
            }
            const record = records[key];
            record.lastIndex = i;
            record.lastSavedMs = savedAtMs;
            record.seenSnapshots++;
            const kind = text(row.relationKind, 32);
            if (kind)
                record.relationKinds[kind] = true;
        }
    }

    const firstTimelineMs = total > 0
                          ? Math.floor(finite(snapshots[0].savedAtMs, -1))
                          : -1;
    const providerRows = Object.keys(providers).map(function(source) {
        const row = providers[source];
        return {
            source: row.source,
            firstIndex: row.firstIndex,
            lastIndex: row.lastIndex,
            firstSavedMs: row.firstSavedMs,
            lastSavedMs: row.lastSavedMs,
            firstOffsetHours: archivedOffsetHours(
                firstTimelineMs, row.firstSavedMs
            ),
            lastOffsetHours: archivedOffsetHours(
                firstTimelineMs, row.lastSavedMs
            ),
            seenSnapshots: row.seenSnapshots,
            presenceRatio: total > 0 ? row.seenSnapshots / total : 0,
            current: row.lastIndex === total - 1,
            lifecycle: lifecycleLabel(
                row.firstIndex, row.lastIndex,
                row.seenSnapshots, total
            )
        };
    });

    const recordRows = Object.keys(records).map(function(key) {
        const row = records[key];
        const kinds = Object.keys(row.relationKinds).sort();
        return {
            key: row.key,
            source: row.source,
            id: row.id,
            title: row.title,
            mentionOnly: row.mentionOnly,
            firstIndex: row.firstIndex,
            lastIndex: row.lastIndex,
            firstSavedMs: row.firstSavedMs,
            lastSavedMs: row.lastSavedMs,
            firstOffsetHours: archivedOffsetHours(
                firstTimelineMs, row.firstSavedMs
            ),
            lastOffsetHours: archivedOffsetHours(
                firstTimelineMs, row.lastSavedMs
            ),
            seenSnapshots: row.seenSnapshots,
            presenceRatio: total > 0 ? row.seenSnapshots / total : 0,
            current: row.lastIndex === total - 1,
            relationKinds: kinds,
            lifecycle: lifecycleLabel(
                row.firstIndex, row.lastIndex,
                row.seenSnapshots, total
            )
        };
    });

    providerRows.sort(function(a, b) {
        if (a.firstIndex !== b.firstIndex)
            return a.firstIndex - b.firstIndex;
        return a.source.localeCompare(b.source);
    });

    recordRows.sort(function(a, b) {
        if (a.current !== b.current)
            return a.current ? -1 : 1;
        if (b.presenceRatio !== a.presenceRatio)
            return b.presenceRatio - a.presenceRatio;
        if (a.firstIndex !== b.firstIndex)
            return a.firstIndex - b.firstIndex;
        return a.key.localeCompare(b.key);
    });

    let persistentRecords = 0;
    let droppedRecords = 0;
    let intermittentRecords = 0;
    for (let i = 0; i < recordRows.length; i++) {
        if (recordRows[i].lifecycle === "PERSISTENT")
            persistentRecords++;
        else if (recordRows[i].lifecycle === "INTERMITTENT")
            intermittentRecords++;
        else if (!recordRows[i].current)
            droppedRecords++;
    }

    return {
        providers: providerRows,
        records: recordRows,
        summary: {
            snapshotCount: total,
            providerCount: providerRows.length,
            recordCount: recordRows.length,
            currentProviders: providerRows.filter(function(row) {
                return row.current;
            }).length,
            currentRecords: recordRows.filter(function(row) {
                return row.current;
            }).length,
            persistentRecords: persistentRecords,
            droppedRecords: droppedRecords,
            intermittentRecords: intermittentRecords,
            additions: additions,
            removals: removals,
            totalChurn: additions + removals,
            maxTransitionChurn: maxChurn
        }
    };
}

function offsetLabel(hours) {
    const value = finite(hours, -1);
    if (value < 0)
        return "--";
    if (value < 1)
        return "+" + Math.round(value * 60) + "M";
    return "+" + value.toFixed(value < 10 ? 1 : 0) + "H";
}

function presenceLabel(row, totalSnapshots) {
    if (!row)
        return "";
    const total = Math.max(0, Number(totalSnapshots) || 0);
    return String(row.lifecycle || "UNKNOWN")
         + " // " + Number(row.seenSnapshots || 0)
         + "/" + total + " SNAPSHOTS"
         + " // FIRST " + offsetLabel(row.firstOffsetHours)
         + " // LAST " + offsetLabel(row.lastOffsetHours);
}
