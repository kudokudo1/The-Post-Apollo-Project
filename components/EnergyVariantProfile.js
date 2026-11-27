// Visual profiles only. These never change operation progress or authority.
function profile(variant) {
    switch (variant) {
    case "omnitrix": return {x:.10,y:.05,brightness:1.65,head:1.28,headConsume:1.35,fragments:0,flash:.72,style:"contained"};
    case "tron": return {x:.06,y:.025,brightness:1.0,head:1.10,headConsume:1.35,fragments:0,flash:0,style:"speed"};
    case "flamethrower": return {x:.95,y:.90,brightness:1.05,head:1.0,headConsume:1,fragments:.8,flash:0,style:"fire"};
    default: return {x:1,y:1,brightness:1,head:1.15,headConsume:1.42,fragments:1,flash:0,style:"struggle"};
    }
}
function clamp(x) { return Math.max(0,Math.min(1,Number.isFinite(x)?x:0)); }
function smooth(x) { x=clamp(x); return x*x*(3-2*x); }
function host(variant, time, level, strength, phase, reduced, fireMode) {
    const p=profile(variant);
    const t=Number.isFinite(time)?Math.max(0,time):0;
    const drive=variant==="flamethrower" && phase==="running"
        ? fireDrive(fireMode,t,level) : level;
    const power=reduced?0:clamp(drive*strength);
    // Directional road buzz and slow lateral drift, rather than quake harmonics.
    const x=p.style==="speed" ? 1.9*Math.sin(t*11)+1.1*Math.sin(t*46)
        : 2.3*Math.sin(t*27)+.7*Math.sin(t*13);
    const y=p.style==="speed" ? .55*Math.sin(t*37)+1.45*Math.sin(t*16)
        : 1.5*Math.sin(t*21)+.5*Math.sin(t*9);
    // A single soft green-white completion pulse, never a running strobe.
    const flash=phase==="success" && !reduced
        ? p.flash*smooth((t-.42)/.10)*(1-smooth((t-.52)/.30)) : 0;
    return {power:power,dx:power===0?0:power*x*p.x,dy:power===0?0:power*y*p.y,
        flash:flash,flashSpread:clamp((t-.42)/.32),fragments:power*p.fragments,style:p.style,
        score:power*Math.max(p.x,p.y)};
}

function fireDrive(mode,t,level) {
    // Standard flame kicks hard immediately; ash and erosion gather force.
    const start=mode==="burn-away"?.39:mode==="ash-trail"?.53:.88;
    const ramp=mode==="burn-away"?2.8:mode==="ash-trail"?2.0:.65;
    const ignition=start+(1-start)*smooth(t/ramp);
    return Math.max(clamp(level),ignition);
}
function barMotion(variant,time,level,reduced) {
    if(reduced || variant!=="tron") return {dx:0,dy:0};
    const p=.45+.55*clamp(level);
    return {dx:p*(.85*Math.sin(time*27)+.30*Math.sin(time*13)),
        dy:p*(.42*Math.sin(time*22)+.14*Math.sin(time*11))};
}
