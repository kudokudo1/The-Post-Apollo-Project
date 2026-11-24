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

// Preview in the observed unit only. Not an apply validation contract.
function previewSpec(observation, key) {
    if (!observation) return null;
    if (key === "background" || key === "writer") {
        const p = observation[key];
        if (!p || (p.mode !== "BYTES" && p.mode !== "RATIO")) return null;
        return p.mode === "RATIO"
            ? {value:p.ratio, unit:"%", min:1, max:100, step:1, coarse:5}
            : {value:p.bytes, unit:"B", min:1, max:Number.MAX_SAFE_INTEGER, step:1048576, coarse:16777216};
    }
    if (key === "cachePressure") return {value:observation.cachePressure, unit:"RAW", min:0,
        max:Number.MAX_SAFE_INTEGER, step:1, coarse:10};
    if (key === "writebackCentisecs" || key === "expireCentisecs")
        return {value:observation[key], unit:"cs", min:0, max:Number.MAX_SAFE_INTEGER, step:100, coarse:1000};
    return null;
}
function validPreview(spec, value) {
    return !!spec && Number.isSafeInteger(value) && value >= spec.min && value <= spec.max;
}
function previewLabel(spec, value) {
    if (!validPreview(spec, value)) return "UNAVAILABLE";
    return spec.unit === "cs" ? seconds(value)
        : spec.unit === "RAW" ? String(value) : value + (spec.unit === "%" ? "%" : " B");
}
function pairWarning(observation, key, target) {
    if (!observation || (key !== "background" && key !== "writer")) return "";
    const spec = previewSpec(observation,key);
    const other = previewSpec(observation,key === "background" ? "writer" : "background");
    if (!validPreview(spec,target) || !other || other.unit !== spec.unit)
        return "THRESHOLD ORDER // NOT COMPARABLE";
    const background = key === "background" ? target : other.value;
    const writer = key === "writer" ? target : other.value;
    return background >= writer ? "CAUTION // BACKGROUND AT OR ABOVE WRITER" : "";
}
