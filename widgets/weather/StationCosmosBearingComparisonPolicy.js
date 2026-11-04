.pragma library

// COSMOS V3c // Angular separation of TWO independent, dated USNO
// local-horizon rise OR set azimuths. This is not ecliptic longitude,
// geocentric/heliocentric separation, orbital alignment or astrology.
var FORMAT = "post-apollo.weather.cosmos-bearing-comparison.v3c.v1";
var PLANETS = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"];
var KINDS = ["rise", "set"];

function azimuth(value) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return isFinite(n) && n >= 0 && n <= 360 ? n % 360 : null;
}

function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    var d = new Date(value + "T00:00:00Z");
    return !isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === value;
}

function list(value) {
    if (!value || typeof value === "string") return [];
    var length = Number(value.length);
    if (!isFinite(length) || length < 0 || length > 10
        || Math.floor(length) !== length) return [];
    var out = [];
    for (var i = 0; i < length; i++) out.push(value[i]);
    return out;
}

function bearing(markers, name, kind, date) {
    if (PLANETS.indexOf(name) < 0 || KINDS.indexOf(kind) < 0
        || !validDate(date)) return null;
    var source = list(markers);
    for (var i = 0; i < source.length; i++) {
        var item = source[i], angle = item ? azimuth(item.azimuth) : null;
        if (item && angle !== null && item.planet === name
            && item.kind === kind && item.date === date
            && item.source === "USNO MRST"
            && typeof item.id === "string" && item.id.length > 0
            && /^\d{2}:\d{2}$/.test(String(item.time || ""))) {
            return {id:item.id, planet:name, kind:kind, date:date,
                    azimuth:angle, clock:item.time, source:"USNO MRST"};
        }
    }
    return null;
}

function signedGap(a, b) {
    var aa = azimuth(a), bb = azimuth(b);
    if (aa === null || bb === null) return null;
    // [-180, 180), with a deterministic positive 180° half-turn.
    var signed = ((bb - aa + 540) % 360) - 180;
    return signed === -180 ? 180 : signed;
}

function compare(markers, date, planetA, planetB, kind) {
    var blank = {ready:false, reason:"NO MATCHING DATED USNO BEARINGS",
                 eventA:null,eventB:null,gap:null,direction:"",
                 signed:null,kind:kind,date:date};
    if (!validDate(date)) {
        blank.reason = "CIVIL DATE UNAVAILABLE";
        return blank;
    }
    if (PLANETS.indexOf(planetA) < 0 || PLANETS.indexOf(planetB) < 0
        || planetA === planetB || KINDS.indexOf(kind) < 0) {
        blank.reason = "SELECT TWO DIFFERENT PLANETS AND RISE OR SET";
        return blank;
    }
    var a = bearing(markers, planetA, kind, date),
        b = bearing(markers, planetB, kind, date);
    if (!a || !b) return blank;
    var signed = signedGap(a.azimuth, b.azimuth);
    var gap = Math.abs(signed);
    var direction = gap === 0 ? "SAME BEARING"
                  : gap === 180 ? "HALF TURN"
                  : signed > 0 ? "CLOCKWISE" : "COUNTERCLOCKWISE";
    return {ready:true,reason:"",eventA:a,eventB:b,gap:gap,
            direction:direction,signed:signed,kind:kind,date:date,
            source:"USNO MRST",frame:"TRUE-NORTH AZIMUTH"};
}

// Canvas theta: zero is E and positive angles run clockwise on screen.
// Mapping azimuth 0=N, 90=E, 180=S, 270=W preserves geographic bearings.
function theta(az) {
    var value = azimuth(az);
    return value === null ? null : (value - 90) * Math.PI / 180;
}

function point(az, cx, cy, radius) {
    var angle = theta(az), x = Number(cx), y = Number(cy),
        r = Number(radius);
    if (angle === null || !isFinite(x) || !isFinite(y)
        || !isFinite(r) || r <= 0) return null;
    return {x:x + r*Math.cos(angle), y:y + r*Math.sin(angle)};
}

function pickSide(result, x, y, cx, cy, radius, tolerance) {
    if (!result || !result.ready) return "";
    var px=Number(x),py=Number(y),tol=Number(tolerance);
    if (!isFinite(px) || !isFinite(py) || !isFinite(tol)
        || tol <= 0 || tol > 30) return "";
    var a = point(result.eventA.azimuth,cx,cy,radius),
        b = point(result.eventB.azimuth,cx,cy,radius);
    var da=(a.x-px)*(a.x-px)+(a.y-py)*(a.y-py),
        db=(b.x-px)*(b.x-px)+(b.y-py)*(b.y-py);
    var threshold=tol*tol;
    if (Math.min(da,db)>threshold) return "";
    return da<=db ? "A" : "B";
}

function eventLabel(event) {
    if (!event) return "EVENT UNAVAILABLE";
    return event.planet + " // " + event.kind.toUpperCase()
        + " " + event.clock + " LOCAL // "
        + event.azimuth + "° TRUE N";
}
