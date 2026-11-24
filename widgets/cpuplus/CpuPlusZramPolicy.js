// Read-only compression observation and UI preview. Not device authority.
function parseAlgorithms(raw) {
    if (typeof raw !== "string" || raw.length > 4096) return null;
    const tokens = raw.trim().split(/\s+/);
    if (!tokens.length || tokens.length > 64) return null;
    const options = [];
    let actual = null;
    for (const token of tokens) {
        const match = token.match(/^(?:\[([A-Za-z0-9_-]{1,64})\]|([A-Za-z0-9_-]{1,64}))$/);
        if (!match) return null;
        const name = match[1] || match[2];
        if (options.includes(name)) return null;
        options.push(name);
        if (match[1]) {
            if (actual !== null) return null;
            actual = name;
        }
    }
    return actual === null ? null : {actual:actual, options:options};
}
function activeDevices(sample) {
    if (!sample || !Array.isArray(sample.rows)) return [];
    const rows = sample.rows.filter(row => row && typeof row.name === "string"
        && /^\/dev\/zram[0-9]{1,6}$/.test(row.name));
    if (rows.some((row,i) => !Number.isSafeInteger(row.size) || row.size <= 0
        || rows.findIndex(other => other.name === row.name) !== i)) return [];
    return rows;
}
function observedDevice(sample, name, size) {
    return activeDevices(sample).find(row => row.name === name && row.size === size) || null;
}
function algorithmPath(name) {
    return typeof name === "string" && /^\/dev\/zram[0-9]{1,6}$/.test(name)
        ? "/sys/block/" + name.slice(5) + "/comp_algorithm" : null;
}
