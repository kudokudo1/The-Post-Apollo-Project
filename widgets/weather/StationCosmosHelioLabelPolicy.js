.pragma library

// V5a // Layout-only readable labels for the real HELIO JPL positions.
// Never change source XYZ, marker coordinates, AU distance or hit targets.
// Dense markers remain clickable via the V4e/V4f policy and body inspector.
var MAX_LABELS = 12;
var MAX_LABEL_WIDTH = 126;
var FONT_HEIGHT = 14;

function num(value) {
    return typeof value==="number" && isFinite(value) &&
           Math.abs(value)<=1e7 ? value : null;
}
function collide(a,b,pad) {
    var p=num(pad);
    if(!a||!b||p===null)return false;
    return a.left < b.right+p && a.right > b.left-p &&
           a.top < b.bottom+p && a.bottom > b.top-p;
}
function inside(box,bounds) {
    return box.left>=bounds.left && box.right<=bounds.right &&
           box.top>=bounds.top && box.bottom<=bounds.bottom;
}
function rect(cx,cy,width,height) {
    return {left:cx-width/2,right:cx+width/2,
            top:cy-height/2,bottom:cy+height/2};
}
function plaque(bounds,visible) {
    if(!visible || !bounds)return null;
    var available=bounds.right-bounds.left;
    if(available<125 || bounds.bottom-bounds.top<65)return null;
    var left=bounds.left+6,top=bounds.top+25;
    return {left:left,top:top,right:left+Math.min(172,available-12),
            bottom:top+33};
}

// Input screen markers already come from Helio.viewportMarker(), including
// truthful directional OUT indicators. All coords are purely display pixels.
// Labels are measured in QML via ctx.measureText before entering this helper.
function layout(markers,bounds,selectedBody,hoveredBody,hasPlaque) {
    if(!Array.isArray(markers) || markers.length>MAX_LABELS ||
       !bounds || ![bounds.left,bounds.top,bounds.right,bounds.bottom]
                    .every(function(v){return num(v)!==null;}) ||
       bounds.right-bounds.left<60 || bounds.bottom-bounds.top<40)
        return [];
    var reserved=[],focusBox=plaque(bounds,hasPlaque);
    if(focusBox)reserved.push(focusBox);
    // Every marker stays identifiable/clickable; labels may not occlude them.
    for(var k=0;k<markers.length;k++){
        var m=markers[k];
        if(!m || num(m.x)===null || num(m.y)===null ||
           typeof m.body!=="string")return [];
        reserved.push(rect(m.x,m.y,13,13));
    }
    var candidates=markers.map(function(m,index){
        var focused=m.body===selectedBody,hovered=m.body===hoveredBody;
        return {index:index,marker:m,focused:focused,hovered:hovered,
                priority:focused?100:hovered?90:m.offscreen?20:10};
    });
    candidates.sort(function(a,b){
        return b.priority-a.priority || a.index-b.index;
    });

    var labels=[],taken=reserved.slice();
    var left=bounds.left+4,right=bounds.right-4;
    var top=bounds.top+5,bottom=bounds.bottom-5;
    for(var i=0;i<candidates.length;i++){
        var item=candidates[i],mark=item.marker;
        var available=Math.max(8,right-left-8);
        var raw=num(mark.width),label=String(mark.label||mark.body);
        if(raw===null || raw<=0)continue;
        var width=Math.min(MAX_LABEL_WIDTH,available,raw),height=FONT_HEIGHT;
        var dx=12+width/2,dy=17;
        var spots=[
            [mark.x+dx,mark.y-dy],
            [mark.x-dx,mark.y-dy],
            [mark.x+dx,mark.y+dy],
            [mark.x-dx,mark.y+dy],
            [mark.x,mark.y-23],
            [mark.x,mark.y+23]
        ];
        var best=null,bestPenalty=Infinity;
        for(var j=0;j<spots.length;j++){
            var x=Math.max(left+width/2+3,
                    Math.min(right-width/2-3,spots[j][0]));
            var y=Math.max(top+height/2+2,
                    Math.min(bottom-height/2-2,spots[j][1]));
            var r=rect(x,y,width+6,height+2);
            if(!inside(r,bounds))continue;
            var overlap=0;
            for(var z=0;z<taken.length;z++)
                if(collide(r,taken[z],2))overlap++;
            var penalty=overlap*100+j;
            if(penalty<bestPenalty){
                best={body:mark.body,text:label,x:x,y:y,width:width,
                      rect:r,anchorX:mark.x,anchorY:mark.y,
                      focused:item.focused,hovered:item.hovered,
                      offscreen:!!mark.offscreen,visible:true,
                      priority:item.priority};
                bestPenalty=penalty;
            }
            if(overlap===0)break;
        }
        // Focus/hover should always be readable. Otherwise omit a label
        // rather than plaster a wall of overlapping text over the planets.
        if(!best || (bestPenalty>=100 && !item.focused && !item.hovered))
            continue;
        labels.push(best);
        taken.push(best.rect);
    }
    // Selected/hovered labels paint last and remain clear over background.
    labels.sort(function(a,b){return a.priority-b.priority;});
    return labels;
}
