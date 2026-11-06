.pragma library

// V5b // Source-calibrated AU rulers and *discrete* real JPL samples.
// No guessed orbits, no interpolation, no additional kernel or process.
var ATLAS_FORMAT = "post-apollo.weather.solar-overview.v1";
var FRAME = "true-ecliptic-of-date";
var MAX_WINDOW = 12;
var MAX_SAMPLES = 181;

function validNumber(n) {
    return typeof n === "number" && isFinite(n) && Math.abs(n) <= 10000;
}
function auLabel(au) {
    if (!validNumber(au) || au <= 0) return "";
    return au < 0.1 ? au.toFixed(3) + " AU"
         : au < 10 ? au.toFixed(2) + " AU"
         : au.toFixed(1) + " AU";
}

// Ring 4 is the actual active AU domain (ALL or INNER); the visual
// camera only changes pixel radius, never the physical AU scale.
function rings(domainAu) {
    if (!validNumber(domainAu) || domainAu <= 0) return [];
    var result = [];
    for (var i = 1; i <= 4; i++) {
        var distance = domainAu * i / 4;
        result.push({fraction:i / 4,au:distance,label:auLabel(distance)});
    }
    return result;
}

// Labels are optional when camera pan/zoom puts the scale outside the plot.
// The background rings still represent exactly 1/4, 1/2, 3/4, 1 of domainAu.
// Use the right-hand top quadrant to keep numeric ticks away from the SUN.
function ringCallouts(domainAu,origin,bounds,tilt) {
    if (!origin || !bounds || !validNumber(domainAu) ||
        !validNumber(origin.cx) || !validNumber(origin.cy) ||
        !validNumber(origin.r) || origin.r <= 0 ||
        ![bounds.left,bounds.top,bounds.right,bounds.bottom].every(
            function(v){return validNumber(v);}))
        return [];
    var flattened = tilt === true ? Math.SQRT1_2 : 1;
    var candidates = rings(domainAu),output=[],last = null;
    for (var i = 0; i < candidates.length; i++) {
        var tick = candidates[i];
        var radius = origin.r * tick.fraction;
        var x = origin.cx + Math.SQRT1_2 * radius;
        var y = origin.cy - Math.SQRT1_2 * radius * flattened;
        // Put text only where the whole small label can fit.
        if (radius < 20 || x < bounds.left + 27 ||
            x > bounds.right - 42 || y < bounds.top + 10 ||
            y > bounds.bottom - 10)
            continue;
        if (last && Math.hypot(x-last.x,y-last.y) < 24)
            continue;
        output.push({x:x,y:y,au:tick.au,label:tick.label});
        last={x:x,y:y};
    }
    return output;
}

function empty(reason) {return {ready:false,reason:reason||"NO VERIFIED JPL SAMPLES",samples:[]};}

function sampleWindow(payload,scene,body,index,halfWindow) {
    if (!payload || !scene || scene.ready !== true || scene.atlas !== true ||
        typeof body !== "string" || !body || !Array.isArray(scene.points) ||
        !scene.points.some(function(p){return p && p.body === body;}) ||
        !payload.provenance || !payload.solar_overview)
        return empty("NO SELECTED VERIFIED JPL BODY");
    var atlas = payload.solar_overview,provenance=payload.provenance;
    if (atlas.format !== ATLAS_FORMAT || atlas.origin !== "heliocentric" ||
        atlas.origin_body !== "sun" || atlas.position_model !== "geometric" ||
        atlas.frame !== FRAME || atlas.units !== "AU" ||
        atlas.epoch !== "exact-m4-grid" ||
        atlas.source !== "same-JPL-kernel-as-M4" ||
        provenance.ephemeris_id !== scene.source ||
        typeof provenance.ephemeris_sha256 !== "string" ||
        provenance.ephemeris_sha256.slice(0,10) !== scene.hash ||
        !Array.isArray(atlas.series) || !Array.isArray(atlas.times_unix_ms) ||
        !Number.isInteger(atlas.sample_count) ||
        atlas.sample_count < 2 || atlas.sample_count > MAX_SAMPLES ||
        atlas.times_unix_ms.length !== atlas.sample_count ||
        !Number.isInteger(index) || index < 0 || index >= atlas.sample_count ||
        scene.timeMs !== atlas.times_unix_ms[index])
        return empty("STALE OR DIFFERENT JPL SOURCE");
    var radius = halfWindow===undefined ? MAX_WINDOW : halfWindow;
    if (!Number.isInteger(radius) || radius < 1 || radius > MAX_WINDOW)
        return empty("INVALID SAMPLE WINDOW");
    var series=atlas.series.filter(function(s){return s && s.body===body;});
    if (series.length!==1 || !Array.isArray(series[0].vectors_au) ||
        series[0].vectors_au.length!==atlas.sample_count)
        return empty("MISSING SOURCE BODY SERIES");
    var row=series[0],result=[],previous=null;
    // Check the complete source timestamps before using even a small slice.
    for (var t=0;t<atlas.sample_count;t++) {
        var ts=atlas.times_unix_ms[t];
        if (typeof ts!=="number" || !isFinite(ts) ||
            !Number.isInteger(ts) || (previous!==null && ts<=previous))
            return empty("INVALID JPL UTC GRID");
        previous=ts;
    }
    var start=Math.max(0,index-radius),
        end=Math.min(atlas.sample_count-1,index+radius);
    for (var i=start;i<=end;i++) {
        var xyz=row.vectors_au[i];
        if (!Array.isArray(xyz) || xyz.length!==3 ||
            !xyz.every(validNumber) || Math.hypot(xyz[0],xyz[1],xyz[2])<=0)
            return empty("INVALID JPL XYZ SAMPLE");
        result.push({body:body,index:i,unix_ms:atlas.times_unix_ms[i],
                     x_au:xyz[0],y_au:xyz[1],z_au:xyz[2],
                     kind:i<index?"past":i>index?"future":"now"});
    }
    return {ready:true,reason:"",body:body,center:index,
            start:start,end:end,frame:FRAME,samples:result};
}
