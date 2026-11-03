.pragma library

// V1 // read-only, source-agnostic time-series geometry for SUBJECTS.
// Origin records retain observation and receipt clocks separately.
// No interpolation, provider request, storage writer or fictitious samples.
var FORMAT = "post-apollo.weather.visual-series.v1";
var SIX_HOURS_MS = 6 * 60 * 60 * 1000;
var DAY_MS = 24 * 60 * 60 * 1000;
var TWO_DAYS_MS = 48 * 60 * 60 * 1000;
var PRESETS = [
    {id:"6h",label:"6H",durationMs:SIX_HOURS_MS},
    {id:"24h",label:"24H",durationMs:DAY_MS},
    {id:"48h",label:"48H",durationMs:TWO_DAYS_MS}
];

function finite(value) {
    if(value===null || value===undefined || value==="")
        return null;
    var n=Number(value);
    return isFinite(n)?n:null;
}
function positiveTime(value) {
    var n=finite(value);
    return n!==null && n>0 ? Math.floor(n) : -1;
}
function durationFor(preset) {
    for(var i=0;i<PRESETS.length;i++)
        if(PRESETS[i].id===preset) return PRESETS[i].durationMs;
    return DAY_MS;
}
function observationRows(samples,field,nowMs,durationMs) {
    var now=positiveTime(nowMs);
    var duration=Number(durationMs);
    if(now<1 || !isFinite(duration) || duration<=0
       || duration>TWO_DAYS_MS) return [];
    var floor=now-duration;
    var src=Array.isArray(samples)?samples:[];
    var byTime={};
    for(var i=0;i<src.length;i++){
        var item=src[i]||{};
        var time=positiveTime(item.observedAtMs);
        if(time<floor || time>now) continue;
        var receive=positiveTime(item.receivedAtMs);
        if(receive<=0 || receive>now+300000) continue;
        var payload=item.payload && typeof item.payload==="object"
                    ? item.payload:{};
        var value=finite(payload[field]);
        if(value===null) continue;
        var key=String(time);
        var row={timeMs:time,value:value,receivedAtMs:receive};
        if(!byTime[key] || receive>=byTime[key].receivedAtMs)
            byTime[key]=row;
    }
    return Object.keys(byTime).map(function(k){return byTime[k];})
      .sort(function(a,b){return a.timeMs-b.timeMs;});
}

