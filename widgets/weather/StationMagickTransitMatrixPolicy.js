.pragma library
// M8k // Strict multi-natal x multi-transit JPL source and event matrix.
// No astronomical calculations, storage, external URLs or implicit locations.
var REQUEST_FORMAT="post-apollo.weather.magick-natal-transit-matrix.m8k.v1";
var RESULT_FORMAT="post-apollo.weather.magick-natal-transit-matrix-result.m8k.v1";
var TARGETS=["sun","moon","mercury","venus","mars_barycenter",
    "jupiter_barycenter","saturn_barycenter","uranus_barycenter",
    "neptune_barycenter","pluto_barycenter"];
var NAIF={sun:10,moon:301,mercury:199,venus:299,mars_barycenter:4,
    jupiter_barycenter:5,saturn_barycenter:6,uranus_barycenter:7,
    neptune_barycenter:8,pluto_barycenter:9};
var ASPECTS={conjunction:0,sextile:60,square:90,trine:120,opposition:180};
var ANGLES=[0,60,90,120,180];
var SPANS=[1,7,14,31];
var PAGE_SIZE=10;
var MAX_PAIR_SAMPLES=2200;
var MAX_STATION_SAMPLES=3000;
function hash(x){return typeof x==="string"&&/^[0-9a-fA-F]{64}$/.test(x);}
function degree(v){return typeof v==="number"&&isFinite(v)&&v>=0&&v<360;}
function utc(s){
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s))return NaN;
    var ms=Date.parse(s);
    return isFinite(ms)&&new Date(ms).toISOString().slice(0,19)+"Z"===s?ms:NaN;
}
function day(s){
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return "";
    var ms=utc(s+"T00:00:00Z");
    if(!isFinite(ms))return "";
    var yr=new Date(ms).getUTCFullYear();
    return yr>=1901&&yr<=2099?s:"";
}
function sourceNatal(chart){
    if(!chart||chart.format!=="post-apollo.weather.magick-natal-chart.m8a.v1"||
        !isFinite(utc(chart.epoch_utc))||
        chart.origin!=="topocentric"||chart.frame!=="true-ecliptic-of-date"||
        chart.position_model!=="apparent"||chart.zodiac!=="tropical"||
        !["whole-sign","equal"].includes(chart.house_system)||
        !chart.provenance||chart.provenance.engine!=="skyfield"||
        !hash(chart.provenance.ephemeris_sha256)||
        !chart.observer||chart.observer.elevation_m!==0||
        typeof chart.observer.latitude_deg!=="number"||
        typeof chart.observer.longitude_deg!=="number"||
        !isFinite(chart.observer.latitude_deg)||
        !isFinite(chart.observer.longitude_deg)||
        chart.observer.latitude_deg< -90||chart.observer.latitude_deg>90||
        chart.observer.longitude_deg< -180||chart.observer.longitude_deg>180||
        !Array.isArray(chart.positions)||chart.positions.length!==10)return false;
    for(var i=0;i<TARGETS.length;i++){
        var id=TARGETS[i],entries=chart.positions.filter(function(p){return p&&p.id===id;});
        if(entries.length!==1||entries[0].naif_id!==NAIF[id]||
            !degree(entries[0].longitude_deg))return false;
    }
    return true;
}
function validBodies(items){
    return Array.isArray(items)&&items.length>=1&&items.length<=3&&
        new Set(items).size===items.length&&
        items.every(function(id){return TARGETS.indexOf(id)>=0;});
}
function request(chart,startDate,spanDays,natalBodies,transitBodies,aspects,step){
    if(!sourceNatal(chart)||!day(startDate)||SPANS.indexOf(spanDays)<0||
        !validBodies(natalBodies)||!validBodies(transitBodies)||
        !Array.isArray(aspects)||aspects.length<1||aspects.length>5||
        new Set(aspects).size!==aspects.length||
        aspects.some(function(a){return ANGLES.indexOf(a)<0;})||
        (step!==30&&step!==60))return null;
    var start=startDate+"T00:00:00Z";
    var end=new Date(Date.parse(start)+spanDays*86400000);
    if(end.getUTCFullYear()>2099)return null;
    var count=Math.ceil(spanDays*24*60/step)+1;
    var stationCount=spanDays*24*4+1;
    if(count*natalBodies.length*transitBodies.length>MAX_PAIR_SAMPLES||
       stationCount*transitBodies.length>MAX_STATION_SAMPLES)return null;
    return {format:REQUEST_FORMAT,natal_epoch_utc:chart.epoch_utc,
        start_utc:start,end_utc:end.toISOString().slice(0,19)+"Z",
        latitude_deg:chart.observer.latitude_deg,
        longitude_deg:chart.observer.longitude_deg,
        expected_ephemeris_sha256:chart.provenance.ephemeris_sha256.toLowerCase(),
        natal_bodies:natalBodies.slice(),transit_bodies:transitBodies.slice(),
        sample_minutes:step,
        aspects_deg:aspects.slice().sort(function(a,b){return a-b;}),
        include_stations:true};
}
function fail(reason){return {ready:false,reason:reason||"VERIFIED JPL MATRIX REQUIRED",
    natals:[],series:[],matrix:[],events:[]};}
