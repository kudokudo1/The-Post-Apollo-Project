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
const shell=read("widgets/weather/StationMagickSubjectPane.qml");
const context=vm.createContext({Date,Math,isFinite});
vm.runInContext(code.replace(/^\.pragma library\s*/m,""),context);
const plain=value=>JSON.parse(JSON.stringify(value));
const start=Date.UTC(2026,10,1,0,0,0);

function fixture(){
    const times=Array.from({length:5},(_,i)=>start+i*86400000);
    const sample=(body,i)=>{
        const isMoon=body==="moon";
        const longitude=isMoon?(350+15*i)%360:10+i;
        return {time_utc:new Date(times[i]).toISOString().replace("Z","000Z"),
            unix_ms:times[i],longitude_deg:longitude,
            unwrapped_longitude_deg:isMoon?350+15*i:10+i,
            latitude_deg:0.4,distance_au:isMoon?0.0025:1.0,
            longitude_rate_deg_per_day:isMoon?15:1,
            motion:"direct"};
    };
    const moon=times.map((_,i)=>sample("moon",i));
    const sun=times.map((_,i)=>sample("sun",i));
    return {
        format:context.FORMAT,
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies:["moon","sun"]},
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",ephemeris_sha256:"a".repeat(64),
            time_data_id:"builtin-1.55"},
        sample_count:5,
        series:[{body:"moon",samples:moon},{body:"sun",samples:sun}],
        relationships:[{bodies:["moon","sun"],samples:times.map((time,i)=>({
            unix_ms:time,time_utc:moon[i].time_utc,
            longitude_separation_deg:Math.abs(((moon[i].longitude_deg-
                  sun[i].longitude_deg+540)%360)-180),
            aspects:i===0?[{name:"conjunction",angle_deg:0,
                             separation_deg:20,signed_orb_deg:20}]:[],
        }))}],
        event_markers:[{type:"exact_longitude_aspect",name:"conjunction",
            time_utc:new Date(times[1]).toISOString().replace("Z","000Z"),
            bodies:["moon","sun"],contact_kind:"crossing"}]
    };
}

test("M5 rejects empty, missing-provenance and incompatible coordinate input",()=>{
    const missing=context.model(null);
    assert.equal(missing.ready,false);
    assert.equal(missing.series.length,0);
    const noSource=fixture();
    delete noSource.provenance;
    assert.equal(context.model(noSource).ready,false);
    const wrongFrame=fixture();
    wrongFrame.query.frame="sidereal";
    assert.equal(context.model(wrongFrame).ready,false);
    assert.equal(context.FORMAT,"post-apollo.weather.celestial-visual-data.v1");
});

test("M5 reads source-stamped M4 rows and aligned aspect events",()=>{
    const m=context.model(fixture());
    assert.equal(m.ready,true,m.reason);
    assert.equal(m.sampleCount,5);
    assert.deepEqual(plain(m.bodies),["moon","sun"]);
    assert.equal(m.source,"de440s.bsp");
    assert.equal(m.hash,"aaaaaaaaaa");
    assert.equal(m.relationships.length,1);
    assert.equal(m.events.length,1);
    assert.equal(m.times[1]-m.times[0],86400000);
});

test("wraparound is a continuous graph, not a fake jump from 359 to 0",()=>{
    const m=context.model(fixture());
    const curve=m.series[0].rows;
    assert.deepEqual(plain(curve.map(x=>x.longitude_deg)),[350,5,20,35,50]);
    assert.deepEqual(plain(curve.map(x=>x.unwrapped_longitude_deg)),
                     [350,365,380,395,410]);
    const range=context.rangeFor(m,{from:0,to:4},"motion");
    assert.ok(range.max>410);
    assert.ok(range.min<10);
    assert.ok(context.chartY(410,range,100)<context.chartY(350,range,100));
});

