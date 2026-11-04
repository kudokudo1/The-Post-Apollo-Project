.pragma library

// COSMOS V3d // Read-only 24-hour civil-day event wheel.
// The angle is the exact local HH:MM of a USNO MRST rise / transit / set
// calculation. Radius is a categorical PLANET LANE, not orbit, distance,
// altitude, ecliptic longitude, azimuth, or an actual simultaneous sky map.
var FORMAT = "post-apollo.weather.cosmos-day-wheel.v3d.v1";
var PLANETS = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"];
var KINDS = ["rise", "transit", "set"];

function indexed(value, cap) {
    if (!value || typeof value === "string") return [];
    var n=Number(value.length);
    if(!isFinite(n) || n<0 || n>cap || Math.floor(n)!==n) return [];
    var out=[];
    for(var i=0;i<n;i++)out.push(value[i]);
    return out;
}

function dateValid(value) {
    if(typeof value!=="string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    var d=new Date(value+"T00:00:00Z");
    return !isNaN(d.valueOf()) && d.toISOString().slice(0,10)===value;
}

function validEvent(item, date) {
    if(!item || !dateValid(date)
       || item.date!==date || item.source!=="USNO MRST"
       || PLANETS.indexOf(item.planet)<0
       || KINDS.indexOf(item.kind)<0
       || typeof item.id!=="string" || item.id.length===0
       || typeof item.clock!=="string"
       || !/^\d{2}:\d{2}$/.test(item.clock)) return false;
    var h=Number(item.clock.slice(0,2)),m=Number(item.clock.slice(3,5));
    if(h>23 || m>59)return false;
    return typeof item.minute==="number"
        && isFinite(item.minute) && Math.floor(item.minute)===item.minute
        && item.minute===h*60+m;
}

function datedEvents(events, civilDate) {
    var input=indexed(events,15), out=[];
    for(var i=0;i<input.length;i++)
        if(validEvent(input[i],civilDate))out.push(input[i]);
    out.sort(function(a,b) {
        if(a.minute!==b.minute)return a.minute-b.minute;
        var ai=PLANETS.indexOf(a.planet),bi=PLANETS.indexOf(b.planet);
        if(ai!==bi)return ai-bi;
        return KINDS.indexOf(a.kind)-KINDS.indexOf(b.kind);
    });
    return out;
}

function geometry(width,height) {
    var w=Number(width),h=Number(height);
    if(!isFinite(w)||!isFinite(h)||w<=0||h<=0)
        return {ready:false,x:0,y:0,radius:0};
    var radius=Math.min(w,h)/2-23;
    return {ready:radius>0,x:w/2,y:h/2,radius:Math.max(0,radius)};
}

function ringRadius(planet,width,height) {
    var i=PLANETS.indexOf(planet),g=geometry(width,height);
    if(i<0||!g.ready)return null;
    return g.radius*(0.40+i*0.15);
}

function timeAngle(minute) {
    var n=Number(minute);
    if(!isFinite(n)||n<0||n>=1440||Math.floor(n)!==n)return null;
    return n*Math.PI*2/1440;
}

function point(event,width,height) {
    if(!event || PLANETS.indexOf(event.planet)<0)return null;
    var a=timeAngle(event.minute),r=ringRadius(event.planet,width,height),
        g=geometry(width,height);
    if(a===null||r===null||!g.ready)return null;
    return {x:g.x+Math.sin(a)*r, y:g.y-Math.cos(a)*r,
            angle:a,radius:r};
}

function pick(events,x,y,width,height,tolerance) {
    var input=indexed(events,15),px=Number(x),py=Number(y),tol=Number(tolerance);
    if(!isFinite(px)||!isFinite(py)||!isFinite(tol)
        ||tol<=0||tol>20)return null;
    var best=null,dist=tol*tol;
    for(var i=0;i<input.length;i++) {
        var p=point(input[i],width,height);
        if(!p)continue;
        var d=(p.x-px)*(p.x-px)+(p.y-py)*(p.y-py);
        if(d<=dist){dist=d;best=input[i];}
    }
    return best;
}

function countKind(events,kind) {
    if(KINDS.indexOf(kind)<0)return 0;
    var input=indexed(events,15),n=0;
    for(var i=0;i<input.length;i++)
        if(input[i]&&input[i].kind===kind)n++;
    return n;
}

function timeLabel(minute) {
    var n=Number(minute);
    if(!isFinite(n)||n<0||n>1440||Math.floor(n)!==n)return "--:--";
    return String(Math.floor(n/60)).padStart(2,"0")+":"
        +String(n%60).padStart(2,"0");
}

function ordinal(events,event) {
    var input=indexed(events,15),id=event&&event.id;
    for(var i=0;i<input.length;i++)
        if(input[i]&&input[i].id===id)return (i+1)+"/"+input.length;
    return "—/"+input.length;
}
