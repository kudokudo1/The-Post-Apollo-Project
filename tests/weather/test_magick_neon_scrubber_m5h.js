"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const code=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const service=read("services/weather/CelestialVisualService.qml");
const ctx=vm.createContext({Date,Math,isFinite});
vm.runInContext(code.replace(/^\.pragma library\s*/m,""),ctx);
const plain=x=>JSON.parse(JSON.stringify(x));
const start=Date.UTC(2026,10,3);

function fixture(){
    const times=Array.from({length:5},(_,i)=>start+i*86400000);
    function point(body,i){
        const moon=body==="moon",lon=moon?(350+15*i)%360:10+i;
        return {time_utc:new Date(times[i]).toISOString(),
            unix_ms:times[i],longitude_deg:lon,
            unwrapped_longitude_deg:moon?350+15*i:10+i,
            latitude_deg:moon?2:-0.2,distance_au:moon?0.0027:1,
            longitude_rate_deg_per_day:moon?15:1,motion:"direct"};
    }
    const a=times.map((_,i)=>point("moon",i));
    const b=times.map((_,i)=>point("sun",i));
    return {format:ctx.FORMAT,
        query:{origin:"geocentric",position_model:"apparent",
               frame:"true-ecliptic-of-date",bodies:["moon","sun"]},
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",
            ephemeris_sha256:"a".repeat(64),time_data_id:"builtin"},
        sample_count:5,
        series:[{body:"moon",samples:a},{body:"sun",samples:b}],
        relationships:[{bodies:["moon","sun"],samples:times.map((time,i)=>({
            time_utc:a[i].time_utc,unix_ms:time,
            longitude_separation_deg:Math.abs(
                ((a[i].longitude_deg-b[i].longitude_deg+540)%360)-180),
            aspects:[] }))}],
        event_markers:[{name:"conjunction",type:"exact_longitude_aspect",
            contact_kind:"crossing",
            time_utc:new Date(start+1.5*86400000).toISOString(),
            bodies:["moon","sun"]}]
    };
}

test("all twelve real zodiac glyphs replace ASCII wheel sector labels",()=>{
    const glyphs=plain(ctx.ZODIAC_GLYPHS);
    assert.deepEqual(glyphs,["♈","♉","♊","♋","♌","♍",
                            "♎","♏","♐","♑","♒","♓"]);
    assert.equal(new Set(glyphs).size,12);
    assert.deepEqual(plain(ctx.SIGNS),["AR","TA","GE","CN","LE","VI",
                                      "LI","SC","SG","CP","AQ","PI"]);
    glyphs.forEach((glyph,i)=>{
        assert.equal(ctx.zodiacGlyph(i),glyph);
        assert.ok(ctx.zodiacColor(i).startsWith("#"));
    });
    assert.equal(ctx.zodiacGlyph(12),"");
    assert.equal(ctx.zodiacGlyph(-1),"");
    assert.equal(ctx.zodiacGlyph("1"),"");
});

test("element colors follow fire/earth/air/water across each zodiac quarter",()=>{
    const colors=plain(ctx.ZODIAC_COLORS);
    assert.equal(colors.length,12);
    for(let i=0;i<8;i++)
        assert.equal(colors[i],colors[i+4]);
    assert.deepEqual(colors.slice(0,4),
        ["#ED981A","#9ECE6A","#55CFCA","#C74EC7"]);
    assert.equal(ctx.zodiacColor(-1),"#DCF3FA");
});

test("draggable thumb represents real UTC sample timestamps in visible window",()=>{
    const m=ctx.model(fixture());
    assert.equal(m.ready,true,m.reason);
    const view=ctx.windowFor(m,1,0.5);
    assert.equal(ctx.timelineHandleFraction(m,view,0),0);
    assert.equal(ctx.timelineHandleFraction(m,view,4),1);
    assert.equal(ctx.timelineHandleFraction(m,view,2),0.5);
    assert.equal(ctx.timelineHandleX(m,view,2,320),160);
    assert.equal(ctx.timelineHandleX(m,view,4,320),320);
    const cropped={from:1,to:3,count:3};
    assert.equal(ctx.timelineHandleFraction(m,cropped,0),0);
    assert.equal(ctx.timelineHandleFraction(m,cropped,4),1);
    assert.equal(ctx.timelineHandleFraction(m,cropped,2),0.5);
    assert.equal(ctx.timelineSampleIndex(m,cropped,160,320),2);
    assert.equal(ctx.timelineHandleX(m,cropped,2,320),160);
    assert.equal(ctx.timelineHandleX(m,cropped,0,320),0);
    assert.equal(ctx.timelineHandleX(m,cropped,4,320),320);
    assert.equal(ctx.timelineHandleFraction(m,view,NaN),null);
    assert.equal(ctx.timelineHandleFraction(m,{from:0,to:0,count:1},1),null);
    assert.equal(ctx.timelineHandleFraction(ctx.model(null),view,1),null);
});

