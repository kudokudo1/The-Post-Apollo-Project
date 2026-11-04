.pragma library

// COSMOS/MAGICK V4a read-only VISUAL RELATIONSHIP NETWORK.
// Input: StationMagickCelestialVisualPolicy.model(raw M4 JSON) ONLY.
// Does not calculate an ephemeris, fetch, mutate, classify influence, or
// infer heliocentric location from geocentric apparent longitude.
var FORMAT = "post-apollo.weather.celestial-network.v4a.v1";
var FRAME = "true-ecliptic-of-date";

function finite(value) {
    return typeof value === "number" && isFinite(value) ? value : null;
}

function blank(reason) {
    return {ready:false,reason:reason||"AWAITING VERIFIED JPL DATA",
            nodes:[],edges:[],timeMs:null,isoUtc:"",frame:FRAME,
            source:"",hash:"",count:0};
}

function separation(a,b) {
    var aa=finite(a),bb=finite(b);
    if(aa===null || bb===null || aa<0 || aa>=360 || bb<0 || bb>=360)
        return null;
    return Math.abs(((bb-aa+540)%360)-180);
}

function keyFor(a,b) {
    if(typeof a!=="string" || !a || typeof b!=="string" || !b || a===b)
        return "";
    return [a,b].sort().join("|");
}

function network(model,index) {
    if(!model || model.ready!==true || model.frame!==FRAME
       || typeof model.source!=="string" || !model.source
       || typeof model.hash!=="string" || !/^[a-f0-9]{10}$/i.test(model.hash)
       || !Array.isArray(model.series) || model.series.length<2
       || model.series.length>4 || !Array.isArray(model.relationships)
       || !Array.isArray(model.times) || !Number.isInteger(index)
       || index<0 || index>=model.times.length)
        return blank("NO SOURCE-VERIFIED GEOCENTRIC M4 SAMPLE");
    var moment=finite(model.times[index]);
    if(moment===null)return blank("UTC SAMPLE NOT AVAILABLE");
    var nodes=[],lookup={},relationships=model.relationships;
    for(var i=0;i<model.series.length;i++){
        var row=model.series[i],sample=row && row.rows && row.rows[index];
        var name=row&&row.body,lon=sample&&finite(sample.longitude_deg);
        if(typeof name!=="string" || !name || lookup[name]
           || lon===null || lon<0 || lon>=360
           || finite(sample.unix_ms)!==moment)
            return blank("M4 LONGITUDE SAMPLES MISSING OR MISALIGNED");
        var point={body:name,color:row.color,longitude_deg:lon,
                   motion:sample.motion,source_time_ms:moment};
        nodes.push(point);
        lookup[name]=point;
    }
    var expected=nodes.length*(nodes.length-1)/2;
    if(relationships.length!==expected)
        return blank("M4 SOURCE RELATIONSHIPS INCOMPLETE");
    var edges=[],used={};
    for(var j=0;j<relationships.length;j++){
        var rel=relationships[j],pair=rel&&rel.bodies;
        if(!Array.isArray(pair)||pair.length!==2
           || !lookup[pair[0]] || !lookup[pair[1]]
           || !rel.samples || !rel.samples[index])
            return blank("M4 RELATIONSHIP SAMPLE MISSING");
        var k=keyFor(pair[0],pair[1]);
        var sourceRow=rel.samples[index];
        var value=finite(sourceRow.longitude_separation_deg);
        var calculated=separation(lookup[pair[0]].longitude_deg,
                                 lookup[pair[1]].longitude_deg);
        if(!k||used[k] || value===null || value<0 || value>180
           || finite(sourceRow.unix_ms)!==moment
           || calculated===null || Math.abs(value-calculated)>0.001
           || !Array.isArray(sourceRow.aspects))
            return blank("M4 RELATIONSHIP / LONGITUDE MISMATCH");
        used[k]=true;
        // The aspect strings, when present, are already supplied by M4.
        // Never independently invent an orb or a tradition's interpretation.
        edges.push({key:k,first:pair[0],second:pair[1],
                    longitude_separation_deg:value,
                    aspects:sourceRow.aspects.map(function(a){
                        return String(a && a.name || "");
                    }).filter(function(name){return name!=="";}),
                    source_time_ms:moment});
    }
    return {ready:true,reason:"",nodes:nodes,edges:edges,count:nodes.length,
            timeMs:moment,isoUtc:new Date(moment).toISOString(),
            frame:FRAME,source:model.source,hash:model.hash};
}

