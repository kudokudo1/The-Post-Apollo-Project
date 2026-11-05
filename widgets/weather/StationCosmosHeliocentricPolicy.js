.pragma library

// V4c // STRICT source-verified Sun-centered geometric spatial scene.
// Angular coordinates and apparent M4 data are NOT substituted for real XYZ.
// One M4 result, one JPL kernel, one UTC sample shared with the network.
var FORMAT = "post-apollo.weather.heliocentric-spatial.v1";
var FRAME = "true-ecliptic-of-date";
var MAX_NODES = 4;
var MAX_SAMPLES = 721;
// V4f: explicitly wider than the old fixed 0.4..5 mouse-wheel range.
// Only the camera scale changes; JPL XYZ and measured AU remain exact.
var MIN_CAMERA_SCALE = 0.02;
var MAX_CAMERA_SCALE = 160;
var WHEEL_FACTOR = 1.32;

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
       s<MIN_CAMERA_SCALE||s>MAX_CAMERA_SCALE)
        return {ready:false,cx:0,cy:0,r:0};
    var unscaled=Math.min(h/2-24,w*0.30);
    var radius=unscaled*s;
    // Even an extreme zoomed-out view remains paintable; using radius>8
    // as the readiness test was a second, hidden zoom-out limit.
    return {ready:unscaled>8&&radius>0,cx:w*0.39,cy:h/2,
            r:Math.max(0,radius)};
}
// Camera is an independent pixel transform, not a modification to any
// heliocentric source position. Start at the original Sun-centered view.
function cameraOrigin(width,height,scale,panX,panY) {
    var g=layout(width,height,scale),x=finite(panX),y=finite(panY);
    if(!g.ready||x===null||y===null)return null;
    return {cx:g.cx+x,cy:g.cy+y,r:g.r};
}

// Keep the exact source position under the wheel pointer at the same screen
// coordinate after zoom. Mouse-wheel direction is +/-1, no timers required.
function zoomAt(width,height,scale,panX,panY,mouseX,mouseY,direction) {
    var g=layout(width,height,scale);
    var px=finite(panX),py=finite(panY),
        mx=finite(mouseX),my=finite(mouseY);
    if(!g.ready||px===null||py===null||mx===null||my===null||
       (direction!==1&&direction!==-1))return null;
    var next=Math.max(MIN_CAMERA_SCALE,Math.min(MAX_CAMERA_SCALE,
        scale*(direction===1?WHEEL_FACTOR:1/WHEEL_FACTOR)));
    var ratio=next/scale;
    return {scale:next,
            panX:mx-g.cx-(mx-g.cx-px)*ratio,
            panY:my-g.cy-(my-g.cy-py)*ratio};
}

// Double-click a body to move that measured JPL target to the usable plot
// center. The angular/radial position is still unchanged by the camera.
function focusPan(scene,body,width,height,scale,tilt,domainAu,compact) {
    var point=byBody(scene,body),box=viewport(width,height,compact);
    if(!point||!box)return null;
    var p=position(scene,point,width,height,scale,tilt,domainAu);
    if(!p)return null;
    return {panX:(box.left+box.right)/2-p.x,
            panY:(box.top+box.bottom)/2-p.y};
}

