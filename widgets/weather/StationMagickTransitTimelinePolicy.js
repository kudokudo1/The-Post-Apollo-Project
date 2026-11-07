.pragma library
// M8g // Request/result gate for the existing offline M8f JPL crossing search.
// This file does not perform astronomy. All result claims are source-checked.
var REQUEST_FORMAT="post-apollo.weather.magick-transit-timeline.m8f.v1";
var RESULT_FORMAT="post-apollo.weather.magick-transit-timeline-result.m8f.v1";
var TARGETS=["sun","moon","mercury","venus","mars_barycenter",
    "jupiter_barycenter","saturn_barycenter","uranus_barycenter",
    "neptune_barycenter","pluto_barycenter"];
var NAIF={sun:10,moon:301,mercury:199,venus:299,
    mars_barycenter:4,jupiter_barycenter:5,saturn_barycenter:6,
    uranus_barycenter:7,neptune_barycenter:8,pluto_barycenter:9};
var ASPECT_NAMES={conjunction:0,sextile:60,square:90,trine:120,opposition:180};
var DEFAULT_ASPECTS=[0,60,90,120,180];
var SPANS=[1,7,14,31];
function sha(x){return typeof x==="string"&&/^[0-9a-fA-F]{64}$/.test(x);}
function day(x){
    if(typeof x!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(x))return "";
    var ms=Date.parse(x+"T00:00:00Z");
    if(!isFinite(ms))return "";
    var d=new Date(ms);
    return d.toISOString().slice(0,10)===x&&d.getUTCFullYear()>=1901&&
        d.getUTCFullYear()<=2099?x:"";
}
function shiftedUtc(date,days){
    if(!day(date)||SPANS.indexOf(days)<0)return "";
    var d=new Date(Date.parse(date+"T00:00:00Z")+days*86400000);
    if(!isFinite(d.getTime())||d.getUTCFullYear()>2099)return "";
    return d.toISOString().slice(0,19)+"Z";
}
function validNatal(chart) {
    if(!chart||chart.format!=="post-apollo.weather.magick-natal-chart.m8a.v1"||
       chart.zodiac!=="tropical"||chart.origin!=="topocentric"||
       chart.frame!=="true-ecliptic-of-date"||
       chart.position_model!=="apparent"||
       !["whole-sign","equal"].includes(chart.house_system)||
       !chart.provenance||chart.provenance.engine!=="skyfield"||
       !sha(chart.provenance.ephemeris_sha256)||
       !chart.observer||chart.observer.elevation_m!==0||
       typeof chart.observer.latitude_deg!=="number"||
       typeof chart.observer.longitude_deg!=="number"||
       !isFinite(chart.observer.latitude_deg)||!isFinite(chart.observer.longitude_deg)||
       chart.observer.latitude_deg< -90||chart.observer.latitude_deg>90||
       chart.observer.longitude_deg< -180||chart.observer.longitude_deg>180||
       typeof chart.epoch_utc!=="string"||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(chart.epoch_utc)||
       !isFinite(utc(chart.epoch_utc))||
       !Array.isArray(chart.positions)||chart.positions.length!==10)return false;
    for(var i=0;i<10;i++){
        var v=chart.positions.find(function(p){return p.id===TARGETS[i];});
        if(!v||v.naif_id!==NAIF[v.id]||typeof v.longitude_deg!=="number"||
           !isFinite(v.longitude_deg)||v.longitude_deg<0||
           v.longitude_deg>=360)return false;
    }
    return true;
}
function request(chart,startDate,spanDays,natalBody,transitBody,sampleMinutes){
    var end=shiftedUtc(startDate,spanDays);
    if(!validNatal(chart)||!end||
       TARGETS.indexOf(natalBody)<0||TARGETS.indexOf(transitBody)<0||
       (sampleMinutes!==30&&sampleMinutes!==60))return null;
    return {format:REQUEST_FORMAT,natal_epoch_utc:chart.epoch_utc,
        start_utc:startDate+"T00:00:00Z",end_utc:end,
        latitude_deg:chart.observer.latitude_deg,
        longitude_deg:chart.observer.longitude_deg,
        expected_ephemeris_sha256:chart.provenance.ephemeris_sha256.toLowerCase(),
        natal_body:natalBody,transit_body:transitBody,
        sample_minutes:sampleMinutes,aspects_deg:DEFAULT_ASPECTS.slice()};
}
function fail(reason){return {ready:false,reason:reason||"NO VERIFIED TIMELINE",
    timeline:[],contacts:[],sample_count:0};}
