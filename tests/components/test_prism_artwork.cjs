// Run: node --test tests/components/test_prism_artwork.cjs
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const scope=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root,"components/PrismArtwork.js"),"utf8"),scope);
const palette=["DCF3FA","ED981A","F2BE4E","9ECE6A","55CFCA","5B5FD4","A879ED","C74EC7","1B0623"]
    .map(s=>[0,2,4].map(i=>parseInt(s.slice(i,i+2),16)/255));
function render(size,strength=1,border=1,faceHeight=size) {
    const face=Math.min(size,faceHeight),pad=Math.ceil(face*.09);
    const W=size+2*pad,H=faceHeight+2*pad,scale=Math.min(2,256/Math.max(W,H));
    const w=Math.min(256,Math.ceil(W*scale)),h=Math.min(256,Math.ceil(H*scale));
    let data;
    scope.paint({createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),
        clearRect(){},putImageData(im){data=im.data;}},w,h,size,faceHeight,pad,border,palette,strength);
    const sample=(fx,fy)=>{
        const col=Math.floor((fx+W/2)/W*w),row=Math.floor((fy+H/2)/H*h);
        assert.ok(col>=0&&col<w&&row>=0&&row<h);
        const i=(row*w+col)*4; return Array.from(data.slice(i,i+4));
    };
    const unit=face/(244/2.4);
    return {w,h,data,sample,icon:(x,y)=>sample((x-103/2.4)*unit,(y-40)*unit)};
}
test("approved angles, constant widths, symmetric entry gap and spectrum anchors",()=>{
    const g=scope.prismGeometry();
    assert.deepEqual(Array.from(g.angles),[25,-20,-2.5,35]);
    assert.equal(g.coreWidth,2.5);
    assert.equal(g.startX,2);assert.equal(g.endX,87);
    assert.equal(g.entryGap,1.33);assert.equal(g.compactGap,2.13);
    assert.equal(g.nodeRadius,5.8);
    assert.equal(g.spectrumIndices[0],0);
    assert.equal(g.spectrumIndices[4],3);assert.equal(g.spectrumIndices[5],3);
    assert.equal(g.spectrumIndices.at(-1),6);
});
test("bounded raster, white rear and saturated cyan outgoing node at seven sizes",()=>{
    for(const size of [24,32,44,64,96,128,256]) {
        const r=render(size);
        assert.ok(r.w<=256&&r.h<=256);
        assert.equal(r.data.length,r.w*r.h*4);
        const back=r.icon(39,40),front=r.icon(45,40);
        assert.ok(back[0]>=back[1]*.75&&back[2]>200,"white rear "+size);
        assert.ok(front[0]<front[1]&&front[0]<front[2],"colored front "+size);
        assert.ok(back[3]>240&&front[3]>240,"opaque node "+size);
    }
});
test("exterior glow and interior artwork are separated by the native white border",()=>{
    const r=render(96),half=48;
    const bl=r.sample(-half-1,half+1),tr=r.sample(half+1,-half-1);
    const tl=r.sample(-half-1,-half-1),br=r.sample(half+1,half+1);
    assert.ok(bl[0]>bl[1]&&bl[1]>bl[2]);
    assert.ok(tr[0]>tr[1]&&tr[2]>tr[1]);
    for(const c of [tl,br]) assert.ok(c[1]>c[0]&&c[2]>c[0]&&c[3]>0);
    assert.equal(r.sample(half-.5,0)[3],0,"native border stays clear");
    assert.equal(render(96,0).sample(half+1,0)[3],0,"glow-off exterior");
});
test("rectangular allocation is centered and keeps the raster bounded",()=>{
    const r=render(220,1,2,44);
    assert.ok(r.w<=256&&r.h<=256);
    const back=r.icon(39,40),front=r.icon(45,40);
    assert.ok(back[2]>200&&front[1]>front[0]);
});
test("component uses canonical colors and existing action behavior without sampled sources",()=>{
    const qml=fs.readFileSync(path.join(root,"components/PrismButton.qml"),"utf8");
    const qmldir=fs.readFileSync(path.join(root,"components/qmldir"),"utf8");
    assert.match(qml,/ActionButton\s*\{/);
    for(const c of ["white","orange","yellow","green","cyan","blue","purple","magenta","black"])
        assert.match(qml,new RegExp("Colors\\."+c+"\\b"));
    assert.match(qml,/keyboardActivationSignal: "leftClicked"/);
    assert.match(qml,/contentGlowSource: null/);
    assert.match(qml,/rasterLimit: 256/);
    assert.doesNotMatch(qml,/\b(?:Timer|Process|ShaderEffectSource)\s*\{/);
    assert.match(qmldir,/^PrismButton 1\.0 PrismButton\.qml$/m);
});
