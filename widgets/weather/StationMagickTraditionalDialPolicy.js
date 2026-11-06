.pragma library
// M8a // SOURCE-BOUND CHALDEAN CIVIL-CLOCK DIAL
// Angles represent minutes between local sunrise and next local sunrise.
// Segments are NOT equal visual widths when day and night lengths differ.
// This is historical symbolic attribution, not astronomical rulership.
var FORMAT="post-apollo.weather.magick-clock.m8a.v1";
var ORDER=["saturn","jupiter","mars","sun","venus","mercury","moon"];
function fail(reason){return {ready:false,reason:reason||"TWO-DAY SOLAR WINDOW REQUIRED",sectors:[],totalMinutes:0};}
function build(plan){
    if(!plan||plan.ready!==true||!Array.isArray(plan.hours)||plan.hours.length!==24||
       typeof plan.sunrise!=="string"||typeof plan.sunset!=="string"||
       typeof plan.nextSunrise!=="string"||
       typeof plan.basis!=="string"||plan.basis.indexOf("DST")<0)
       return fail("VERIFIED SOURCE CLOCK REQUIRED");
    var h=plan.hours,first=h[0].startMinute,last=h[23].endMinute;
    if(typeof first!=="number"||typeof last!=="number"||
       !isFinite(first)||!isFinite(last)||last<=first||
       last-first<1200||last-first>1680)return fail("SOURCE WINDOW INVALID");
    var sectors=[],prev=first,total=last-first;
    for(var i=0;i<24;i++){
        var v=h[i];
        if(!v||v.index!==i||ORDER.indexOf(v.ruler)<0||
           v.phase!==(i<12?"day":"night")||
           !isFinite(v.startMinute)||!isFinite(v.endMinute)||
           Math.abs(v.startMinute-prev)>0.001||v.endMinute<=v.startMinute||
           v.endMinute>last+0.001)
           return fail("SOURCE DIVISIONS DISCONTINUOUS");
        sectors.push({index:i,ruler:v.ruler,phase:v.phase,
            ordinal:v.ordinal,startMinute:v.startMinute,
            endMinute:v.endMinute,startLabel:v.startLabel,endLabel:v.endLabel,
            startAngle:-Math.PI/2+2*Math.PI*(v.startMinute-first)/total,
            endAngle:-Math.PI/2+2*Math.PI*(v.endMinute-first)/total});
        prev=v.endMinute;
    }
    if(Math.abs(prev-last)>0.001)return fail("SOURCE WINDOW INCOMPLETE");
    return {ready:true,reason:"",format:FORMAT,date:plan.date,
        source:plan.source,basis:plan.basis,totalMinutes:total,
        dayMinutes:plan.dayMinutes,nightMinutes:plan.nightMinutes,sectors:sectors};
}
function layout(width,height){
    if(!isFinite(width)||!isFinite(height)||width<170||height<120)return null;
    var r=Math.max(25,Math.min(width-12,height-12)*0.43);
    return {cx:width/2,cy:height/2,r:r,inner:r*0.51,outer:r*0.98};
}
function select(model,geometry,x,y){
    if(!model||!model.ready||!geometry||![x,y].every(isFinite))return -1;
    var dx=x-geometry.cx,dy=y-geometry.cy,r=Math.hypot(dx,dy);
    if(r<geometry.inner||r>geometry.outer)return -1;
    var angle=(Math.atan2(dy,dx)+Math.PI/2+2*Math.PI)%(2*Math.PI);
    for(var i=0;i<model.sectors.length;i++){
        var start=(model.sectors[i].startAngle+Math.PI/2+2*Math.PI)%(2*Math.PI);
        var end=(model.sectors[i].endAngle+Math.PI/2+2*Math.PI)%(2*Math.PI);
        if(i===23||angle>=start && angle<end)return i;
    }
    return -1;
}
