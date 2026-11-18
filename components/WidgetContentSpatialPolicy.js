.pragma library

// One coordinate policy for plain arrows and H/J/K/L. These are
// *content* directions, never main-mode/sub-mode navigation.
function directionForKey(key) {
    if(key === 16777234 || key === 72) return [-1, 0]; // Left / H
    if(key === 16777235 || key === 75) return [0, -1]; // Up / K
    if(key === 16777236 || key === 76) return [1, 0];  // Right / L
    if(key === 16777237 || key === 74) return [0, 1];  // Down / J
    return null;
}

function center(rect) {
    return {x: rect.x + rect.width/2,
            y: rect.y + rect.height/2};
}

function initialIndex(rects) {
    if(!rects || !rects.length) return -1;
    var best=-1, bestY=Infinity, bestX=Infinity;
    for(var i=0;i<rects.length;i++) {
        var r=rects[i];
        if(r.width<=0 || r.height<=0 || !isFinite(r.x) || !isFinite(r.y))
            continue;
        if(r.visible === false) continue;
        var y=r.y, x=r.x;
        if(y<bestY-1 || (Math.abs(y-bestY)<=1 && x<bestX)) {
            best=i; bestX=x; bestY=y;
        }
    }
    return best;
}

function nextIndex(rects,current,dx,dy) {
    if(!rects || !rects.length) return -1;
    if(current<0 || current>=rects.length)
        return initialIndex(rects);
    var origin=center(rects[current]);
    var best=-1, score=Infinity;
    for(var i=0;i<rects.length;i++) {
        if(i===current) continue;
        var r=rects[i];
        if(!r || r.width<=0 || r.height<=0) continue;
        var c=center(r);
        var primary=dx!==0 ? dx*(c.x-origin.x) : dy*(c.y-origin.y);
        if(primary<=0.5) continue;
        var cross=dx!==0 ? Math.abs(c.y-origin.y) : Math.abs(c.x-origin.x);
        var size=dx!==0
            ? (r.height+rects[current].height)/2
            : (r.width+rects[current].width)/2;
        // A far-offscreen diagonal must not steal an edge arrow. Nearby
        // on-screen diagonal controls remain valid when a row is sparse,
        // and offscreen controls in the SAME column/row remain scrollable.
        if(r.visible === false && cross>Math.max(60,size)) continue;
        // Preserve the current row/column first; pick nearby controls
        // only when a straight directional neighbor does not exist.
        var perpendicular=Math.max(0,cross-size/2);
        var candidate=primary+perpendicular*3.3+cross*0.05;
        if(candidate<score) {best=i;score=candidate;}
    }
    return best>=0 ? best : current; // bounded at content edge
}
