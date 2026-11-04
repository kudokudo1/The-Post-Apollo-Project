"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
const policy=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const vector=read("widgets/weather/StationMagickZodiacVectorPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const ctx=vm.createContext({Math,isFinite});
const art=vm.createContext({Math,isFinite});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),ctx);
vm.runInContext(vector.replace(/^\.pragma library\s*/m,""),art);
const model={ready:true,sampleCount:61};
const view={from:8,to:40,count:33};
const pick=(start,dx,v=view,m=model)=>ctx.wheelDragIndex(m,v,start,dx);

test("wheel drag is relative to current sample, not absolute canvas X",()=>{
    assert.equal(pick(20,0),20);
    assert.equal(pick(20,5),20);
    assert.equal(pick(20,6),21);
    assert.equal(pick(20,12),21);
    assert.equal(pick(20,18),22);
    assert.equal(pick(20,-5),20);
    assert.equal(pick(20,-6),19);
    assert.equal(pick(20,-12),19);
    assert.equal(pick(20,-18),18);
    // 220px absolute pointer X must never force a jump when delta is tiny.
    assert.equal(pick(20,2),20);
    assert.equal(pick(20,-2),20);
    // Purely relative: same delta from either graph horizontal position.
    assert.equal(pick(20,24),22);
    assert.equal(pick(20,24),pick(20,24));
});

test("wheel scrub remains bounded by selected zoom window",()=>{
    assert.equal(pick(20,1000),40);
    assert.equal(pick(20,-1000),8);
    assert.equal(pick(3,0),8);
    assert.equal(pick(58,0),40);
    assert.equal(pick(40,60),40);
    assert.equal(pick(8,-60),8);
    const narrow={from:30,to:31,count:2};
    assert.equal(pick(30,12,narrow),31);
    assert.equal(pick(30,-12,narrow),30);
    assert.equal(pick(31,-12,narrow),30);
    assert.equal(pick(31,12,narrow),31);
});

test("wheel scrub rejects invalid or missing source and finger movement",()=>{
    assert.equal(pick(20,12,view,{ready:false,sampleCount:61}),-1);
    assert.equal(pick(20,NaN),-1);
    assert.equal(pick(20,Infinity),-1);
    assert.equal(pick(NaN,12),-1);
    assert.equal(pick(20,12,{from:1,to:1,count:1}),-1);
    assert.equal(pick(20,12,{from:1,to:100,count:100}),-1);
});

test("wheel/relationship hovering does not auto-scrub or force repaints",()=>{
    assert.match(qml,/property int gestureStartIndex: -1/);
    assert.match(qml,/gestureStartIndex=instrument\.focusIndex/);
    assert.match(qml,/gestureStartIndex,mouse\.x-gestureOriginX/);
    assert.match(qml,/Celestial\.wheelDragIndex\(/);
    assert.match(qml,/if\(next>=0 && next!==instrument\.lockedIndex\)/);
    assert.match(qml,/instrument\.mode!=="wheel"\s*&&\s*instrument\.mode!=="relations"/);
    assert.match(qml,/if\(next!==instrument\.hoveredIndex\)/);
    assert.match(qml,/onModeChanged:\s*\{/);
    assert.match(qml,/instrument\.hoveredIndex=-1/);
    assert.match(qml,/if\(!pressed && instrument\.lockedIndex<0\)/);
    assert.doesNotMatch(qml,/instrument\.viewWindow,\s*sampleFraction\(mouse\.x\)\);\s*\}\s*previousX/);
});

