// ForestW read-only projection of B1 session metadata. PRESENTATION ONLY.
// A verified native host must authorize identity, database custody, Tree scope
// and session read BEFORE passing records into QML. Parsing cannot grant trust.
function openSessions(records, treeKey) {
    if (!Array.isArray(records) || records.length > 100
            || typeof treeKey !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(treeKey))
        return [];
    const allowed = ["session_id", "tree_key", "title", "state", "revision",
                     "created_at_ms", "updated_at_ms"];
    const ids = Object.create(null);
    const result = [];
    for (let i = 0; i < records.length; i++) {
        const row = records[i];
        if (!row || typeof row !== "object" || Array.isArray(row))
            return [];
        const fields = Object.keys(row);
        if (fields.length !== allowed.length
                || fields.some(k => allowed.indexOf(k) < 0))
            return []; // refuse content bodies, owner keys and unknown fields
        const validKey = v => typeof v === "string"
            && /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(v);
        const validMs = v => typeof v === "number" && isFinite(v)
            && Math.floor(v) === v && v > 0 && v <= Number.MAX_SAFE_INTEGER;
        if (!validKey(row.session_id) || !validKey(row.tree_key)
                || typeof row.title !== "string" || !row.title
                || row.title.length > 160 || /[\x00-\x1f\x7f]/.test(row.title)
                || ["OPEN", "PAUSED", "ARCHIVED"].indexOf(row.state) < 0
                || typeof row.revision !== "number" || !isFinite(row.revision)
                || Math.floor(row.revision) !== row.revision
                || row.revision < 0 || row.revision > Number.MAX_SAFE_INTEGER
                || !validMs(row.created_at_ms) || !validMs(row.updated_at_ms)
                || row.updated_at_ms < row.created_at_ms
                || ids[row.session_id])
            return []; // fail the complete snapshot, not individual rows
        ids[row.session_id] = true;
        if (row.tree_key === treeKey && row.state === "OPEN")
            result.push({ session_id: row.session_id, title: row.title,
                          revision: row.revision, updated_at_ms: row.updated_at_ms });
    }
    result.sort((a, b) => b.updated_at_ms - a.updated_at_ms
                 || a.session_id.localeCompare(b.session_id));
    return result;
}
