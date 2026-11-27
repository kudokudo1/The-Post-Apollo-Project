// Original procedural pixel combustion. The front is rounded, the rear
// tapers with the wind. The same clock drives detached sparks.
function fire(height,time,reduced,mode) {
    const h=Math.max(0,Number.isFinite(height)?height:0);
    if(h<4) return {unit:1,cells:[],embers:[]};
    const unit=Math.max(1,Math.round(h/12));
    const t=reduced?0:Math.max(0,Number.isFinite(time)?time:0);
    const tick=Math.floor(t*12);
    const rocket=mode!=="ash-trail"&&mode!=="burn-away";
    const extent=rocket?15:mode==="ash-trail"?12:10;
    const cells=[],embers=[];
    for(let x=-extent;x<=6;x++){
        const tail=x< -4;
        const q=tail?(x+extent)/(extent-4):0;
        const radius=tail?(.45+4.7*Math.pow(q,.72)):
            6.15*Math.sqrt(Math.max(0,1-((x-.4)/6.8)**2));
        const wave=Math.sin(tick*.55+x*.75)*.65;
        const center=tail?Math.sin(tick*.41+x*.47)*(1-q)*1.65:wave*.38;
        for(let y=-7;y<=7;y++){
            const d=Math.abs(y-center);
            if(d>radius+wave*.45) continue;
            const heat=d>radius*.77?0:d>radius*.48?1:d>radius*.22?2:3;
            cells.push({x:x,y:y,heat:heat});
        }
    }
    for(let i=0;i<12;i++){
        const age=(t*(.62+i%3*.13)+i*.173)%1;
        const x=Math.round(-5-age*(extent+5+i%5));
        const y=Math.round(Math.sin(i*2.4+t*.8)*(3+age*5)-age*1.5);
        embers.push({x:x,y:y,heat:i%3===0?2:1,alpha:(1-age)*.80});
    }
    return {unit:unit,cells:cells,embers:embers};
}
