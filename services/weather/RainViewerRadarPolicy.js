.pragma library

var MERCATOR_LIMIT = 85.05112878;

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function normalizeHistoryMinutes(value) {
    const minutes = Math.round(Number(value));
    if (!isFinite(minutes) || minutes < 0 || minutes > 120)
        return -1;
    return minutes;
}

function safeHost(value) {
    const host = String(value || "").replace(/\/+$/, "");
    return /^https:\/\/(?:[a-z0-9-]+\.)*rainviewer\.com(?::\d+)?$/i.test(host)
           ? host : "";
}

function safeFramePath(value) {
    const path = String(value || "");
    return /^\/v\d+\/radar\/\d+$/.test(path) ? path : "";
}

function parseMetadata(root) {
    if (!root || typeof root !== "object")
        throw new Error("Invalid RainViewer metadata");

    const host = safeHost(root.host);
    if (host === "")
        throw new Error("Unsafe RainViewer tile host");

    const sourceFrames = root.radar && Array.isArray(root.radar.past)
                       ? root.radar.past : [];
    const frames = [];
    for (let i = 0; i < sourceFrames.length; i++) {
        const row = sourceFrames[i] || {};
        const time = Math.round(Number(row.time));
        const path = safeFramePath(row.path);
        if (!isFinite(time) || time <= 0 || path === "")
            continue;
        frames.push({time: time, path: path});
    }
    frames.sort(function(a, b) { return a.time - b.time; });
    if (frames.length === 0)
        throw new Error("No RainViewer past radar frames");

    const keep = frames.slice(Math.max(0, frames.length - 24));
    return {
        host: host,
        generated: Math.max(0, Math.round(Number(root.generated) || 0)),
        frames: keep
    };
}

function selectFrame(frames, minutesAgo) {
    if (!Array.isArray(frames) || frames.length === 0)
        return null;

    const requested = normalizeHistoryMinutes(minutesAgo);
    if (requested < 0)
        return null;

    const latest = frames[frames.length - 1];
    const target = latest.time - requested * 60;
    let best = latest;
    let bestDelta = Math.abs(latest.time - target);
    for (let i = 0; i < frames.length; i++) {
        const row = frames[i];
        const delta = Math.abs(Number(row.time) - target);
        if (delta < bestDelta) {
            best = row;
            bestDelta = delta;
        }
    }

    return {
        time: Number(best.time),
        path: String(best.path),
        requestedMinutes: requested,
        actualMinutes: Math.max(
            0,
            Math.round((Number(latest.time) - Number(best.time)) / 60)
        ),
        latestTime: Number(latest.time)
    };
}

function mercatorY(latitude, zoom) {
    const lat = clamp(Number(latitude), -MERCATOR_LIMIT, MERCATOR_LIMIT);
    const n = Math.pow(2, Number(zoom));
    const rad = lat * Math.PI / 180;
    return (1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI)
           / 2 * n;
}

function mercatorLatitude(tileY, zoom) {
    const n = Math.pow(2, Number(zoom));
    const y = Number(tileY);
    const angle = Math.PI * (1 - 2 * y / n);
    return 180 / Math.PI * Math.atan(Math.sinh(angle));
}

