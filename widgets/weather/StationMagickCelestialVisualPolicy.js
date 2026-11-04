.pragma library

// M5 // Read-only presentation policy for M4 celestial visual-data.v1.
// No provider process, no astronomical computation, no invented sample.
// A production instrument requires validated source provenance.
var FORMAT = "post-apollo.weather.celestial-visual-data.v1";
var MODES = ["wheel", "motion", "aspects", "relations"];
var SIGNS = ["AR", "TA", "GE", "CN", "LE", "VI",
             "LI", "SC", "SG", "CP", "AQ", "PI"];
// True Unicode zodiac symbols; SIGNS remains compact Latin text for
// existing M5d inspector/backwards-compatible export.
var ZODIAC_GLYPHS = ["♈","♉","♊","♋","♌","♍",
                     "♎","♏","♐","♑","♒","♓"];
// Fire, earth, air, water in the canonical Post-Apollo palette.
var ZODIAC_COLORS = ["#ED981A","#9ECE6A","#55CFCA","#C74EC7",
                     "#ED981A","#9ECE6A","#55CFCA","#C74EC7",
                     "#ED981A","#9ECE6A","#55CFCA","#C74EC7"];
function zodiacGlyph(index) {
    return typeof index==="number" && index>=0 && index<12 &&
           Math.floor(index)===index ? ZODIAC_GLYPHS[index] : "";
}
function zodiacColor(index) {
    return typeof index==="number" && index>=0 && index<12 &&
           Math.floor(index)===index ? ZODIAC_COLORS[index] : "#DCF3FA";
}
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


// M5d // Pure read-only event navigation. Event timestamps are exact-search
// results; selected body coordinates are explicitly the nearest M4 sample.
function nearestSampleIndex(m,unixMs) {
    if(!m || !m.ready || number(unixMs)===null)return -1;
    var times=m.times,lo=0,hi=times.length-1;
    if(unixMs<=times[0])return 0;
    if(unixMs>=times[hi])return hi;
    while(lo+1<hi) {
        var mid=Math.floor((lo+hi)/2);
        if(times[mid]<unixMs)lo=mid;
        else hi=mid;
    }
    return unixMs-times[lo]<=times[hi]-unixMs?lo:hi;
}
function visibleEvents(m,view) {
    if(!m || !m.ready || !view || view.count<2)return [];
    var start=m.times[view.from],end=m.times[view.to];
    if(number(start)===null || number(end)===null)return [];
    return m.events.filter(function(event){
        var ms=Date.parse(event.time_utc);
        return ms>=start && ms<=end;
    }).sort(function(a,b){return Date.parse(a.time_utc)-Date.parse(b.time_utc);});
}
function eventAt(m,view,ordinal) {
    var events=visibleEvents(m,view);
    return typeof ordinal==="number" && ordinal>=0 &&
        ordinal<events.length && Math.floor(ordinal)===ordinal
        ? events[ordinal] : null;
}
function stepEvent(m,view,currentOrdinal,direction) {
    var events=visibleEvents(m,view);
    if(!events.length)return null;
    var next;
    if(typeof currentOrdinal!=="number" || currentOrdinal<0 ||
       currentOrdinal>=events.length || Math.floor(currentOrdinal)!==currentOrdinal)
        next=direction<0?events.length-1:0;
    else next=(currentOrdinal+(direction<0?-1:1)+events.length)%events.length;
    var event=events[next];
    return {ordinal:next,event:event,
            sampleIndex:nearestSampleIndex(m,Date.parse(event.time_utc))};
}
function eventLabel(m,view,ordinal) {
    var events=visibleEvents(m,view);
    if(!events.length)return "NO CALCULATED EVENTS IN VIEW";
    var e=eventAt(m,view,ordinal);
    if(!e)return events.length+" EVENTS // SELECT TO INSPECT";
    var kind=e.contact_kind==="tangent_candidate"?"GRAZING CANDIDATE":
        e.type==="apparent_longitude_station"?"ESTIMATED STATION":"ANGLE CROSSING";
    return (ordinal+1)+"/"+events.length+"  "+
        String(e.name||"event").replace(/_/g," ").toUpperCase()+
        " // "+kind+" // "+axisText(Date.parse(e.time_utc));
}
function bodyDetails(m,index,body) {
    if(!m || !m.ready || index<0)return "NO POSITION SELECTED";
    var entry=m.series.find(function(s){return s.body===body;});
    if(!entry || index>=entry.rows.length)return "NO POSITION SELECTED";
    var p=entry.rows[index],signIndex=Math.floor(p.longitude_deg/30)%12;
    return body.toUpperCase()+"  "+p.longitude_deg.toFixed(3)+"° "+
        SIGNS[signIndex]+" "+(p.longitude_deg%30).toFixed(2)+"°"+
        "  LAT "+p.latitude_deg.toFixed(2)+"°  "+
        p.distance_au.toFixed(4)+" AU";
}
function pairDetails(m,index) {
    if(!m || !m.ready || index<0)return "NO RELATIONSHIP SELECTED";
    if(!m.relationships.length)return "SINGLE BODY // NO PAIR";
    var rel=m.relationships[0],sample=rel.samples[index];
    if(!sample)return "NO RELATIONSHIP SELECTED";
    var aspects=sample.aspects.map(function(a){return String(a.name||"").toUpperCase();});
    return rel.bodies.map(function(body){return body.toUpperCase();}).join(" / ")+
        "  SEPARATION "+sample.longitude_separation_deg.toFixed(3)+"°"+
        (aspects.length?"  "+aspects.join(", "):"  NO ASPECT IN ORB");
}


