.pragma library

// TimeW zone directory parser/search. Caller supplies a trusted system
// tzdata listing; this pure helper never launches a process or writes data.
var MAX_ZONES = 1200;
// The ListView virtualizes rows, so searches can expose the full bounded catalog.
var MAX_RESULTS = MAX_ZONES;

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

// Country-name metadata from system tzdata (read by the QML adapter).
function parseCountryNames(text) {
    var output = {};
    if (typeof text !== "string") return output;
    var lines = text.split(/\r?\n/);
    for (var i = 0; i < lines.length && i < 1000; i++) {
        if (!lines[i] || lines[i].charAt(0) === "#") continue;
        var fields = lines[i].split("\t");
        var code = fields[0];
        var name = fields.slice(1).join(" ").trim();
        if (/^[A-Z]{2}$/.test(code) && name.length > 0 && name.length <= 120)
            output[code] = name;
    }
    return output;
}

function parseCountryZones(text, countries) {
    var output = {};
    if (typeof text !== "string" || !countries || typeof countries !== "object")
        return output;
    var lines = text.split(/\r?\n/);
    for (var i = 0; i < lines.length && i < 1600; i++) {
        if (!lines[i] || lines[i].charAt(0) === "#") continue;
        var fields = lines[i].split("\t");
        if (fields.length < 3 || !validZone(fields[2])) continue;
        var id = fields[2], codes = fields[0].split(","), matched = [], seen = {};
        for (var j = 0; j < codes.length; j++) {
            var code = codes[j];
            if (/^[A-Z]{2}$/.test(code) && typeof countries[code] === "string"
                    && !seen[code]) {
                matched.push({code: code, name: countries[code]});
                seen[code] = true;
            }
        }
        if (matched.length > 0) output[id] = matched;
    }
    return output;
}

function search(catalog, query, limit, countryIndex) {
    if (!Array.isArray(catalog) || typeof query !== "string")
        return [];
    var needle = normalize(query);
    if (needle.length > 100)
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
        var score = needle === "" ? 0 : -1;
        var countryList = countryIndex && Array.isArray(countryIndex[id])
                          ? countryIndex[id] : [];
        var countryMatched = -1;
        for (var k = 0; k < countryList.length; k++) {
            var country = normalize(countryList[k].name);
            var code = normalize(countryList[k].code);
            if (country === needle || code === needle)
                countryMatched = 0;
            else if (country.indexOf(needle) === 0
                     && (countryMatched < 0 || countryMatched > 1))
                countryMatched = 1;
            else if (country.indexOf(needle) !== -1
                     && (countryMatched < 0 || countryMatched > 2))
                countryMatched = 2;
        }
        if (!needle) {
            // Browse all installed zones. Country-first sorting below
            // makes the empty-query directory more useful to navigate.
            score = 0;
        } else if (full === needle || city === needle)
            score = 0;
        else if (city.indexOf(needle) === 0)
            score = 1;
        else if (countryMatched === 0)
            score = 2;
        else if (countryMatched === 1)
            score = 3;
        else if (full.indexOf(needle) === 0)
            score = 4;
        else if (city.indexOf(needle) !== -1)
            score = 5;
        else if (countryMatched === 2)
            score = 6;
        else if (full.indexOf(needle) !== -1)
            score = 7;
        else {
            // Also match searches such as "america new" or "new york",
            // without interpreting user input as a regular expression.
            var tokens = needle.split(" ");
            if (tokens.every(function(token) { return full.indexOf(token) !== -1; }))
                score = 8;
        }
        if (score >= 0)
            scored.push({
                id: id, label: label(id), rank: score,
                country: countryList.length > 0 ? countryList[0].name : ""
            });
    }
    scored.sort(function(a, b) {
        if (!needle) {
            // Country groups first. Zones without a country mapping remain
            // browseable at the end (UTC, Etc/* and other system aliases).
            var countryA = a.country || "\uffff";
            var countryB = b.country || "\uffff";
            var countryCompare = countryA.localeCompare(countryB);
            if (countryCompare !== 0) return countryCompare;
        }
        return a.rank - b.rank || a.label.localeCompare(b.label);
    });
    return scored.slice(0, max);
}
