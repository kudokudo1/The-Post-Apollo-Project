// Visual profiles only. These never change operation progress or authority.
function profile(variant) {
    switch (variant) {
    case "omnitrix": return {x:.10,y:.05,brightness:1.45,head:1.10,fragments:0,flash:.72,style:"contained"};
    case "tron": return {x:.45,y:.18,brightness:1.0,head:.75,fragments:0,flash:0,style:"speed"};
    case "flamethrower": return {x:.95,y:.90,brightness:1.05,head:1.0,fragments:.8,flash:0,style:"fire"};
    default: return {x:1,y:1,brightness:1,head:1,fragments:1,flash:0,style:"struggle"};
    }
}
function clamp(x) { return Math.max(0,Math.min(1,Number.isFinite(x)?x:0)); }
function smooth(x) { x=clamp(x); return x*x*(3-2*x); }
function host(variant, time, level, strength, phase, reduced) {
    const p=profile(variant);
    const t=Number.isFinite(time)?Math.max(0,time):0;
    const power=reduced?0:clamp(level*strength);
    // Directional road buzz and slow lateral drift, rather than quake harmonics.
    const x=p.style==="speed" ? 1.9*Math.sin(t*11)+1.1*Math.sin(t*46)
        : 2.3*Math.sin(t*27)+.7*Math.sin(t*13);
    const y=p.style==="speed" ? .55*Math.sin(t*37)+1.45*Math.sin(t*16)
        : 1.5*Math.sin(t*21)+.5*Math.sin(t*9);
    // A single soft green-white completion pulse, never a running strobe.
    const flash=phase==="success" && !reduced
        ? p.flash*smooth((t-.42)/.10)*(1-smooth((t-.52)/.30)) : 0;
    return {power:power,dx:power*x*p.x,dy:power*y*p.y,
        flash:flash,fragments:power*p.fragments,style:p.style,
        score:power*Math.max(p.x,p.y)};
}
