.pragma library

function numberOr(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function timeMs(value) {
    const text = String(value || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z)?$/.test(text))
        return -1;
    const millis = Date.parse(text.endsWith("Z") ? text : text + "Z");
    return isFinite(millis) && millis > 0 ? millis : -1;
}

function timeLabel(value) {
    const millis = timeMs(value);
    if (millis <= 0)
        return "-- UTC";
    const iso = new Date(millis).toISOString();
    return iso.slice(5, 10) + " " + iso.slice(11, 13) + "Z";
}

function parseKpHistory(root, limit) {
    if (!Array.isArray(root))
        throw new Error("Invalid Kp history");

    const rows = [];
    for (let i = 0; i < root.length; i++) {
        const item = root[i] || {};
        const kp = numberOr(item.Kp, -1);
        const stamp = timeMs(item.time_tag);
        if (kp < 0 || kp > 9 || stamp <= 0)
            continue;
        rows.push({
            time: String(item.time_tag || ""),
            timeMs: stamp,
            timeLabel: timeLabel(item.time_tag),
            kp: kp,
            level: Math.max(0, Math.min(1, kp / 9)),
            aRunning: numberOr(item.a_running, -1),
            stationCount: numberOr(item.station_count, -1)
        });
    }

    rows.sort(function(a, b) { return a.timeMs - b.timeMs; });

    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(64, Math.floor(requested)) : 24;
    const trend = rows.slice(Math.max(0, rows.length - size));
    if (trend.length === 0)
        throw new Error("No valid Kp history");

    let maxKp = -1;
    let sumKp = 0;
    let activeBins = 0;
    let stormBins = 0;
    let minStationCount = Infinity;
    for (let i = 0; i < trend.length; i++) {
        const row = trend[i];
        maxKp = Math.max(maxKp, row.kp);
        sumKp += row.kp;
        if (row.kp >= 4)
            activeBins++;
        if (row.kp >= 5)
            stormBins++;
        if (row.stationCount >= 0)
            minStationCount = Math.min(minStationCount, row.stationCount);
    }

    const latest = trend[trend.length - 1];
    const previous = trend.length >= 2 ? trend[trend.length - 2] : null;

    return {
        latest: latest,
        rows: trend,
        summary: {
            bins: trend.length,
            hours: trend.length * 3,
            maxKp: maxKp,
            averageKp: sumKp / trend.length,
            activeBins: activeBins,
            stormBins: stormBins,
            latestDelta: previous ? latest.kp - previous.kp : 0,
            latestA: latest.aRunning,
            latestStationCount: latest.stationCount,
            minStationCount: isFinite(minStationCount) ? minStationCount : -1
        }
    };
}
