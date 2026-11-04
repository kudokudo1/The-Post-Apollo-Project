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

// Visual reference symbols only. Planet names remain explicit for legibility
// and font fallback; this does not encode physical/ecliptic positions.
var PLANET_GLYPHS = {
    MERCURY:"☿", VENUS:"♀", MARS:"♂", JUPITER:"♃", SATURN:"♄"
};
function planetLabel(name) {
    var id = String(name || "").toUpperCase();
    return Object.prototype.hasOwnProperty.call(PLANET_GLYPHS, id)
        ? PLANET_GLYPHS[id] + " " + id : id;
}

// Flat chronological inspection of source-backed event points; never a
// simulated trajectory between rise, transit and set. Use the same selected
// planet/kind gates as the visible markers.
function orderedEvents(planetRows, selectedPlanet, selectedKind) {
    var rows = indexedRows(planetRows), output = [];
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        if (!row || (selectedPlanet !== "ALL" && row.name !== selectedPlanet))
            continue;
        var markers = eventsFor(row, selectedKind);
        for (var j = 0; j < markers.length; j++) {
            var e = markers[j];
            if (e && typeof e.id === "string"
                && boundedNumber(e.minute, 0, 1439) !== null)
                output.push(e);
        }
    }
    output.sort(function(a, b) {
        if (a.minute !== b.minute) return a.minute - b.minute;
        if (a.planet !== b.planet)
            return PLANETS.indexOf(a.planet) - PLANETS.indexOf(b.planet);
        return KINDS.indexOf(a.kind) - KINDS.indexOf(b.kind);
    });
    return output;
}
function stepEvent(events, current, direction) {
    var list = indexedRows(events);
    if (!list.length || (direction !== 1 && direction !== -1)) return null;
    var id = current && typeof current.id === "string" ? current.id : "";
    var index = -1;
    for (var i = 0; i < list.length; i++)
        if (list[i] && list[i].id === id) { index = i; break; }
    if (index < 0) return direction > 0 ? list[0] : list[list.length-1];
    return list[(index + direction + list.length) % list.length];
}
function eventOrdinal(events, current) {
    var list = indexedRows(events), id = current && current.id;
    for (var i = 0; i < list.length; i++)
        if (list[i] && list[i].id === id) return (i+1) + "/" + list.length;
    return "—/" + list.length;
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

// V2d // Pure, bounded local-day viewport geometry. Zoom changes the
// displayed scale, never the source record or source time. A hidden marker
// is not a missing provider event.
var WINDOW_HOURS = [6, 12, 24];

function viewportSpan(hours) {
    var value = Number(hours);
    return WINDOW_HOURS.indexOf(value) >= 0 ? value * 60 : 1440;
}

function clampViewStart(start, span) {
    var s = Number(span), n = Number(start);
    if (!isFinite(s) || s < 1 || s > 1440) return 0;
    if (!isFinite(n)) n = 0;
    return Math.max(0, Math.min(1440 - s, Math.round(n)));
}

function zoomStart(start, previousSpan, nextSpan, focusMinute) {
    var oldSpan = Number(previousSpan), span = Number(nextSpan);
    if (!isFinite(oldSpan) || oldSpan <= 0 || oldSpan > 1440 ||
        !isFinite(span) || span <= 0 || span > 1440)
        return 0;
    var oldStart = clampViewStart(start, oldSpan);
    var focus = boundedNumber(focusMinute, 0, 1440);
    if (focus === null) focus = oldStart + oldSpan / 2;
    var ratio = Math.max(0, Math.min(1, (focus - oldStart) / oldSpan));
    return clampViewStart(focus - ratio * span, span);
}

function panStart(start, span, dragPixels, plotWidth) {
    var distance = Number(dragPixels), width = Number(plotWidth);
    if (!isFinite(distance) || !isFinite(width) || width <= 0)
        return clampViewStart(start, span);
    return clampViewStart(Number(start) - (distance / width) * span, span);
}

function inWindow(minute, start, span) {
    var m = boundedNumber(minute, 0, 1439);
    var width = Number(span);
    if (m === null || !isFinite(width) || width <= 0 || width > 1440)
        return false;
    var from = clampViewStart(start, width);
    return m >= from && m < from + width;
}

function visibleEvents(row, kind, start, span) {
    return eventsFor(row, kind).filter(function(e) {
        return e && inWindow(e.minute, start, span);
    });
}

// Marker LEFT EDGE, with space for its entire clickable shell.
// The matching ruler uses the same 0..1 source-minute fraction.
function viewX(minute, start, span, laneWidth, markerWidth) {
    if (!inWindow(minute, start, span)) return null;
    var width = Number(laneWidth), marker = Number(markerWidth);
    if (!isFinite(width) || !isFinite(marker)
        || width <= marker + 2 || marker < 1) return null;
    var from = clampViewStart(start, span);
    return 1 + (Number(minute) - from) / Number(span) * (width - marker - 2);
}

function rulerX(index, laneWidth, markerWidth) {
    var i = Number(index), width = Number(laneWidth);
    var marker = Number(markerWidth);
    if (!isFinite(i) || i < 0 || i > 4
        || !isFinite(width) || !isFinite(marker)
        || marker < 1 || width <= marker + 2) return null;
    return 1 + marker / 2 + i / 4 * (width - marker - 2);
}

function localMinuteLabel(value) {
    var m = Number(value);
    if (!isFinite(m) || m < 0 || m > 1440) return "--:--";
    var min = Math.round(m);
    return String(Math.floor(min / 60)).padStart(2, "0") + ":"
           + String(min % 60).padStart(2, "0");
}

function rulerTicks(start, span) {
    var width = Number(span);
    if (!isFinite(width) || width <= 0 || width > 1440) return [];
    var from = clampViewStart(start, width), result = [];
    for (var i = 0; i <= 4; i++) {
        var minute = from + i * width / 4;
        result.push({minute:minute, label:localMinuteLabel(minute)});
    }
    return result;
}

function revealStart(eventMinute, start, span) {
    var minute = boundedNumber(eventMinute, 0, 1439);
    if (minute === null) return clampViewStart(start, span);
    if (inWindow(minute, start, span)) return clampViewStart(start, span);
    return clampViewStart(minute - Number(span) / 2, span);
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
