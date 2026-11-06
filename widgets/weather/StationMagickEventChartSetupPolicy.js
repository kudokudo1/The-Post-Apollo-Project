.pragma library

// M7a // Unpersisted EVENT chart input contract, never a natal chart engine.
// The current root JPL service supplies a selected pair, NOT all chart bodies.
// Do not display fake houses, aspects, birth readings or sidereal positions.
var FORMAT="post-apollo.weather.magick-event-setup.m7a.v1";
var ZODIACS=["tropical","sidereal"];
var HOUSES=["whole-sign","equal"];
function eventDate(s){
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;
    var p=s.split("-").map(Number);
    if(p[0]<1901||p[0]>2099)return null;
    var d=new Date(Date.UTC(p[0],p[1]-1,p[2]));
    return d.getUTCFullYear()===p[0] &&
        d.getUTCMonth()===p[1]-1 && d.getUTCDate()===p[2]
        ? s:null;
}
function eventTime(s){
    if(typeof s!=="string"||!/^\d{2}:\d{2}$/.test(s))return null;
    var p=s.split(":").map(Number);
    return p[0]<24&&p[1]<60?s:null;
}
function coordinate(s,min,max){
    if(typeof s!=="string"||s.trim()===""||s.length>24 ||
       !/^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(s.trim()))return null;
    var n=Number(s);
    return isFinite(n)&&n>=min&&n<=max?n:null;
}
function validate(date,time,latitude,longitude,zodiac,houses){
    var d=eventDate(date),t=eventTime(time),
        lat=coordinate(latitude,-90,90),lon=coordinate(longitude,-180,180),
        z=ZODIACS.indexOf(zodiac)>=0,h=HOUSES.indexOf(houses)>=0,
        errors=[];
    if(!d)errors.push("UTC DATE");
    if(!t)errors.push("UTC TIME");
    if(lat===null)errors.push("LATITUDE");
    if(lon===null)errors.push("LONGITUDE");
    if(!z)errors.push("ZODIAC MODEL");
    if(!h)errors.push("HOUSE MODEL");
    return {format:FORMAT,valid:errors.length===0,errors:errors,
        eventUtc:d&&t?d+"T"+t+":00Z":"",
        latitude:lat,longitude:lon,
        zodiac:z?zodiac:"",houseSystem:h?houses:"",
        chartCalculated:false,
        missing:"COMPLETE MULTI-BODY EPHEMERIS + VERIFIED ASCENDANT / HOUSE CALCULATION",
        sessionOnly:true};
}
