.pragma library

// Diff only successful, authoritative Room Report list results. An initial
// Room read establishes a silent baseline; listing is not proof of an
// approved handoff, operator approval, or report content verification.
function initial() { return {}; }
function reportIds(rows) {
    if (!Array.isArray(rows))
        return null;
    const out = [];
    const seen = {};
    for (let i = 0; i < rows.length && i < 50; ++i) {
        const row = rows[i] || {};
        const id = String(row.id || "").trim();
        if (!id || seen[id])
            continue;
        seen[id] = true;
        out.push(id);
    }
    return out;
}
function advance(previous, room, rows) {
    const old = previous || initial();
    const key = String(room || "").trim();
    const ids = reportIds(rows);
    if (!key || ids === null)
        return { state: old, addedCount: 0 };
    const before = old[key];
    const now = {};
    for (const id of ids) now[id] = true;
    const next = Object.assign({}, old);
    next[key] = now;
    if (before === undefined)
        return { state: next, addedCount: 0 };
    let added = 0;
    for (const id of ids)
        if (!before[id]) added++;
    return { state: next, addedCount: added };
}
