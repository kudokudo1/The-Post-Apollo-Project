.pragma library

// COSMOS V2 // rendering-only models over already obtained astronomy.
// Provider Moon illumination is a percentage; the Moon disk is a
// schematic phase, NOT a live sky photograph or telescope orientation.
// Solar arc samples the existing calibrated NOAA-style solar formula.
// No ephemeris fetcher, independent clock, storage or astrology inference.
var FORMAT = "post-apollo.weather.cosmos-visuals.v2.v1";
var PHASES = [
    {id:"new",label:"NEW"},
    {id:"waxing-crescent",label:"WAX CRES"},
    {id:"first-quarter",label:"FIRST QTR"},
    {id:"waxing-gibbous",label:"WAX GIB"},
    {id:"full",label:"FULL"},
    {id:"waning-gibbous",label:"WAN GIB"},
    {id:"last-quarter",label:"LAST QTR"},
    {id:"waning-crescent",label:"WAN CRES"}
];
function finite(value) {
    if(value===null||value===undefined||String(value).trim()==="")
        return null;
    var number=Number(value);
    return isFinite(number)?number:null;
}
function pct(value) {
    var n=finite(value);
    return n!==null&&n>=0&&n<=100?n:null;
}
function normalizedPhase(raw) {
    var phase=String(raw||"").toLowerCase().trim()
         .replace(/[_-]+/g," ").replace(/\s+/g," ");
    if(phase==="third quarter")phase="last quarter";
    if(phase==="new moon")phase="new";
    if(phase==="full moon")phase="full";
    if(phase==="first quarter moon")phase="first quarter";
    if(phase==="last quarter moon")phase="last quarter";
    var id=phase.replace(/ /g,"-");
    for(var i=0;i<PHASES.length;i++)
        if(PHASES[i].id===id)return id;
    return "";
}
function waxingDirection(phase) {
    if(phase.indexOf("waxing")===0||phase==="first-quarter")return true;
    if(phase.indexOf("waning")===0||phase==="last-quarter")return false;
    // At new/full the side isn't distinguishable, but the phase remains valid.
    return true;
}
function moonDisplay(usnoReady,ephemeris,dailyFallback) {
    var usno=usnoReady&&ephemeris&&ephemeris.available
             ?ephemeris:null;
    var fallback=dailyFallback&&dailyFallback.available?dailyFallback:null;
    var source=usno||fallback;
    var phase=source?normalizedPhase(usno?source.phase:source.moonPhaseLabel):"";
    var illumination=source?pct(usno?source.illumination:source.moonIllumination):null;
    var ready=!!source&&(phase!==""||illumination!==null);
    return {
        ready:ready,
        phaseId:ready?phase:"",
        phaseLabel:ready?(phase?phase.replace(/-/g," ").toUpperCase():"PHASE UNKNOWN"):"--",
        illumination:ready?illumination:null,
        waxing:ready&&phase!==""?waxingDirection(phase):null,
        directionKnown:ready&&phase!=="",
        source:ready?(usno?"USNO ONE-DAY":"WTTR DAILY FORECAST"):"NO VERIFIED PHASE",
        sourceDate:ready?String((usno?source.sourceDate:source.date)||""):"",
        schematic:true
    };
}
function illuminatedSpan(percent,waxing,y,radius) {
    var f=pct(percent),r=finite(radius),row=finite(y);
    if(f===null||r===null||r<=0||row===null||Math.abs(row)>r)
        return null;
    var half=Math.sqrt(Math.max(0,r*r-row*row));
    var boundary=(1-2*f)*half;
    return waxing
        ?{left:boundary,right:half}
        :{left:-half,right:-boundary};
}
function solarArc(date,latitude,longitude,offsetMinutes,evaluator) {
    var lat=finite(latitude),lon=finite(longitude),offset=finite(offsetMinutes);
    var empty={ready:false,date:String(date||""),rows:[],min:-90,max:90,
               source:"CALIBRATED SOLAR POSITION MODEL",frame:"LOCAL CIVIL TIME"};
    if(!/^\d{4}-\d{2}-\d{2}$/.test(String(date||""))
       ||lat===null||Math.abs(lat)>=90||lon===null||Math.abs(lon)>180
       ||offset===null||offset< -720||offset>840
       ||typeof evaluator!=="function")return empty;
    var samples=[];
    for(var minute=0;minute<1440;minute+=20) {
        var result=evaluator(minute,date,lat,lon,offset);
        var elevation=finite(result&&result.altitudeDegrees);
        if(!result||!result.available||elevation===null
           ||elevation< -90||elevation>90)return empty;
        samples.push({minute:minute,altitude:elevation,aboveHorizon:elevation>=0});
    }
    // End of civil day is sampled at the actual last minute, not
    // an invented value or a next-day request.
    var last=evaluator(1439,date,lat,lon,offset);
    var end=finite(last&&last.altitudeDegrees);
    if(!last||!last.available||end===null||end< -90||end>90)return empty;
    samples.push({minute:1439,altitude:end,aboveHorizon:end>=0});
    return {
        ready:true,date:String(date),rows:samples,min:-90,max:90,
        source:"CALIBRATED SOLAR POSITION MODEL",frame:"LOCAL CIVIL TIME"
    };
}
function nearestSolar(rows,minute) {
    var value=finite(minute),data=Array.isArray(rows)?rows:[];
    if(value===null||value<0||value>=1440)return null;
    var nearest=null,distance=Infinity;
    for(var i=0;i<data.length;i++){
        var delta=Math.abs(data[i].minute-value);
        if(delta<distance){distance=delta;nearest=data[i];}
    }
    return nearest;
}
function positionX(minute,width){
    var n=finite(minute),w=finite(width);
    if(n===null||w===null||w<=0)return 0;
    return Math.max(0,Math.min(w,n/1439*w));
}
function positionY(altitude,height){
    var n=finite(altitude),h=finite(height);
    if(n===null||h===null||h<=0)return 0;
    return Math.max(0,Math.min(h,(90-n)/180*h));
}
function clockLabel(minute){
    var n=finite(minute);
    if(n===null||n<0||n>=1440)return "--";
    var m=Math.floor(n),h=Math.floor(m/60);
    return String(h).padStart(2,"0")+":"+String(m%60).padStart(2,"0");
}
