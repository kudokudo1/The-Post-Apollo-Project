.pragma library

// Open-Meteo GeoNames lookup M4. User-initiated name queries only.
// This parser never writes the Places registry or silently chooses a result.
const ENDPOINT = "https://geocoding-api.open-meteo.com/v1/search";
const LIMIT = 8;
const MAX_RESPONSE = 65536;

function request(queryRaw) {
    const query = String(queryRaw === null || queryRaw === undefined
                         ? "" : queryRaw).trim();
    if (query.length < 2 || query.length > 80
            || /[\u0000-\u001f\u007f]/.test(query))
        return {ok:false, reason:"QUERY_INVALID"};
    return {ok:true, query:query,
            url:ENDPOINT + "?name=" + encodeURIComponent(query)
                 + "&count=" + LIMIT + "&language=en&format=json"};
}

function cleanLabel(raw, maxLength) {
    if (typeof raw !== "string")
        return "";
    const label = raw.trim();
    if (!label || label.length > maxLength
            || /[\u0000-\u001f\u007f<>]/.test(label))
        return "";
    return label;
}

function coordinate(raw, maxAbs) {
    if (typeof raw !== "number" || !isFinite(raw)
            || Math.abs(raw) > maxAbs)
        return null;
    return Number(raw.toFixed(6));
}

function displayLabel(name, region, country) {
    // Preserve a name that will fit the existing 64-character Home field.
    const parts = [name];
    if (region && region.toLowerCase() !== name.toLowerCase())
        parts.push(region);
    if (country && country.toLowerCase() !== name.toLowerCase())
        parts.push(country);
    const full = parts.join(", ");
    if (full.length <= 64)
        return full;
    const simpler = [name, country].filter(Boolean).join(", ");
    return simpler.length <= 64 ? simpler : name;
}

function parseResponse(rawText) {
    const text = String(rawText === null || rawText === undefined
                        ? "" : rawText);
    if (!text || text.length > MAX_RESPONSE)
        return {ok:false, reason:"RESPONSE_INVALID"};
    let value;
    try {
        value = JSON.parse(text);
    } catch (error) {
        return {ok:false, reason:"JSON_INVALID"};
    }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.error === true)
        return {ok:false, reason:"PROVIDER_ERROR"};
    if (value.results === undefined)
        return {ok:true, rows:[]};
    if (!Array.isArray(value.results))
        return {ok:false, reason:"RESPONSE_INVALID"};

    const rows = [];
    for (let i = 0; i < value.results.length && rows.length < LIMIT; i++) {
        const raw = value.results[i];
        if (!raw || typeof raw !== "object" || Array.isArray(raw))
            continue;
        const name = cleanLabel(raw.name, 64);
        const latitude = coordinate(raw.latitude, 90);
        const longitude = coordinate(raw.longitude, 180);
        if (!name || latitude === null || longitude === null)
            continue;
        const region = cleanLabel(raw.admin1, 64);
        const country = cleanLabel(raw.country, 64);
        const timezone = cleanLabel(raw.timezone, 64);
        const label = displayLabel(name, region, country);
        if (!label || label.length > 64)
            continue;
        rows.push({
            label:label, name:name, region:region, country:country,
            latitude:latitude, longitude:longitude,
            timezone:timezone,
            provider:"OPEN_METEO_GEONAMES"
        });
    }
    return {ok:true, rows:rows};
}
