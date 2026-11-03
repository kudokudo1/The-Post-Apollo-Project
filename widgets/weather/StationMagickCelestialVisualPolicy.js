.pragma library

// M5 // Read-only presentation policy for M4 celestial visual-data.v1.
// No provider process, no astronomical computation, no invented sample.
// A production instrument requires validated source provenance.
var FORMAT = "post-apollo.weather.celestial-visual-data.v1";
var MODES = ["wheel", "motion", "aspects"];
var SIGNS = ["AR", "TA", "GE", "CN", "LE", "VI",
             "LI", "SC", "SG", "CP", "AQ", "PI"];
var BODY_COLORS = ["#ED981A", "#55CFCA", "#C74EC7", "#F2BE4E"];

function number(value) {
    return typeof value === "number" && isFinite(value) ? value : null;
}
function clamp(value, low, high) {
    return Math.max(low,Math.min(high,value));
}
function unavailable(reason) {
    return {ready:false,reason:reason || "NO SOURCE-VERIFIED M4 DATA",
            series:[],relationships:[],events:[],sampleCount:0,
            times:[],startMs:0,endMs:0,bodies:[],source:"",mode:""};
}
function validRows(rows, expectedCount, sharedTimes) {
    if (!Array.isArray(rows) || rows.length !== expectedCount) return false;
    var last = -Infinity, prevLon = null, prevUnwrapped = null;
    for (var i=0;i<rows.length;i++) {
        var p=rows[i];
        if (!p || typeof p !== "object")return false;
        var time=number(p.unix_ms),lon=number(p.longitude_deg);
        var unwrapped=number(p.unwrapped_longitude_deg);
        var lat=number(p.latitude_deg),distance=number(p.distance_au);
        var rate=number(p.longitude_rate_deg_per_day);
        if (time === null || time <= last ||
            !isFinite(Date.parse(p.time_utc)) ||
            Date.parse(p.time_utc) !== time ||
            !/Z$/.test(String(p.time_utc || "")) ||
            lon === null || lon < 0 || lon >= 360 ||
            unwrapped === null || lat === null || Math.abs(lat)>90 ||
            distance === null || distance <= 0 ||
            rate === null || !["direct","retrograde","indeterminate"].includes(p.motion))
            return false;
        if (p.motion !== (rate>0?"direct":rate<0?"retrograde":"indeterminate"))
            return false;
        if (prevLon !== null) {
            var delta=((lon-prevLon+540)%360)-180;
            if (Math.abs(delta)>=90 ||
                Math.abs(unwrapped-prevUnwrapped-delta)>0.000001)
                return false;
        }
        if (sharedTimes && sharedTimes[i] !== time)return false;
        last=time;prevLon=lon;prevUnwrapped=unwrapped;
    }
    return true;
}
function model(payload) {
    if (!payload || typeof payload!=="object" || payload.format!==FORMAT)
        return unavailable("AWAITING SOURCE-VERIFIED M4 JSON");
    var source=payload.provenance,query=payload.query;
    if (!source || typeof source!=="object" ||
        !source.engine || !source.ephemeris_id ||
        !/^[0-9a-f]{64}$/i.test(String(source.ephemeris_sha256||"")) ||
        !source.engine_version || !source.time_data_id ||
        !query || query.origin!=="geocentric" ||
        query.position_model!=="apparent" ||
        query.frame!=="true-ecliptic-of-date")
        return unavailable("M4 SOURCE OR COORDINATE FRAME UNVERIFIED");
    var n=number(payload.sample_count), raw=payload.series;
    if (n===null || n<2 || n>721 || n%1!==0 ||
        !Array.isArray(raw) || raw.length<1 || raw.length>4 ||
        !Array.isArray(query.bodies) || query.bodies.length!==raw.length)
        return unavailable("M4 SERIES COUNT INVALID");
    var seen={},times=[],series=[];
    for (var i=0;i<raw.length;i++) {
        var entry=raw[i];
        if (!entry || typeof entry.body!=="string" ||
            seen[entry.body] || query.bodies.indexOf(entry.body)<0)
            return unavailable("M4 BODY ID INVALID");
        seen[entry.body]=true;
        if (!validRows(entry.samples,n,i===0?null:times))
            return unavailable("M4 SAMPLES INVALID OR MISALIGNED");
        if (i===0)times=entry.samples.map(function(s){return s.unix_ms;});
        series.push({body:entry.body,rows:entry.samples,color:BODY_COLORS[i]});
    }
    var relationships=Array.isArray(payload.relationships)?payload.relationships:[];
    if (relationships.length!==series.length*(series.length-1)/2)
        return unavailable("M4 RELATIONSHIPS INCOMPLETE");
    var pairs={};
    for (var j=0;j<relationships.length;j++){
        var rel=relationships[j],key;
        if (!rel || !Array.isArray(rel.bodies) || rel.bodies.length!==2 ||
            !seen[rel.bodies[0]] || !seen[rel.bodies[1]] ||
            rel.bodies[0]===rel.bodies[1] ||
            !Array.isArray(rel.samples) || rel.samples.length!==n)
            return unavailable("M4 RELATIONSHIP INVALID");
        key=rel.bodies.slice().sort().join("|");
        if (pairs[key])return unavailable("M4 RELATIONSHIP REPEATED");
        pairs[key]=true;
        for (var k=0;k<n;k++){
            var point=rel.samples[k],value=point&&number(point.longitude_separation_deg);
            if (value===null || value<0 || value>180 ||
                point.unix_ms!==times[k] ||
                !Array.isArray(point.aspects))
                return unavailable("M4 RELATIONSHIP SAMPLE INVALID");
        }
    }
    var events=Array.isArray(payload.event_markers)?payload.event_markers:[];
    for(var e=0;e<events.length;e++){
        var event=events[e],t=event&&Date.parse(event.time_utc);
        if (!event || !isFinite(t) || !/Z$/.test(String(event.time_utc||"")) ||
            t<times[0] || t>times[n-1] ||
            !Array.isArray(event.bodies) ||
            !event.bodies.every(function(body){return seen[body]===true;}))
            return unavailable("M4 EVENT MARKERS INVALID");
    }
    return {ready:true,reason:"",series:series,
        relationships:relationships,events:events,
        times:times,sampleCount:n,startMs:times[0],endMs:times[n-1],
        bodies:query.bodies,source:String(source.ephemeris_id),
        hash:String(source.ephemeris_sha256).slice(0,10),
        engine:String(source.engine),frame:query.frame};
}
function windowFor(m,zoom,pan) {
    if (!m || !m.ready)return {from:0,to:0,count:0};
    var n=m.sampleCount, z=clamp(number(zoom)||1,1,8);
    var count=clamp(Math.ceil(n/z),Math.min(n,2),n);
    var from=Math.round((n-count)*clamp(number(pan)===null?0.5:pan,0,1));
    return {from:from,to:from+count-1,count:count};
}
function indexAtFraction(m,view,fraction) {
    if (!m || !m.ready)return -1;
    return clamp(view.from+Math.round(clamp(fraction,0,1)*
                       (view.to-view.from)),0,m.sampleCount-1);
}
function selectedIndex(m,selected,hovered) {
    if (!m || !m.ready)return -1;
    var value=selected>=0?selected:hovered>=0?hovered:m.sampleCount-1;
    return clamp(Math.floor(value),0,m.sampleCount-1);
}
function wheelPositions(m,index) {
    if (!m || !m.ready || index<0)return [];
    return m.series.map(function(entry){
        var p=entry.rows[index],rad=p.longitude_deg*Math.PI/180;
        return {body:entry.body,color:entry.color,
                longitude_deg:p.longitude_deg,
                latitude_deg:p.latitude_deg,
                x:0.5+0.36*Math.sin(rad),
                y:0.5-0.36*Math.cos(rad)};
    });
}
function nearestWheelBody(m,index,x,y) {
    var candidates=wheelPositions(m,index),closest=null,score=0.1*0.1;
    for(var i=0;i<candidates.length;i++){
        var p=candidates[i],d=(p.x-x)*(p.x-x)+(p.y-y)*(p.y-y);
        if(d<=score){score=d;closest=p.body;}
    }
    return closest;
}
function rangeFor(m,view,mode) {
    if(!m || !m.ready)return {min:0,max:1};
    var vals=[];
    if(mode==="aspects"){
        m.relationships.forEach(function(pair){
            for(var i=view.from;i<=view.to;i++)
                vals.push(pair.samples[i].longitude_separation_deg);
        });
    }else{
        m.series.forEach(function(s){
            for(var i=view.from;i<=view.to;i++)
                vals.push(s.rows[i].unwrapped_longitude_deg);
        });
    }
    if(!vals.length)return {min:0,max:1};
    var lo=Math.min.apply(null,vals),hi=Math.max.apply(null,vals);
    var margin=Math.max((hi-lo)*0.12,0.1);
    return {min:lo-margin,max:hi+margin};
}
function chartX(index,view,width) {
    return (index-view.from)/Math.max(1,view.to-view.from)*width;
}
function chartY(value,range,height) {
    return (range.max-value)/Math.max(0.000001,range.max-range.min)*height;
}
function valueLabel(m,index,body) {
    if(!m || !m.ready || index<0)return "--";
    var series=m.series.find(function(s){return s.body===body;});
    if(!series)return "--";
    var point=series.rows[index];
    return body.toUpperCase()+"  "+point.longitude_deg.toFixed(3)+"°"+
      "  "+point.motion.toUpperCase()+" "+
      point.longitude_rate_deg_per_day.toFixed(3)+"°/DAY";
}
function axisText(ms) {
    if(number(ms)===null)return "--";
    return new Date(ms).toISOString().slice(0,16).replace("T"," ")+"Z";
}