// Bucket envelope, not a regular stride: preserves extrema and endpoints.
// Rendering point budget is bounded; timestamps remain real/unmodified.
function boundedPoints(rows,maxPoints) {
    var src=Array.isArray(rows)?rows:[];
    var cap=Math.max(8,Math.floor(Number(maxPoints)||192));
    if(src.length<=cap) return src.slice();
    var result=[src[0]];
    var interior=src.length-2;
    var bucketCount=Math.max(1,Math.floor((cap-2)/2));
    for(var b=0;b<bucketCount;b++){
        var lo=1+Math.floor(interior*b/bucketCount);
        var hi=1+Math.floor(interior*(b+1)/bucketCount);
        if(lo>=hi)continue;
        var min=src[lo],max=src[lo];
        for(var i=lo+1;i<hi;i++){
            if(src[i].value<min.value) min=src[i];
            if(src[i].value>max.value) max=src[i];
        }
        result.push(min);
        if(max!==min)result.push(max);
    }
    result.push(src[src.length-1]);
    result.sort(function(a,b){return a.timeMs-b.timeMs;});
    return result;
}
function medianInterval(rows) {
    var values=[];
    for(var i=1;i<rows.length;i++){
        var delta=rows[i].timeMs-rows[i-1].timeMs;
        if(delta>0)values.push(delta);
    }
    if(!values.length)return 0;
    values.sort(function(a,b){return a-b;});
    return values[Math.floor(values.length/2)];
}
function axisFor(rows) {
    if(!rows.length)return {min:null,max:null};
    var min=rows[0].value,max=min;
    for(var i=1;i<rows.length;i++){
        min=Math.min(min,rows[i].value);
        max=Math.max(max,rows[i].value);
    }
    if(max===min){
        var pad=Math.max(Math.abs(min)*0.05,0.1);
        return {min:min-pad,max:max+pad};
    }
    var padding=(max-min)*0.10;
    return {min:min-padding,max:max+padding};
}
function model(samples,field,nowMs,durationMs,maxPoints){
    var now=positiveTime(nowMs);
    var period=Number(durationMs);
    var valid=now>0 && isFinite(period) && period>0
              && period<=TWO_DAYS_MS;
    var empty={rows:[],segments:[],count:0,drawnCount:0,gaps:0,
        startMs:valid?now-period:-1,endMs:valid?now:-1,
        firstMs:-1,lastMs:-1,axis:{min:null,max:null},
        gapThresholdMs:0};
    if(!valid)return empty;
    var all=observationRows(samples,field,now,period);
    if(!all.length)return empty;
    var downsampled=boundedPoints(all,maxPoints);
    var median=medianInterval(all);
    var gapThreshold=Math.max(45*60000,median*3);
    // Segment ORIGINAL observations before any pixel/downsample pass.
    // No point after a gap is attached to the preceding line.
    var grouped=[],group=[];
    for(var i=0;i<all.length;i++){
        if(group.length && all[i].timeMs-group[group.length-1].timeMs
           >gapThreshold){
            grouped.push(group);
            group=[];
        }
        group.push(all[i]);
    }
    if(group.length)grouped.push(group);
    // Cap points per source while preserving gap boundaries.
    var groups=grouped.map(function(segment){
        return boundedPoints(segment,Math.max(8,Math.floor(
           Number(maxPoints||192)/Math.max(1,grouped.length))));
    });
    return {
        rows:downsampled,
        segments:groups,
        count:all.length,
        drawnCount:groups.reduce(function(n,s){return n+s.length;},0),
        gaps:Math.max(0,groups.length-1),
        startMs:now-period,endMs:now,
        firstMs:all[0].timeMs,lastMs:all[all.length-1].timeMs,
        axis:axisFor(all),gapThresholdMs:gapThreshold
    };
}
function xPosition(timeMs,chart,plotWidth){
    var t=finite(timeMs),w=Number(plotWidth);
    if(!chart || t===null || !(w>0) ||
       chart.endMs<=chart.startMs)return 0;
    return Math.max(0,Math.min(w,
           (t-chart.startMs)/(chart.endMs-chart.startMs)*w));
}
function yPosition(value,axis,plotHeight){
    var n=finite(value),h=Number(plotHeight);
    if(n===null||!axis||axis.min===null||axis.max===null
       ||!(h>0)||axis.max<=axis.min)return 0;
    var p=(n-axis.min)/(axis.max-axis.min);
    return Math.max(0,Math.min(h,(1-p)*h));
}
function nearestTimestamp(left,right,atMs){
    var t=finite(atMs);
    if(t===null)return -1;
    var best=-1,distance=Infinity;
    var all=[left,right];
    for(var j=0;j<all.length;j++){
        var a=all[j]&&Array.isArray(all[j].rows)?all[j].rows:[];
        for(var i=0;i<a.length;i++){
            var d=Math.abs(a[i].timeMs-t);
            if(d<distance){distance=d;best=a[i].timeMs;}
        }
    }
    return best;
}
function nearestValue(chart,atMs,toleranceMs){
    var rows=chart&&Array.isArray(chart.rows)?chart.rows:[];
    var t=finite(atMs),tolerance=Number(toleranceMs);
    if(t===null||!isFinite(tolerance)||tolerance<0)return null;
    var best=null,delta=Infinity;
    for(var i=0;i<rows.length;i++){
        var d=Math.abs(rows[i].timeMs-t);
        if(d<=tolerance&&d<delta){best=rows[i];delta=d;}
    }
    return best;
}
function formatNumber(value,digits){
    var v=finite(value);
    if(v===null)return "--";
    return v.toFixed(Math.max(0,Math.min(4,Math.floor(Number(digits)||0))));
}
function displayClock(ms){
    var t=positiveTime(ms);
    if(t<0)return "NO SAMPLE";
    return new Date(t).toLocaleString();
}