test("a drag resolves to nearby samples without creating intermediate positions",()=>{
    const m=ctx.model(fixture()),view=ctx.windowFor(m,1,0.5);
    for(let idx=0;idx<m.sampleCount;idx++){
        const x=ctx.timelineHandleX(m,view,idx,320);
        assert.equal(ctx.timelineSampleIndex(m,view,x,320),idx);
        assert.ok(m.times[idx]>=m.times[view.from]);
        assert.ok(m.times[idx]<=m.times[view.to]);
    }
    assert.equal(ctx.timelineSampleIndex(m,view,-100,320),0);
    assert.equal(ctx.timelineSampleIndex(m,view,999,320),4);
    const marker=ctx.timelineMarkers(m,view)[0];
    const picked=ctx.timelinePick(m,view,marker.fraction*320,320,10);
    assert.equal(picked.name,"conjunction");
    assert.equal(picked.sampleIndex,1); // 1.5 day tie goes earlier
});

test("QML uses actual symbol text, Qt Canvas neon and existing semantic palette",()=>{
    assert.match(qml,/import QtQuick\.Effects/);
    assert.match(qml,/Celestial\.zodiacGlyph\(sign\)/);
    assert.match(qml,/Celestial\.zodiacColor\(sign\)/);
    assert.match(qml,/18px 'Noto Sans Symbols 2'/);
    assert.match(qml,/function neonStroke\(ctx,color,width,blur\)/);
    assert.match(qml,/function neonText\(ctx,text,x,y,color,blur\)/);
    assert.match(qml,/ctx\.shadowColor=String\(color\)/);
    assert.match(qml,/ctx\.shadowBlur=instrument\.neonEnabled \? blur : 0/);
    assert.match(qml,/Colors\.magenta/);
    assert.match(qml,/Colors\.cyan/);
    assert.match(qml,/Colors\.orange/);
    assert.match(qml,/Colors\.yellow/);
    assert.match(qml,/instrument\.neonStroke\(ctx/);
    assert.match(qml,/instrument\.neonText\(ctx/);
    assert.match(qml,/property bool neonEnabled: true/);
});

test("timeline contains a visible glowing thumb and actual drag handlers",()=>{
    assert.match(qml,/id: timelineThumb/);
    assert.match(qml,/width: 17/);
    assert.match(qml,/height: 20/);
    assert.match(qml,/id: timelineInput/);
    assert.match(qml,/cursorShape: Qt\.SizeHorCursor/);
    assert.match(qml,/preventStealing: true/);
    assert.match(qml,/Celestial\.timelineHandleX\(/);
    assert.match(qml,/Celestial\.timelineHandleFraction\(graphModel,viewWindow,focusIndex\)/);
    assert.match(qml,/function scrubTo\(x\)/);
    assert.match(qml,/onPositionChanged: function\(mouse\)/);
    assert.match(qml,/if\(didDrag\)scrubTo\(mouse\.x-grabOffset\)/);
    assert.match(qml,/onReleased: function\(mouse\)/);
    assert.match(qml,/Celestial\.timelinePick\(instrument\.graphModel/);
    assert.match(qml,/instrument\.lockedIndex=index/);
    assert.match(qml,/instrument\.eventOrdinal=-1/);
    assert.match(qml,/RectangularShadow \{/);
    assert.match(qml,/color: timelineInput\.pressed \? Colors\.yellow : Colors\.white/);
    assert.match(qml,/enabled: !timelineInput\.pressed/);
});

test("glow+scrubber remain a view-only change, not an extra source collector",()=>{
    assert.equal((service.match(/Process\s*\{/g)||[]).length,1);
    for(const forbidden of [
        "Process {","Timer {","FileView {","XMLHttpRequest","Qt.openUrlExternally",
        "Math.random(","Date.now()","swaymsg","curl ","pip install"
    ])assert.equal(qml.includes(forbidden),false,forbidden);
    assert.match(qml,/property var visualData: null/);
    assert.match(qml,/onGraphModelChanged: graphCanvas\.requestPaint\(\)/);
    assert.match(qml,/Celestial\.relationAt\(m,instrument\.focusIndex\)/);
    assert.match(qml,/Celestial\.timelineSampleIndex\(/);
});
