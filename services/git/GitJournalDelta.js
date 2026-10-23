// Bounded journal overlay. All disk writes remain synchronous/atomic in QML.
// The legacy checkpoint's entry order is newest-first. Mutating an existing
// record never moves it; adding a new one prepends it.
function requireRecord(row) {
    if (!row || typeof row !== "object" || Array.isArray(row)
            || typeof row.id !== "string" || !row.id.trim())
        throw new Error("INVALID JOURNAL DELTA RECORD");
    return row;
}

function upsert(rows, record) {
    requireRecord(record);
    const input = Array.isArray(rows) ? rows : [];
    const next = input.slice();
    for (let i = 0; i < next.length; ++i) {
        if (String((next[i] || {}).id || "") === record.id) {
            next[i] = record;
            return next;
        }
    }
    next.push(record);
    return next;
}

function overlay(base, deltas, limit) {
    const list = Array.isArray(base) ? base.slice() : [];
    const changes = Array.isArray(deltas) ? deltas : [];
    const cap = Number(limit);
    if (!Number.isSafeInteger(cap) || cap < 1)
        throw new Error("INVALID JOURNAL RETENTION LIMIT");

    const seen = Object.create(null);
    for (let i = 0; i < changes.length; ++i) {
        const record = requireRecord(changes[i]);
        if (seen[record.id])
            throw new Error("DUPLICATE JOURNAL DELTA ID");
        seen[record.id] = true;
        const index = list.findIndex(function(existing) {
            return String((existing || {}).id || "") === record.id;
        });
        if (index >= 0)
            list[index] = record;
        else
            list.unshift(record);
    }
    if (list.length > cap)
        list.length = cap;
    return list;
}

function checkGeneration(value) {
    if (!Number.isSafeInteger(value) || value < 0)
        throw new Error("INVALID JOURNAL CHECKPOINT GENERATION");
    return value;
}

function readSidecar(raw, checkpointGeneration) {
    const generation = checkGeneration(checkpointGeneration);
    const source = String(raw || "").trim();
    if (!source)
        return { rows: [], stale: false, present: false };
    let parsed;
    try {
        parsed = JSON.parse(source);
    } catch (error) {
        throw new Error("MALFORMED JOURNAL DELTA JSON");
    }
    if (!parsed || parsed.deltaVersion !== 1
            || !Array.isArray(parsed.records))
        throw new Error("UNKNOWN JOURNAL DELTA FORMAT");
    const basedOn = checkGeneration(parsed.baseGeneration);
    const seen = Object.create(null);
    for (let i = 0; i < parsed.records.length; ++i) {
        const record = requireRecord(parsed.records[i]);
        if (seen[record.id])
            throw new Error("DUPLICATE JOURNAL DELTA ID");
        seen[record.id] = true;
    }
    // After a checkpoint is written, an older sidecar can remain until its
    // own atomic clear. This one-step stale overlay is already incorporated.
    if (basedOn === generation - 1)
        return { rows: [], stale: true, present: true };
    if (basedOn !== generation)
        throw new Error("JOURNAL DELTA CHECKPOINT MISMATCH");
    return { rows: parsed.records, stale: false, present: true };
}

function encodeSidecar(checkpointGeneration, rows) {
    checkGeneration(checkpointGeneration);
    const input = Array.isArray(rows) ? rows : [];
    for (let i = 0; i < input.length; ++i)
        requireRecord(input[i]);
    return JSON.stringify({
        deltaVersion: 1,
        baseGeneration: checkpointGeneration,
        records: input
    });
}


// Cache JSON for unchanged immutable operation records. Each journal mutation
// replaces its record object, so reference equality is the reuse boundary.
// The on-disk sidecar remains byte-for-byte compatible with encodeSidecar().
function encodeSidecarCached(checkpointGeneration, rows, previous) {
    const generation = checkGeneration(checkpointGeneration);
    const input = Array.isArray(rows) ? rows : [];
    const old = Array.isArray(previous) ? previous : [];
    const known = Object.create(null);
    for (let i = 0; i < old.length; ++i) {
        const item = old[i];
        if (item && typeof item.id === "string" && item.id)
            known[item.id] = item;
    }

    const payloads = [];
    const cache = [];
    let reusedCount = 0;
    for (let i = 0; i < input.length; ++i) {
        const record = requireRecord(input[i]);
        const prior = known[record.id];
        const reuse = Boolean(prior && prior.record === record
            && typeof prior.text === "string");
        const encoded = reuse ? prior.text : JSON.stringify(record);
        if (typeof encoded !== "string")
            throw new Error("INVALID JOURNAL DELTA RECORD // CANNOT SERIALIZE");
        payloads.push(encoded);
        cache.push({ id: record.id, record: record, text: encoded });
        if (reuse)
            reusedCount += 1;
    }

    return {
        text: '{"deltaVersion":1,"baseGeneration":'
            + JSON.stringify(generation)
            + ',"records":[' + payloads.join(",") + ']}',
        cache: cache,
        reusedCount: reusedCount
    };
}
