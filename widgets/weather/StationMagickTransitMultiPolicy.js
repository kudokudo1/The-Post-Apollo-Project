.pragma library
// M8h // Explicit three-body source contract and inspectable event-browser model.
// All graph points, angular crossings and stations originate in M8f/M8h JPL.
// No generated dates, inferred GPS, additional ephemeris or profile storage.
var REQUEST_FORMAT="post-apollo.weather.magick-transit-multi.m8h.v1";
var RESULT_FORMAT="post-apollo.weather.magick-transit-multi-result.m8h.v1";
var TARGETS=["sun","moon","mercury","venus","mars_barycenter",
    "jupiter_barycenter","saturn_barycenter","uranus_barycenter",
    "neptune_barycenter","pluto_barycenter"];
var NAIF={sun:10,moon:301,mercury:199,venus:299,mars_barycenter:4,
    jupiter_barycenter:5,saturn_barycenter:6,uranus_barycenter:7,
    neptune_barycenter:8,pluto_barycenter:9};
var ANGLES=[0,60,90,120,180];
var ASPECTS={conjunction:0,sextile:60,square:90,trine:120,opposition:180};
var DAYS=[1,7,14,31];
function sha(x){return typeof x==="string"&&/^[0-9a-f]{64}$/i.test(x);}
function degree(x){return typeof x==="number"&&isFinite(x)&&x>=0&&x<360;}
function utc(text){
    if(typeof text!=="string"||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(text))return NaN;
    var t=Date.parse(text);
    return isFinite(t)&&new Date(t).toISOString().slice(0,19)+"Z"===text?t:NaN;
}
function sourceNatal(chart){
    if(!chart||chart.format!=="post-apollo.weather.magick-natal-chart.m8a.v1"||
       !isFinite(utc(chart.epoch_utc))||
       chart.origin!=="topocentric"||chart.frame!=="true-ecliptic-of-date"||
       chart.position_model!=="apparent"||chart.zodiac!=="tropical"||
       !["equal","whole-sign"].includes(chart.house_system)||
       !chart.provenance||chart.provenance.engine!=="skyfield"||
       !sha(chart.provenance.ephemeris_sha256)||
       !chart.observer||chart.observer.elevation_m!==0||
       typeof chart.observer.latitude_deg!=="number"||
       typeof chart.observer.longitude_deg!=="number"||
       !isFinite(chart.observer.latitude_deg)||
       !isFinite(chart.observer.longitude_deg)||
       chart.observer.latitude_deg < -90||chart.observer.latitude_deg>90||
       chart.observer.longitude_deg < -180||chart.observer.longitude_deg>180||
       !Array.isArray(chart.positions)||chart.positions.length!==10)
       return false;
    for(var i=0;i<TARGETS.length;i++){
        var id=TARGETS[i];
        var matches=chart.positions.filter(function(p){return p&&p.id===id;});
        if(matches.length!==1||matches[0].naif_id!==NAIF[id]||
           !degree(matches[0].longitude_deg))return false;
    }
    return true;
}
function day(text){
    if(typeof text!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(text))return "";
    var ms=Date.parse(text+"T00:00:00Z");
    if(!isFinite(ms))return "";
    var d=new Date(ms);
    return d.getUTCFullYear()>=1901&&d.getUTCFullYear()<=2099&&
        d.toISOString().slice(0,10)===text?text:"";
}
function request(chart,startDate,days,natalBody,moving,aspects,step){
    if(!sourceNatal(chart)||!day(startDate)||DAYS.indexOf(days)<0||
       TARGETS.indexOf(natalBody)<0||
       !Array.isArray(moving)||moving.length<1||moving.length>3||
       new Set(moving).size!==moving.length||
       moving.some(function(b){return TARGETS.indexOf(b)<0;})||
       !Array.isArray(aspects)||aspects.length<1||aspects.length>5||
       new Set(aspects).size!==aspects.length||
       aspects.some(function(a){return ANGLES.indexOf(a)<0;})||
       (step!==30&&step!==60))return null;
    var begin=startDate+"T00:00:00Z",end=new Date(
        Date.parse(begin)+days*86400000);
    if(end.getUTCFullYear()>2099)return null;
    return {format:REQUEST_FORMAT,natal_epoch_utc:chart.epoch_utc,
        start_utc:begin,end_utc:end.toISOString().slice(0,19)+"Z",
        latitude_deg:chart.observer.latitude_deg,
        longitude_deg:chart.observer.longitude_deg,
        expected_ephemeris_sha256:chart.provenance.ephemeris_sha256.toLowerCase(),
        natal_body:natalBody,transit_bodies:moving.slice(),
        sample_minutes:step,aspects_deg:aspects.slice().sort(function(a,b){return a-b;}),
        include_stations:true};
}
function fail(reason){return {ready:false,reason:reason||"VERIFIED MULTI-JPL DATA REQUIRED",
    series:[],events:[],natal_body:"",start_utc:"",end_utc:""};}