// M5f // Plot geometry is shared between Canvas painting and pointer mapping.
// The margins reserve real space for labels instead of overwriting the curve.
function chartLayout(width,height) {
    var w=number(width),h=number(height);
    if(w===null || h===null || w<=0 || h<=0)
        return {left:0,top:0,width:1,height:1,right:1,bottom:1};
    var left=Math.min(52,Math.max(36,Math.floor(w*0.14)));
    var right=8,top=28,bottom=23;
    return {
        left:left,top:top,
        width:Math.max(1,w-left-right),
        height:Math.max(1,h-top-bottom),
        right:Math.max(left+1,w-right),
        bottom:Math.max(top+1,h-bottom)
    };
}
function plotX(index,view,layout) {
    return layout.left+chartX(index,view,layout.width);
}
function plotY(value,range,layout) {
    return layout.top+chartY(value,range,layout.height);
}
function plotFraction(pixelX,width,height) {
    var layout=chartLayout(width,height);
    return clamp((pixelX-layout.left)/layout.width,0,1);
}
function shortBodyName(body) {
    var names={
        "sun":"SUN","moon":"MOON","mercury":"MERCURY",
        "venus":"VENUS","mars_barycenter":"MARS SYS",
        "jupiter_barycenter":"JUP SYS",
        "saturn_barycenter":"SAT SYS",
        "uranus_barycenter":"URA SYS",
        "neptune_barycenter":"NEP SYS",
        "pluto_barycenter":"PLU SYS"
    };
    return names[body] || String(body||"").toUpperCase().slice(0,12);
}
function legendRows(m,mode) {
    if(!m || !m.ready)return [];
    if(mode==="aspects")
        return m.relationships.map(function(pair,i){
            return {text:pair.bodies.map(shortBodyName).join("/"),
                    color:BODY_COLORS[i%BODY_COLORS.length],index:i};
        });
    return m.series.map(function(entry,i){
        return {text:shortBodyName(entry.body),
                color:entry.color,index:i,body:entry.body};
    });
}
function wheelLabels(m,index,width,height) {
    if(!m || !m.ready)return [];
    var pts=wheelPositions(m,index),radius=Math.max(30,Math.min(width,height)*0.36);
    var cx=width/2,cy=height/2;
    var labels=pts.map(function(p){
        var theta=p.longitude_deg*Math.PI/180;
        var x=cx+radius*Math.sin(theta),y=cy-radius*Math.cos(theta);
        var label=shortBodyName(p.body);
        var left=x+(x>cx?-1:1)*11;
        left=x>cx?left:left-label.length*6;
        return {body:p.body,color:p.color,pointX:x,pointY:y,
                x:clamp(left,3,Math.max(3,width-label.length*6-3)),
                y:clamp(y-8,11,Math.max(11,height-7)),
                label:label};
    });
    // Keep the original angular markers intact; offset only colliding text.
    for(var i=1;i<labels.length;i++) {
        for(var j=0;j<i;j++) {
            if(Math.abs(labels[i].x-labels[j].x)<70 &&
               Math.abs(labels[i].y-labels[j].y)<12)
                labels[i].y=clamp(labels[j].y+13,11,Math.max(11,height-7));
        }
    }
    return labels;
}


