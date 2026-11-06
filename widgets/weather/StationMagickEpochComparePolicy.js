.pragma library

// MAGICK M6c // Two observed M4 JPL geocentric-apparent longitude snapshots.
// REF is the first source timestamp until deliberately pinned by operator.
// Date-specific ecliptic frames are NOT a common fixed-inertial reference;
// cross-epoch offsets are comparisons of REPORTED chart longitudes only.
// No natal event, house, location, transit influence or new ephemeris actor.
var FORMAT="post-apollo.weather.celestial-visual-data.v1";
var FRAME="true-ecliptic-of-date";
var MAX_SAMPLES=721;
var MAX_BODIES=4;
var SOURCE_EPOCH="FIRST SOURCE UTC";
function finite(n){return typeof n==="number" && isFinite(n);}
function unavailable(reason){
    return {ready:false,reason:reason||"NO SOURCE-VERIFIED TWO-EPOCH DATA",
        bodies:[],pair:null,refMs:0,nowMs:0,refIndex:-1,nowIndex:-1,
        refKind:"",source:"",hash:"",frame:""};
}
function signedOffset(refLongitude,currentLongitude){
    if(!finite(refLongitude)||!finite(currentLongitude)||
       refLongitude<0||refLongitude>=360||
       currentLongitude<0||currentLongitude>=360)return null;
    // Shortest wrapped difference in reported date-specific longitudes.
    return ((currentLongitude-refLongitude+540)%360)-180;
}
function build(model,payload,requestedReference,nowIndex){
    if(!model || model.ready!==true ||
       model.frame!==FRAME || !model.source || !model.hash ||
       !payload || payload.format!==FORMAT || !payload.query ||
       payload.query.origin!=="geocentric" ||
       payload.query.position_model!=="apparent" ||
       payload.query.frame!==FRAME ||
       !payload.provenance ||
       payload.provenance.ephemeris_id!==model.source ||
       typeof payload.provenance.ephemeris_sha256!=="string" ||
       payload.provenance.ephemeris_sha256.slice(0,10)!==model.hash ||
       !Array.isArray(model.series) ||
       model.series.length<1 || model.series.length>MAX_BODIES ||
       !Array.isArray(model.times) ||
       model.sampleCount!==model.times.length ||
       model.sampleCount<2 || model.sampleCount>MAX_SAMPLES ||
       !Number.isInteger(nowIndex) ||
       nowIndex<0 || nowIndex>=model.sampleCount ||
       !Number.isInteger(requestedReference) ||
       requestedReference< -1 || requestedReference>=model.sampleCount)
       return unavailable("M4 SOURCE, FRAME OR SAMPLE INDEX UNVERIFIED");
    var referenceIndex=requestedReference<0?0:requestedReference;
    var previous=null;
    for(var t=0;t<model.sampleCount;t++){
        var stamp=model.times[t];
        if(!Number.isInteger(stamp) || !finite(stamp) ||
           (previous!==null && stamp<=previous))
            return unavailable("M4 UTC GRID INVALID");
        previous=stamp;
    }
    var refMs=model.times[referenceIndex],nowMs=model.times[nowIndex];
    var seen={},entries=[];
    for(var s=0;s<model.series.length;s++){
        var series=model.series[s];
        if(!series || typeof series.body!=="string" || !series.body ||
           seen[series.body] || !Array.isArray(series.rows) ||
           series.rows.length!==model.sampleCount ||
           !Array.isArray(payload.query.bodies) ||
           payload.query.bodies.indexOf(series.body)<0)
            return unavailable("M4 BODY SERIES MISMATCH");
        seen[series.body]=true;
        var ref=series.rows[referenceIndex],
            now=series.rows[nowIndex];
        if(!ref || !now || ref.unix_ms!==refMs ||
           now.unix_ms!==nowMs || !finite(ref.longitude_deg) ||
           !finite(now.longitude_deg))
            return unavailable("M4 TWO-EPOCH POINT MISMATCH");
        var delta=signedOffset(ref.longitude_deg,now.longitude_deg);
        if(delta===null)return unavailable("M4 LONGITUDE INVALID");
        entries.push({body:series.body,color:series.color,
            refLongitude:ref.longitude_deg,nowLongitude:now.longitude_deg,
            refMs:refMs,nowMs:nowMs,delta:delta,
            refMotion:ref.motion,nowMotion:now.motion});
    }
    var pair=null;
    if(model.relationships && model.relationships.length===1){
        var rel=model.relationships[0];
        if(!rel || !Array.isArray(rel.bodies) || rel.bodies.length!==2 ||
           !seen[rel.bodies[0]] || !seen[rel.bodies[1]] ||
           !Array.isArray(rel.samples) ||
           rel.samples.length!==model.sampleCount)
            return unavailable("M4 RELATIONSHIP SOURCE MISMATCH");
        var old=rel.samples[referenceIndex],current=rel.samples[nowIndex];
        if(!old || !current || old.unix_ms!==refMs ||
           current.unix_ms!==nowMs ||
           !finite(old.longitude_separation_deg) ||
           !finite(current.longitude_separation_deg) ||
           !Array.isArray(old.aspects) || !Array.isArray(current.aspects))
            return unavailable("M4 PAIR SAMPLE MISMATCH");
        pair={bodies:rel.bodies.slice(),
            refSeparation:old.longitude_separation_deg,
            nowSeparation:current.longitude_separation_deg,
            refAspects:old.aspects.map(function(a){return String(a.name||"");}),
            nowAspects:current.aspects.map(function(a){return String(a.name||"");})};
    }
    return {ready:true,reason:"",bodies:entries,pair:pair,
        refMs:refMs,nowMs:nowMs,refIndex:referenceIndex,nowIndex:nowIndex,
        refKind:requestedReference<0?SOURCE_EPOCH:"PINNED SOURCE UTC",
        source:String(model.source),hash:String(model.hash),frame:FRAME};
}
function geometry(width,height){
    if(!finite(width)||!finite(height)||width<160||height<105)return null;
    var spacious=width>=430;
    var cx=spacious?width*0.37:width/2;
    var cy=height*0.54;
    var outer=Math.min(height*0.38,spacious?width*0.27:width*0.38);
    if(outer<30)return null;
    return {cx:cx,cy:cy,outer:outer,
        referenceRadius:outer*0.82,currentRadius:outer*0.56,
        inspectorX:spacious?width*0.68:0,
        spacious:spacious};
}
function point(longitude,cx,cy,radius){
    if(!finite(longitude)||longitude<0||longitude>=360||
       !finite(cx)||!finite(cy)||!finite(radius)||radius<=0)return null;
    var angle=longitude*Math.PI/180;
    return {x:cx+radius*Math.sin(angle),
            y:cy-radius*Math.cos(angle)};
}
function pick(model,geometry,x,y){
    if(!model || model.ready!==true || !geometry||
       !finite(x) || !finite(y))return null;
    var nearest=null,distance=12*12;
    for(var i=0;i<model.bodies.length;i++){
        var body=model.bodies[i];
        for(var which of ["ref","now"]){
            var p=point(which==="ref"?body.refLongitude:body.nowLongitude,
                geometry.cx,geometry.cy,
                which==="ref"?geometry.referenceRadius:geometry.currentRadius);
            if(!p)continue;
            var d=(x-p.x)*(x-p.x)+(y-p.y)*(y-p.y);
            if(d<=distance){distance=d;nearest={body:body.body,which:which};}
        }
    }
    return nearest;
}
