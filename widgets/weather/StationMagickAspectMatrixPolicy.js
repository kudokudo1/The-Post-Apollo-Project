.pragma library

// MAGICK M6b // Read-only conventional aspect-reference heat matrix.
// Each colored cell is the closest ORIGINAL source sample to its target
// longitude-gap angle in a bounded UTC bucket. No invented 3D angles,
// no interpolated events, no natal/transit reading, and no new source actor.
var FORMAT="post-apollo.weather.celestial-visual-data.v1";
var FRAME="true-ecliptic-of-date";
var MAX_SAMPLES=721;
var MAX_COLUMNS=48;
var GUIDES=[
    {name:"CONJ",angle:0},
    {name:"SEXTILE",angle:60},
    {name:"SQUARE",angle:90},
    {name:"TRINE",angle:120},
    {name:"OPP",angle:180}
];
function finite(n){return typeof n==="number" && isFinite(n);}
function unavailable(reason){return {ready:false,reason:reason||"NO SOURCE-VERIFIED ASPECT PAIR",
    columns:[],rows:[],from:0,to:0,startMs:0,endMs:0,focus:-1,
    focusMs:0,pair:[],orb:0,source:""};}
function build(model,raw,view,focus,maximumColumns) {
    if(!model || model.ready!==true || model.frame!==FRAME ||
       !raw || raw.format!==FORMAT || !raw.query ||
       raw.query.origin!=="geocentric" ||
       raw.query.position_model!=="apparent" || raw.query.frame!==FRAME ||
       !Array.isArray(raw.query.bodies) ||
       !finite(raw.query.orb_degrees) ||
       raw.query.orb_degrees<0 || raw.query.orb_degrees>30 ||
       !Array.isArray(model.relationships) ||
       model.relationships.length!==1 ||
       !Array.isArray(model.times) || model.sampleCount!==model.times.length ||
       model.sampleCount<2 || model.sampleCount>MAX_SAMPLES ||
       !view || !Number.isInteger(view.from) ||
       !Number.isInteger(view.to) ||
       view.from<0 || view.to>=model.sampleCount || view.from>=view.to ||
       !Number.isInteger(focus) || focus<view.from || focus>view.to)
        return unavailable("M4 PAIR, FRAME, UTC WINDOW OR ORB UNAVAILABLE");
    var rel=model.relationships[0],times=model.times,
        n=view.to-view.from+1;
    if(!rel || !Array.isArray(rel.bodies) || rel.bodies.length!==2 ||
       rel.bodies[0]===rel.bodies[1] ||
       !rel.bodies.every(function(b){return raw.query.bodies.indexOf(b)>=0;}) ||
       !Array.isArray(rel.samples) || rel.samples.length!==model.sampleCount)
        return unavailable("INCONSISTENT M4 RELATIONSHIP");
    // The heat grid uses equally wide sample buckets, so only plot a
    // uniform UTC cadence. Irregular samples require a time-width chart.
    var cadence=times[1]-times[0];
    if(!finite(cadence) || cadence<=0)
        return unavailable("UNVERIFIED SOURCE UTC CADENCE");
    for(var i=0;i<model.sampleCount;i++){
        var t=times[i],s=rel.samples[i];
        if(!finite(t) || !Number.isInteger(t) ||
           (i>0 && t-times[i-1]!==cadence) ||
           !s || s.unix_ms!==t ||
           !finite(s.longitude_separation_deg) ||
           s.longitude_separation_deg<0 || s.longitude_separation_deg>180)
            return unavailable("CORRUPT M4 UTC OR ANGULAR SERIES");
    }
    var limit=Number.isInteger(maximumColumns) &&
              maximumColumns>=2 && maximumColumns<=MAX_COLUMNS
              ? maximumColumns : MAX_COLUMNS;
    var count=Math.min(n,limit),columns=[];
    for(var col=0;col<count;col++){
        var from=view.from+Math.floor(col*n/count);
        var to=view.from+Math.floor((col+1)*n/count)-1;
        if(to<from || to>=model.sampleCount)
            return unavailable("INVALID UTC BUCKET");
        columns.push({index:col,fromIndex:from,toIndex:to,
                      fromMs:times[from],toMs:times[to],size:to-from+1});
    }
    var rows=[];
    for(var r=0;r<GUIDES.length;r++){
        var guide=GUIDES[r],cells=[];
        for(var c=0;c<count;c++){
            var column=columns[c],bestIndex=-1,bestError=Infinity;
            for(var index=column.fromIndex;index<=column.toIndex;index++){
                var error=Math.abs(rel.samples[index].longitude_separation_deg-
                                   guide.angle);
                if(error<bestError){bestIndex=index;bestError=error;}
            }
            var sample=rel.samples[bestIndex],orb=raw.query.orb_degrees;
            cells.push({row:r,column:c,name:guide.name,
                angle_deg:guide.angle,sampleIndex:bestIndex,
                unix_ms:times[bestIndex],
                separation_deg:sample.longitude_separation_deg,
                error_deg:bestError,sampleCount:column.size,
                inOrb:bestError<=orb,
                strength:bestError<=orb
                    ? orb===0?1:Math.max(0,1-bestError/orb):0});
        }
        rows.push({name:guide.name,angle_deg:guide.angle,cells:cells});
    }
    return {ready:true,reason:"",source:String(model.source||""),
        frame:FRAME,orb:raw.query.orb_degrees,
        pair:rel.bodies.slice(),columns:columns,rows:rows,
        from:view.from,to:view.to,startMs:times[view.from],
        endMs:times[view.to],focus:focus,focusMs:times[focus]};
}
function geometry(width,height) {
    if(!finite(width)||!finite(height)||width<180||height<116)
        return null;
    var left=60,right=width-7,top=30,bottom=height-24;
    if(right<=left||bottom-top<80)return null;
    return {left:left,right:right,top:top,bottom:bottom,
            width:right-left,height:bottom-top,
            cellHeight:(bottom-top)/GUIDES.length};
}
function cellRect(geo,column,row,columns) {
    if(!geo || !Number.isInteger(column)||!Number.isInteger(row)||
       !Number.isInteger(columns)||columns<1||columns>MAX_COLUMNS||
       column<0||column>=columns||row<0||row>=GUIDES.length)return null;
    return {x:geo.left+geo.width*column/columns,
            y:geo.top+geo.cellHeight*row,
            width:geo.width/columns,height:geo.cellHeight};
}
function pick(data,geo,x,y) {
    if(!data||data.ready!==true||!geo||!finite(x)||!finite(y)||
       x<geo.left||x>=geo.right||y<geo.top||y>=geo.bottom)return null;
    var col=Math.floor((x-geo.left)/geo.width*data.columns.length),
        row=Math.floor((y-geo.top)/geo.cellHeight);
    if(row<0||row>=data.rows.length||col<0||
       col>=data.columns.length)return null;
    return data.rows[row].cells[col];
}
