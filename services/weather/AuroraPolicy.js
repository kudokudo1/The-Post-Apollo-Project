.pragma library

// NOAA SWPC OVATION 30-90 minute model. This summarizes the HIGHEST cell in
// each hemisphere; it is not a local observation or visibility forecast.
function validTarget(latitudeValue, longitudeValue) {
    if (latitudeValue === undefined || latitudeValue === null
            || longitudeValue === undefined || longitudeValue === null
            || latitudeValue === "" || longitudeValue === "")
        return null;
    const latitude = Number(latitudeValue);
    const longitude = Number(longitudeValue);
    if (!isFinite(latitude) || !isFinite(longitude)
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    return { latitude: latitude, longitude: longitude };
}

function signedLongitude(value) {
    const longitude = Number(value);
    if (!isFinite(longitude))
        return NaN;
    return longitude > 180 ? longitude - 360 : longitude;
}

function wrappedLongitudeDelta(a, b) {
    let delta = Number(a) - Number(b);
    while (delta > 180)
        delta -= 360;
    while (delta < -180)
        delta += 360;
    return delta;
}

function distanceKm(latA, lonA, latB, lonB) {
    const values = [latA, lonA, latB, lonB].map(Number);
    if (values.some(function(value) { return !isFinite(value); }))
        return -1;
    const rad = Math.PI / 180;
    const dLat = (values[2] - values[0]) * rad;
    const dLon = wrappedLongitudeDelta(values[3], values[1]) * rad;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
            + Math.cos(values[0] * rad) * Math.cos(values[2] * rad)
              * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(
        Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a))
    );
}

function parseOvation(root, targetLatitude, targetLongitude) {
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

    const target = validTarget(targetLatitude, targetLongitude);
    let localIntensity = -1;
    let localLatitude = NaN;
    let localLongitude = NaN;
    let localDistanceKm = Infinity;

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

        if (target) {
            const signedLon = signedLongitude(longitude);
            const distance = distanceKm(
                target.latitude, target.longitude,
                latitude, signedLon
            );
            if (distance >= 0 && distance < localDistanceKm) {
                localDistanceKm = distance;
                localLatitude = latitude;
                localLongitude = signedLon;
                localIntensity = intensity;
            }
        }

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
        southCells: southCells,
        localReady: !!target && localIntensity >= 0
                    && isFinite(localDistanceKm),
        localIntensity: localIntensity,
        localLatitude: isFinite(localLatitude) ? localLatitude : 0,
        localLongitude: isFinite(localLongitude) ? localLongitude : 0,
        localDistanceKm: isFinite(localDistanceKm) ? localDistanceKm : -1
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
