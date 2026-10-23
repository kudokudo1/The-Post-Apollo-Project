.pragma library

// NOAA SWPC OVATION 30-90 minute model. This summarizes the HIGHEST cell in
// each hemisphere; it is not a local observation or visibility forecast.
function parseOvation(root) {
    if (!root || !Array.isArray(root.coordinates)
            || root.coordinates.length === 0)
        throw new Error("No OVATION grid");

    const observed = Date.parse(String(root["Observation Time"] || ""));
    const valid = Date.parse(String(root["Forecast Time"] || ""));
    if (!isFinite(observed) || !isFinite(valid) || observed <= 0
            || valid <= observed)
        throw new Error("Invalid OVATION forecast times");

    let northPeak = -1;
    let southPeak = -1;
    let northCells = 0;
    let southCells = 0;

    const grid = root.coordinates;
    for (let i = 0; i < grid.length; i++) {
        const point = grid[i];
        if (!Array.isArray(point) || point.length < 3)
            continue;
        // Null or blank cells must never be reported as zero probability.
        if (point[0] === null || point[1] === null || point[2] === null
                || point[0] === "" || point[1] === "" || point[2] === "")
            continue;
        const longitude = Number(point[0]);
        const latitude = Number(point[1]);
        const intensity = Number(point[2]);
        if (!isFinite(longitude) || longitude < 0 || longitude > 359
                || !isFinite(latitude) || latitude < -90 || latitude > 90
                || !isFinite(intensity) || intensity < 0 || intensity > 100)
            continue;

        if (latitude > 0) {
            northCells++;
            northPeak = Math.max(northPeak, intensity);
        } else if (latitude < 0) {
            southCells++;
            southPeak = Math.max(southPeak, intensity);
        }
    }
    if (northCells === 0 || southCells === 0)
        throw new Error("Incomplete OVATION hemispheres");

    return {
        observationTimeMs: observed,
        forecastTimeMs: valid,
        northPeak: northPeak,
        southPeak: southPeak,
        northCells: northCells,
        southCells: southCells
    };
}

function utcLabel(timeMs) {
    if (!isFinite(timeMs) || timeMs <= 0)
        return "-- UTC";
    const date = new Date(timeMs);
    if (!isFinite(date.getTime()))
        return "-- UTC";
    return date.toISOString().slice(11, 16) + " UTC";
}
