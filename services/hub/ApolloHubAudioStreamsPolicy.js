.pragma library

// P3-B: read-only, bounded view of Team 6 PipeWire sink-input evidence.
// A stream is NOT a stable application, window or tab identity.
// This policy does not poll, discover applications, send commands or
// create persistent mute/volume policies.
var MAX_STREAMS = 16;
var MAX_LABEL = 68;

function validIndex(index) {
    return typeof index === "number" && isFinite(index)
        && Math.floor(index) === index && index >= 0
        && index <= 2147483647;
}
function trimLabel(value) {
    return typeof value === "string"
        ? value.replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0,MAX_LABEL) : "";
}
function key(value) {
    return typeof value === "string"
        ? value.slice(0,128) : "";
}
function identity(input) {
    if (!input || !validIndex(input.index))
        return "";
    const p = input.properties || {};
    const fields = [
        key(p["application.process.id"]),
        key(p["application.process.binary"]),
        key(p["application.id"]),
        key(p["application.name"]),
        key(p["media.name"])
    ];
    // Empty/generic evidence must not authorize a guessed stream target.
    if (!fields.some(function(v) { return v.trim().length > 0; }))
        return "";
    return JSON.stringify([input.index].concat(fields));
}
function volume(input) {
    const channels = input && input.volume;
    if (!channels || typeof channels !== "object")
        return -1;
    const keys = Object.keys(channels);
    let total = 0, count = 0;
    for (let i = 0; i < keys.length; i++) {
        const c = channels[keys[i]];
        const raw = c && c.value_percent;
        const match = typeof raw === "string"
                      ? /^(\d+(?:\.\d+)?)%$/.exec(raw.trim()) : null;
        if (!match) continue;
        const n = Number(match[1]);
        if (isFinite(n) && n >= 0) {
            total += n; count++;
        }
    }
    return count ? Math.round(total / count) : -1;
}
function snapshot(inputs, generation, loading, error) {
    const blank = {source:"team6-sink-inputs",state:"unavailable",
                   generation:0,total:0,shown:0,truncated:false,items:[]};
    if (typeof error === "string" && error.trim())
        return Object.assign({},blank,{state:"error"});
    if (!Array.isArray(inputs) || !Number.isSafeInteger(generation)
            || generation < 1)
        return Object.assign({},blank,{state:loading === true
                                      ? "refreshing" : "unavailable"});
    const items = [];
    const seen = Object.create(null);
    let total = 0;
    for (let i = 0; i < inputs.length; i++) {
        const input = inputs[i];
        const id = identity(input);
        if (!id || seen[String(input.index)]) continue;
        seen[String(input.index)] = true;
        total++;
        if (items.length >= MAX_STREAMS) continue;
        const props = input.properties || {};
        const app = trimLabel(props["application.name"])
                    || trimLabel(props["application.process.binary"])
                    || "UNNAMED STREAM";
        const media = trimLabel(props["media.name"]);
        items.push({index:input.index, identity:id,
                    label:app, media:media, muted:input.mute === true,
                    volumePercent:volume(input)});
    }
    return {source:"team6-sink-inputs",
            state:loading === true ? "refreshing"
                 : total === 0 ? "empty" : "ready",
            generation:generation,total:total,shown:items.length,
            truncated:total > items.length,items:items};
}
function findExact(inputs, index, fingerprint) {
    if (!Array.isArray(inputs) || !validIndex(index)
            || typeof fingerprint !== "string"
            || fingerprint.length > 768 || fingerprint.length === 0)
        return null;
    for (let i = 0; i < inputs.length; i++) {
        const input = inputs[i];
        if (input && input.index === index
                && identity(input) === fingerprint)
            return input;
    }
    return null;
}