test("selected zodiac grows while idle elements dim but remain legible",()=>{
    const idle=art.appearance(false),on=art.appearance(true);
    assert.ok(on.chipRadius>=idle.chipRadius*1.2);
    assert.ok(on.symbolScale>=idle.symbolScale*1.25);
    assert.ok(on.edgeOpacity>idle.edgeOpacity);
    assert.ok(on.inkOpacity>idle.inkOpacity);
    assert.ok(on.inkWidth>idle.inkWidth);
    assert.ok(on.inkGlow>=idle.inkGlow*3);
    assert.ok(idle.inkOpacity>=0.65);
    assert.ok(idle.chipOpacity>=0.70);
    assert.ok(idle.inkWidth>=1.8);
    for(const height of [100,112,150,220]){
        const radius=Math.max(30,Math.min(410,height)*0.36);
        for(let sign=0;sign<12;sign++){
            const pos=art.sectorCenter(sign,410,height,radius);
            // Even selected chip fits within the compact canvas.
            assert.ok(pos.y>=on.chipRadius);
            assert.ok(pos.y<=height-on.chipRadius);
        }
    }
    assert.match(qml,/ZodiacVector\.appearance\(isSelected\)/);
    assert.match(qml,/ctx\.arc\(x,y,visual\.chipRadius,0,2\*Math\.PI\)/);
    assert.match(qml,/ctx\.scale\(visual\.symbolScale,visual\.symbolScale\)/);
    assert.match(qml,/ctx\.globalAlpha=visual\.inkOpacity/);
    assert.match(qml,/ctx\.shadowBlur=instrument\.neonEnabled\?visual\.inkGlow:0/);
    assert.match(qml,/if\(sign===activeSign\)continue/);
    assert.match(qml,/Celestial\.zodiacColor\(activeSign\),true/);
});

test("wheel body picking, zoom, timeline thumb and backend ownership survive",()=>{
    assert.match(qml,/Celestial\.nearestWheelBody\(/);
    assert.match(qml,/instrument\.selectedBody=body/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/instrument\.zoom\*\(wheel\.angleDelta\.y>0\?1\.4:1\/1\.4\)/);
    assert.match(qml,/id: timelineInput/);
    assert.match(qml,/function scrubTo\(x\)/);
    assert.match(qml,/Celestial\.timelineSampleIndex\(/);
    assert.match(qml,/instrument\.lockedIndex=index/);
    assert.match(qml,/Celestial\.timelinePick\(/);
    assert.match(qml,/onClicked: instrument\.stepToEvent\(1\)/);
    for(const forbidden of ["Process {","Timer {","FileView {","XMLHttpRequest","Qt.openUrlExternally"])
        assert.equal(qml.includes(forbidden),false);
});


// A font-free rendered comparison of the same glyph with M5j idle/focused
// styles. Unlike regex tests, this checks visible color and enlargement.
if(process.argv[2]==="--emit-focus-svg"){
    const target=process.argv[3];
    if(!target)throw Error("expected SVG output path");
    const signs=[{x:65,y:44,focus:false},{x:155,y:44,focus:true}];
    const paths=art.strokesFor(4); // The SAME Leo vector in both states.
    const shapes=['<rect width="220" height="88" fill="#1B0623"/>'];
    for(const item of signs){
        const a=art.appearance(item.focus),color="#ED981A";
        shapes.push('<circle cx="'+item.x+'" cy="'+item.y+'" r="'+a.chipRadius+
            '" fill="#16051F" fill-opacity="'+a.chipOpacity+'" stroke="'+color+
            '" stroke-opacity="'+a.edgeOpacity+'" stroke-width="'+a.edgeWidth+'"/>');
        for(const commands of paths){
            const d=commands.map(cmd=>cmd.join(" ")).join(" ");
            shapes.push('<path d="'+d+'" transform="translate('+item.x+
                " "+item.y+") scale("+a.symbolScale+') translate(-12 -12)" '+
                'fill="none" stroke="'+color+'" stroke-opacity="'+a.inkOpacity+
                '" stroke-width="'+a.inkWidth+'" stroke-linecap="round"'+
                ' stroke-linejoin="round"/>');
        }
    }
    fs.writeFileSync(target,
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="88"'+
        ' viewBox="0 0 220 88">'+shapes.join("")+"</svg>");
}
