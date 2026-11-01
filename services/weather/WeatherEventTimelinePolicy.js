.pragma library

// Read-only longitudinal analysis over operator-saved event dossiers.
//
// Event identity is intentionally strict: one timeline means the exact same
// source + source event ID. Cross-provider relationships remain context and
// are never promoted into a shared event identity by this policy.

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

function anchorKey(anchor) {
    if (!anchor)
        return "";
    const source = text(anchor.source, 48);
    const id = text(anchor.id, 120);
    if (!source || !id)
        return "";
    return source + "|" + id;
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

function uniqueSorted(values) {
    const seen = {};
    const out = [];
    const rows = Array.isArray(values) ? values : [];
    for (let i = 0; i < rows.length; i++) {
        const value = text(rows[i], 80);
        if (!value || seen[value])
            continue;
        seen[value] = true;
        out.push(value);
    }
    out.sort();
    return out;
}

function relationState(relations) {
    const rows = Array.isArray(relations) ? relations : [];
    const records = {};
    const sources = {};
    let mentions = 0;
    let timeSpace = 0;
    let spaceOnly = 0;

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i] || {};
        const key = relationKey(row);
        if (key)
            records[key] = true;
        const source = text(row.source, 48);
        if (source)
            sources[source] = true;

        const kind = text(row.relationKind, 32).toUpperCase();
        if (row.mentionOnly === true || kind === "MENTION NEARBY")
            mentions++;
        else if (kind === "TIME + SPACE")
            timeSpace++;
        else if (kind === "SPACE ONLY")
            spaceOnly++;
    }

    return {
        recordKeys: Object.keys(records).sort(),
        sources: Object.keys(sources).sort(),
        relationCount: Object.keys(records).length,
        mentionCount: mentions,
        timeSpaceCount: timeSpace,
        spaceOnlyCount: spaceOnly
    };
}

function difference(nextValues, previousValues) {
    const previous = {};
    const before = Array.isArray(previousValues) ? previousValues : [];
    const after = Array.isArray(nextValues) ? nextValues : [];
    for (let i = 0; i < before.length; i++)
        previous[String(before[i])] = true;
    const result = [];
    for (let i = 0; i < after.length; i++) {
        const value = String(after[i]);
        if (!previous[value])
            result.push(value);
    }
    return result;
}

function matchingDossiers(document, anchor, limit) {
    const key = anchorKey(anchor);
    if (!key || !document || !Array.isArray(document.dossiers))
        return [];

    const matches = [];
    for (let i = 0; i < document.dossiers.length; i++) {
        const dossier = document.dossiers[i];
        if (!dossier || anchorKey(dossier.anchor) !== key)
            continue;
        const savedAtMs = Math.floor(finite(dossier.savedAtMs, -1));
        if (savedAtMs <= 0)
            continue;
        matches.push(dossier);
    }
    matches.sort(function(a, b) {
        return Number(a.savedAtMs) - Number(b.savedAtMs);
    });

    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(128, Math.floor(requested)) : 24;
    if (matches.length <= size)
        return matches;
    return matches.slice(matches.length - size);
}

function timelineForAnchor(document, anchor, limit) {
    const key = anchorKey(anchor);
    const dossiers = matchingDossiers(document, anchor, limit);
    const snapshots = [];
    let previous = null;
    const allSources = {};
    let maxRelations = 0;

    for (let i = 0; i < dossiers.length; i++) {
        const dossier = dossiers[i];
        const state = relationState(dossier.relations);
        for (let j = 0; j < state.sources.length; j++)
            allSources[state.sources[j]] = true;

        const addedSources = previous
            ? difference(state.sources, previous.sources) : state.sources.slice();
        const removedSources = previous
            ? difference(previous.sources, state.sources) : [];
        const addedRecords = previous
            ? difference(state.recordKeys, previous.recordKeys) : state.recordKeys.slice();
        const removedRecords = previous
            ? difference(previous.recordKeys, state.recordKeys) : [];

        maxRelations = Math.max(maxRelations, state.relationCount);
        snapshots.push({
            id: text(dossier.id, 220),
            savedAtMs: Math.floor(finite(dossier.savedAtMs, -1)),
            anchor: dossier.anchor,
            relationCount: state.relationCount,
            sources: state.sources,
            sourceCount: state.sources.length,
            mentionCount: state.mentionCount,
            timeSpaceCount: state.timeSpaceCount,
            spaceOnlyCount: state.spaceOnlyCount,
            addedSources: addedSources,
            removedSources: removedSources,
            addedRecords: addedRecords,
            removedRecords: removedRecords,
            addedCount: addedRecords.length,
            removedCount: removedRecords.length,
            relationDelta: previous
                ? state.relationCount - previous.relationCount : 0,
            baseline: previous === null
        });
        previous = state;
    }

    const firstSavedMs = snapshots.length > 0 ? snapshots[0].savedAtMs : -1;
    const lastSavedMs = snapshots.length > 0
                      ? snapshots[snapshots.length - 1].savedAtMs : -1;
    const spanHours = firstSavedMs > 0 && lastSavedMs >= firstSavedMs
                    ? (lastSavedMs - firstSavedMs) / 3600000 : 0;

    return {
        anchorKey: key,
        anchor: anchor || null,
        snapshots: snapshots,
        summary: {
            snapshotCount: snapshots.length,
            firstSavedMs: firstSavedMs,
            lastSavedMs: lastSavedMs,
            spanHours: spanHours,
            uniqueSources: Object.keys(allSources).length,
            maxRelations: maxRelations
        }
    };
}

function sourceTransitionLabel(snapshot) {
    if (!snapshot)
        return "";
    const added = Array.isArray(snapshot.addedSources)
                ? snapshot.addedSources : [];
    const removed = Array.isArray(snapshot.removedSources)
                  ? snapshot.removedSources : [];
    if (snapshot.baseline)
        return added.length > 0
             ? "BASE SOURCES // " + added.join(" / ")
             : "BASE SOURCES // NONE";
    const parts = [];
    if (added.length > 0)
        parts.push("+ " + added.join(" / "));
    if (removed.length > 0)
        parts.push("- " + removed.join(" / "));
    return parts.length > 0 ? parts.join(" // ") : "SOURCE SET UNCHANGED";
}

function recordTransitionLabel(snapshot) {
    if (!snapshot)
        return "";
    if (snapshot.baseline)
        return "BASELINE // " + Number(snapshot.relationCount || 0)
             + " RELATED RECORDS";
    return "RECORDS +" + Number(snapshot.addedCount || 0)
         + " / -" + Number(snapshot.removedCount || 0)
         + " // TOTAL " + Number(snapshot.relationCount || 0)
         + " // Δ "
         + (Number(snapshot.relationDelta || 0) > 0 ? "+" : "")
         + Number(snapshot.relationDelta || 0);
}
