.pragma library

// V4b // Earth-centered APPARENT geocentric ecliptic RAY/DISTANCE display.
// Input is the validated M4/JPL model and V4a verified network scene.
// The plotted vector is derived from (apparent longitude, apparent
// latitude, apparent geocentric distance) from the SAME UTC sample.
// This is not a simultaneous physical 3D solar-system map, heliocentric
// planet position, orbital path, or predictive interpolation.
var FORMAT = "post-apollo.weather.apparent-depth.v4b.v1";
var FRAME = "true-ecliptic-of-date";

function finite(n) {
    return typeof n === "number" && isFinite(n) ? n : null;
}
function empty(reason) {
    return {ready:false,reason:reason||"NO VERIFIED M4 APPARENT DEPTH",
        points:[],timeMs:null,isoUtc:"",source:"",hash:"",
        frame:FRAME,origin:"geocentric",positionModel:"apparent",
        maxDistanceAu:null,count:0};
}
function vector(longitudeDeg,latitudeDeg,distanceAu) {
    var lon=finite(longitudeDeg),lat=finite(latitudeDeg),r=finite(distanceAu);
    if(lon===null||lat===null||r===null||lon<0||lon>=360
       ||lat<-90||lat>90||r<=0) return null;
    var longitude=lon*Math.PI/180,latitude=lat*Math.PI/180;
    var cosLat=Math.cos(latitude);
    return {x_au:r*cosLat*Math.cos(longitude),
            y_au:r*cosLat*Math.sin(longitude),
            z_au:r*Math.sin(latitude)};
}
function depth(model,index,verified) {
    if(!verified || verified.ready!==true
       || verified.frame!==FRAME
       || verified.timeMs===null
       || typeof verified.source!=="string" || !verified.source
       || !Array.isArray(verified.nodes)
       || !model || model.ready!==true || model.frame!==FRAME
       || !Number.isInteger(index) || index<0
       || !Array.isArray(model.series)
       || model.series.length!==verified.nodes.length
       || !Array.isArray(model.times)
       || index>=model.times.length
       || finite(model.times[index])!==verified.timeMs
       || verified.source!==model.source
       || verified.hash!==model.hash)
        return empty("NO MATCHING VERIFIED APPARENT GEOCENTRIC SAMPLE");
    var out=[],max=0,used={};
    for(var i=0;i<model.series.length;i++){
        var row=model.series[i],sample=row&&row.rows&&row.rows[index];
        var node=verified.nodes[i],body=row&&row.body;
        if(!node || body!==node.body || used[body] || !sample
           || finite(sample.unix_ms)!==verified.timeMs
           || finite(sample.longitude_deg)!==node.longitude_deg)
            return empty("APPARENT DEPTH SOURCE SAMPLE MISMATCH");
        var lat=finite(sample.latitude_deg),
            dist=finite(sample.distance_au);
        var xyz=vector(node.longitude_deg,lat,dist);
        if(!xyz)return empty("APPARENT LATITUDE OR DISTANCE UNAVAILABLE");
        used[body]=true;
        max=Math.max(max,dist);
        out.push({body:body,color:node.color,longitude_deg:node.longitude_deg,
                  latitude_deg:lat,distance_au:dist,
                  x_au:xyz.x_au,y_au:xyz.y_au,z_au:xyz.z_au,
                  source_time_ms:verified.timeMs});
    }
    if(!out.length||max<=0)return empty("NO DEPTH SOURCE POINTS");
    return {ready:true,reason:"",points:out,count:out.length,
            timeMs:verified.timeMs,isoUtc:verified.isoUtc,
            source:verified.source,hash:verified.hash,
            frame:FRAME,origin:"geocentric",positionModel:"apparent",
            maxDistanceAu:max};
}

// Top-down apparent geocentric ecliptic-plane projection.
// The radial axis is LINEAR APPARENT GEOCENTRIC DISTANCE in AU.
// The outer ring is the farthest body INCLUDED IN THIS QUERY, not a
// fixed solar-system size. Latitude appears as a separate Z component.
function layout(width,height) {
    var w=finite(width),h=finite(height);
    if(w===null||h===null||w<=0||h<=0)
        return {ready:false,cx:0,cy:0,r:0};
    var r=Math.min(h/2-22,w*0.28);
    return {ready:r>10,cx:w*0.39,cy:h/2,r:Math.max(0,r)};
}
function projected(scene,point,width,height) {
    if(!scene||!scene.ready||!point)return null;
    var g=layout(width,height),max=finite(scene.maxDistanceAu),
        x=finite(point.x_au),y=finite(point.y_au);
    if(!g.ready||max===null||max<=0||x===null||y===null)return null;
    return {x:g.cx+g.r*y/max,y:g.cy-g.r*x/max};
}
function hit(scene,x,y,width,height,tolerance) {
    if(!scene||!scene.ready)return "";
    var px=finite(x),py=finite(y),t=finite(tolerance);
    if(px===null||py===null||t===null||t<=0||t>30)return "";
    var best="",dist=t*t;
    for(var i=0;i<scene.points.length;i++){
        var item=scene.points[i],p=projected(scene,item,width,height);
        if(!p)continue;
        var d=(p.x-px)*(p.x-px)+(p.y-py)*(p.y-py);
        if(d<=dist){dist=d;best=item.body;}
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
    if(!point)return "SELECT SOURCE BODY";
    return point.body.toUpperCase()
      +" // "+point.distance_au.toFixed(6)+" AU"
      +" // LAT "+point.latitude_deg.toFixed(3)+"°"
      +" // LON "+point.longitude_deg.toFixed(3)+"°";
}
