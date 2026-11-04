.pragma library

// MAGICK M5c // Pure, bounded UTC and exact-JPL-body selection policy.
// No network, local time inference, ephemeris execution, or user-data storage.
var FORMAT = "post-apollo.weather.celestial-visual-data.v1";
var PAIRS = [
    {id:"moon-sun",label:"MOON / SUN",bodies:["moon","sun"]},
    {id:"mercury-sun",label:"MERCURY / SUN",bodies:["mercury","sun"]},
    {id:"venus-mars",label:"VENUS / MARS SYS",bodies:["venus","mars_barycenter"]},
    {id:"jupiter-saturn",label:"JUP / SAT SYS",bodies:["jupiter_barycenter","saturn_barycenter"]},
    {id:"uranus-neptune",label:"URA / NEP SYS",bodies:["uranus_barycenter","neptune_barycenter"]},
    {id:"moon-pluto",label:"MOON / PLUTO SYS",bodies:["moon","pluto_barycenter"]}
];
var SPANS = [14,29,90];
var MAX_DAY_OFFSET = 3650;
var DAY_MS = 86400000;

// MAGICK M5k // The date-navigation step is a UI calibration, NOT the
// graph sampling interval and NOT a new JPL request field.
// Strict decimal-only positive day counts: 1, 5, 10, 30, etc.
var DEFAULT_DAY_STEP = 5;
function parseDayStep(value) {
    if(typeof value!=="string" && typeof value!=="number")return null;
    var str=String(value).trim();
    if(!/^[1-9][0-9]{0,3}$/.test(str))return null;
    var n=Number(str);
    return n<=MAX_DAY_OFFSET ? n : null;
}
function adjustDayStep(current,direction) {
    if(typeof current!=="number" || parseDayStep(current)===null ||
       typeof direction!=="number" || !isFinite(direction) ||
       Math.floor(direction)!==direction || Math.abs(direction)!==1)
       return null;
    return Math.max(1,Math.min(MAX_DAY_OFFSET,current+direction));
}

function pairFor(id) {
    for (var i=0;i<PAIRS.length;i++)
        if(PAIRS[i].id===id)return PAIRS[i];
    return null;
}
function pairAfter(id,step) {
    var index=0;
    for(var i=0;i<PAIRS.length;i++)
        if(PAIRS[i].id===id){index=i;break;}
    var next=(index+(step<0?-1:1)+PAIRS.length)%PAIRS.length;
    return PAIRS[next].id;
}
function initialPairForRoute(route) {
    return route==="magick/astrology/retrogrades" ? "mercury-sun" : "moon-sun";
}
function spanAfter(span) {
    var index=SPANS.indexOf(span);
    return SPANS[(index+1+SPANS.length)%SPANS.length];
}
function shiftOffset(current,days) {
    if(typeof current!=="number" || !isFinite(current) ||
       Math.floor(current)!==current ||
       typeof days!=="number" || !isFinite(days) ||
       Math.floor(days)!==days)
        return null;
    return Math.max(-MAX_DAY_OFFSET,Math.min(MAX_DAY_OFFSET,current+days));
}
function dayFor(utcDay,offset) {
    if(typeof utcDay!=="string" || !/^\d{4}-\d\d-\d\d$/.test(utcDay) ||
       typeof offset!=="number" || Math.floor(offset)!==offset ||
       Math.abs(offset)>MAX_DAY_OFFSET)
        return "";
    var anchor=Date.parse(utcDay+"T00:00:00.000Z");
    if(!isFinite(anchor) || new Date(anchor).toISOString().slice(0,10)!==utcDay)
        return "";
    var target=anchor+offset*DAY_MS;
    if(!isFinite(target))return "";
    return new Date(target).toISOString().slice(0,10);
}
function requestFor(utcDay,offset,pairId,spanDays) {
    var day=dayFor(utcDay,offset),pair=pairFor(pairId);
    if(day==="" || !pair || SPANS.indexOf(spanDays)<0)return null;
    var middle=Date.parse(day+"T00:00:00.000Z");
    return {
        format:FORMAT,
        start_utc:new Date(middle-Math.floor(spanDays/2)*DAY_MS).toISOString(),
        end_utc:new Date(middle+Math.ceil(spanDays/2)*DAY_MS).toISOString(),
        bodies:pair.bodies.slice(),
        step_hours:12,
        rate_window_hours:6,
        orb_degrees:6,
        include_events:true
    };
}
function matchesResult(payload,expected) {
    if(!payload || !expected || payload.format!==FORMAT ||
       !payload.provenance ||
       !/^[0-9a-f]{64}$/i.test(String(payload.provenance.ephemeris_sha256||"")) ||
       !Array.isArray(payload.series) || payload.series.length!==2 ||
       !Array.isArray(payload.relationships) || payload.relationships.length!==1 ||
       !Array.isArray(payload.event_markers) ||
       !payload.query || payload.query.origin!=="geocentric" ||
       payload.query.position_model!=="apparent" ||
       payload.query.frame!=="true-ecliptic-of-date" ||
       !Array.isArray(payload.query.bodies))
        return false;
    var bodies=expected.bodies.slice().sort();
    if(JSON.stringify(payload.query.bodies)!==JSON.stringify(bodies))
        return false;
    if(Date.parse(payload.query.start_utc)!==Date.parse(expected.start_utc) ||
       Date.parse(payload.query.end_utc)!==Date.parse(expected.end_utc) ||
       payload.query.step_hours!==expected.step_hours ||
       payload.query.include_events!==true)
        return false;
    return true;
}
