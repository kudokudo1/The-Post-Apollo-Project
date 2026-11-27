// Deterministic visual geometry only. Pixel speed scales with bar height,
// not track length, and the number of streaks is bounded.
function flow(variant, fireMode, side, span, height, time, reduced, speedLevel) {
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
            // Keep combustion wake distributed even at a single frozen frame.
            const seed=fire&&wake?i/count:((i*.61803398875+.17)%1);
            const v=fire&&wake?speed:speed*(.82+(i%5)*.09);
            const travel=((seed*region+t*v)%region+region)%region;
            const size=Math.min(region,h*length*(.6+(i%4)*.23));
            // Left/player current travels right; enemy travels left.
            const start=side==="enemy"?region-travel-size:travel;
            rows.push({x:offset+start,y:h*(.14+.72*lane),length:size,
                alpha:opacity*(.68+(i%4)*.10),wake:wake});
        }
    }
    if(tron) {
        const speed=Number.isFinite(speedLevel)?Math.max(0,Math.min(1,speedLevel)):1;
        const density=.08+.92*speed;
        // The fast visible wake remains attached to the head even on a
        // wall-wide track; faint internal current still covers the lane.
        stream(w,0,Math.ceil(Math.min(44,Math.max(12,Math.ceil(w/h*2.1)))*density),h*(5+18*speed),1.45,.24*(.35+.65*speed),false);
        const wake=Math.min(w,h*4.2);
        stream(wake,w-wake,Math.ceil(9*density),h*(6+22*speed),1.65,.84*(.35+.65*speed),true);
    } else if(ki) {
        stream(w,0,Math.min(32,Math.max(7,Math.ceil(w/h*1.55))),h*11,1.15,.68,false);
    } else {
        const wake=Math.min(w,h*(fireMode==="burn-away"?4.4:fireMode==="ash-trail"?6.0:6.8));
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
    return {rx:Math.min(h*(variant==="omnitrix"?.93:.82)*(1+.16*(scale-1)),w*.48),
        ry:h*((variant==="omnitrix"?.72:.70)+.055*(scale-1)),solid:.48};
}

function clashSizes(fraction,heat) {
    const p=Math.max(0,Math.min(1,fraction));
    const bias=2*p-1;
    return {player:1+.60*bias,enemy:1-.60*bias+.22*heat};
}

// Shared contact chord, smaller as either sphere dominates. The winning
// sphere is clipped only at its small contact cap, not through its center.
function contact(fraction,heat,height,width) {
    const size=clashSizes(fraction,heat);
    const h=Math.max(0,height),w=Math.max(0,width);
    const base=Math.min(h*.92,w*.22);
    const left={rx:base*size.player,ry:h*.72*size.player};
    const right={rx:base*size.enemy,ry:h*.72*size.enemy};
    const chord=Math.min(left.ry,right.ry)*.76;
    for(const lobe of [left,right]) {
        const ratio=lobe.ry>0?chord/lobe.ry:0;
        lobe.offset=lobe.rx*Math.sqrt(Math.max(0,1-ratio*ratio));
    }
    return {left:left,right:right,chord:chord};
}

// Short atmospheric lines outside the chamber. Anchored to the active
// head, not to the window or a percentage of the entire track.
function airFlow(span,height,time,reduced,speedLevel) {
    if(reduced || span<1 || height<1) return [];
    const h=height,t=Math.max(0,time),w=Math.min(span,h*5.8);
    const lines=[];
    // Deterministic irregular bursts. Seed each new streak at its own
    // lifetime boundary rather than flickering random values every frame.
    function hash(n) { const v=Math.sin(n*127.1+31.73)*43758.5453; return v-Math.floor(v); }
    const speed=Number.isFinite(speedLevel)?Math.max(0,Math.min(1,speedLevel)):1;
    const count=Math.round(14*speed);
    for(let i=0;i<count;i++){
        const clock=t*(1.8+hash(i+51)*2.4)*(.35+.65*speed)+hash(i+13);
        const cycle=Math.floor(clock), age=clock-cycle;
        const seed=i*101+cycle*37;
        const length=Math.min(w,h*(.30+hash(seed+7)*1.42));
        const distance=age*Math.max(0,w-length)*(.55+.45*hash(seed+17));
        const side=hash(seed+29)>.5?1:-1;
        lines.push({x:-distance-length,y:side*h*(.55+hash(seed+31)*.41),
            length:length,alpha:Math.sin(Math.PI*age)*(.32+.60*hash(seed+41))*(.40+.60*speed)});
    }
    return lines;
}

// Normalize actual observed fractional advance per second, not elapsed
// time or absolute progress. Short smoothing avoids measured-step flicker.
function speedSample(previous,current,dt,prior) {
    if(!Number.isFinite(dt)||dt<=0) return 0;
    const rate=Math.max(0,(current-previous)/dt);
    const target=Math.min(1,rate/.24);
    const old=Math.max(0,Math.min(1,Number.isFinite(prior)?prior:0));
    return old+(target-old)*(1-Math.exp(-dt/.16));
}
