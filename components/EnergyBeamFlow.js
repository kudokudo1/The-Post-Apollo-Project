// Deterministic visual geometry only. Pixel speed scales with bar height,
// not track length, and the number of streaks is bounded.
function flow(variant, fireMode, side, span, height, time, reduced) {
    const w=Math.max(0,Number.isFinite(span)?span:0);
    const h=Math.max(0,Number.isFinite(height)?height:0);
    if(w<1 || h<1) return [];
    const t=reduced?0:Math.max(0,Number.isFinite(time)?time:0);
    const tron=variant==="tron", fire=variant==="flamethrower";
    const ki=variant==="ki-blast";
    if(!tron && !fire && !ki) return [];
    const rows=[];
    function stream(region, offset, count, speed, length, opacity, wake) {
        if(region<1) return;
        for(let i=0;i<count;i++){
            const lane=(i*7%13)/12;
            const seed=((i*.61803398875+.17)%1);
            const v=speed*(.82+(i%5)*.09);
            const travel=((seed*region+t*v)%region+region)%region;
            const size=Math.min(region,h*length*(.6+(i%4)*.23));
            // Left/player current travels right; enemy travels left.
            const start=side==="enemy"?region-travel-size:travel;
            rows.push({x:offset+start,y:h*(.14+.72*lane),length:size,
                alpha:opacity*(.68+(i%4)*.10),wake:wake});
        }
    }
    if(tron) {
        stream(w,0,Math.min(44,Math.max(12,Math.ceil(w/h*2.1))),h*23,2.2,.84,false);
        const wake=Math.min(w,h*7);
        stream(wake,w-wake,9,h*28,3.5,.91,true);
    } else if(ki) {
        stream(w,0,Math.min(32,Math.max(7,Math.ceil(w/h*1.55))),h*11,1.15,.68,false);
    } else {
        const wake=Math.min(w,h*4.4);
        // Cooled residue and exposed background never acquire a live
        // full-lane current. Only standard fire retains scattered lines.
        if(fireMode==="standard") stream(w,0,Math.min(12,Math.max(3,Math.ceil(w/h*.45))),h*7,.8,.30,false);
        stream(wake,w-wake,11,h*12,1.35,.65,true);
    }
    return rows;
}
function head(variant,height,power,width) {
    const h=Math.max(0,height),w=Math.max(0,width);
    const large=variant==="tron"||variant==="omnitrix";
    if(!large) return null;
    const scale=Math.max(1,Math.min(2.5,power));
    // A core that covers the entire cross-section even at ignition.
    return {rx:Math.min(h*(variant==="omnitrix"?.83:.76)*(1+.16*(scale-1)),w*.48),
        ry:h*(.66+.055*(scale-1)),solid:.48};
}

function clashSizes(fraction,heat) {
    const p=Math.max(0,Math.min(1,fraction));
    const bias=2*p-1;
    return {player:1+.60*bias,enemy:1-.60*bias+.22*heat};
}
