.pragma library

// TimeW zone directory parser/search. Caller supplies a trusted system
// tzdata listing; this pure helper never launches a process or writes data.
var MAX_ZONES = 1200;
var MAX_RESULTS = 6;

// Keep only well-formed IANA zone IDs. These are later checked for membership
// in the listing before they can become the existing date process's TZ env.
function validZone(id) {
    return typeof id === "string"
           && (id === "UTC"
               || /^[A-Za-z][A-Za-z0-9._+-]*(?:\/[A-Za-z0-9._+-]+)+$/.test(id));
}

function parseCatalog(text) {
    if (typeof text !== "string")
        return [];
    var seen = {};
    var output = [];
    var rows = text.split(/\r?\n/);
    for (var i = 0; i < rows.length && output.length < MAX_ZONES; i++) {
        var id = rows[i].trim();
        if (validZone(id) && !seen[id]) {
            seen[id] = true;
            output.push(id);
        }
    }
    output.sort();
    return output;
}

function contains(catalog, zoneId) {
    return validZone(zoneId) && Array.isArray(catalog)
           && catalog.indexOf(zoneId) !== -1;
}

function label(id) {
    return typeof id === "string" ? id.replace(/_/g, " ") : "";
}

function cityName(id) {
    if (typeof id !== "string")
        return "";
    return label(id.slice(id.lastIndexOf("/") + 1));
}

function normalize(value) {
    return String(value).toLowerCase()
           .replace(/[\/_-]+/g, " ")
           .replace(/\s+/g, " ").trim();
}

function search(catalog, query, limit) {
    if (!Array.isArray(catalog) || typeof query !== "string")
        return [];
    var needle = normalize(query);
    if (!needle || needle.length > 100)
        return [];

    var max = typeof limit === "number" && isFinite(limit)
              ? Math.max(0, Math.min(MAX_RESULTS, Math.floor(limit)))
              : MAX_RESULTS;
    if (max === 0)
        return [];

    var scored = [];
    for (var i = 0; i < catalog.length; i++) {
        var id = catalog[i];
        if (!validZone(id))
            continue;
        var full = normalize(id);
        var city = normalize(cityName(id));
        var score = -1;
        if (full === needle || city === needle)
            score = 0;
        else if (city.indexOf(needle) === 0)
            score = 1;
        else if (full.indexOf(needle) === 0)
            score = 2;
        else if (city.indexOf(needle) !== -1)
            score = 3;
        else if (full.indexOf(needle) !== -1)
            score = 4;
        else {
            // Also match searches such as "america new" or "new york",
            // without interpreting user input as a regular expression.
            var tokens = needle.split(" ");
            if (tokens.every(function(token) { return full.indexOf(token) !== -1; }))
                score = 5;
        }
        if (score >= 0)
            scored.push({ id: id, label: label(id), rank: score });
    }
    scored.sort(function(a, b) {
        return a.rank - b.rank || a.label.localeCompare(b.label);
    });
    return scored.slice(0, max);
}
