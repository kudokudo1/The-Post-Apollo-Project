.pragma library

// C41 // Reconcile two different, already-owned USNO observations:
// CelNav: an instantaneous *sample* (may exclude a below-threshold body).
// MRST: source-dated RISE / TRANSIT / SET for the five civil-day lanes.
// The fallback never calls a dated transit altitude "current altitude".
var PLANETS = ["MERCURY","VENUS","MARS","JUPITER","SATURN"];
var KINDS = ["rise","transit","set"];

function list(value, limit) {
    if (!value || typeof value === "string") return [];
    var n = Number(value.length);
    if (!isFinite(n) || n < 0 || n > limit || Math.floor(n) !== n) return [];
    var out = [];
    for (var i=0;i<n;i++) out.push(value[i]);
    return out;
}
function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    var d = new Date(value + "T00:00:00Z");
    return !isNaN(d.valueOf()) && d.toISOString().slice(0,10) === value;
}
function numberDegrees(raw, maximum) {
    if (raw === null || raw === undefined || raw === "") return "--";
    var n = Number(raw);
    return isFinite(n) && n >= -90 && n <= maximum
        ? n.toFixed(1) + "°" : "--";
}
function planetName(row) {
    return row ? String(row.name || "").trim().toUpperCase() : "";
}
function selectedName(requested, currentRecords, datedRows) {
    var name = String(requested || "").toUpperCase();
    if (PLANETS.indexOf(name) >= 0) return name;
    var current = list(currentRecords,32);
    for (var i=0;i<current.length;i++) {
        name = planetName(current[i]);
        if (PLANETS.indexOf(name) >= 0) return name;
    }
    var dated = list(datedRows,5);
    for (var j=0;j<dated.length;j++) {
        name = planetName(dated[j]);
        if (PLANETS.indexOf(name) >= 0 && dated[j].available)
            return name;
    }
    return PLANETS[0];
}
function currentIndex(records, name) {
    var listRecords = list(records,32);
    for (var i=0;i<listRecords.length;i++)
        if (planetName(listRecords[i]) === name) return i;
    return -1;
}
function datedRow(rows, name, date) {
    if (!validDate(date)) return null;
    var listRows = list(rows,5);
    for (var i=0;i<listRows.length;i++) {
        var row=listRows[i];
        if (planetName(row)===name && String(row.date || "")===date)
            return row;
    }
    return null;
}
function event(row, kind, date, name) {
    var events = list(row && row.events,3);
    for (var i=0;i<events.length;i++) {
        var e=events[i];
        if (!e || e.kind!==kind || e.source!=="USNO MRST"
            || e.planet!==name || e.date!==date) continue;
        var t=String(e.clock || "");
        if (!/^\d{2}:\d{2}$/.test(t)) continue;
        if (Number(t.slice(0,2))>23 || Number(t.slice(3,5))>59) continue;
        return e;
    }
    return null;
}
function eventTime(row, kind, date, name) {
    var e=event(row,kind,date,name);
    return e ? String(e.clock) : "--";
}
function selection(requested, records, datedRows, date,
                   currentReady, datedReady, utcSample) {
    var observed = currentReady ? list(records,32) : [];
    var name = selectedName(requested,observed,datedRows);
    var index = currentIndex(observed,name);
    var current = index >= 0 ? observed[index] : null;
    var row = datedReady ? datedRow(datedRows,name,date) : null;
    var info = {
        planet:name,
        mode:"unavailable",
        currentIndex:index,
        currentRecord:current,
        datedRow:row,
        labels:["ALT // HC","AZ // ZN","DIR"],
        values:["--","--","--"],
        sourceNote:"NO USNO DATA",
        stamp:"--",
        detailAvailable:false,
        status:row ? String(row.status || "UNAVAILABLE") : "NO SOURCE DATA"
    };
    if (current) {
        info.mode="current";
        info.values=[
            numberDegrees(current.altitude,90),
            numberDegrees(current.azimuth,360),
            String(current.direction || "--")
        ];
        info.sourceNote="CURRENT FIX";
        info.stamp=String(utcSample || "--") + " UTC";
        info.detailAvailable=true;
    } else if (row) {
        info.mode="dated";
        info.labels=["RISE","TRANSIT","SET"];
        info.values=KINDS.map(function(kind) {
            return eventTime(row,kind,date,name);
        });
        info.sourceNote=info.values.some(function(value){return value!=="--";})
            ? "USNO MRST // DAY" : "USNO MRST // "+info.status;
        info.stamp=date+" LOCAL";
        info.detailAvailable=true;
    } else {
        info.sourceNote=datedReady ? "NO DATED RESPONSE"
                        : currentReady ? "NOT IN CURRENT SAMPLE" : "USNO WAITING";
        info.status=info.sourceNote;
    }
    return info;
}
