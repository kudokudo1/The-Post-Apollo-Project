.pragma library

// NOAA GOES XRS event records report observed peak X-ray classes, not a
// continuously sampled X-ray flux, a flare forecast, or an SWPC alert.
function parseTime(value) {
    if (typeof value !== "string"
            || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value))
        return -1;
    const time = Date.parse(value);
    return isFinite(time) && time > 0 ? time : -1;
}

function parseClass(value) {
    if (typeof value !== "string")
        return null;
    const match = value.trim().toUpperCase().match(/^([ABCMX])(\d+(?:\.\d+)?)$/);
    if (!match)
        return null;
    const strength = Number(match[2]);
    if (!isFinite(strength) || strength <= 0)
        return null;
    return {
        label: match[1] + match[2],
        letter: match[1],
        strength: strength
    };
}

function utcLabel(timeMs) {
    if (!isFinite(timeMs) || timeMs <= 0)
        return "-- UTC";
    const date = new Date(timeMs);
    return isFinite(date.getTime())
           ? date.toISOString().slice(5, 16).replace("T", " ") + " UTC"
           : "-- UTC";
}

function parseFlares(payload, nowMs) {
    if (!Array.isArray(payload))
        throw new Error("Invalid GOES X-ray flare feed");

    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0)
        throw new Error("Invalid receive clock");

    const list = [];
    const seen = {};
    for (let i = 0; i < payload.length; i++) {
        const record = payload[i];
        if (!record || typeof record !== "object")
            continue;

        const flare = parseClass(record.max_class);
        const peakMs = parseTime(record.max_time);
        if (!flare || peakMs < 0 || peakMs > now + 300000)
            continue;

        const satellite = Number(record.satellite);
        const satelliteLabel = Number.isInteger(satellite)
                               && satellite > 0 ? "GOES-" + satellite : "GOES --";
        const key = satelliteLabel + "/" + peakMs;
        if (seen[key])
            continue;
        seen[key] = true;

        const startMs = parseTime(record.begin_time);
        const endMs = parseTime(record.end_time);
        list.push({
            classLabel: flare.label,
            classLetter: flare.letter,
            peakMs: peakMs,
            peakUtc: utcLabel(peakMs),
            satellite: satelliteLabel,
            beginUtc: utcLabel(startMs),
            endUtc: utcLabel(endMs),
            ended: endMs > 0,
            flux: typeof record.max_xrlong === "number"
                  && isFinite(record.max_xrlong) && record.max_xrlong >= 0
                  ? record.max_xrlong : -1
        });
    }
    list.sort(function(a, b) { return b.peakMs - a.peakMs; });

    const recent = list.filter(function(entry) {
        return entry.peakMs >= now - 86400000 && entry.peakMs <= now;
    });
    const significant = recent.filter(function(entry) {
        return entry.classLetter === "C" || entry.classLetter === "M"
               || entry.classLetter === "X";
    });

    return {
        latest: list.length ? list[0] : null,
        events: list.slice(0, 3),
        count24h: recent.length,
        cPlus24h: significant.length
    };
}
