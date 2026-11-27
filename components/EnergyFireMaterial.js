// Laboratory-only material experiment. No operation state or randomness
// outside the deterministic material geometry.
function geometry(mode, fraction, width, height) {
    const w=Math.max(0, Number.isFinite(width)?width:0);
    const h=Math.max(0, Number.isFinite(height)?height:0);
    const p=Math.max(0,Math.min(1,Number.isFinite(fraction)?fraction:0));
    const ash=mode==="ash-trail", erosion=mode==="burn-away";
    return {fraction:p, burned:w*p, remaining:w*(1-p), height:h,
        ash:ash, erosion:erosion, experimental:ash||erosion};
}
function grain(n, salt) {
    const v=Math.sin(n*127.1+salt*311.7)*43758.5453123;
    return v-Math.floor(v);
}
function tint(r,g,b,a) { return Qt.rgba(r,g,b,a); }
// Grain coordinates are anchored to the material, not the moving head.
// The burned surface does not flicker or continue to burn indefinitely.
function drawAsh(c,x,y,w,h,edge,hot) {
    if (edge<=x || w<=0 || h<=0) return;
    const burned=Math.min(w,edge-x);
    c.save(); c.beginPath(); c.rect(x,y,burned,h); c.clip();
    const base=c.createLinearGradient(0,y,0,y+h);
    base.addColorStop(0,"#39383e"); base.addColorStop(.48,"#67656b");
    base.addColorStop(1,"#25252a");
    c.fillStyle=base; c.fillRect(x,y,burned,h);
    for(let i=0;i<Math.min(300,Math.ceil(w*h/32));i++){
        const px=x+grain(i,1)*w, py=y+grain(i,2)*h;
        const r=grain(i,3), size=.5+grain(i,4)*2.3;
        if(px>x+burned) continue;
        c.fillStyle=r>.7?tint(.75,.73,.72,.32):tint(.08,.08,.10,.4);
        c.fillRect(px,py,size*1.7,size);
    }
    if(hot) {
        const heatAlpha=typeof hot==="number"?Math.max(0,Math.min(1,hot)):1;
        const span=Math.min(burned,h*.85);
        const heat=c.createLinearGradient(edge-span,y,edge,y);
        heat.addColorStop(0,tint(.42,.18,.04,0));
        heat.addColorStop(.72,tint(.75,.26,.03,.35*heatAlpha));
        heat.addColorStop(1,tint(.92,.46,.12,.60*heatAlpha));
        c.fillStyle=heat; c.fillRect(edge-span,y,span,h);
    }
    c.restore();
}
// Render only the remaining solid chassis. The left region is genuinely
// transparent except for small stationary burnt fragments near the cut.
function drawRemaining(c,x,y,w,h,edge,hot,border,inset) {
    const remaining=Math.max(0,x+w-edge);
    if(remaining>0 && h>0) {
        const n=Math.min(remaining,h*.24);
        c.save();
        c.beginPath();
        c.moveTo(edge+n,y); c.lineTo(x+w,y);
        c.lineTo(x+w,y+h); c.lineTo(edge+n,y+h);
        c.lineTo(edge+n*.20,y+h*.83);
        c.lineTo(edge+n*.62,y+h*.64);
        c.lineTo(edge,y+h*.49);
        c.lineTo(edge+n*.55,y+h*.27);
        c.closePath();
        const g=c.createLinearGradient(0,y,0,y+h);
        g.addColorStop(0,"#26212b"); g.addColorStop(.5,"#3b323c"); g.addColorStop(1,"#16121b");
        const pad=Math.max(0,Number.isFinite(inset)?inset:0);
        if(pad>0) {
            // The surviving shell is still present, but its solid material
            // sits inside the same clear channel as the other treatments.
            c.fillStyle="#16051F"; c.fill();
            c.save(); c.clip();
            const left=Math.max(x+pad,edge+pad);
            const right=x+w-pad;
            if(right>left && h>2*pad) {
                c.fillStyle=g;
                c.fillRect(left,y+pad,right-left,h-2*pad);
            }
            c.restore();
        } else {
            c.fillStyle=g; c.fill();
        }
        c.strokeStyle=border; c.lineWidth=1; c.stroke();
        c.restore();
    }
    if(hot && remaining>0) {
        const heatAlpha=typeof hot==="number"?Math.max(0,Math.min(1,hot)):1;
        const start=Math.max(x,edge-h*.75);
        for(let i=0;i<10;i++){
            const px=start+grain(i,12)*(edge-start);
            const py=y+h*(.25+.6*grain(i,13));
            c.fillStyle=tint(.40,.27,.19,(.28+.32*grain(i,14))*heatAlpha);
            c.fillRect(px,py,1+grain(i,15)*2,1+grain(i,16)*2);
        }
    }
}

// A small living contact bed, not a second flame sprite. Coordinates
// are normalized to the remaining material, so no erased shell reappears.
function heatBed(time,speed,reduced) {
    const t=reduced?0:Math.max(0,Number.isFinite(time)?time:0);
    const v=reduced?0:Math.max(0,Math.min(1,Number.isFinite(speed)?speed:0));
    const rows=[];
    for(let i=0;i<7;i++) {
        const wave=Math.sin(t*(9.2+i*.67)+i*2.17);
        const q=Math.sin(t*(5.4+i*.31)-i*1.37);
        rows.push({y:(i+.5)/7, reach:.24+.22*(wave*.5+.5)+.26*v,
            alpha:.20+.20*(q*.5+.5), shift:.08*(wave*.5+.5)});
    }
    return {pulse:.82+.11*Math.sin(t*8.9)+.07*Math.sin(t*15.1),
        reach:.86+.22*v+.10*Math.sin(t*6.8), rows:rows};
}
