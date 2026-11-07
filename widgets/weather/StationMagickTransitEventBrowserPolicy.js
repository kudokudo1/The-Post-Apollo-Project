.pragma library
// M8j // Read-only, bounded browsing of already-verified M8h JPL events.
// Filtering/paging/inspection does not launch a process or modify ephemeris.
var PAGE_SIZE=12;
var TYPES=["ALL","aspect","station"];
var ASPECTS=["ALL","conjunction","sextile","square","trine","opposition"];
var MOTIONS=["ALL","prograde","retrograde","direct","stationary"];
function eventKey(e){
    if(!e)return "";
    return String(e.utc)+"|"+String(e.transit_body)+"|"+
        String(e.type)+"|"+String(e.aspect)+"|"+String(e.direction);
}
function filtered(model,kind,planet,descending,aspect,motion) {
    if(!model||!model.ready||!Array.isArray(model.events)||
       TYPES.indexOf(kind)<0||ASPECTS.indexOf(aspect)<0||
       MOTIONS.indexOf(motion)<0||typeof descending!=="boolean")
        return [];
    if(planet!==""&&(!model.series||
       !model.series.some(function(s){return s.id===planet;})))return [];
    var events=model.events.filter(function(e){
        if(kind!=="ALL"&&e.type!==kind)return false;
        if(planet!==""&&e.transit_body!==planet)return false;
        // Aspect filter intentionally leaves stations in ALL mode: stations
        // have no aspect class, so must not be mislabeled as aspect matches.
        if(e.type==="aspect"&&aspect!=="ALL"&&e.aspect!==aspect)return false;
        if(motion!=="ALL"&&e.direction!==motion)return false;
        return true;
    });
    return descending?events.slice().reverse():events;
}
function page(model,kind,planet,descending,aspect,motion,index){
    var matches=filtered(model,kind,planet,descending,aspect,motion);
    var pages=Math.max(1,Math.ceil(matches.length/PAGE_SIZE));
    var at=Number.isInteger(index)&&index>=0?Math.min(index,pages-1):0;
    var start=at*PAGE_SIZE;
    return {ready:!!model&&!!model.ready,
        index:at,pages:pages,total:matches.length,
        first:matches.length?start+1:0,
        last:Math.min(start+PAGE_SIZE,matches.length),
        items:matches.slice(start,start+PAGE_SIZE)};
}
function inspect(model,key){
    if(!model||!model.ready||!Array.isArray(model.events)||
       typeof key!=="string"||key.length===0)return null;
    var found=model.events.find(function(e){return eventKey(e)===key;});
    if(!found)return null;
    if(found.type==="station"){
        return {type:"station",utc:found.utc,planet:found.transit_body,
            direction:found.direction,longitude_deg:found.longitude_deg,
            velocity_deg_day:found.velocity_deg_day,
            numerical_bracket_seconds:60,exact_astronomical_time:false};
    }
    if(found.type==="aspect"){
        return {type:"aspect",utc:found.utc,planet:found.transit_body,
            direction:found.direction,aspect:found.aspect,
            angle_deg:found.degrees,residual_deg:found.residual_deg,
            numerical_bracket_seconds:1,exact_astronomical_time:false};
    }
    return null;
}
function nextOption(items,current){
    var i=items.indexOf(current);
    return items[(i+1)%items.length];
}