// M5g // One pair = one source-measured ecliptic-longitude separation.
// These angles are traditional aspect REFERENCE targets, not measured
// influences, local sky angular distances, or ephemeris predictions.
var ASPECT_GUIDES = [
    {angle:0,label:"CONJ"},
    {angle:60,label:"SEXT"},
    {angle:90,label:"SQR"},
    {angle:120,label:"TRINE"},
    {angle:180,label:"OPP"}
];
function relationAt(m,index) {
    if(!m || !m.ready || !m.relationships.length ||
       typeof index!=="number" || Math.floor(index)!==index ||
       index<0 || index>=m.sampleCount)return null;
    var pair=m.relationships[0],sample=pair.samples[index];
    if(!sample)return null;
    var a=m.series.find(function(s){return s.body===pair.bodies[0];});
    var b=m.series.find(function(s){return s.body===pair.bodies[1];});
    if(!a || !b)return null;
    return {bodies:pair.bodies.slice(),
        first:shortBodyName(a.body),second:shortBodyName(b.body),
        firstColor:a.color,secondColor:b.color,
        separation_deg:sample.longitude_separation_deg,
        aspects:sample.aspects.map(function(x){return String(x.name||"");}),
        sample_utc:sample.time_utc};
}
function relationArcPoint(degrees,width,height) {
    var d=number(degrees),w=number(width),h=number(height);
    if(d===null || w===null || h===null || w<=0 || h<=0 ||
       d<0 || d>180)return null;
    var cx=w/2,cy=Math.max(70,h*0.79);
    var radius=Math.max(20,Math.min(w*0.39,h*0.64));
    var theta=Math.PI*(1-d/180);
    return {x:cx+radius*Math.cos(theta),
            y:cy-radius*Math.sin(theta),
            cx:cx,cy:cy,radius:radius};
}
// Timelines show ONLY M4 event positions, sorted and confined to the
// currently viewed M4 sample window. Event timestamps may lie between
// sample dates. The selected visual body position remains a real sample.
function timelineMarkers(m,view) {
    if(!m || !m.ready || !view || view.count<2)return [];
    var start=m.times[view.from],end=m.times[view.to];
    if(number(start)===null || number(end)===null || end<=start)return [];
    return visibleEvents(m,view).map(function(event,ordinal) {
        var ms=Date.parse(event.time_utc);
        var kind=event.contact_kind==="tangent_candidate"?"candidate":
            event.type==="apparent_longitude_station"?"station":"crossing";
        return {ordinal:ordinal,kind:kind,time_utc:event.time_utc,
                name:String(event.name||"EVENT"),
                fraction:(ms-start)/(end-start),
                sampleIndex:nearestSampleIndex(m,ms)};
    });
}
function timelinePick(m,view,pixelX,width,tolerancePixels) {
    var x=number(pixelX),w=number(width),t=number(tolerancePixels);
    if(x===null || w===null || w<=0 || t===null || t<0)return null;
    var markers=timelineMarkers(m,view),best=null,closest=t;
    for(var i=0;i<markers.length;i++){
        var diff=Math.abs(markers[i].fraction*w-x);
        if(diff<=closest){closest=diff;best=markers[i];}
    }
    return best;
}
function timelineSampleIndex(m,view,pixelX,width) {
    if(!m || !m.ready || !view || view.count<2 ||
       number(pixelX)===null || number(width)===null || width<=0)return -1;
    var start=m.times[view.from],end=m.times[view.to];
    var frac=clamp(pixelX/width,0,1);
    return clamp(nearestSampleIndex(m,start+(end-start)*frac),
                 view.from,view.to);
}


// M5h // Slider thumb always corresponds to a REAL M4 series timestamp.
// Its fraction tracks actual UTC time, not a fabricated interpolation,
// and naturally changes when zoom/pan chooses another sample window.
function timelineHandleFraction(m,view,index) {
    if(!m || !m.ready || !view || view.count<2 ||
       number(index)===null || Math.floor(index)!==index ||
       number(view.from)===null || number(view.to)===null ||
       view.from<0 || view.to>=m.sampleCount || view.to<=view.from)
        return null;
    var first=m.times[view.from],last=m.times[view.to];
    if(last<=first)return null;
    var visible=clamp(index,view.from,view.to);
    return clamp((m.times[visible]-first)/(last-first),0,1);
}
function timelineHandleX(m,view,index,width) {
    var fraction=timelineHandleFraction(m,view,index),w=number(width);
    if(fraction===null || w===null || w<0)return null;
    return fraction*w;
}


// M5j // Fine wheel/relationship scrubbing is relative to the sample the
// gesture STARTED on. Absolute canvas X selects an unrelated timestamp and
// makes a tiny drag jump across the whole graph. The timeline slider remains
// the separate coarse/absolute navigation control.
var WHEEL_DRAG_PIXELS_PER_SAMPLE = 12;
function wheelDragIndex(m,view,startIndex,deltaX) {
    if(!m || !m.ready || !view || view.count<2 ||
       number(startIndex)===null || Math.floor(startIndex)!==startIndex ||
       number(deltaX)===null ||
       number(view.from)===null || number(view.to)===null ||
       view.to<=view.from || view.from<0 || view.to>=m.sampleCount)
        return -1;
    var origin=clamp(startIndex,view.from,view.to);
    // Symmetric thresholds: moving 6px either direction advances one
    // sample. Math.round(-0.5) would otherwise stick on the negative side.
    var steps=Math.floor(Math.abs(deltaX)/WHEEL_DRAG_PIXELS_PER_SAMPLE+0.5);
    var offset=deltaX<0 ? -steps : steps;
    return clamp(origin+offset,view.from,view.to);
}
