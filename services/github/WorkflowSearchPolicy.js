.pragma library

// Local presentation only. Original source indices preserve CONTROL selection.
// Search never invents missing remote records or grants dispatch capability.
function filter(rows, query) {
    if (!Array.isArray(rows)) return [];
    const terms = String(query || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
    const result = [];
    for (let i = 0; i < rows.length; i++) {
        const workflow = rows[i];
        if (!workflow || typeof workflow !== "object") continue;
        const haystack = String(workflow.name || "").toLowerCase() + " " + String(workflow.path || "").toLowerCase();
        if (terms.every(term => haystack.includes(term)))
            result.push({workflow: workflow, sourceIndex: i});
    }
    return result;
}
