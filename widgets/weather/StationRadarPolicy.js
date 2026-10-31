.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function boundedArea(bounds, maxLongitudeSpan, maxLatitudeSpan) {
    if (!bounds || !bounds.valid)
        return {valid: false, reason: "MAP VIEW UNAVAILABLE", bbox: ""};

    const west = finite(bounds.west);
    const south = finite(bounds.south);
    const east = finite(bounds.east);
    const north = finite(bounds.north);
    if (west === null || south === null || east === null || north === null
            || west < -180 || east > 180 || south < -90 || north > 90
            || !(west < east) || !(south < north)) {
        return {valid: false, reason: "MAP BOUNDS INVALID", bbox: ""};
    }

    const lonSpan = east - west;
    const latSpan = north - south;
    const lonLimit = Number(maxLongitudeSpan);
    const latLimit = Number(maxLatitudeSpan);
    if (!isFinite(lonLimit) || !isFinite(latLimit)
            || lonLimit <= 0 || latLimit <= 0)
        return {valid: false, reason: "REQUEST LIMIT INVALID", bbox: ""};

    if (lonSpan > lonLimit + 1e-9 || latSpan > latLimit + 1e-9) {
        return {
            valid: false,
            reason: "ZOOM IN // VIEW TOO WIDE",
            bbox: "",
            longitudeSpan: lonSpan,
            latitudeSpan: latSpan
        };
    }

    return {
        valid: true,
        reason: "",
        bbox: [west, south, east, north]
            .map(function(value) { return Number(value).toFixed(5); })
            .join(","),
        west: west,
        south: south,
        east: east,
        north: north,
        longitudeSpan: lonSpan,
        latitudeSpan: latSpan
    };
}

function normalizeHistoryMinutes(value) {
    const minutes = Math.round(Number(value));
    if (!isFinite(minutes) || minutes <= 0)
        return 0;
    return Math.min(240, Math.max(0, minutes));
}

function historyTimeMillis(nowValue, minutesAgo) {
    const now = Number(nowValue);
    const minutes = normalizeHistoryMinutes(minutesAgo);
    if (!isFinite(now) || now <= 0 || minutes <= 0)
        return 0;

    // MRMS history is updated on an approximately ten-minute cadence.
    // Snap to that cadence so manual historical requests are stable.
    const cadenceMs = 10 * 60 * 1000;
    const roundedNow = Math.floor(now / cadenceMs) * cadenceMs;
    return roundedNow - minutes * 60 * 1000;
}

function historyOptions() {
    return [
        {minutes: 0, label: "NOW"},
        {minutes: 30, label: "-30M"},
        {minutes: 60, label: "-1H"},
        {minutes: 120, label: "-2H"},
        {minutes: 240, label: "-4H"}
    ];
}

function exportImageUrl(area, widthValue, heightValue, timeMillis) {
    if (!area || !area.valid || !area.bbox)
        return "";

    const width = Math.round(Number(widthValue));
    const height = Math.round(Number(heightValue));
    if (!isFinite(width) || !isFinite(height)
            || width < 64 || height < 64
            || width > 1600 || height > 1200)
        return "";

    const endpoint =
        "https://mapservices.weather.noaa.gov/eventdriven/rest/services/"
        + "radar/radar_base_reflectivity_time/ImageServer/exportImage";

    const requestedTime = Number(timeMillis);
    const timePart = isFinite(requestedTime) && requestedTime > 0
                   ? "&time=" + Math.round(requestedTime)
                   : "";

    return endpoint
        + "?bbox=" + area.bbox
        + "&bboxSR=4326"
        + "&size=" + width + "," + height
        + "&imageSR=4326"
        + "&format=png32"
        + "&transparent=true"
        + "&adjustAspectRatio=false"
        + timePart
        + "&f=image";
}

function snapshot(bounds) {
    if (!bounds || !bounds.valid)
        return null;
    const west = finite(bounds.west);
    const south = finite(bounds.south);
    const east = finite(bounds.east);
    const north = finite(bounds.north);
    if (west === null || south === null || east === null || north === null
            || !(west < east) || !(south < north))
        return null;
    return {
        valid: true,
        west: west,
        south: south,
        east: east,
        north: north
    };
}
