.pragma library

// MAGICK M6a // Read-only retrograde/station-window view of the *existing*
// source-validated M4 geocentric APPARENT ecliptic-longitude rate samples.
// Reversal brackets bound a possible crossing; they are NOT exact station UTC.
var MAX_BODIES = 4;
var MAX_SAMPLES = 721;
var FRAME = "true-ecliptic-of-date";
var STATUS = ["direct","retrograde","indeterminate"];

function finite(value) {
    return typeof value === "number" && isFinite(value) ? value : null;
}
function state(rate) {
    if (finite(rate) === null) return "";
    return rate > 0 ? "direct" : rate < 0 ? "retrograde" : "indeterminate";
}
function unavailable(reason) {
    return {ready:false,reason:reason || "NO SOURCE-VERIFIED M4 RATES",
            lanes:[],boundaries:[],times:[],from:0,to:0,focus:-1};
}
function fraction(ms,start,end) {
    var n=finite(ms),a=finite(start),b=finite(end);
    if(n===null || a===null || b===null || b<=a)return null;
    return (n-a)/(b-a);
}
function build(model,view,focus) {
    if(!model || model.ready!==true ||
       model.frame!==FRAME || !Array.isArray(model.series) ||
       model.series.length<1 || model.series.length>MAX_BODIES ||
       !Array.isArray(model.times) ||
       model.sampleCount!==model.times.length ||
       model.sampleCount<2 || model.sampleCount>MAX_SAMPLES ||
       !view || !Number.isInteger(view.from) ||
       !Number.isInteger(view.to) || view.from<0 ||
       view.to>=model.sampleCount || view.to<=view.from ||
       !Number.isInteger(focus) || focus<view.from || focus>view.to)
        return unavailable("INVALID M4 SOURCE OR TIME WINDOW");
    var start=model.times[view.from],end=model.times[view.to],previous=null;
    if(fraction(start,start,end)!==0)return unavailable("INVALID UTC GRID");
    for(var t=0;t<model.sampleCount;t++){
        var time=model.times[t];
        if(finite(time)===null || !Number.isInteger(time) ||
           (previous!==null && time<=previous))
            return unavailable("UNORDERED M4 UTC GRID");
        previous=time;
    }
    var lanes=[],boundaries=[],allBodies={};
    for(var i=0;i<model.series.length;i++){
        var row=model.series[i];
        if(!row || typeof row.body!=="string" || !row.body ||
           allBodies[row.body] || !Array.isArray(row.rows) ||
           row.rows.length!==model.sampleCount)
            return unavailable("SOURCE RATE SERIES INVALID");
        allBodies[row.body]=true;
        var points=[],maxRate=0,prior=null;
        for(var j=0;j<model.sampleCount;j++){
            var sample=row.rows[j],rate=sample &&
                finite(sample.longitude_rate_deg_per_day);
            if(rate===null || !sample ||
               sample.unix_ms!==model.times[j] ||
               sample.motion!==state(rate))
                return unavailable("RATE OR MOTION DOES NOT MATCH M4 SOURCE");
            if(j<view.from || j>view.to)continue;
            var point={index:j,unix_ms:sample.unix_ms,
                       fraction:fraction(sample.unix_ms,start,end),
                       rate:rate,motion:sample.motion};
            if(point.fraction===null)return unavailable("INVALID RATE SAMPLE");
            points.push(point);
            maxRate=Math.max(maxRate,Math.abs(rate));
            if(prior){
                if((prior.rate>0 && rate<0) ||
                   (prior.rate<0 && rate>0) ||
                   (prior.rate!==0 && rate===0) ||
                   (prior.rate===0 && rate!==0)){
                    // A sign change or sampled zero only brackets a station
                    // candidate; we never invent a precise between-sample UTC.
                    boundaries.push({body:row.body,fromIndex:prior.index,
                        toIndex:j,fromMs:prior.unix_ms,toMs:sample.unix_ms,
                        fromRate:prior.rate,toRate:rate,
                        fromFraction:prior.fraction,toFraction:point.fraction,
                        kind:"RATE TRANSITION WINDOW"});
                }
            }
            prior=point;
        }
        if(points.length<2)return unavailable("NO RATE SAMPLES IN VIEW");
        lanes.push({body:row.body,color:row.color||"",
                    maxAbsRate:maxRate,points:points,
                    focusRate:row.rows[focus].longitude_rate_deg_per_day,
                    focusMotion:row.rows[focus].motion});
    }
    return {ready:true,reason:"",source:model.source||"",
            frame:model.frame,lanes:lanes,boundaries:boundaries,
            from:view.from,to:view.to,startMs:start,endMs:end,
            focus:focus,focusMs:model.times[focus]};
}
function layout(width,height,laneCount) {
    var w=finite(width),h=finite(height);
    if(w===null||h===null||w<150||h<105||
       !Number.isInteger(laneCount)||laneCount<1||laneCount>MAX_BODIES)
        return null;
    var left=44,right=w-9,top=37,bottom=h-23;
    if(bottom-top<laneCount*19)return null;
    return {left:left,right:right,top:top,bottom:bottom,
            width:right-left,height:bottom-top,
            laneHeight:(bottom-top)/laneCount};
}
function samplePoint(point,lane,geometry,laneIndex) {
    if(!point || !lane || !geometry ||
       !Number.isInteger(laneIndex) ||
       laneIndex<0 || finite(point.rate)===null ||
       finite(point.fraction)===null ||
       finite(lane.maxAbsRate)===null ||
       lane.maxAbsRate<0)return null;
    var cy=geometry.top+(laneIndex+0.5)*geometry.laneHeight;
    var max=Math.max(lane.maxAbsRate,0.0000001);
    var x=geometry.left+geometry.width*point.fraction;
    var amplitude=geometry.laneHeight*0.36;
    var y=cy-point.rate/max*amplitude;
    return {x:x,y:y,cy:cy};
}
