// Prism artwork: screen-coordinate angles (positive is down).
// Pure geometry / smooth analytic glow, intentionally independent of input.
function prismGeometry() {
    const angles = [25, -20, -2.5, 35];
    return { angles, junction:[42,40], triangle:[[43,14],[68,65],[18,65]],
        startX:2, endX:87, coreWidth:2.5, outlineWidth:1.5,
        entryGap:1.33, compactGap:2.13, nodeRadius:5.8,
        spectrumStops:[0,.17,.23,.28,.36,.63,.69,.76,.83,1],
        spectrumIndices:[0,0,1,2,3,3,4,5,6,6] };
}

function paint(ctx, pixelWidth, pixelHeight, faceWidth, faceHeight, padding, borderWidth, palette, strength) {
    // Render one bounded, antialiased texture; no sampled scene items or animation.
    const g=prismGeometry(), w=pixelWidth, h=pixelHeight;
    const W=faceWidth+2*padding, H=faceHeight+2*padding;
    const face=Math.min(faceWidth,faceHeight);
    if (!(w>0 && h>0 && face>0)) return;
    const unit=face/(244/2.4), sx=W/w, sy=H/h;
    const aa=Math.max(sx,sy)/unit;
    const [white,orange,yellow,green,cyan,blue,purple,magenta,black]=palette;
    const spectral=[orange,yellow,green,cyan,blue,purple,magenta];
    const clamp=v=>Math.max(0,Math.min(1,v));
    const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
    const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
    const gaussian=(d,s)=>Math.exp(-0.5*(d/s)*(d/s));
    const dist=(x,y,a,b)=>{
        const dx=b[0]-a[0],dy=b[1]-a[1];
        const t=clamp(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy));
        return Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);
    };
    const j=g.junction, ts=g.triangle, rad=Math.PI/180;
    const incoming=[g.startX,j[1]+(g.startX-j[0])*Math.tan(g.angles[0]*rad)];
    const ends=g.angles.slice(1).map(a=>[g.endX,j[1]+(g.endX-j[0])*Math.tan(a*rad)]);
    const cosines=g.angles.map(a=>Math.cos(a*rad)), sines=g.angles.map(a=>Math.sin(a*rad));
    const beamColors=[white,magenta,cyan,orange];
    const spectrum=t=>{
        for(let i=1;i<g.spectrumStops.length;i++) if(t<=g.spectrumStops[i])
            return mix(spectral[g.spectrumIndices[i-1]],spectral[g.spectrumIndices[i]],
                clamp((t-g.spectrumStops[i-1])/(g.spectrumStops[i]-g.spectrumStops[i-1])));
        return magenta;
    };
    const nodeSpectrum=dy=>dy<-.6?mix(magenta,cyan,smooth(-3.4,-.6,dy)):mix(cyan,orange,smooth(.1,3.5,dy));
    const image=ctx.createImageData(w,h), data=image.data;
    const p=[0,0,0,0];
    function over(c,a) {
        a=clamp(a);
        if(a<=0) return;
        const k=1-a;
        p[0]=c[0]*a+p[0]*k;p[1]=c[1]*a+p[1]*k;p[2]=c[2]*a+p[2]*k;p[3]=a+p[3]*k;
    }
    const glow=Math.max(0,Math.min(1,Number(strength)));
    const gap=face<=32?g.compactGap:g.entryGap;
    const sideLength=Math.hypot(51,25);
    for(let row=0;row<h;row++) for(let col=0;col<w;col++) {
        p[0]=p[1]=p[2]=p[3]=0;
        const fx=(col+.5)*sx-W/2, fy=(row+.5)*sy-H/2;
        const ox=Math.max(0,Math.abs(fx)-faceWidth/2),oy=Math.max(0,Math.abs(fy)-faceHeight/2);
        if(ox>0 || oy>0) {
            // Exterior border only; cyan is shared by top-left and bottom-right.
            const t=clamp(.5+Math.max(-.5,Math.min(.5,fx/faceWidth))/2
                             -Math.max(-.5,Math.min(.5,fy/faceHeight))/2);
            const d=Math.hypot(ox,oy)/unit;
            over(spectrum(t),glow*(.48*gaussian(d,1.6)+.22*gaussian(d,4.8))*(1-smooth(7,9,d)));
        } else if(Math.abs(fx)<faceWidth/2-borderWidth && Math.abs(fy)<faceHeight/2-borderWidth) {
            const x=fx/unit+103/2.4,y=fy/unit+40;
            const lx=(51*(x-43)+25*(y-14))/sideLength;
            const rx=(-51*(x-43)+25*(y-14))/sideLength;
            const sd=Math.min(lx,rx,65-y);
            const td=Math.min(dist(x,y,ts[0],ts[1]),dist(x,y,ts[1],ts[2]),dist(x,y,ts[2],ts[0]));
            const triCover=smooth(-aa/2,aa/2,sd);
            const triangleColor=mix(white,nodeSpectrum((y-40)/4),smooth(33,66,x));
            // A noticeable but subordinate triangle halo. It never colors the glass fill.
            over(triangleColor,glow*(1-triCover)*(.12*gaussian(td,8)+.14*gaussian(td,3)));
            // White wash is the dominant material identity, not a spectral fill.
            const wash=.48+(.12-.48)*clamp((y-14)/51);
            over(mix(mix(black,white,.035),white,wash),triCover);
            // Full white beam luminosity on BOTH sides of the entrance; only its core is interrupted.
            const distances=[dist(x,y,incoming,j),...ends.map(e=>dist(x,y,j,e))];
            for(let i=1;i<4;i++) {
                const d=distances[i];
                over(beamColors[i],glow*(.23*gaussian(d,10)+.32*gaussian(d,3.4)));
            }
            over(white,glow*(.23*gaussian(distances[0],10)+.32*gaussian(distances[0],3.4)));
            over(white,1-smooth(g.outlineWidth/2-aa/2,g.outlineWidth/2+aa/2,td));
            // Vertical start/end clipping; surface gap parallel to the left face.
            const cover=i=>{
                const normal=Math.abs(-(x-j[0])*sines[i]+(y-j[1])*cosines[i]);
                const widthCoverage=1-smooth(g.coreWidth/2-aa/2,g.coreWidth/2+aa/2,normal);
                const min=i===0?g.startX:j[0], max=i===0?j[0]:g.endX;
                return widthCoverage*smooth(min-aa/2,min+aa/2,x)*(1-smooth(max-aa/2,max+aa/2,x));
            };
            // Shared coverage for the close pair removes stack-order color slivers.
            const m=cover(1),c=cover(2);
            if(m+c>0) over(mix(magenta,cyan,c/(m+c)),.9*Math.max(m,c));
            over(orange,.9*cover(3));
            const entryClear=1-smooth(-gap-aa/2,-gap+aa/2,lx)+smooth(gap-aa/2,gap+aa/2,lx);
            over(white,.9*cover(0)*clamp(entryClear));
            // Compact directional nucleus: a solid color mask, not more diffuse blur.
            // White left, spectrum right; the short central transition blends them.
            const dx=x-j[0],dy=y-j[1],d=Math.hypot(dx,dy);
            if(d<g.nodeRadius+aa) {
                const nucleus=mix(white,nodeSpectrum(dy),smooth(-1.7,2.2,dx));
                over(nucleus,.98*(1-smooth(g.nodeRadius-1.1-aa/2,g.nodeRadius+aa/2,d)));
            }
        }
        const at=(row*w+col)*4, a=p[3];
        data[at]=a>0?Math.round(clamp(p[0]/a)*255):0;
        data[at+1]=a>0?Math.round(clamp(p[1]/a)*255):0;
        data[at+2]=a>0?Math.round(clamp(p[2]/a)*255):0;
        data[at+3]=Math.round(clamp(a)*255);
    }
    ctx.clearRect(0,0,w,h);
    ctx.putImageData(image,0,0);
}
