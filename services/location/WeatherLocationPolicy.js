.pragma library

// M5: the user's Place Registry owns selected coordinates, not the
// availability or geolocation response of an external weather provider.
// Return null for unconfigured/invalid user coordinates, never (0,0) by
// coercing blank fields.
function manualPoint(place) {
    if (!place || typeof place !== "object" || Array.isArray(place)
            || place.source !== "MANUAL")
        return null;
    const lat = place.latitude;
    const lon = place.longitude;
    if (typeof lat !== "number" || typeof lon !== "number"
            || !isFinite(lat) || !isFinite(lon)
            || lat < -90 || lat > 90 || lon < -180 || lon > 180)
        return null;
    return {latitude:Number(lat.toFixed(6)),
            longitude:Number(lon.toFixed(6))};
}

function requestContextKey(place, legacyLocation) {
    const selected = manualPoint(place);
    if (selected)
        return "MANUAL|" + selected.latitude + "|" + selected.longitude;
    return "LEGACY|" + String(legacyLocation || "").trim();
}

function locationQuery(place, legacyLocation) {
    const selected = manualPoint(place);
    if (selected)
        return selected.latitude + "," + selected.longitude;
    return String(legacyLocation || "").trim();
}

function coordinates(place, providerLatitude, providerLongitude) {
    const selected = manualPoint(place);
    if (selected)
        return {latitude:String(selected.latitude),
                longitude:String(selected.longitude)};
    // Legacy fallback is deliberately strict. Empty coordinates must not
    // become false zero, and a single missing axis is not a valid point.
    const latitude = String(providerLatitude === null
                            || providerLatitude === undefined
                            ? "" : providerLatitude).trim();
    const longitude = String(providerLongitude === null
                             || providerLongitude === undefined
                             ? "" : providerLongitude).trim();
    if (latitude === "" || longitude === ""
            || !/^[-+]?\d+(?:\.\d+)?$/.test(latitude)
            || !/^[-+]?\d+(?:\.\d+)?$/.test(longitude))
        return {latitude:"", longitude:""};
    const lat = Number(latitude);
    const lon = Number(longitude);
    if (!isFinite(lat) || !isFinite(lon)
            || lat < -90 || lat > 90 || lon < -180 || lon > 180)
        return {latitude:"", longitude:""};
    return {latitude:String(lat), longitude:String(lon)};
}
