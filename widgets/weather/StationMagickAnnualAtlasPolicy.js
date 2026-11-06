.pragma library

// M7b // Renderer-only checks. No astronomy inferred from the clock.
var FORMAT="post-apollo.weather.magick-annual-atlas.m7b.v1";
var PHASES=["new","waxing-crescent","first-quarter","waxing-gibbous",
    "full","waning-gibbous","last-quarter","waning-crescent"];
var SOLAR_TERMS=[
    "spring-equinox","clear-and-bright","grain-rain","start-of-summer",
    "grain-full","grain-in-ear","summer-solstice","minor-heat","major-heat",
    "start-of-autumn","end-of-heat","white-dew","autumn-equinox","cold-dew",
    "frost-descent","start-of-winter","minor-snow","major-snow",
    "winter-solstice","minor-cold","major-cold","start-of-spring",
    "rain-water","awakening-of-insects"
];
var MONTHS=["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
var MS_DAY=86400000;
function fail(reason){return {ready:false,reason:reason||"NO VERIFIED ANNUAL ATLAS",
    days:[],lunar_events:[],solar_terms:[],calendar_markers:null};}
function dateMs(day) {
    if(typeof day!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(day))return null;
    var value=Date.parse(day+"T00:00:00Z");
    return isFinite(value)&&new Date(value).toISOString().slice(0,10)===day
        ? value:null;
}
function dayCount(year) {
    if(!Number.isInteger(year)||year<1901||year>2099)return 0;
    return (Date.UTC(year+1,0,1)-Date.UTC(year,0,1))/MS_DAY;
}
function phaseFor(angle){
    if(typeof angle!=="number"||!isFinite(angle)||angle<0||angle>=360)
        return "";
    return PHASES[Math.floor((angle+22.5)/45)%8];
}
function validate(value,expectedYear,expectedZone) {
    if(!value||value.format!==FORMAT || value.year!==expectedYear ||
       value.timezone!==expectedZone || value.day_basis!=="local-noon" ||
       !value.source || value.source.engine!=="skyfield" ||
       !/^[a-fA-F0-9]{64}$/.test(String(value.source.ephemeris_sha256||"")) ||
       !Array.isArray(value.days)||value.days.length!==dayCount(expectedYear) ||
       !Array.isArray(value.lunar_events)||value.lunar_events.length<45 ||
       value.lunar_events.length>54 ||
       !Array.isArray(value.solar_terms)||value.solar_terms.length!==24 ||
       !value.calendar_markers ||
       !Array.isArray(value.calendar_markers.daily_moon) ||
       value.calendar_markers.daily_moon.length!==value.days.length ||
       !Array.isArray(value.calendar_markers.events))
        return fail("INCOMPLETE OR UNSOURCED YEAR");
    var base=Date.UTC(expectedYear,0,1),seen={};
    for(var i=0;i<value.days.length;i++){
        var row=value.days[i],date=new Date(base+i*MS_DAY).toISOString().slice(0,10);
        if(!row || row.date!==date || row.day_index!==i ||
           row.month!==new Date(base+i*MS_DAY).getUTCMonth()+1 ||
           typeof row.phase_angle_deg!=="number" ||
           !isFinite(row.phase_angle_deg) ||
           row.phase_id!==phaseFor(row.phase_angle_deg) ||
           typeof row.illumination!=="number" ||
           !isFinite(row.illumination)||row.illumination<0||row.illumination>100)
            return fail("INVALID DAILY LUNAR MEASUREMENTS");
        var marker=value.calendar_markers.daily_moon[i];
        if(!marker||marker.date!==date||marker.phase_id!==row.phase_id ||
            marker.illumination!==row.illumination)
            return fail("CALENDAR MARKER MISMATCH");
    }
    for(var j=0;j<value.solar_terms.length;j++){
        var term=value.solar_terms[j];
        if(!term|| SOLAR_TERMS.indexOf(term.id)<0 ||
           term.longitude_deg!==SOLAR_TERMS.indexOf(term.id)*15 ||
           dateMs(term.date)===null || term.date.slice(0,4)!==String(expectedYear) ||
           seen[term.id] ||
           typeof term.time_utc!=="string" || !/Z$/.test(term.time_utc))
            return fail("INVALID SOLAR TERM");
        seen[term.id]=true;
    }
    for(var k=0;k<value.lunar_events.length;k++){
        var ev=value.lunar_events[k];
        if(!ev||["new","first-quarter","full","last-quarter"].indexOf(ev.id)<0 ||
           dateMs(ev.date)===null||ev.date.slice(0,4)!==String(expectedYear) ||
           typeof ev.time_utc!=="string"||!/Z$/.test(ev.time_utc))
            return fail("INVALID LUNAR EVENT");
    }
    if(value.calendar_markers.events.length!==
       value.solar_terms.length+value.lunar_events.length)
        return fail("CALENDAR EVENT CONTRACT MISMATCH");
    return {ready:true,reason:"",year:expectedYear,timezone:expectedZone,
        days:value.days,lunar_events:value.lunar_events,
        solar_terms:value.solar_terms,
        calendar_markers:value.calendar_markers,
        source:value.source};
}
function dayIndex(model,day){
    if(!model||!model.ready)return -1;
    var start=Date.UTC(model.year,0,1),d=dateMs(day);
    if(d===null)return -1;
    var i=Math.round((d-start)/MS_DAY);
    return i>=0&&i<model.days.length ? i : -1;
}
function monthRows(model,month){
    if(!model||!model.ready||!Number.isInteger(month)||month<1||month>12)return [];
    return model.days.filter(function(d){return d.month===month;});
}
function monthIndex(model,month){
    if(!model||!model.ready||month<1||month>12)return -1;
    return Math.round((Date.UTC(model.year,month-1,1)-
                       Date.UTC(model.year,0,1))/MS_DAY);
}
function angleFor(index,total){
    return -Math.PI/2+Math.PI*2*(index+0.5)/total;
}
function indexAtAngle(x,y,cx,cy,count){
    if(!Number.isInteger(count)||count<1||![x,y,cx,cy].every(
        function(v){return typeof v==="number"&&isFinite(v);}))return -1;
    var a=(Math.atan2(y-cy,x-cx)+Math.PI/2+2*Math.PI)%(Math.PI*2);
    return Math.min(count-1,Math.floor(a/(Math.PI*2)*count));
}
function selectedDay(model,index){
    return model&&model.ready&&Number.isInteger(index)&&index>=0&&
           index<model.days.length?model.days[index]:null;
}
function eventsOnDay(model,date){
    if(!model||!model.ready)return [];
    return model.calendar_markers.events.filter(function(x){return x.date===date;});
}
