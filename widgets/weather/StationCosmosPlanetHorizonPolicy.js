.pragma library

// COSMOS V3a // Read-only bearings from validated USNO dated event records.
// 0 degrees is TRUE NORTH; positive azimuth rotates clockwise toward east.
// A rise or set bearing is a single event direction, NOT a planet's current
// position, continuous apparent track, orbital coordinate, or zodiac aspect.
var FORMAT = "post-apollo.weather.cosmos-horizon-compass.v3a.v1";
var PLANETS = ["MERCURY","VENUS","MARS","JUPITER","SATURN"];
var KINDS = ["rise","set"];

function bounded(value, low, high) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return isFinite(n) && n >= low && n <= high ? n : null;
}

function indexed(value, max) {
    if (!value || typeof value === "string") return [];
    var length = Number(value.length);
    if (!isFinite(length) || Math.floor(length) !== length
            || length < 0 || length > max) return [];
    var out = [];
    for (var i=0;i<length;i++) out.push(value[i]);
    return out;
}

function acceptedRow(row) {
    return row && PLANETS.indexOf(String(row.name || "")) >= 0
        && row.available === true
        && typeof row.date === "string"
        && /^\d{4}-\d{2}-\d{2}$/.test(row.date);
}

function markers(rows, selectedPlanet) {
    var source = indexed(rows,5), out = [];
    for (var i=0;i<source.length;i++) {
        var row = source[i];
        if (!acceptedRow(row)
                || (selectedPlanet !== "ALL" && row.name !== selectedPlanet))
            continue;
        var events = indexed(row.events,3);
        for (var j=0;j<events.length;j++) {
            var event = events[j];
            if (!event || KINDS.indexOf(event.kind) < 0
                    || event.planet !== row.name || event.date !== row.date
                    || event.source !== "USNO MRST")
                continue;
            var az = bounded(event.azimuth,0,360);
            if (az === null) continue;
            out.push({id:event.id,planet:row.name,kind:event.kind,
                      azimuth:az,time:event.clock,date:row.date,
                      source:event.source});
        }
    }
    return out;
}

function transits(rows) {
    var source = indexed(rows,5), out = [];
    for (var p=0;p<PLANETS.length;p++) {
        var name=PLANETS[p], row=null;
        for(var i=0;i<source.length;i++)
            if(source[i] && source[i].name===name) {row=source[i];break;}
        var altitude=null, at="--", hemi="", date="";
        if(acceptedRow(row)) {
            var events=indexed(row.events,3);
            for(var j=0;j<events.length;j++) {
                var e=events[j];
                if(!e || e.kind!=="transit" || e.planet!==name
                        || e.date!==row.date || e.source!=="USNO MRST")
                    continue;
                altitude=bounded(e.altitude,0,90);
                at=String(e.clock || "--");
                hemi=e.hemisphere==="N" || e.hemisphere==="S"
                    ? e.hemisphere : "";
                date=row.date;
                break;
            }
        }
        out.push({planet:name,altitude:altitude,clock:at,
                  hemisphere:hemi,date:date,source:altitude===null?"":"USNO MRST"});
    }
    return out;
}

function geometry(width,height) {
    var w=Number(width),h=Number(height);
    if(!isFinite(w)||!isFinite(h)||w<=0||h<=0)
        return {ready:false,x:0,y:0,radius:0};
    return {ready:true,x:w/2,y:h/2,radius:Math.max(0,Math.min(w,h)/2-24)};
}

// V3b: five concentric DISPLAY lanes, inner Mercury -> outer Saturn.
// The radial lane distinguishes simultaneous bearings from different planets.
// Radius never represents planet distance, altitude, orbital size, or visibility.
function laneRadius(name, width, height) {
    var i=PLANETS.indexOf(String(name || ""));
    var g=geometry(width,height);
    if(i<0 || !g.ready || g.radius<=0) return null;
    return g.radius*(0.40+0.15*i);
}

function point(azimuth,width,height,planet) {
    var az=bounded(azimuth,0,360),g=geometry(width,height);
    if(!g.ready || az===null || g.radius<=0) return null;
    // Omitting a planet preserves the previous full-radius cardinal geometry.
    var radius=planet===undefined ? g.radius
              : laneRadius(planet,width,height);
    if(radius===null)return null;
    var rad=az*Math.PI/180;
    return {x:g.x+Math.sin(rad)*radius,
            y:g.y-Math.cos(rad)*radius};
}

// A 0–90° transit altitude is mapped to one circular progress revolution,
// independently of the azimuth compass. Missing data draw NO progress arc.
function altitudeFraction(altitude) {
    var value=bounded(altitude,0,90);
    return value===null ? null : value/90;
}

function pick(markersInput, x, y, width, height, hitRadius) {
    var source=indexed(markersInput,10), px=Number(x),py=Number(y);
    var radius=Number(hitRadius);
    if(!isFinite(px)||!isFinite(py)||!isFinite(radius)
            || radius<=0||radius>50) return null;
    var best=null, distance=radius*radius;
    for(var i=0;i<source.length;i++) {
        var e=source[i], p=e?point(e.azimuth,width,height,e.planet):null;
        if(!p)continue;
        var d=(p.x-px)*(p.x-px)+(p.y-py)*(p.y-py);
        if(d<=distance) {distance=d;best=e;}
    }
    return best;
}

function byId(markersInput, id) {
    var source=indexed(markersInput,10);
    if(typeof id!=="string" || !id) return null;
    for(var i=0;i<source.length;i++)
        if(source[i] && source[i].id===id) return source[i];
    return null;
}

function markerLabel(marker) {
    if(!marker)return "SELECT A RISE OR SET MARKER";
    return marker.planet+" // "+marker.kind.toUpperCase()
         +" "+marker.time+" // "+marker.azimuth+"° TRUE N";
}

function altitudeLabel(row) {
    if(!row || row.altitude===null || row.altitude===undefined)
        return "NO TRANSIT ALTITUDE";
    return row.altitude+"°"+String(row.hemisphere||"")
           +" @ "+row.clock+" LOCAL";
}

function planetInk(name) {
    var i=PLANETS.indexOf(String(name||""));
    return i<0 ? 0 : i;
}
