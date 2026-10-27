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

function exportImageUrl(area, widthValue, heightValue) {
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

    return endpoint
        + "?bbox=" + area.bbox
        + "&bboxSR=4326"
        + "&size=" + width + "," + height
        + "&imageSR=4326"
        + "&format=png32"
        + "&transparent=true"
        + "&adjustAspectRatio=false"
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
