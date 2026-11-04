"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickZodiacVectorPolicy.js");
const painter=read("widgets/weather/StationMagickCelestialInstrument.qml");
const celestial=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const context=vm.createContext({Math,isFinite});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),context);
const arity={M:3,L:3,Q:5,C:7,Z:1};

test("all twelve signs contain non-empty, executable font-independent strokes",()=>{
    assert.equal(context.STROKES.length,12);
    for(let i=0;i<12;i++){
        const paths=context.strokesFor(i);
        assert.ok(Array.isArray(paths) && paths.length>=1,"sign "+i);
        let commands=0;
        for(const p of paths){
            assert.ok(p.length>1,"sign "+i+" has more than a point");
            assert.equal(p[0][0],"M");
            for(const c of p){
                assert.equal(c.length,arity[c[0]],"command arity "+i);
                assert.ok(c.slice(1).every(n=>typeof n==="number" &&
                    Number.isFinite(n) && n>=0 && n<=24),
                    "bounded vector coordinates "+i);
                commands++;
            }
        }
        assert.ok(commands>=4,"visible glyph geometry "+i);
    }
    assert.deepEqual(JSON.parse(JSON.stringify(context.strokesFor(-1))),[]);
    assert.deepEqual(JSON.parse(JSON.stringify(context.strokesFor(12))),[]);
});

test("symbol chips fit inside the actual narrow Station Canvas and remain separated",()=>{
    for(const height of [100,110,120,150,220]){
        const width=410,radius=Math.min(width,height)*0.36;
        const centers=[];
        for(let i=0;i<12;i++){
            const c=context.sectorCenter(i,width,height,radius);
            assert.ok(c,"valid sector");
            // 9.3px background chip + small outline must remain visible.
            assert.ok(c.x>=10 && c.x<=width-10);
            assert.ok(c.y>=10 && c.y<=height-10);
            centers.push(c);
        }
        for(let i=0;i<12;i++)
            for(let j=i+1;j<12;j++){
                const dx=centers[i].x-centers[j].x;
                const dy=centers[i].y-centers[j].y;
                assert.ok(Math.hypot(dx,dy)>18.6,
                    "chips have separate centers "+height+" "+i+" "+j);
            }
    }
    assert.equal(context.sectorCenter(-1,400,120,40),null);
    assert.equal(context.sectorCenter(12,400,120,40),null);
    assert.equal(context.sectorCenter(0,0,120,40),null);
    assert.equal(context.sectorCenter(0,400,0,40),null);
});

test("each zodiac symbol is drawn at its correct tropical sector center",()=>{
    const width=400,height=112,radius=40;
    for(let i=0;i<12;i++){
        const pos=context.sectorCenter(i,width,height,radius);
        const dx=pos.x-width/2,dy=height/2-pos.y;
        const angle=(i+0.5)*Math.PI/6;
        assert.ok(Math.abs(dx-pos.radius*Math.sin(angle))<1e-9);
        assert.ok(Math.abs(dy-pos.radius*Math.cos(angle))<1e-9);
    }
});

test("QML paints vector glyphs with visible contrast, NOT missing glyph fonts",()=>{
    assert.match(painter,/import "StationMagickZodiacVectorPolicy.js" as ZodiacVector/);
    assert.match(painter,/function paintZodiacVector\(ctx,sign,x,y,color,isSelected\)/);
    assert.match(painter,/ZodiacVector\.strokesFor\(sign\)/);
    assert.match(painter,/ZodiacVector\.sectorCenter\(/);
    assert.match(painter,/ctx\.quadraticCurveTo\(/);
    assert.match(painter,/ctx\.bezierCurveTo\(/);
    assert.match(painter,/ctx\.arc\(x,y,9\.3,0,2\*Math\.PI\)/);
    assert.match(painter,/ctx\.strokeStyle=String\(Colors\.black\)/);
    assert.match(painter,/ctx\.lineWidth=4\.3/);
    assert.match(painter,/ctx\.lineWidth=isSelected\?2\.6:2\.3/);
    assert.match(painter,/ctx\.shadowBlur=instrument\.neonEnabled\?9:0/);
    assert.match(painter,/Math\.floor\(activePoint\.longitude_deg\/30\)%12/);
    assert.match(painter,/paintZodiacVector\(ctx,sign,at\.x,at\.y,/);
    assert.doesNotMatch(painter,/Noto Sans Symbols 2/);
    assert.doesNotMatch(painter,/ctx\.fillText\(glyph/);
    assert.match(celestial,/var ZODIAC_GLYPHS/);
    assert.match(painter,/onGraphModelChanged: graphCanvas\.requestPaint\(\)/);
});

test("does not modify the source processing or timeline slider owner",()=>{
    for(const forbidden of ["Quickshell.Io","Process {","Timer {",
                              "FileView {","XMLHttpRequest","curl ","pip install"])
        assert.equal(source.includes(forbidden),false);
    assert.match(painter,/id: timelineThumb/);
    assert.match(painter,/function scrubTo\(x\)/);
    assert.match(painter,/instrument\.lockedIndex=index/);
    assert.match(painter,/Celestial\.timelinePick\(/);
    assert.match(painter,/instrument\.neonStroke\(ctx/);
});

// Pixel-level fixture: same vector artwork at actual compact wheel dimensions.
// Its rasterization can be checked in CI without requiring a font or Quickshell.
if(process.argv[2]==="--emit-svg"){
    const target=process.argv[3];
    if(!target)throw Error("expected output path");
    const w=410,h=112,r=40;
    const palette=["#ED981A","#9ECE6A","#55CFCA","#C74EC7"];
    const shapes=[];
    for(let i=0;i<12;i++){
        const center=context.sectorCenter(i,w,h,r);
        const color=palette[i%4];
        const scale=0.61;
        shapes.push('<circle cx="'+center.x+'" cy="'+center.y+
            '" r="9.3" fill="#16051F" stroke="'+color+'" stroke-width="1"/>');
        for(const stroke of context.strokesFor(i)){
            const d=stroke.map(c=>c.join(" ")).join(" ");
            shapes.push('<path d="'+d+'" transform="translate('+center.x+
                ' '+center.y+') scale('+scale+') translate(-12 -12)"'+
                ' fill="none" stroke="'+color+'" stroke-width="2.3"'+
                ' stroke-linecap="round" stroke-linejoin="round"/>');
        }
    }
    fs.writeFileSync(target,'<svg xmlns="http://www.w3.org/2000/svg" '+
        'width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'">'+
        '<rect width="'+w+'" height="'+h+'" fill="#1B0623"/>'+
        shapes.join("")+'</svg>');
}