function utc(value) {
    if(typeof value!=="string"||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value))return NaN;
    var ms=Date.parse(value);
    return isFinite(ms)&&new Date(ms).toISOString().slice(0,19)+"Z"===value?ms:NaN;
}
function angle(v){return typeof v==="number"&&isFinite(v)&&v>=0&&v<360;}
function separation(a,b){var d=Math.abs(a-b)%360;return Math.min(d,360-d);}
function validate(result,req,chart){
    if(!result||!req||!validNatal(chart)||result.format!==RESULT_FORMAT||
       !result.source||result.source.engine!=="skyfield"||
       !sha(result.source.ephemeris_sha256)||
       result.source.ephemeris_sha256.toLowerCase()!==req.expected_ephemeris_sha256||
       result.source.position_model!=="topocentric-apparent"||
       result.source.coordinate_frame!=="true-ecliptic-of-date"||
       !result.observer||result.observer.elevation_m!==0||
       result.observer.latitude_deg!==req.latitude_deg||
       result.observer.longitude_deg!==req.longitude_deg||
       result.natal_epoch_utc!==req.natal_epoch_utc||
       result.start_utc!==req.start_utc||result.end_utc!==req.end_utc||
       result.natal_body!==req.natal_body||
       result.transit_body!==req.transit_body||
       result.sample_minutes!==req.sample_minutes||
       !angle(result.natal_longitude_deg)||!Number.isInteger(result.sample_count)||
       result.sample_count<2||result.sample_count>1500||
       !Array.isArray(result.timeline)||result.timeline.length<2||
       result.timeline.length>300||!Array.isArray(result.contacts)||
       result.contacts.length>250||!result.limitations||
       result.limitations.crossing_search_not_tangency_complete!==true||
       result.limitations.contact_time_precision_seconds!==1||
       result.limitations.chart_uses_respective_equinoxes_of_date!==true||
       result.limitations.medical_or_spiritual_causality_claim!==false)
       return fail("JPL TIMELINE SOURCE/CONTRACT REJECTED");
    var natal=chart.positions.find(function(p){return p.id===req.natal_body;});
    if(!natal||separation(natal.longitude_deg,result.natal_longitude_deg)>0.001)
        return fail("NATAL POSITION SOURCE MISMATCH");
    var from=utc(req.start_utc),to=utc(req.end_utc),last=from-1;
    var positions=[];
    for(var i=0;i<result.timeline.length;i++){
        var row=result.timeline[i],ms=utc(row.epoch_utc);
        if(!isFinite(ms)||ms<=last||ms<from||ms>to||
           !angle(row.longitude_deg)||
           typeof row.relative_unwrapped_deg!=="number"||
           !isFinite(row.relative_unwrapped_deg))
            return fail("TIMELINE SAMPLE INVALID");
        positions.push({utc:row.epoch_utc,ms:ms,
            longitude_deg:row.longitude_deg,
            relative_deg:row.relative_unwrapped_deg});
        last=ms;
    }
    if(result.sample_count!==Math.ceil((to-from)/(req.sample_minutes*60000))+1)
        return fail("SAMPLE COUNT INCONSISTENT");
    for(var j=0;j<positions.length;j++){
        var v=positions[j];
        var expected=((v.longitude_deg-result.natal_longitude_deg)%360+360)%360;
        var reported=((v.relative_deg%360)+360)%360;
        if(separation(expected,reported)>0.002)
            return fail("SAMPLE LONGITUDES INCONSISTENT");
    }
    if(positions[0].ms!==from||positions[positions.length-1].ms!==to)
        return fail("TIMELINE BOUNDARIES INCOMPLETE");
    var events=[],prev=from-1;
    for(var j=0;j<result.contacts.length;j++){
        var e=result.contacts[j],when=utc(e.utc);
        if(!isFinite(when)||when<from||when>to||when<prev||
           !Object.prototype.hasOwnProperty.call(ASPECT_NAMES,e.aspect)||
           e.aspect_target_deg!==ASPECT_NAMES[e.aspect]||
           !["prograde","retrograde","stationary"].includes(e.direction)||
           typeof e.residual_deg!=="number"||
           !isFinite(e.residual_deg)||e.residual_deg<0||e.residual_deg>0.1)
           return fail("CONTACT EVENT INVALID");
        events.push({utc:e.utc,ms:when,aspect:e.aspect,
            degrees:e.aspect_target_deg,direction:e.direction,
            residual_deg:e.residual_deg});
        prev=when;
    }
    return {ready:true,reason:"",start_utc:req.start_utc,end_utc:req.end_utc,
        natal_body:req.natal_body,transit_body:req.transit_body,
        sample_minutes:req.sample_minutes,sample_count:result.sample_count,
        timeline:positions,contacts:events,source_hash:req.expected_ephemeris_sha256,
        natal_longitude_deg:result.natal_longitude_deg};
}
function nearestMinute(instant){
    var ms=utc(instant);
    if(!isFinite(ms))return "";
    var value=new Date(Math.round(ms/60000)*60000);
    if(value.getUTCFullYear()<1901||value.getUTCFullYear()>2099)return "";
    return value.toISOString().slice(0,16)+":00Z";
}
function plot(result,width,height){
    if(!result||!result.ready||width<40||height<30)return null;
    var data=result.timeline,min=Infinity,max=-Infinity;
    for(var i=0;i<data.length;i++){
        min=Math.min(min,data[i].relative_deg);
        max=Math.max(max,data[i].relative_deg);
    }
    if(!isFinite(min)||!isFinite(max))return null;
    var range=Math.max(4,max-min),mid=(max+min)/2;
    min=mid-range*.6;max=mid+range*.6;
    var from=utc(result.start_utc),to=utc(result.end_utc);
    if(!(to>from))return null;
    function x(ms){return 6+(width-12)*(ms-from)/(to-from);}
    function y(degrees){return 5+(height-10)*(max-degrees)/(max-min);}
    return {points:data.map(function(v){return {x:x(v.ms),y:y(v.relative_deg)};}),
        events:result.contacts.map(function(v){return {x:x(v.ms),utc:v.utc};}),
        min:min,max:max};
}