function tileRange(bounds, zoom) {
    if (!bounds || !bounds.valid)
        return {valid: false, reason: "MAP VIEW UNAVAILABLE", count: 0};

    const west = finite(bounds.west);
    const east = finite(bounds.east);
    const north = finite(bounds.north);
    const south = finite(bounds.south);
    const z = Math.round(Number(zoom));
    if (west === null || east === null || north === null || south === null
            || !(west < east) || !(south < north)
            || z < 1 || z > 7) {
        return {valid: false, reason: "RAINVIEWER BOUNDS INVALID", count: 0};
    }

    const n = Math.pow(2, z);
    const westClamped = clamp(west, -180, 180);
    const eastClamped = clamp(east, -180, 180);
    const northClamped = clamp(north, -MERCATOR_LIMIT, MERCATOR_LIMIT);
    const southClamped = clamp(south, -MERCATOR_LIMIT, MERCATOR_LIMIT);
    if (!(westClamped < eastClamped) || !(southClamped < northClamped))
        return {valid: false, reason: "RAINVIEWER VIEW OUTSIDE MERCATOR", count: 0};

    const xStart = clamp(
        Math.floor((westClamped + 180) / 360 * n),
        0, n - 1
    );
    const xEnd = clamp(
        Math.floor(((eastClamped + 180) / 360 * n) - 1e-9),
        0, n - 1
    );
    const yStart = clamp(
        Math.floor(mercatorY(northClamped, z)),
        0, n - 1
    );
    const yEnd = clamp(
        Math.floor(mercatorY(southClamped, z) - 1e-9),
        0, n - 1
    );
    const columns = Math.max(0, xEnd - xStart + 1);
    const rows = Math.max(0, yEnd - yStart + 1);

    return {
        valid: columns > 0 && rows > 0,
        reason: columns > 0 && rows > 0 ? "" : "RAINVIEWER VIEW EMPTY",
        zoom: z,
        xStart: xStart,
        xEnd: xEnd,
        yStart: yStart,
        yEnd: yEnd,
        columns: columns,
        rows: rows,
        count: columns * rows
    };
}

function chooseTileRange(bounds, maxTiles) {
    const limit = Math.max(1, Math.min(24, Math.floor(Number(maxTiles) || 12)));
    let fallback = null;
    for (let z = 7; z >= 1; z--) {
        const range = tileRange(bounds, z);
        if (!range.valid)
            continue;
        fallback = range;
        if (range.count <= limit)
            return range;
    }
    if (fallback && fallback.count <= limit)
        return fallback;
    return {
        valid: false,
        reason: "RAINVIEWER VIEW TOO WIDE",
        count: fallback ? fallback.count : 0
    };
}

function tileUrl(hostValue, framePathValue, zoom, x, y) {
    const host = safeHost(hostValue);
    const framePath = safeFramePath(framePathValue);
    const z = Math.round(Number(zoom));
    const tileX = Math.round(Number(x));
    const tileY = Math.round(Number(y));
    if (host === "" || framePath === ""
            || z < 1 || z > 7
            || !isFinite(tileX) || !isFinite(tileY))
        return "";
    return host + framePath + "/512/" + z + "/"
           + tileX + "/" + tileY + "/2/1_1.png";
}

function buildPlan(bounds, host, framePath, maxTiles, stripCount) {
    const range = chooseTileRange(bounds, maxTiles);
    if (!range.valid)
        return {
            valid: false,
            reason: range.reason,
            zoom: 0,
            tileCount: 0,
            stripCount: 0,
            strips: []
        };

    const stripsPerTile = Math.max(
        1,
        Math.min(8, Math.floor(Number(stripCount) || 4))
    );
    const tileSize = 512;
    const n = Math.pow(2, range.zoom);
    const strips = [];

    for (let y = range.yStart; y <= range.yEnd; y++) {
        for (let x = range.xStart; x <= range.xEnd; x++) {
            const url = tileUrl(host, framePath, range.zoom, x, y);
            if (url === "")
                continue;

            const west = x / n * 360 - 180;
            const east = (x + 1) / n * 360 - 180;
            for (let strip = 0; strip < stripsPerTile; strip++) {
                const topY = y + strip / stripsPerTile;
                const bottomY = y + (strip + 1) / stripsPerTile;
                strips.push({
                    tileKey: range.zoom + "/" + x + "/" + y,
                    url: url,
                    west: west,
                    east: east,
                    north: mercatorLatitude(topY, range.zoom),
                    south: mercatorLatitude(bottomY, range.zoom),
                    sourceY: tileSize * strip / stripsPerTile,
                    sourceHeight: tileSize / stripsPerTile,
                    sourceSize: tileSize
                });
            }
        }
    }

    return {
        valid: strips.length > 0,
        reason: strips.length > 0 ? "" : "RAINVIEWER TILES UNAVAILABLE",
        zoom: range.zoom,
        tileCount: range.count,
        stripCount: strips.length,
        strips: strips
    };
}
