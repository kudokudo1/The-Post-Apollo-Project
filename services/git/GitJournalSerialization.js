// Pure JSON encoder. Disk durability belongs to GitOperationJournalService.
function serializeJournal(schemaVersion, entries, previous) {
    const known = Object.create(null);
    const cachedRows = Array.isArray(previous) ? previous : [];
    for (let i = 0; i < cachedRows.length; ++i) {
        const entry = cachedRows[i];
        if (entry && entry.id)
            known[entry.id] = entry;
    }
    const source = Array.isArray(entries) ? entries : [];
    const payloads = [];
    const next = [];
    let reusedCount = 0;

    for (let i = 0; i < source.length; ++i) {
        const record = source[i];
        const id = String((record || {}).id || "");
        const cache = id ? known[id] : null;
        const reused = Boolean(cache && cache.record === record);
        const encoded = reused ? cache.text : JSON.stringify(record);
        if (typeof encoded !== "string")
            throw new Error("INVALID JOURNAL RECORD // CANNOT SERIALIZE");
        if (reused)
            reusedCount += 1;
        payloads.push(encoded);
        next.push({ id: id, record: record, text: encoded });
    }

    return {
        text: '{"schemaVersion":' + JSON.stringify(schemaVersion)
            + ',"entries":[' + payloads.join(",") + ']}',
        cache: next,
        reusedCount: reusedCount
    };
}