test("zoom window and click-lock sample are bounded to actual measurements",()=>{
    const m=context.model(fixture());
    const all=context.windowFor(m,1,0.5);
    assert.deepEqual(plain(all),{from:0,to:4,count:5});
    const cropped=context.windowFor(m,2,1);
    assert.deepEqual(plain(cropped),{from:2,to:4,count:3});
    assert.equal(context.indexAtFraction(m,cropped,0),2);
    assert.equal(context.indexAtFraction(m,cropped,1),4);
    assert.equal(context.selectedIndex(m,-1,-1),4);
    assert.equal(context.selectedIndex(m,0,3),0);
    assert.equal(context.selectedIndex(m,-1,3),3);
    assert.equal(context.windowFor(m,999,-10).count,2);
    assert.equal(context.chartX(4,cropped,100),100);
});

test("wheel hit-testing selects actual bodies only",()=>{
    const m=context.model(fixture());
    const points=context.wheelPositions(m,0);
    assert.equal(points.length,2);
    assert.equal(context.nearestWheelBody(m,0,points[0].x,points[0].y),
                 points[0].body);
    assert.equal(context.nearestWheelBody(m,0,0.5,0.5),null);
    assert.match(context.valueLabel(m,0,"moon"),/MOON.*DIRECT/);
    assert.equal(context.valueLabel(m,0,"unknown"),"--");
});

test("untrusted M4 NaN, missing values, time drift, and mismatched pairs fail closed",()=>{
    const variations=[
        payload=>{payload.series[0].samples[0].longitude_deg=null;},
        payload=>{payload.series[0].samples[1].distance_au=-1;},
        payload=>{payload.series[0].samples[2].unwrapped_longitude_deg=20;},
        payload=>{payload.series[1].samples[1].unix_ms+=1000;},
        payload=>{payload.series[0].samples[0].motion="retrograde";},
        payload=>{payload.series[0].samples[3].longitude_rate_deg_per_day="NaN";},
        payload=>{payload.relationships=[];},
        payload=>{payload.relationships[0].samples[0].longitude_separation_deg=181;},
        payload=>{payload.event_markers[0].time_utc="2028-01-01T00:00:00Z";},
        payload=>{payload.provenance.ephemeris_sha256="not-a-sha";},
        payload=>{payload.sample_count=722;},
    ];
    variations.forEach((apply,i)=>{
        const data=fixture();apply(data);
        assert.equal(context.model(data).ready,false,"case "+i);
    });
});

test("standalone QML contains actual mode, scrub, zoom, pan and unlock handlers",()=>{
    assert.match(qml,/property var visualData: null/);
    assert.match(qml,/Celestial\.model\(visualData\)/);
    assert.match(qml,/onGraphModelChanged: graphCanvas\.requestPaint\(\)/);
    assert.match(qml,/id: graphCanvas/);
    assert.match(qml,/function paintWheel\(ctx\)/);
    assert.match(qml,/function paintChart\(ctx\)/);
    assert.match(qml,/mode: "wheel"/);
    for(const tag of ["wheel","motion","aspects"])
        assert.ok(qml.includes('id:"'+tag+'"'));
    assert.match(qml,/onClicked: instrument\.mode = modelData\.id/);
    assert.match(qml,/onPositionChanged: function\(mouse\)/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/instrument\.panPosition=Celestial\.clamp\(/);
    assert.match(qml,/instrument\.zoom=Celestial\.clamp\(/);
    assert.match(qml,/instrument\.lockedIndex=Celestial\.indexAtFraction\(/);
    assert.match(qml,/instrument\.lockedIndex=-1/);
    assert.match(qml,/onClicked: function\(mouse\)/);
    assert.match(qml,/Celestial\.nearestWheelBody\(/);
    assert.match(qml,/selected: instrument\.mode === modelData\.id/);
    assert.match(qml,/enabled: instrument\.graphModel\.ready/);
});

test("M5 stays isolated from existing source/workspace ownership",()=>{
    assert.match(qml,/AWAITING|graphModel\.reason|NO CALCULATION SOURCE/);
    assert.match(shell,/INTERPRETIVE WORKSPACE \/\/ NOT IMPLEMENTED/);
    for(const text of [qml,code]){
        for(const forbidden of [
          "Process {","Timer {","FileView {","WeatherServices.",
          "XMLHttpRequest","swaymsg","new WebSocket",
          "StationTerminal {","Component.onCompleted: Process",
        ]) assert.ok(!text.includes(forbidden),forbidden);
    }
    assert.ok(!qml.includes("Date.now()"));
    assert.ok(!code.includes("Math.random("));
});
