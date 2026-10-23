.pragma library

// NOAA GOES primary 6-hour 1-minute samples. Long-band soft X-ray flux is
// an instantaneous observed irradiance, NOT an officially detected flare.
function numeric(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const number = Number(value);
    return isFinite(number) ? number : -1;
}

function timeValue(value) {
    if (typeof value !== "string" ||
            !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z)?$/.test(value))
        return -1;
    const ms = Date.parse(value.endsWith("Z") ? value : value + "Z");
    return isFinite(ms) && ms > 0 ? ms : -1;
}

function fluxClass(flux) {
    const value = numeric(flux);
    if (value <= 0)
        return {letter: "", label: "--"};
    let letter, base;
    if (value >= 1e-4) { letter = "X"; base = 1e-4; }
    else if (value >= 1e-5) { letter = "M"; base = 1e-5; }
    else if (value >= 1e-6) { letter = "C"; base = 1e-6; }
    else if (value >= 1e-7) { letter = "B"; base = 1e-7; }
    else { letter = "A"; base = 1e-8; }
    return {letter: letter, label: letter + (value / base).toFixed(1)};
}

function utcTime(timeMs) {
    if (!isFinite(timeMs) || timeMs <= 0)
        return "-- UTC";
    return new Date(timeMs).toISOString().slice(11, 16) + " UTC";
}

// Logarithmic display only. 0.1-0.8nm powers of ten range A/B/C/M/X.
// The meter is NOT an official severity scale.
function logMeter(flux) {
    const value = numeric(flux);
    if (value <= 0)
        return 0;
    return Math.max(0, Math.min(1, (Math.log(value) / Math.LN10 + 9) / 5));
}

function parseXraySeries(payload, nowMs) {
    if (!Array.isArray(payload))
        throw new Error("Invalid GOES X-ray stream");
    const now = numeric(nowMs);
    if (now <= 0)
        throw new Error("Invalid receive time");

    const longBand = [];
    const shortBand = [];
    for (let i = 0; i < payload.length; ++i) {
        const row = payload[i];
        if (!row || typeof row !== "object")
            continue;
        if (row.energy !== "0.1-0.8nm" && row.energy !== "0.05-0.4nm")
            continue;
        const timeMs = timeValue(row.time_tag);
        const flux = numeric(row.flux);
        const satellite = numeric(row.satellite);
        if (timeMs < now - 8 * 3600000 || timeMs > now + 300000 ||
                flux <= 0 || flux > 1 ||
                !Number.isInteger(satellite) || satellite <= 0)
            continue;
        const entry = {timeMs: timeMs, flux: flux, satellite: satellite};
        if (row.energy === "0.1-0.8nm")
            longBand.push(entry);
        else
            shortBand.push(entry);
    }

    longBand.sort(function(a, b) { return a.timeMs - b.timeMs; });
    shortBand.sort(function(a, b) { return a.timeMs - b.timeMs; });
    if (longBand.length === 0)
        throw new Error("No valid 0.1-0.8nm readings");

    const latest = longBand[longBand.length - 1];
    let shortLatest = null;
    for (let i = shortBand.length - 1; i >= 0; --i) {
        if (shortBand[i].satellite === latest.satellite &&
                Math.abs(shortBand[i].timeMs - latest.timeMs) <= 300000) {
            shortLatest = shortBand[i];
            break;
        }
    }

    // Downsample six hours into 30-minute buckets. One actual sample per
    // bucket, maximum 12 bars. Do not fabricate a smoother time series.
    const buckets = {};
    const from = latest.timeMs - 6 * 3600000;
    for (let i = 0; i < longBand.length; ++i) {
        const point = longBand[i];
        if (point.satellite !== latest.satellite || point.timeMs < from)
            continue;
        // Include the newest sample in the final bucket rather than
        // dropping the exact six-hour endpoint at bucket 12.
        const bucket = Math.min(11, Math.floor((point.timeMs - from) / 1800000));
        if (bucket >= 0)
            buckets[bucket] = point;
    }
    const trend = [];
    for (let i = 0; i < 12; ++i) {
        if (buckets[i])
            trend.push({timeMs: buckets[i].timeMs,
                        flux: buckets[i].flux,
                        level: logMeter(buckets[i].flux),
                        classLetter: fluxClass(buckets[i].flux).letter});
    }

    return {
        fluxLong: latest.flux,
        fluxShort: shortLatest ? shortLatest.flux : -1,
        satellite: "GOES-" + latest.satellite,
        sampleTimeMs: latest.timeMs,
        sampleUtc: utcTime(latest.timeMs),
        classEquivalent: fluxClass(latest.flux),
        trend: trend
    };
}