// 0° ecliptic longitude points UP, increasing clockwise. This is a
// LONGITUDE DIAGRAM only, not heliocentric orbital geometry or sky bearings.
function layout(width,height) {
    var w=finite(width),h=finite(height);
    if(w===null || h===null || w<=0 || h<=0)
        return {ready:false,cx:0,cy:0,r:0};
    var r=Math.min(h/2-22,w*0.28);
    return {ready:r>10,cx:w*0.39,cy:h/2,r:Math.max(0,r)};
}
function position(longitude,width,height) {
    var lon=finite(longitude),g=layout(width,height);
    if(!g.ready || lon===null || lon<0 || lon>=360)return null;
    var radians=lon*Math.PI/180;
    return {x:g.cx+g.r*Math.sin(radians),
            y:g.cy-g.r*Math.cos(radians)};
}
function bodyHit(scene,x,y,width,height,tolerance) {
    if(!scene || !scene.ready)return "";
    var px=finite(x),py=finite(y),tol=finite(tolerance);
    if(px===null||py===null||tol===null||tol<=0||tol>30)return "";
    var best="",distance=tol*tol;
    for(var i=0;i<scene.nodes.length;i++){
        var node=scene.nodes[i],p=position(node.longitude_deg,width,height);
        if(!p)continue;
        var d=(p.x-px)*(p.x-px)+(p.y-py)*(p.y-py);
        if(d<=distance){distance=d;best=node.body;}
    }
    return best;
}
function edgeHit(scene,x,y,width,height,tolerance) {
    if(!scene || !scene.ready)return "";
    var px=finite(x),py=finite(y),tol=finite(tolerance);
    if(px===null||py===null||tol===null||tol<=0||tol>20)return "";
    var byName={},best="",distance=tol*tol;
    for(var i=0;i<scene.nodes.length;i++)byName[scene.nodes[i].body]=scene.nodes[i];
    for(var j=0;j<scene.edges.length;j++){
        var edge=scene.edges[j],na=byName[edge.first],nb=byName[edge.second];
        if(!na||!nb)continue;
        var a=position(na.longitude_deg,width,height);
        var b=position(nb.longitude_deg,width,height);
        if(!a||!b)continue;
        var dx=b.x-a.x,dy=b.y-a.y,denom=dx*dx+dy*dy;
        if(denom<=1e-9)continue;
        var t=Math.max(0,Math.min(1,((px-a.x)*dx+(py-a.y)*dy)/denom));
        var vx=a.x+t*dx,vy=a.y+t*dy;
        var d=(vx-px)*(vx-px)+(vy-py)*(vy-py);
        if(d<=distance){distance=d;best=edge.key;}
    }
    return best;
}
function edgeByKey(scene,key) {
    if(!scene||!scene.ready||typeof key!=="string")return null;
    for(var i=0;i<scene.edges.length;i++)
        if(scene.edges[i].key===key)return scene.edges[i];
    return null;
}
function nodeByBody(scene,body) {
    if(!scene||!scene.ready||typeof body!=="string")return null;
    for(var i=0;i<scene.nodes.length;i++)
        if(scene.nodes[i].body===body)return scene.nodes[i];
    return null;
}
function pairLabel(edge) {
    if(!edge)return "NO SOURCE PAIR SELECTED";
    return edge.first.toUpperCase()+" / "+edge.second.toUpperCase()
        +" // "+edge.longitude_separation_deg.toFixed(3)+"°"
        +" LONGITUDE SEPARATION";
}