function angularSep(a,b){var d=Math.abs(a-b)%360;return Math.min(d,360-d);}
function validate(raw,req,natal) {
    if(!raw||!req||!sourceNatal(natal)||raw.format!==RESULT_FORMAT||
       !raw.source||raw.source.engine!=="skyfield"||
       !sha(raw.source.ephemeris_sha256)||
       raw.source.ephemeris_sha256.toLowerCase()!==req.expected_ephemeris_sha256||
       raw.source.position_model!=="topocentric-apparent"||
       raw.source.coordinate_frame!=="true-ecliptic-of-date"||
       !raw.observer||raw.observer.elevation_m!==0||
       raw.observer.latitude_deg!==req.latitude_deg||
       raw.observer.longitude_deg!==req.longitude_deg||
       raw.natal_epoch_utc!==req.natal_epoch_utc||
       raw.natal_body!==req.natal_body||
       raw.start_utc!==req.start_utc||raw.end_utc!==req.end_utc||
       raw.sample_minutes!==req.sample_minutes||
       !degree(raw.natal_longitude_deg)||
       !Array.isArray(raw.transit_bodies)||
       raw.transit_bodies.length!==req.transit_bodies.length||
       raw.transit_bodies.some(function(b,i){return b!==req.transit_bodies[i];})||
       !Array.isArray(raw.aspects_deg)||
       raw.aspects_deg.length!==req.aspects_deg.length||
       raw.aspects_deg.some(function(a,i){return a!==req.aspects_deg[i];})||
       raw.include_stations!==true||
       !Array.isArray(raw.series)||raw.series.length!==req.transit_bodies.length||
       !Array.isArray(raw.events)||raw.events.length>150||
       !raw.limitations||
       raw.limitations.crossing_search_not_tangency_complete!==true||
       raw.limitations.station_search_not_all_turns_guaranteed!==true||
       raw.limitations.station_velocity_central_difference_minutes!==20||
       raw.limitations.station_time_bracket_seconds!==60||
       raw.limitations.contact_time_precision_seconds!==1||
       raw.limitations.chart_uses_respective_equinoxes_of_date!==true||
       raw.limitations.medical_or_spiritual_causality_claim!==false)
        return fail("SOURCE CONTRACT MISMATCH");
    var original=natal.positions.find(function(p){return p.id===req.natal_body;});
    if(!original||angularSep(original.longitude_deg,raw.natal_longitude_deg)>0.001)
        return fail("NATAL LONGITUDE MISMATCH");
    var start=utc(req.start_utc),end=utc(req.end_utc);
    if(!isFinite(start)||!isFinite(end)||end<=start)return fail("UTC WINDOW INVALID");
    var count=Math.ceil((end-start)/(req.sample_minutes*60000))+1;
    var tracks=[];
    for(var i=0;i<raw.series.length;i++){
        var s=raw.series[i];
        if(!s||s.id!==req.transit_bodies[i]||
           s.sample_count!==count||
           !Array.isArray(s.timeline)||s.timeline.length<2||
           s.timeline.length>300)return fail("SOURCE SERIES INCOMPLETE");
        var points=[],last=start-1;
        for(var j=0;j<s.timeline.length;j++){
            var p=s.timeline[j],ms=p&&utc(p.epoch_utc);
            if(!isFinite(ms)||ms<=last||ms<start||ms>end||
               !degree(p.longitude_deg)||
               typeof p.relative_unwrapped_deg!=="number"||
               !isFinite(p.relative_unwrapped_deg)||
               angularSep(p.relative_unwrapped_deg%360,
                  (p.longitude_deg-raw.natal_longitude_deg+360)%360)>0.002)
               return fail("SAMPLE SOURCE GEOMETRY INVALID");
            points.push({utc:p.epoch_utc,ms:ms,
                longitude_deg:p.longitude_deg,relative_deg:p.relative_unwrapped_deg});
            last=ms;
        }
        if(points[0].ms!==start||last!==end)
            return fail("SERIES UTC BOUNDARIES INVALID");
        tracks.push({id:s.id,sample_count:count,points:points});
    }
    var events=[],lastEvent=start-1;
    for(var k=0;k<raw.events.length;k++){
        var e=raw.events[k],when=e&&utc(e.utc);
        if(!isFinite(when)||when<start||when>end||when<lastEvent||
           e.natal_body!==req.natal_body||
           req.transit_bodies.indexOf(e.transit_body)<0)
            return fail("EVENT UTC/SOURCE INVALID");
        if(e.type==="aspect"){
            if(!Object.prototype.hasOwnProperty.call(ASPECTS,e.aspect)||
               e.aspect_target_deg!==ASPECTS[e.aspect]||
               req.aspects_deg.indexOf(e.aspect_target_deg)<0||
               !["prograde","retrograde","stationary"].includes(e.direction)||
               typeof e.residual_deg!=="number"||
               !isFinite(e.residual_deg)||e.residual_deg<0||e.residual_deg>0.1)
                return fail("ASPECT NOT SOURCE-VERIFIED");
        }else if(e.type==="station"){
            if(!["direct","retrograde"].includes(e.direction)||
               !degree(e.longitude_deg)||
               typeof e.velocity_deg_day!=="number"||
               !isFinite(e.velocity_deg_day)||
               Math.abs(e.velocity_deg_day)>1||
               e.uncertainty_seconds!==60)
                return fail("STATION EVIDENCE INVALID");
        }else return fail("UNKNOWN EVENT TYPE");
        events.push({utc:e.utc,ms:when,type:e.type,
            transit_body:e.transit_body,natal_body:e.natal_body,
            aspect:e.type==="aspect"?e.aspect:"",
            degrees:e.type==="aspect"?e.aspect_target_deg:null,
            direction:e.direction,
            residual_deg:e.type==="aspect"?e.residual_deg:null,
            longitude_deg:e.type==="station"?e.longitude_deg:null,
            velocity_deg_day:e.type==="station"?e.velocity_deg_day:null});
        lastEvent=when;
    }
    return {ready:true,reason:"",natal_body:req.natal_body,
        start_utc:req.start_utc,end_utc:req.end_utc,
        series:tracks,events:events,sample_count:count,
        source_hash:req.expected_ephemeris_sha256,
        natal_longitude_deg:raw.natal_longitude_deg};
}
function browserEvents(model,kind,planet,descending){
    if(!model||!model.ready)return [];
    var items=model.events.filter(function(e){
        return (kind==="ALL"||e.type===kind)&&(!planet||e.transit_body===planet);
    });
    return descending?items.slice().reverse():items;
}
function graph(model,width,height){
    if(!model||!model.ready||width<80||height<45)return null;
    var from=utc(model.start_utc),to=utc(model.end_utc);
    var lo=Infinity,hi=-Infinity;
    for(var i=0;i<model.series.length;i++)
        for(var j=0;j<model.series[i].points.length;j++){
            var v=model.series[i].points[j].relative_deg;
            lo=Math.min(lo,v);hi=Math.max(hi,v);
        }
    if(!isFinite(lo)||!isFinite(hi)||to<=from)return null;
    var size=Math.max(6,hi-lo),center=(lo+hi)/2;
    lo=center-size*.6;hi=center+size*.6;
    function x(ms){return 8+(width-16)*(ms-from)/(to-from);}
    function y(value){return 6+(height-12)*(hi-value)/(hi-lo);}
    return {
        lines:model.series.map(function(s){return {
            id:s.id,points:s.points.map(function(p){
                return {x:x(p.ms),y:y(p.relative_deg)};
            })};}),
        events:model.events.map(function(e){return {
            x:x(e.ms),utc:e.utc,type:e.type,body:e.transit_body};}),
        low:lo,high:hi,
    };
}
function nearestMinute(exactUtc){
    var when=utc(exactUtc);
    if(!isFinite(when))return "";
    var result=new Date(Math.round(when/60000)*60000);
    return result.getUTCFullYear()>2099||result.getUTCFullYear()<1901
        ?"":result.toISOString().slice(0,16)+":00Z";
}
function shortLabel(id){
    var labels={sun:"SUN",moon:"MON",mercury:"MER",venus:"VEN",
        mars_barycenter:"MAR",jupiter_barycenter:"JUP",
        saturn_barycenter:"SAT",uranus_barycenter:"URA",
        neptune_barycenter:"NEP",pluto_barycenter:"PLU"};
    return labels[id]||"--";
}
