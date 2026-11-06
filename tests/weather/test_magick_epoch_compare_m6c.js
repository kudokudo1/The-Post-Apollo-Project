"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickEpochComparePolicy.js");
const oldModel=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const deep=read("widgets/weather/StationMagickSubjectPane.qml");
const panel=read("widgets/weather/StationMagickAstrologyPane.qml");
const routes=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const ctx=vm.createContext({});
const core=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),ctx);
vm.runInContext(oldModel.replace(/^\.pragma library\s*/m,""),core);
const C=ctx;
const plain=v=>JSON.parse(JSON.stringify(v));
const times=Array.from({length:6},(_,i)=>Date.UTC(2026,10,6+i,0,0,0));
const mercury=[350,355,2,8,14,21],unwrapped=[350,355,362,368,374,381];
const sun=[10,11,12,13,14,15];
function separation(a,b){return Math.abs(((a-b+540)%360)-180);}
function validFixture(){
    const row=(body,lon,unwrap,i)=>({
        time_utc:new Date(times[i]).toISOString().replace("Z","000Z"),
        unix_ms:times[i],longitude_deg:lon,
        unwrapped_longitude_deg:unwrap,
        latitude_deg:body==="sun"?0:0.2,
        distance_au:body==="sun"?1.01:0.7,
        longitude_rate_deg_per_day:body==="sun"?1:3,
        motion:"direct"
    });
    const sha="b".repeat(64);
    const payload={
        format:C.FORMAT,
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",ephemeris_sha256:sha,
            time_data_id:"builtin-1.55"},
        query:{origin:"geocentric",position_model:"apparent",
            frame:C.FRAME,bodies:["mercury","sun"]},
        sample_count:times.length,
        series:[
            {body:"mercury",samples:mercury.map((lon,i)=>
                row("mercury",lon,unwrapped[i],i))},
            {body:"sun",samples:sun.map((lon,i)=>
                row("sun",lon,lon,i))}
        ],
        relationships:[{bodies:["mercury","sun"],
            samples:times.map((t,i)=>({
                unix_ms:t,time_utc:new Date(t).toISOString().replace("Z","000Z"),
                longitude_separation_deg:separation(mercury[i],sun[i]),
                aspects:[]
            }))}],
        event_markers:[]
    };
    const model=core.model(payload);
    assert.equal(model.ready,true,model.reason);
    return {model,payload};
}

test("M6c two real M4 epochs give measured wrapped chart-longitude deltas",()=>{
    const {model,payload}=validFixture();
    const before=JSON.stringify(payload);
    const v=C.build(model,payload,-1,3);
    assert.equal(v.ready,true,v.reason);
    assert.equal(v.refIndex,0);
    assert.equal(v.nowIndex,3);
    assert.equal(v.refMs,times[0]);
    assert.equal(v.nowMs,times[3]);
    assert.equal(v.refKind,"FIRST SOURCE UTC");
    assert.equal(v.source,"de440s.bsp");
    assert.equal(v.frame,"true-ecliptic-of-date");
    const m=v.bodies.find(x=>x.body==="mercury");
    const s=v.bodies.find(x=>x.body==="sun");
    assert.equal(m.refLongitude,350);
    assert.equal(m.nowLongitude,8);
    assert.equal(m.delta,18);
    assert.equal(s.refLongitude,10);
    assert.equal(s.nowLongitude,13);
    assert.equal(s.delta,3);
    assert.deepEqual(plain(v.pair.bodies),["mercury","sun"]);
    assert.equal(v.pair.refSeparation,20);
    assert.equal(v.pair.nowSeparation,5);
    assert.equal(JSON.stringify(payload),before,"presentation never mutates M4 source");
});

test("M6c PIN REF locks an actual UTC sample while current changes",()=>{
    const {model,payload}=validFixture();
    const v=C.build(model,payload,2,4);
    assert.equal(v.ready,true);
    assert.equal(v.refKind,"PINNED SOURCE UTC");
    assert.equal(v.refMs,times[2]);
    assert.equal(v.nowMs,times[4]);
    const m=v.bodies.find(x=>x.body==="mercury");
    assert.equal(m.refLongitude,2);
    assert.equal(m.nowLongitude,14);
    assert.equal(m.delta,12);
    const same=C.build(model,payload,2,2);
    assert.equal(same.ready,true);
    assert.ok(same.bodies.every(body=>body.delta===0));
    assert.equal(C.signedOffset(350,8),18);
    assert.equal(C.signedOffset(8,350),-18);
    assert.equal(C.signedOffset(0,180),-180);
    assert.equal(C.signedOffset(NaN,90),null);
    assert.equal(C.signedOffset(-1,90),null);
});

test("M6c uses two circular marker rings and real hit targets",()=>{
    const {model,payload}=validFixture();
    const v=C.build(model,payload,0,3);
    const g=C.geometry(700,220);
    assert.ok(g && g.spacious);
    assert.ok(g.currentRadius<g.referenceRadius);
    assert.ok(g.referenceRadius<g.outer);
    const m=v.bodies.find(x=>x.body==="mercury");
    const ref=C.point(m.refLongitude,g.cx,g.cy,g.referenceRadius);
    const now=C.point(m.nowLongitude,g.cx,g.cy,g.currentRadius);
    assert.ok(ref && now);
    assert.notEqual(ref.x,now.x);
    assert.deepEqual(plain(C.pick(v,g,ref.x,ref.y)),
        {body:"mercury",which:"ref"});
    assert.deepEqual(plain(C.pick(v,g,now.x,now.y)),
        {body:"mercury",which:"now"});
    assert.equal(C.pick(v,g,-100,-100),null);
    assert.equal(C.geometry(100,60),null);
    assert.equal(C.point(361,100,100,40),null);
    const narrow=C.geometry(350,160);
    assert.ok(narrow && !narrow.spacious);
});

