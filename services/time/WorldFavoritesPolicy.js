.pragma library

// Persist an operator-curated list of WORLD timezone IDs, not a second
// timezone engine and never an instruction to change the host clock.
var VERSION = 1;
var MAX_FAVORITES = 8;

function validZone(zoneId) {
    return typeof zoneId === "string"
           && zoneId.length <= 100
           && (zoneId === "UTC"
               || /^[A-Za-z][A-Za-z0-9._+-]*(?:\/[A-Za-z0-9._+-]+)+$/.test(zoneId));
}

function initialDocument() {
    return {version: VERSION, zones: []};
}

function validate(zones) {
    if (!Array.isArray(zones) || zones.length > MAX_FAVORITES)
        return {ok: false, reason: "INVALID_FAVORITES"};
    var seen = {};
    for (var i = 0; i < zones.length; i++) {
        if (!validZone(zones[i]) || seen[zones[i]])
            return {ok: false, reason: "INVALID_ZONE_OR_DUPLICATE"};
        seen[zones[i]] = true;
    }
    return {ok: true, zones: zones.slice()};
}

function parse(raw) {
    var data;
    try {
        data = JSON.parse(String(raw));
    } catch (error) {
        return {ok: false, reason: "INVALID_JSON"};
    }
    if (!data || typeof data !== "object" || Array.isArray(data))
        return {ok: false, reason: "INVALID_DOCUMENT"};
    if (data.version !== VERSION)
        return {ok: false, reason: "UNSUPPORTED_VERSION"};
    var validation = validate(data.zones);
    if (!validation.ok) return validation;
    return {ok: true, document: {version: VERSION, zones: validation.zones}};
}

function contains(zones, zoneId) {
    return validZone(zoneId) && Array.isArray(zones)
           && zones.indexOf(zoneId) !== -1;
}

function toggle(zones, zoneId) {
    var validation = validate(zones);
    if (!validation.ok)
        return validation;
    if (!validZone(zoneId))
        return {ok: false, reason: "INVALID_ZONE"};
    var next = validation.zones;
    var index = next.indexOf(zoneId);
    var saved = false;
    if (index >= 0) {
        next.splice(index, 1);
    } else {
        if (next.length >= MAX_FAVORITES)
            return {ok: false, reason: "FAVORITES_FULL"};
        next.push(zoneId);
        saved = true;
    }
    return {
        ok: true,
        added: saved,
        document: {version: VERSION, zones: next}
    };
}
