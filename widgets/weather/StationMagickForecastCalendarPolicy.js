.pragma library

// M7a // Forecast-backed lunar/solar outlook only.
// The preexisting WeatherService daily forecast is provider-local; daily
// moon phase and illumination are FORECAST summaries, not precise UTC event
// instants. Do not extrapolate a 29.53-day cycle or manufacture seasons.
var FORMAT="post-apollo.weather.magick-calendar.m7a.v1";
var MAX_DAYS=14;
var PHASES={
    "new moon":"NEW","waxing crescent":"WAX CRESCENT",
    "first quarter":"FIRST QUARTER","waxing gibbous":"WAX GIBBOUS",
    "full moon":"FULL","waning gibbous":"WANE GIBBOUS",
    "last quarter":"LAST QUARTER","waning crescent":"WANE CRESCENT"
};
function stamp(value){
    if(typeof value!=="string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return null;
    var p=value.split("-").map(Number);
    if(p[0]<1901||p[0]>2099)return null;
    var d=Date.UTC(p[0],p[1]-1,p[2]),check=new Date(d);
    return check.getUTCFullYear()===p[0] &&
           check.getUTCMonth()===p[1]-1 &&
           check.getUTCDate()===p[2] ? d : null;
}
function clock(value){
    if(typeof value!=="string")return -1;
    var m=value.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if(!m)return -1;
    var h=Number(m[1]),min=Number(m[2]);
    if(h<1||h>12||min>59)return -1;
    return (h%12+(m[3].toUpperCase()==="PM"?12:0))*60+min;
}
function fail(reason){
    return {ready:false,reason:reason||"FORECAST NOT AVAILABLE",
        format:FORMAT,rows:[],count:0,firstDate:"",lastDate:"",
        source:"WEATHER FORECAST // PROVIDER LOCAL"};
}
function build(daily){
    if(!Array.isArray(daily) || daily.length===0 ||
       daily.length>MAX_DAYS)return fail("VALID DAILY FORECAST REQUIRED");
    var rows=[],previous=null;
    for(var i=0;i<daily.length;i++){
        var item=daily[i],d=item&&stamp(item.date);
        if(d===null || (previous!==null && d!==previous+86400000))
            return fail("CONSECUTIVE LOCAL DATES REQUIRED");
        previous=d;
        var raw=typeof item.moonPhase==="string"
            ? item.moonPhase.trim().toLowerCase():"";
        var phase=Object.prototype.hasOwnProperty.call(PHASES,raw)
            ? PHASES[raw]:"PHASE UNKNOWN";
        var illum=Number(item.moonIllumination);
        if(item.moonIllumination===null ||
           item.moonIllumination===undefined ||
           item.moonIllumination==="" || !isFinite(illum)||
           illum<0||illum>100)illum=null;
        var rise=clock(item.sunrise),set=clock(item.sunset);
        var minutes=rise>=0 && set>rise ? set-rise:null;
        rows.push({date:item.date,ordinal:i,weekday:
            ["SUN","MON","TUE","WED","THU","FRI","SAT"]
                [new Date(d).getUTCDay()],
            phase:phase,illumination:illum,
            sunrise:rise>=0?item.sunrise:"--",
            sunset:set>=0?item.sunset:"--",
            daylightMinutes:minutes,
            dayFraction:minutes===null?null:minutes/1440,
            rawPhase:raw});
    }
    return {ready:true,reason:"",format:FORMAT,rows:rows,
        count:rows.length,firstDate:rows[0].date,
        lastDate:rows[rows.length-1].date,
        source:"WEATHER FORECAST // PROVIDER LOCAL"};
}
function select(model,date) {
    if(!model||!model.ready||typeof date!=="string")return null;
    for(var i=0;i<model.rows.length;i++)
        if(model.rows[i].date===date)return model.rows[i];
    return null;
}
function initialDate(model,localObservation) {
    if(!model||!model.ready)return "";
    var date=typeof localObservation==="string"
        ? localObservation.slice(0,10):"";
    return select(model,date)?date:model.firstDate;
}