function sep(a,b){var d=Math.abs(a-b)%360;return Math.min(d,360-d);}
function key(natal,transit){return natal+"|"+transit;}
function validate(raw,req,chart){
    if(!raw||!req||!sourceNatal(chart)||raw.format!==RESULT_FORMAT||
       !raw.source||raw.source.engine!=="skyfield"||
       !hash(raw.source.ephemeris_sha256)||
       raw.source.ephemeris_sha256.toLowerCase()!==req.expected_ephemeris_sha256||
       raw.source.position_model!=="topocentric-apparent"||
       raw.source.coordinate_frame!=="true-ecliptic-of-date"||
       !raw.observer||raw.observer.elevation_m!==0||
       raw.observer.latitude_deg!==req.latitude_deg||
       raw.observer.longitude_deg!==req.longitude_deg||
       raw.natal_epoch_utc!==req.natal_epoch_utc||
       raw.start_utc!==req.start_utc||raw.end_utc!==req.end_utc||
       raw.sample_minutes!==req.sample_minutes||
       raw.include_stations!==true||!Array.isArray(raw.aspects_deg)||
       raw.aspects_deg.length!==req.aspects_deg.length||
       raw.aspects_deg.some(function(x,i){return x!==req.aspects_deg[i];})||
       !Array.isArray(raw.natal_bodies)||
       raw.natal_bodies.length!==req.natal_bodies.length||
       raw.natal_bodies.some(function(x,i){return x!==req.natal_bodies[i];})||
       !Array.isArray(raw.transit_bodies)||
       raw.transit_bodies.length!==req.transit_bodies.length||
       raw.transit_bodies.some(function(x,i){return x!==req.transit_bodies[i];})||
       !Array.isArray(raw.natal_longitudes)||
       raw.natal_longitudes.length!==req.natal_bodies.length||
       !Array.isArray(raw.series)||raw.series.length!==req.transit_bodies.length||
       !Array.isArray(raw.matrix)||
       raw.matrix.length!==req.natal_bodies.length*req.transit_bodies.length||
       !Array.isArray(raw.events)||raw.events.length>150||
       !raw.limitations||
       raw.limitations.crossing_search_not_tangency_complete!==true||
       raw.limitations.station_search_not_all_turns_guaranteed!==true||
       raw.limitations.station_rate_scan_interval_minutes_max!==15||
       raw.limitations.station_velocity_central_difference_minutes!==20||
       raw.limitations.station_time_bracket_seconds!==60||
       raw.limitations.contact_time_precision_seconds!==1||
       raw.limitations.stations_not_natal_pairs!==true||
       raw.limitations.chart_uses_respective_equinoxes_of_date!==true||
       raw.limitations.medical_or_spiritual_causality_claim!==false)
        return fail("SOURCE OR NATAL IDENTITY MISMATCH");
    var start=utc(req.start_utc),end=utc(req.end_utc);
    if(!isFinite(start)||!isFinite(end)||end<=start)return fail("INVALID UTC RANGE");
    var expectedCount=Math.ceil((end-start)/(req.sample_minutes*60000))+1;
    if(raw.sample_count!==expectedCount)return fail("SAMPLE COUNT MISMATCH");
    var natals=[],expectedNatal={};
    for(var n=0;n<req.natal_bodies.length;n++){
        var id=req.natal_bodies[n],entry=raw.natal_longitudes[n];
        var original=chart.positions.find(function(p){return p.id===id;});
        if(!entry||entry.id!==id||!degree(entry.longitude_deg)||
           !original||sep(original.longitude_deg,entry.longitude_deg)>0.001)
            return fail("NATAL LONGITUDE NOT VERIFIED");
        natals.push({id:id,longitude_deg:entry.longitude_deg});
        expectedNatal[id]=entry.longitude_deg;
    }
    var series=[];
    for(var t=0;t<req.transit_bodies.length;t++){
        var src=raw.series[t];
        if(!src||src.id!==req.transit_bodies[t]||
           src.sample_count!==expectedCount||!Array.isArray(src.timeline)||
           src.timeline.length<2||src.timeline.length>300)
            return fail("MOVING BODY SERIES NOT VERIFIED");
        var last=start-1,points=[];
        for(var i=0;i<src.timeline.length;i++){
            var point=src.timeline[i],ms=point&&utc(point.epoch_utc);
            if(!isFinite(ms)||ms<=last||ms<start||ms>end||
               !degree(point.longitude_deg))
                return fail("SOURCE SAMPLE INVALID");
            points.push({utc:point.epoch_utc,ms:ms,
                longitude_deg:point.longitude_deg});
            last=ms;
        }
        if(points[0].ms!==start||last!==end)
            return fail("SAMPLE ENDPOINT MISSING");
        series.push({id:src.id,points:points,sample_count:expectedCount});
    }
    var cells=[],cellMap={};
    for(var ci=0;ci<raw.matrix.length;ci++){
        var c=raw.matrix[ci],nl=req.natal_bodies[ci%req.natal_bodies.length],
            tl=req.transit_bodies[Math.floor(ci/req.natal_bodies.length)];
        if(!c||c.natal_body!==nl||c.transit_body!==tl||
           !Number.isInteger(c.aspect_count)||c.aspect_count<0||
           c.aspect_count>150)return fail("PAIR MATRIX INVALID");
        var idKey=key(nl,tl);
        if(Object.prototype.hasOwnProperty.call(cellMap,idKey))
            return fail("DUPLICATE PAIR");
        cellMap[idKey]=0;
        cells.push({natal_body:nl,transit_body:tl,aspect_count:c.aspect_count});
    }
    var events=[],previous=start-1,stationKeys={};
    for(var ei=0;ei<raw.events.length;ei++){
        var e=raw.events[ei],ms=e&&utc(e.utc);
        if(!isFinite(ms)||ms<start||ms>end||ms<previous||
           req.transit_bodies.indexOf(e.transit_body)<0)
            return fail("UNVERIFIED EVENT TIME/BODY");
        if(e.type==="aspect"){
            var cellKey=key(e.natal_body,e.transit_body);
            if(!Object.prototype.hasOwnProperty.call(cellMap,cellKey)||
               !Object.prototype.hasOwnProperty.call(ASPECTS,e.aspect)||
               e.aspect_target_deg!==ASPECTS[e.aspect]||
               req.aspects_deg.indexOf(e.aspect_target_deg)<0||
               !["prograde","retrograde","stationary"].includes(e.direction)||
               typeof e.residual_deg!=="number"||
               !isFinite(e.residual_deg)||e.residual_deg<0||e.residual_deg>0.1)
                return fail("ASPECT EVENT NOT SOURCE VERIFIED");
            cellMap[cellKey]++;
        }else if(e.type==="station"){
            var sid=e.utc+"|"+e.transit_body;
            if(e.natal_body!==null||
               Object.prototype.hasOwnProperty.call(stationKeys,sid)||
               !["direct","retrograde"].includes(e.direction)||
               !degree(e.longitude_deg)||
               typeof e.velocity_deg_day!=="number"||
               !isFinite(e.velocity_deg_day)||
               Math.abs(e.velocity_deg_day)>1||
               e.uncertainty_seconds!==60)
                return fail("DUPLICATE OR INVALID STATION");
            stationKeys[sid]=true;
        }else return fail("UNKNOWN EVENT TYPE");
        events.push({utc:e.utc,ms:ms,type:e.type,
            natal_body:e.natal_body,transit_body:e.transit_body,
            aspect:e.type==="aspect"?e.aspect:"",
            degrees:e.type==="aspect"?e.aspect_target_deg:null,
            direction:e.direction,
            residual_deg:e.type==="aspect"?e.residual_deg:null,
            longitude_deg:e.type==="station"?e.longitude_deg:null,
            velocity_deg_day:e.type==="station"?e.velocity_deg_day:null});
        previous=ms;
    }
    for(var cidx=0;cidx<cells.length;cidx++){
        var cell=cells[cidx];
        if(cellMap[key(cell.natal_body,cell.transit_body)]!==cell.aspect_count)
            return fail("PAIR COUNT DIFFERS FROM JPL EVENTS");
    }
    return {ready:true,reason:"",natal_bodies:req.natal_bodies.slice(),
        transit_bodies:req.transit_bodies.slice(),natals:natals,
        series:series,matrix:cells,events:events,
        start_utc:req.start_utc,end_utc:req.end_utc,
        sample_count:expectedCount,source_hash:req.expected_ephemeris_sha256};
}
function filtered(model,natal,transit,kind,reverse){
    if(!model||!model.ready||!Array.isArray(model.events))return [];
    var selected=model.events.filter(function(e){
        if(kind!=="ALL"&&e.type!==kind)return false;
        if(transit&&e.transit_body!==transit)return false;
        if(e.type==="station")return natal===""; // station has no natal pair
        return !natal||e.natal_body===natal;
    });
    return reverse?selected.slice().reverse():selected;
}
function page(model,natal,transit,kind,reverse,index){
    var items=filtered(model,natal,transit,kind,reverse);
    var pages=Math.max(1,Math.ceil(items.length/PAGE_SIZE));
    var at=Number.isInteger(index)&&index>=0?Math.min(index,pages-1):0;
    return {items:items.slice(at*PAGE_SIZE,(at+1)*PAGE_SIZE),
        total:items.length,pages:pages,index:at,
        first:items.length?at*PAGE_SIZE+1:0,
        last:Math.min(items.length,(at+1)*PAGE_SIZE)};
}
function eventKey(e){return !e?"":e.utc+"|"+e.natal_body+"|"+e.transit_body+"|"+e.type+"|"+e.aspect;}
function nearestMinute(value){
    var ms=utc(value);
    if(!isFinite(ms))return "";
    var d=new Date(Math.round(ms/60000)*60000);
    return d.getUTCFullYear()<1901||d.getUTCFullYear()>2099?""
        :d.toISOString().slice(0,16)+":00Z";
}
function shortName(id){
    var map={sun:"SUN",moon:"MON",mercury:"MER",venus:"VEN",
        mars_barycenter:"MAR",jupiter_barycenter:"JUP",
        saturn_barycenter:"SAT",uranus_barycenter:"URA",
        neptune_barycenter:"NEP",pluto_barycenter:"PLU"};
    return map[id]||"--";
}
