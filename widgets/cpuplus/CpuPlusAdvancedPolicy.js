// Fixed Linux VM observation contract. Read-only; no defaults or write authority.
function paths() {
    return ["vfs_cache_pressure", "dirty_background_ratio", "dirty_background_bytes",
        "dirty_ratio", "dirty_bytes", "dirty_writeback_centisecs", "dirty_expire_centisecs"]
        .map(name => "/proc/sys/vm/" + name);
}
function pair(ratio, bytes) {
    if (ratio > 0 && bytes > 0) return {mode:"INCONSISTENT", ratio:ratio, bytes:bytes};
    if (bytes > 0) return {mode:"BYTES", ratio:ratio, bytes:bytes};
    if (ratio > 0) return {mode:"RATIO", ratio:ratio, bytes:bytes};
    return {mode:"BOTH ZERO", ratio:ratio, bytes:bytes};
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length > 1024) return null;
    const lines = raw.trim().split(/\r?\n/);
    if (lines.length !== paths().length) return null;
    const values = lines.map(line => /^\d{1,16}$/.test(line.trim()) ? Number(line.trim()) : NaN);
    if (values.some(n => !Number.isSafeInteger(n) || n < 0)
        || values[1] > 100 || values[3] > 100) return null;
    return {cachePressure:values[0], background:pair(values[1],values[2]),
        writer:pair(values[3],values[4]), writebackCentisecs:values[5], expireCentisecs:values[6]};
}
function pairLabel(value) {
    if (!value) return "UNAVAILABLE";
    if (value.mode === "RATIO") return value.ratio + "%";
    if (value.mode === "BYTES") return value.bytes + " B";
    return value.mode;
}
function seconds(value) {
    return value === 0 ? "0 s" : (value / 100).toFixed(2) + " s";
}
