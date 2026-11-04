.pragma library

// V4c // STRICT source-verified Sun-centered geometric spatial scene.
// Angular coordinates and apparent M4 data are NOT substituted for real XYZ.
// One M4 result, one JPL kernel, one UTC sample shared with the network.
var FORMAT = "post-apollo.weather.heliocentric-spatial.v1";
var FRAME = "true-ecliptic-of-date";
var MAX_NODES = 4;
var MAX_SAMPLES = 721;

function finite(n) {
    return typeof n === "number" && isFinite(n) && Math.abs(n) <= 10000
        ? n : null;
}
function empty(reason) {
    return {ready:false,reason:reason||"HELIOSPATIAL SOURCE UNAVAILABLE",
        points:[],count:0,source:"",hash:"",timeMs:null,utc:"",
        maxAu:0,frame:FRAME,origin:"sun",positionModel:"geometric"};
}
function bodyIdOk(value) {
    return typeof value === "string" && /^[a-z][a-z0-9_]{1,30}$/.test(value);
}
function verifiedScene(payload,model,network,index) {
    var fail=empty("NO MATCHING HELIOCENTRIC JPL SAMPLES");
    if(!payload || !payload.heliocentric_spatial ||
       !payload.provenance || !payload.query ||
       !model || !model.ready || !network || !network.ready ||
       !Number.isInteger(index) || index<0 || index>=model.sampleCount ||
       !Array.isArray(model.times) || index>=model.times.length)
        return fail;
    var data=payload.heliocentric_spatial;
    var sha=payload.provenance.ephemeris_sha256;
    if(payload.format!=="post-apollo.weather.celestial-visual-data.v1" ||
       typeof sha!=="string" || !/^[a-f0-9]{64}$/i.test(sha) ||
       sha.slice(0,10)!==network.hash ||
       payload.provenance.ephemeris_id!==network.source ||
       payload.query.origin!=="geocentric" ||
       payload.query.position_model!=="apparent" ||
       payload.query.frame!==FRAME ||
       payload.query.include_heliocentric_spatial!==true ||
       data.format!==FORMAT || data.frame!==FRAME ||
       data.origin!=="heliocentric" || data.origin_body!=="sun" ||
       data.position_model!=="geometric" ||
       data.epoch!=="per-sample-UTC" || data.units!=="AU" ||
       data.source!=="same-JPL-kernel-as-M4" ||
       !Array.isArray(payload.query.bodies) ||
       !Array.isArray(data.series) ||
       data.series.length!==model.series.length ||
       data.series.length<1 || data.series.length>MAX_NODES ||
       !Number.isInteger(data.sample_count) ||
       data.sample_count!==model.sampleCount ||
       data.sample_count<2 || data.sample_count>MAX_SAMPLES ||
       network.timeMs!==model.times[index] ||
       network.frame!==FRAME)
        return fail;
    // Validate ALL samples against the M4 sample index, not merely the
    // current one. Invalid intermediate records never produce a partial
    // apparently trustworthy spatial view.
    var points=[], maxAu=0, names={};
    for(var i=0;i<data.series.length;i++){
        var src=data.series[i],reference=model.series[i];
        if(!src || !reference || src.body!==reference.body ||
           !bodyIdOk(src.body) || names[src.body] ||
           payload.query.bodies.indexOf(src.body)<0 ||
           !Array.isArray(src.samples) ||
           src.samples.length!==data.sample_count)
            return fail;
        names[src.body]=true;
        for(var j=0;j<data.sample_count;j++){
            var sample=src.samples[j];
            if(!sample || sample.unix_ms!==model.times[j] ||
               typeof sample.time_utc!=="string" ||
               Date.parse(sample.time_utc)!==model.times[j] ||
               !/Z$/.test(sample.time_utc))
                return fail;
            var x=finite(sample.x_au),y=finite(sample.y_au),
                z=finite(sample.z_au),r=finite(sample.distance_au);
            if(x===null||y===null||z===null||r===null||r<0)
                return fail;
            var norm=Math.hypot(x,y,z);
            if(Math.abs(norm-r)>1e-7*Math.max(1,norm) ||
               (src.body==="sun" ? norm!==0 : norm<=0))
                return fail;
        }
        var at=src.samples[index];
        var dist=at.distance_au;
        maxAu=Math.max(maxAu,dist);
        points.push({body:src.body,color:reference.color,
                     x_au:at.x_au,y_au:at.y_au,z_au:at.z_au,
                     distance_au:dist,origin:src.body==="sun",
                     unix_ms:at.unix_ms});
    }
    if(maxAu<=0)return empty("NO NON-SOLAR BODY AT THIS UTC SAMPLE");
    return {ready:true,reason:"",points:points,count:points.length,
            maxAu:maxAu,source:network.source,hash:network.hash,
            timeMs:network.timeMs,utc:network.isoUtc,
            frame:FRAME,origin:"sun",positionModel:"geometric"};
}

// Orthographic view of the true ecliptic-of-date XYZ at a single instant.
// TOP: x/ecliptic 0° up, y/90° right. TILT: rotate toward a view from
// above the ecliptic plane; Z becomes spatially visible. No orbit tracks.
function layout(width,height,scale) {
    var w=finite(width),h=finite(height),s=finite(scale);
    if(w===null||h===null||s===null || w<=0||h<=0 ||
       s<0.25||s>8)return {ready:false,cx:0,cy:0,r:0};
    var radius=Math.min(h/2-24,w*0.30)*s;
    return {ready:radius>8,cx:w*0.39,cy:h/2,r:Math.max(0,radius)};
}
function position(scene,point,width,height,scale,tilt,domainAu) {
    if(!scene||!scene.ready||!point)return null;
    var g=layout(width,height,scale);
    // V4d: optional truthful radial window: ALL source bodies or INNER AU.
    // Data coordinates and actual maxAu remain unchanged.
    var r=domainAu===undefined?finite(scene.maxAu):finite(domainAu),
        x=finite(point.x_au),y=finite(point.y_au),z=finite(point.z_au);
    if(!g.ready||r===null||r<=0||x===null||y===null||z===null)
        return null;
    var angle=tilt===true?Math.PI/4:0;
    return {x:g.cx+g.r*y/r,
            y:g.cy-g.r*(x*Math.cos(angle)+z*Math.sin(angle))/r};
}
function hit(scene,px,py,w,h,scale,tilt,tolerance,domainAu) {
    if(!scene||!scene.ready)return "";
    var x=finite(px),y=finite(py),tol=finite(tolerance);
    if(x===null||y===null||tol===null||tol<=0||tol>30)return "";
    var best="",distance=tol*tol;
    for(var i=0;i<scene.points.length;i++){
        var point=scene.points[i];
        if(point.origin)continue;
        var screen=position(scene,point,w,h,scale,tilt,domainAu);
        if(!screen)continue;
        var d=(screen.x-x)*(screen.x-x)+(screen.y-y)*(screen.y-y);
        if(d<=distance){distance=d;best=point.body;}
    }
    return best;
}
function byBody(scene,body) {
    if(!scene||!scene.ready||typeof body!=="string")return null;
    for(var i=0;i<scene.points.length;i++)
        if(scene.points[i].body===body)return scene.points[i];
    return null;
}
function detail(point) {
    if(!point)return "SELECT A JPL BODY";
    if(point.origin)return "SUN // HELIOCENTRIC ORIGIN // 0 AU";
    return point.body.toUpperCase()+" // "+point.distance_au.toFixed(6)
        +" AU // XYZ ("+point.x_au.toFixed(3)+", "
        +point.y_au.toFixed(3)+", "+point.z_au.toFixed(3)+") AU";
}
