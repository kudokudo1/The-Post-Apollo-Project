.pragma library

// M6d // Traditional Chaldean planetary hours on provider-local *civil
// clock* sunrise/sunset labels. The astronomical events come ONLY from
// existing WeatherService.dailyForecast. The rulers are a named historical
// convention, NOT scientific properties or causal predictions.
//
// Source payload has local "HH:MM AM/PM" but no per-event UTC offset. Night
// intervals spanning a daylight-saving transition are therefore CIVIL-CLOCK
// REFERENCES, not guaranteed equal elapsed SI durations. Show this caveat.
var FORMAT = "post-apollo.weather.magick-planetary-hours.m6d.v1";
var ORDER = ["saturn","jupiter","mars","sun","venus","mercury","moon"];
var WEEKDAY_RULERS = ["sun","moon","mars","mercury","jupiter","venus","saturn"];
var MAX_DAYS = 14;
var HOURS = 24;
var DAY_MS = 86400000;

function fail(reason) {
    return {ready:false,reason:reason||"VERIFIED SOLAR WINDOW MISSING",
            format:FORMAT,source:"WEATHER FORECAST // PROVIDER LOCAL",
            basis:"CIVIL CLOCK // DST TRANSITIONS NOT RESOLVED",
            date:"",nextDate:"",weekday:-1,dayRuler:"",
            sunrise:"",sunset:"",nextSunrise:"",dayMinutes:0,
            nightMinutes:0,hours:[]};
}
function validDate(raw) {
    var match=typeof raw==="string" &&
              raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if(!match)return null;
    var year=Number(match[1]),month=Number(match[2]),
        date=Number(match[3]);
    if(year<1901 || year>2099 || month<1 || month>12 ||
       date<1 || date>31)return null;
    var stamp=Date.UTC(year,month-1,date);
    var d=new Date(stamp);
    return d.getUTCFullYear()===year &&
           d.getUTCMonth()===month-1 && d.getUTCDate()===date
           ? stamp : null;
}
function nextDate(raw) {
    var value=validDate(raw);
    if(value===null)return "";
    return new Date(value+DAY_MS).toISOString().slice(0,10);
}
function localMinute(raw) {
    if(typeof raw!=="string")return -1;
    var m=raw.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if(!m)return -1;
    var hour=Number(m[1]),minute=Number(m[2]);
    if(hour<1 || hour>12 || minute<0 || minute>59)return -1;
    return (hour%12+(m[3].toUpperCase()==="PM"?12:0))*60+minute;
}
function observedDate(raw) {
    if(typeof raw!=="string")return "";
    var match=raw.trim().match(/^(\d{4}-\d{2}-\d{2})\s+\d{1,2}:\d{2}/);
    return match && validDate(match[1])!==null ? match[1] : "";
}
function observedMinute(raw) {
    if(typeof raw!=="string")return -1;
    var match=raw.trim().match(/^\d{4}-\d{2}-\d{2}\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i);
    if(!match)return -1;
    var hour=Number(match[1]),minute=Number(match[2]);
    if(minute>59 || hour>(match[3]?12:23) ||
       (match[3] && hour<1))return -1;
    if(match[3])hour=hour%12+(match[3].toUpperCase()==="PM"?12:0);
    return hour*60+minute;
}
function clockLabel(minute) {
    if(typeof minute!=="number" || !isFinite(minute) ||
       minute<0 || minute>2880)return "--";
    var rounded=Math.round(minute),day=Math.floor(rounded/1440),
        m=rounded%1440,h=Math.floor(m/60),min=m%60,
        period=h<12?"AM":"PM",display=h%12||12;
    return String(display)+":"+(min<10?"0":"")+min+" "+period+
           (day>0?" +1D":"");
}
function build(daily,localObservation,requestedDate) {
    if(!Array.isArray(daily) || daily.length<2 || daily.length>MAX_DAYS)
        return fail("TWO CONSECUTIVE FORECAST DAYS REQUIRED");
    // If the source's location-local observation date exists, use that
    // provider-local date. Never substitute the host machine's timezone.
    var date=requestedDate || observedDate(localObservation) ||
             (daily[0] && daily[0].date) || "";
    var todayStamp=validDate(date),tomorrow=nextDate(date);
    if(todayStamp===null || !tomorrow)
        return fail("SOURCE LOCAL DATE INVALID");
    var first=null,second=null,seen={};
    for(var i=0;i<daily.length;i++){
        var d=daily[i];
        if(!d || validDate(d.date)===null || seen[d.date])
            return fail("DUPLICATED OR INVALID FORECAST DATE");
        seen[d.date]=true;
        if(d.date===date)first=d;
        if(d.date===tomorrow)second=d;
    }
    if(!first || !second)return fail("NEXT-DAY SUNRISE NOT VERIFIED");
    var sunrise=localMinute(first.sunrise),
        sunset=localMinute(first.sunset),
        nextRise=localMinute(second.sunrise);
    if(sunrise<0 || sunset<0 || nextRise<0 ||
       sunrise>=sunset || sunset>=1440)
        return fail("NO NORMAL DAY/NIGHT SOLAR WINDOW");
    var dayMinutes=sunset-sunrise,
        nightMinutes=1440-sunset+nextRise;
    if(dayMinutes<=0 || nightMinutes<=0 || dayMinutes>=1440 ||
       nightMinutes>=1440)return fail("SOLAR HOURS CANNOT BE DIVIDED");
    var weekday=new Date(todayStamp).getUTCDay(),dayRuler=WEEKDAY_RULERS[weekday];
    var firstIndex=ORDER.indexOf(dayRuler);
    if(firstIndex<0)return fail("WEEKDAY RULER UNAVAILABLE");
    var hours=[];
    for(var h=0;h<HOURS;h++){
        var daytime=h<12,part=daytime?h:h-12;
        var begin=daytime
                  ? sunrise+dayMinutes*part/12
                  : sunset+nightMinutes*part/12;
        var end=daytime
                ? sunrise+dayMinutes*(part+1)/12
                : sunset+nightMinutes*(part+1)/12;
        var ruler=ORDER[(firstIndex+h)%ORDER.length];
        hours.push({index:h,ordinal:part+1,phase:daytime?"day":"night",
            ruler:ruler,startMinute:begin,endMinute:end,
            startLabel:clockLabel(begin),endLabel:clockLabel(end),
            fraction:h/24,durationClockMinutes:(end-begin)});
    }
    return {ready:true,reason:"",format:FORMAT,
        source:"WEATHER FORECAST // PROVIDER LOCAL",
        basis:"CIVIL CLOCK // DST TRANSITIONS NOT RESOLVED",
        date:date,nextDate:tomorrow,weekday:weekday,
        dayRuler:dayRuler,sunrise:first.sunrise,
        sunset:first.sunset,nextSunrise:second.sunrise,
        dayMinutes:dayMinutes,nightMinutes:nightMinutes,hours:hours};
}
function observedIndex(plan,localObservation) {
    if(!plan || plan.ready!==true ||
       observedDate(localObservation)!==plan.date)return -1;
    var m=observedMinute(localObservation);
    if(m<0)return -1;
    // Forecast snapshot is a SOURCE observation, not a live current clock.
    for(var i=0;i<plan.hours.length;i++)
        if(plan.hours[i].startMinute<=m && plan.hours[i].endMinute>m)
            return i;
    return -1;
}
function wheelGeometry(width,height){
    if(typeof width!=="number" || typeof height!=="number" ||
       !isFinite(width) || !isFinite(height) ||
       width<200 || height<130)return null;
    var radius=Math.min(width*0.31,height*0.32);
    if(radius<32)return null;
    return {cx:width/2,cy:height/2,radius:radius,
        inner:radius-12,outer:radius+12};
}
function pick(plan,geometry,x,y){
    if(!plan || plan.ready!==true || !geometry ||
       typeof x!=="number" || typeof y!=="number" ||
       !isFinite(x) || !isFinite(y))return -1;
    var dx=x-geometry.cx,dy=y-geometry.cy,r=Math.hypot(dx,dy);
    if(r<geometry.inner-7 || r>geometry.outer+10)return -1;
    var rad=(Math.atan2(dy,dx)+Math.PI/2+2*Math.PI)%(2*Math.PI);
    var index=Math.floor(rad/(2*Math.PI)*24);
    return index>=0 && index<24 ? index : -1;
}
