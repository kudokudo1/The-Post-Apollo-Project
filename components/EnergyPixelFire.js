// Original procedural pixel combustion. The front is rounded, the rear
// tapers with the wind. The same clock drives detached sparks.
function fire(height,time,reduced,mode,speed) {
    const h=Math.max(0,Number.isFinite(height)?height:0);
    if(h<4) return {unit:1,cells:[],embers:[]};
    const unit=Math.max(1,Math.round(h/12));
    const t=reduced?0:Math.max(0,Number.isFinite(time)?time:0);
    const motion=lightMotion(t,speed,reduced);
    const tick=t*16;
    const rocket=mode!=="ash-trail"&&mode!=="burn-away";
    const extent=(rocket?15:mode==="ash-trail"?12:10)+Math.round(3*motion.speed);
    const cells=[],embers=[];
    for(let x=-extent;x<=6;x++){
        const tail=x< -4;
        const q=tail?(x+extent)/(extent-4):0;
        const radius=tail?(.45+4.7*Math.pow(q,.72)):
            6.15*Math.sqrt(Math.max(0,1-((x-.4)/6.8)**2));
        const wave=Math.sin(tick*.71+x*.75)*.90+Math.sin(tick*.43-x*.93)*.48;
        const center=tail?(Math.sin(tick*.49+x*.47)*2.15+Math.sin(tick*.81-x*.32)*.85)*(1-q)+motion.sway*2.5:wave*.48+motion.sway*2.5;
        for(let y=-7;y<=7;y++){
            const d=Math.abs(y-center);
            if(d>radius+wave*.45) continue;
            const heat=d>radius*.77?0:d>radius*.48?1:d>radius*.22?2:3;
            cells.push({x:x,y:y,heat:heat});
        }
    }
    for(let i=0;i<12;i++){
        const age=(t*(.80+i%3*.18)+i*.173)%1;
        const x=Math.round(-5-age*(extent+5+i%5+4*motion.speed));
        const y=Math.round(Math.sin(i*2.4+t*.8)*(3+age*5)-age*1.5);
        embers.push({x:x,y:y,heat:i%3===0?2:1,alpha:(1-age)*.80});
    }
    return {unit:unit,cells:cells,embers:embers};
}

// Normalized screen-space velocity: one unit is twelve bar heights per
// second. Smooth on the existing frame clock; never infer operation progress.
function velocity(previous,current,dt,width,height,prior) {
    if(!Number.isFinite(dt)||dt<=0||!Number.isFinite(width)||!Number.isFinite(height)||height<=0) return 0;
    const rate=(current-previous)*Math.max(0,width)/(dt*height*12);
    const target=Number.isFinite(rate)?Math.max(0,Math.min(1,rate)):0;
    const old=Number.isFinite(prior)?Math.max(0,Math.min(1,prior)):0;
    return old+(target-old)*(1-Math.exp(-dt/.14));
}
// Continuous, bounded flame movement. Distances are in bar heights.
// The glow is advected behind its source, not independently animated.
function lightMotion(time,speed,reduced) {
    if(reduced) return {speed:0,sway:0,drag:0,stretch:1,pulse:1,breath:1};
    const t=Number.isFinite(time)?Math.max(0,time):0;
    const v=Number.isFinite(speed)?Math.max(0,Math.min(1,speed)):0;
    const wave=.65*Math.sin(t*9.1)+.35*Math.sin(t*14.7+.8);
    return {speed:v,sway:.095*wave,
        drag:v*(.48+.08*Math.sin(t*6.7)),
        stretch:1+v*.72+.075*Math.sin(t*8.2),
        pulse:1+.12*Math.sin(t*8.9)+.065*Math.sin(t*13.7+1.2),
        breath:1+.085*Math.sin(t*7.3)+.045*Math.sin(t*11.8)};
}
// Continuous smooth falloff sampled into gradient stops; no solid band.
function falloff(radius) {
    const x=Math.max(0,Math.min(1,radius));
    return (1-x)*(1-x)*(1+2*x);
}
