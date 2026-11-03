.pragma library

// COSMOS V2b // Read-only USNO daily event clock.
// Provider's rise / transit / set times are isolated dated events. They do
// NOT encode a continuous planet track, above-horizon duration, zodiac
// longitude, aspect, current azimuth, or retrograde motion.
var FORMAT = "post-apollo.weather.cosmos-planet-clock.v2b.v1";
var PLANETS = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"];
var KINDS = ["rise", "transit", "set"];

function minuteOf(value) {
    // A QML property var can carry a QString-like value across a component
    // boundary. Parse its text, but still reject anything except exact HH:MM.
    var clock = value === null || value === undefined ? "" : String(value);
    if (!/^\d{2}:\d{2}$/.test(clock)) return null;
    var h = Number(clock.slice(0, 2));
    var m = Number(clock.slice(3, 5));
    return h < 24 && m < 60 ? h * 60 + m : null;
}

function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    var d = new Date(value + "T00:00:00Z");
    return !isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === value;
}

function boundedNumber(value, low, high) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return isFinite(n) && n >= low && n <= high ? n : null;
}

function eventFor(row, kind, date) {
    var minute = minuteOf(row && row[kind]);
    if (minute === null) return null;
    var name = String(row.name || "").toUpperCase();
    var data = {id:date + "|" + name + "|" + kind + "|" + minute,
                planet:name, kind:kind, minute:minute,
                clock:row[kind], date:date, source:"USNO MRST",
                altitude:null, azimuth:null, hemisphere:""};
    if (kind === "transit") {
        data.altitude = boundedNumber(row.transitAltitude, 0, 90);
        data.hemisphere = row.transitHemisphere === "N"
                          || row.transitHemisphere === "S"
                          ? row.transitHemisphere : "";
    } else {
        data.azimuth = boundedNumber(row[kind + "Azimuth"], 0, 360);
    }
    return data;
}

function indexedRows(value) {
    // QQmlListProperty / QVariantList style values can be indexed and used
    // by Repeater even when Array.isArray(value) is false in another scope.
    // Reject unbounded, string or non-indexed inputs instead of guessing.
    if (!value || typeof value === "string") return [];
    var count = Number(value.length);
    if (!isFinite(count) || count < 0 || count > 32
        || Math.floor(count) !== count) return [];
    var result = [];
    for (var i = 0; i < count; i++) result.push(value[i]);
    return result;
}

function clockRows(providerRows, date) {
    var input = indexedRows(providerRows);
    var requestedDate = date === null || date === undefined ? "" : String(date);
    var dateOk = validDate(requestedDate);
    var result = [];
    for (var p = 0; p < PLANETS.length; p++) {
        var name = PLANETS[p], provider = null;
        for (var i = 0; i < input.length; i++) {
            var candidate = input[i];
            if (dateOk && candidate
                && String(candidate.name || "").trim().toUpperCase() === name
                && String(candidate.date || "") === requestedDate) {
                provider = candidate;
                break;
            }
        }
        var status = provider ? String(provider.status || "UNAVAILABLE").trim()
                              : "NO DATED RESPONSE";
        var events = [];
        if (provider && status === "NORMAL") {
            for (var k = 0; k < KINDS.length; k++) {
                var event = eventFor(provider, KINDS[k], requestedDate);
                if (event) events.push(event);
            }
            if (events.length < 3) status = "PARTIAL EVENTS";
        }
        result.push({name:name, status:status, events:events,
                     available:events.length > 0, date:dateOk ? requestedDate : ""});
    }
    return result;
}

function eventsFor(planetRow, kind) {
    var events = planetRow ? indexedRows(planetRow.events) : [];
    return kind === "ALL" ? events.slice()
                         : events.filter(function(e) { return e.kind === kind; });
}

function selectedEvent(locked, hovered) {
    return locked && typeof locked.id === "string" ? locked
         : hovered && typeof hovered.id === "string" ? hovered : null;
}

function timeX(minute, width) {
    var m = boundedNumber(minute, 0, 1439);
    var w = boundedNumber(width, 1, 100000);
    return m === null || w === null ? null : m / 1440 * w;
}

function eventDetail(event) {
    if (!event || KINDS.indexOf(event.kind) < 0) return "SELECT AN EVENT MARKER";
    var detail = event.planet + " // " + event.kind.toUpperCase()
               + " " + event.clock + " LOCAL";
    if (event.kind === "transit" && event.altitude !== null)
        detail += " // ALT " + event.altitude + "°"
                  + (event.hemisphere || "");
    if (event.kind !== "transit" && event.azimuth !== null)
        detail += " // AZ " + event.azimuth + "° TRUE N";
    return detail;
}

function rowCountWithEvents(rows) {
    return indexedRows(rows)
        .filter(function(row) { return row && row.available; }).length;
}
