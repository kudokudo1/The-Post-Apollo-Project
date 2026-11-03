.pragma library

// COSMOS V2b // Read-only USNO daily event clock.
// Provider's rise / transit / set times are isolated dated events. They do
// NOT encode a continuous planet track, above-horizon duration, zodiac
// longitude, aspect, current azimuth, or retrograde motion.
var FORMAT = "post-apollo.weather.cosmos-planet-clock.v2b.v1";
var PLANETS = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"];
var KINDS = ["rise", "transit", "set"];

function minuteOf(value) {
    if (typeof value !== "string" || !/^\d{2}:\d{2}$/.test(value))
        return null;
    var h = Number(value.slice(0, 2));
    var m = Number(value.slice(3, 5));
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

function clockRows(providerRows, date) {
    var input = Array.isArray(providerRows) ? providerRows : [];
    var dateOk = validDate(date);
    var result = [];
    for (var p = 0; p < PLANETS.length; p++) {
        var name = PLANETS[p], provider = null;
        for (var i = 0; i < input.length; i++) {
            var candidate = input[i];
            if (dateOk && candidate && candidate.name === name
                && candidate.date === date) {
                provider = candidate;
                break;
            }
        }
        var status = provider ? String(provider.status || "UNAVAILABLE")
                              : "NO DATED RESPONSE";
        var events = [];
        if (provider && status === "NORMAL") {
            for (var k = 0; k < KINDS.length; k++) {
                var event = eventFor(provider, KINDS[k], date);
                if (event) events.push(event);
            }
            if (events.length < 3) status = "PARTIAL EVENTS";
        }
        result.push({name:name, status:status, events:events,
                     available:events.length > 0, date:dateOk ? date : ""});
    }
    return result;
}

function eventsFor(planetRow, kind) {
    var events = planetRow && Array.isArray(planetRow.events)
                 ? planetRow.events : [];
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
    return Array.isArray(rows)
        ? rows.filter(function(row) { return row.available; }).length : 0;
}
