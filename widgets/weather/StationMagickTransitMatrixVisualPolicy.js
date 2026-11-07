.pragma library
// M8m visual-only projections of the existing VERIFIED M8k/M8l matrix model.
// Zero new ephemeris calculations, invented event timestamps, or disk writes.
var BINS=[0,2,4]; // count 0; 1-2 cyan; 3-4 yellow; 5+ orange
function heatTier(count) {
    if(!Number.isInteger(count)||count<0)return 0;
    return count===0?0:count<=2?1:count<=4?2:3;
}
function cell(model,natal,transit) {
    if(!model||!model.ready||!Array.isArray(model.matrix))return null;
    var pair=model.matrix.find(function(c){
        return c.natal_body===natal&&c.transit_body===transit;
    });
    return pair&&Number.isInteger(pair.aspect_count)&&pair.aspect_count>=0
        ?{count:pair.aspect_count,tier:heatTier(pair.aspect_count)}:null;
}
function eventKey(e){
    return !e?"":String(e.utc)+"|"+String(e.natal_body)+"|"+
        String(e.transit_body)+"|"+String(e.type)+"|"+String(e.aspect);
}
function inspect(model,key){
    if(!model||!model.ready||!Array.isArray(model.events)||
        typeof key!=="string"||!key)return null;
    var match=model.events.find(function(e){return eventKey(e)===key;});
    if(!match)return null;
    var isStation=match.type==="station";
    return {utc:match.utc,ms:match.ms,type:match.type,
        natal_body:match.natal_body,transit_body:match.transit_body,
        direction:match.direction,
        aspect:isStation?"":match.aspect,
        angle_deg:isStation?null:match.degrees,
        residual_deg:isStation?null:match.residual_deg,
        longitude_deg:isStation?match.longitude_deg:null,
        velocity_deg_day:isStation?match.velocity_deg_day:null,
        numerical_bracket_seconds:isStation?60:1,
        physical_time_accuracy_claim:false};
}
function windowModel(model){
    if(!model||!model.ready||typeof model.start_utc!=="string"||
       typeof model.end_utc!=="string")return null;
    var start=Date.parse(model.start_utc),end=Date.parse(model.end_utc);
    if(!isFinite(start)||!isFinite(end)||end<=start||end-start>31*86400000)
        return null;
    return {start:start,end:end};
}
function timeline(model,events,width,height){
    var window=windowModel(model);
    if(!window||!Array.isArray(events)||width<50||height<30||
       !Array.isArray(model.transit_bodies)||model.transit_bodies.length<1)
        return null;
    var duration=window.end-window.start;
    function x(t){return 8+(width-16)*(t-window.start)/duration;}
    var lanes=model.transit_bodies.length;
    var marks=[];
    for(var i=0;i<events.length;i++){
        var e=events[i],lane=model.transit_bodies.indexOf(e.transit_body);
        if(lane<0||!isFinite(e.ms)||e.ms<window.start||e.ms>window.end)continue;
        marks.push({x:x(e.ms),y:16+(lane+.5)*(height-21)/lanes,
            key:eventKey(e),utc:e.utc,type:e.type,lane:lane,
            transit_body:e.transit_body,natal_body:e.natal_body});
    }
    // At most seven evenly spaced UTC guide labels to preserve compact panels.
    var ticks=[];
    var days=Math.round(duration/86400000);
    var step=Math.max(1,Math.ceil(days/7));
    for(var day=0;day<=days;day+=step){
        var ms=window.start+day*86400000;
        ticks.push({x:x(ms),label:new Date(ms).toISOString().slice(5,10)});
    }
    return {markers:marks,ticks:ticks,lanes:lanes,
        from:model.start_utc,to:model.end_utc};
}
function trajectory(model,inspected,width,height,zoom){
    var window=windowModel(model);
    if(!window||!inspected||!isFinite(inspected.ms)||
       inspected.ms<window.start||inspected.ms>window.end||
       !Number.isFinite(zoom)||zoom<1||zoom>8||
       width<80||height<50||!Array.isArray(model.series))
       return null;
    var track=model.series.find(function(s){
        return s.id===inspected.transit_body;
    });
    if(!track||!Array.isArray(track.points)||track.points.length<2)return null;
    var unwrapped=[],previous=null;
    for(var i=0;i<track.points.length;i++){
        var point=track.points[i],angle=point.longitude_deg;
        if(!Number.isFinite(angle)||angle<0||angle>=360||
           !Number.isFinite(point.ms))return null;
        var position=angle;
        if(previous!==null) {
            while(position-previous>180)position-=360;
            while(position-previous< -180)position+=360;
        }
        previous=position;
        unwrapped.push({ms:point.ms,angle:position});
    }
    var reference=null;
    if(inspected.natal_body!==null) {
        var natal=model.natals.find(function(n){
            return n.id===inspected.natal_body;
        });
        if(natal) {
            reference=natal.longitude_deg;
            while(reference-unwrapped[0].angle>180)reference-=360;
            while(reference-unwrapped[0].angle< -180)reference+=360;
        }
    }
    var min=Infinity,max=-Infinity;
    unwrapped.forEach(function(p){min=Math.min(min,p.angle);max=Math.max(max,p.angle);});
    if(reference!==null){min=Math.min(min,reference);max=Math.max(max,reference);}
    var spread=Math.max(1,max-min),mid=(min+max)/2;
    min=mid-spread*.60;max=mid+spread*.60;
    var timeSpan=window.end-window.start;
    function x(ms){return width/2+((ms-inspected.ms)/timeSpan)*(width-16)*zoom;}
    function y(angle){return 7+(height-14)*(max-angle)/(max-min);}
    return {points:unwrapped.map(function(p){return {x:x(p.ms),y:y(p.angle)};}),
        referenceY:reference!==null?y(reference):null,
        eventX:x(inspected.ms),min:min,max:max,
        sampleCount:track.points.length};
}
