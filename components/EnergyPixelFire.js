// Original pixel-fire silhouette, procedurally animated; no external sprite assets.
function fire(height, time, reduced, mode) {
    const h=Math.max(0,Number.isFinite(height)?height:0);
    if(h<4) return {unit:1,cells:[],embers:[]};
    const unit=Math.max(1,Math.round(h/12));
    const t=reduced?0:Math.max(0,Number.isFinite(time)?time:0);
    const tick=Math.floor(t*12);
    const cells=[],embers=[];
    const drag=mode==="burn-away"?1.05:mode==="ash-trail"?1.20:1.42;
    // Rotate the rising tongues into the rearward wind axis.
    for(let col=-7;col<=5;col++){
        const distance=Math.abs(col+1)/8;
        const rise=Math.max(2,Math.round(7*(1-distance)+2.1*Math.sin(tick*.53+col*1.36)));
        const depth=Math.max(1,Math.round(3*(1-distance)+.8*Math.sin(tick*.39+col)));
        for(let row=-rise;row<=depth;row++){
            const lean=Math.round(Math.sin(tick*.40+row*.48)*Math.max(0,-row)*.20);
            const edge=row===-rise||col===-7||col===5;
            const inner=Math.abs(col+1)<4 && row>=-rise+2 && row<2;
            const heat=edge?0:inner?(Math.abs(col+1)<2&&row>=-2?3:2):1;
            cells.push({x:Math.round(row*drag),y:col+lean+1,heat:heat});
        }
    }
    for(let i=0;i<12;i++){
        const age=(t*(.62+i%3*.13)+i*.173)%1;
        const x=Math.round(-5-age*(9+i%5)*drag);
        const y=Math.round(Math.sin(i*2.4+t*.8)*(3+age*5)-age*1.5);
        embers.push({x:x,y:y,heat:i%3===0?2:1,alpha:(1-age)*.80});
    }
    return {unit:unit,cells:cells,embers:embers};
}