test("M6c fails closed if provenance, epoch, frame, pair or source angles are wrong",()=>{
    function invalid(changer,ref=0,now=3){
        const {model,payload}=validFixture();
        changer(model,payload);
        return C.build(model,payload,ref,now).ready;
    }
    assert.equal(invalid(m=>{m.ready=false}),false);
    assert.equal(invalid(m=>{m.frame="J2000"}),false);
    assert.equal(invalid((m,p)=>{p.format="other-format"}),false);
    assert.equal(invalid((m,p)=>{p.query.frame="J2000"}),false);
    assert.equal(invalid((m,p)=>{p.query.origin="heliocentric"}),false);
    assert.equal(invalid((m,p)=>{p.query.position_model="geometric"}),false);
    assert.equal(invalid((m,p)=>{p.provenance.ephemeris_id="other.bsp"}),false);
    assert.equal(invalid((m,p)=>{p.provenance.ephemeris_sha256="a".repeat(64)}),false);
    assert.equal(invalid((m,p)=>{p.query.bodies=["pluto"]}),false);
    assert.equal(invalid(m=>{m.times[2]=m.times[1]}),false);
    assert.equal(invalid(m=>{m.series[0].rows[3].unix_ms++}),false);
    assert.equal(invalid(m=>{m.series[0].rows[3].longitude_deg=Infinity}),false);
    assert.equal(invalid(m=>{m.series[0].rows[3].longitude_deg=360}),false);
    assert.equal(invalid(m=>{m.relationships[0].samples[3].longitude_separation_deg=90}),false);
    assert.equal(invalid(m=>{m.relationships[0].samples[0].unix_ms++}),false);
    const {model,payload}=validFixture();
    assert.equal(C.build(model,payload,-2,3).ready,false);
    assert.equal(C.build(model,payload,6,3).ready,false);
    assert.equal(C.build(model,payload,1,6).ready,false);
    assert.equal(C.build(model,payload,1,-1).ready,false);
    assert.equal(C.build(null,payload,-1,3).ready,false);
});

test("M6c UI retains original ZODIAC wheel and opens actual Transits reference route",()=>{
    assert.match(qml,/import "StationMagickEpochComparePolicy\.js" as Epoch/);
    assert.match(qml,/property string zodiacPresentation: "wheel"/);
    assert.match(qml,/property int referenceIndex: -1/);
    assert.match(qml,/Epoch\.build\(\s*graphModel,visualData,referenceIndex,focusIndex\)/);
    assert.match(qml,/function paintEpochCompare\(ctx\)/);
    assert.match(qml,/instrument\.paintEpochCompare\(ctx\)/);
    assert.match(qml,/function paintWheel\(ctx\)/);
    assert.match(qml,/instrument\.paintWheel\(ctx\)/);
    assert.match(qml,/id: compareControls/);
    assert.match(qml,/\{id:"wheel",label:"WHEEL"\}/);
    assert.match(qml,/\{id:"compare",label:"COMPARE"\}/);
    assert.match(qml,/\{id:"pin",label:"PIN REF"\}/);
    assert.match(qml,/instrument\.referenceIndex=instrument\.focusIndex/);
    assert.match(qml,/Epoch\.pick\(instrument\.epochComparison,/);
    assert.match(qml,/instrument\.selectedBody=body/);
    assert.match(qml,/instrument\.referenceIndex=-1/);
    assert.match(qml,/EPOCH FRAMES DIFFER \/\/ SNAPSHOT LINKS NOT ORBITS/);
    assert.match(qml,/NOT NATAL/);
    assert.match(panel,/zodiacPresentation: astrology\.subjectRoute === "magick\/astrology\/transits"/);
    assert.match(deep,/magickPane\.subjectRoute === "magick\/astrology\/transits"/);
    assert.match(routes,/path === "magick\/astrology\/transits"/);
    assert.match(routes,/NOT A NATAL\/HOUSE CHART/);
    assert.match(qml,/id: aspectViewControls/);
    assert.match(qml,/id: compactNetworkToolbar|StationCosmosCelestialNetwork\s*\{/);
    assert.match(qml,/function paintRetrograde\(ctx\)/);
    assert.match(qml,/function paintAspectMatrix\(ctx\)/);
    const row=qml.slice(qml.indexOf("id: modeRow"),
                        qml.indexOf("id: chartFrame"));
    assert.ok(!row.includes('id:"compare"'),
        "do not create a new tiny top-level menu tab");
    for(const src of [source,qml]){
        for(const forbidden of ["Process {","Timer {","XMLHttpRequest",
            "Qt.callLater","new WebSocket","curl ","fetch("])
            assert.ok(!src.includes(forbidden),"new provider "+forbidden);
    }
});