function position(scene,point,width,height,scale,tilt,domainAu,panX,panY) {
    if(!scene||!scene.ready||!point)return null;
    var g=layout(width,height,scale);
    // V4d: optional truthful radial window: ALL source bodies or INNER AU.
    // Data coordinates and actual maxAu remain unchanged.
    var r=domainAu===undefined?finite(scene.maxAu):finite(domainAu),
        x=finite(point.x_au),y=finite(point.y_au),z=finite(point.z_au);
    if(!g.ready||r===null||r<=0||x===null||y===null||z===null)
        return null;
    var px=panX===undefined?0:finite(panX),
        py=panY===undefined?0:finite(panY);
    if(px===null||py===null)return null;
    var angle=tilt===true?Math.PI/4:0;
    return {x:g.cx+px+g.r*y/r,
            y:g.cy+py-g.r*(x*Math.cos(angle)+z*Math.sin(angle))/r};
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
// V4e // Plot bounds belong to the visualization, never to the JPL source.
// The noncompact view reserves its existing right inspector; the compact
// layout gives the wheel the full canvas. No shared menu geometry changes.
function viewport(width,height,compact) {
    var w=finite(width),h=finite(height);
    if(w===null||h===null||w<=0||h<=0)return null;
    var left=12,top=10,right=compact===true?w-12:
        Math.min(w-12,w*0.70-12),bottom=h-20;
    if(right-left<35 || bottom-top<35)return null;
    return {left:left,top:top,right:right,bottom:bottom};
}

// Return a drawing marker, not an altered astronomical position.
// Onscreen marker = the exact geometric projection. Offscreen marker =
// an explicit viewport-edge pointer toward the real, unclipped XYZ point.
// Keep the original position() result available for numerical inspection.
function viewportMarker(scene,point,width,height,scale,tilt,domainAu,compact,panX,panY) {
    var raw=position(scene,point,width,height,scale,tilt,domainAu,
                     panX,panY);
    var box=viewport(width,height,compact);
    var g=cameraOrigin(width,height,scale,
        panX===undefined?0:panX,panY===undefined?0:panY);
    if(!raw||!box||!g)return null;
    // Leave room for a highlighted ring and a directional arrowhead.
    var left=box.left+14,right=box.right-14;
    var top=box.top+14,bottom=box.bottom-14;
    if(raw.x>=left && raw.x<=right && raw.y>=top && raw.y<=bottom)
        return {x:raw.x,y:raw.y,offscreen:false,angle:0,
                realX:raw.x,realY:raw.y};
    var dx=raw.x-g.cx,dy=raw.y-g.cy;
    if(dx===0 && dy===0)return null;
    // When the Sun/camera origin is outside the plot, ray intersection
    // from that origin could be negative. Clamp only the drawn arrow, never
    // the JPL coordinate; this also works after arbitrarily large pans.
    var originInside=g.cx>=left&&g.cx<=right&&g.cy>=top&&g.cy<=bottom;
    var px=Math.max(left,Math.min(right,raw.x)),
        py=Math.max(top,Math.min(bottom,raw.y));
    if(originInside) {
        var t=Infinity;
        if(dx>0)t=Math.min(t,(right-g.cx)/dx);
        else if(dx<0)t=Math.min(t,(left-g.cx)/dx);
        if(dy>0)t=Math.min(t,(bottom-g.cy)/dy);
        else if(dy<0)t=Math.min(t,(top-g.cy)/dy);
        if(isFinite(t)&&t>=0){
            t=Math.min(1,t);
            px=Math.max(left,Math.min(right,g.cx+dx*t));
            py=Math.max(top,Math.min(bottom,g.cy+dy*t));
        }
    }
    var arrowX=raw.x-px,arrowY=raw.y-py;
    return {x:px,y:py,offscreen:true,
            angle:Math.atan2(arrowY||dy,arrowX||dx),
            realX:raw.x,realY:raw.y};
}

function labelPosition(marker,labelWidth,width,height,compact,centerX) {
    if(!marker)return null;
    var box=viewport(width,height,compact),raw=finite(labelWidth),
        cx=finite(centerX);
    if(!box||raw===null||cx===null||raw<0)return null;
    var maxWidth=Math.max(8,box.right-box.left-12);
    var actual=Math.min(maxWidth,raw);
    // Offscreen labels point inward. Onscreen labels favor the free side,
    // but stay inside the plot area even for long barycenter names.
    var side=marker.offscreen
        ? (marker.x>=cx?-1:1)
        : (marker.x>=cx?1:-1);
    var preferred=marker.x+side*(10+actual/2);
    var left=box.left+6+actual/2,right=box.right-6-actual/2;
    return {x:Math.max(left,Math.min(right,preferred)),
            y:Math.max(box.top+9,Math.min(box.bottom-9,marker.y)),
            maxWidth:maxWidth};
}

function visibleHit(scene,px,py,w,h,scale,tilt,tolerance,domainAu,compact,panX,panY) {
    if(!scene||!scene.ready)return "";
    var x=finite(px),y=finite(py),tol=finite(tolerance);
    if(x===null||y===null||tol===null||tol<=0||tol>30)return "";
    var best="",distance=tol*tol;
    for(var i=0;i<scene.points.length;i++) {
        var point=scene.points[i];
        if(point.origin)continue;
        var mark=viewportMarker(scene,point,w,h,scale,tilt,domainAu,compact,
                                panX,panY);
        if(!mark)continue;
        var d=(mark.x-x)*(mark.x-x)+(mark.y-y)*(mark.y-y);
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
