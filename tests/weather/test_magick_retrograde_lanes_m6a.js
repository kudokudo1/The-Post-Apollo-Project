"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policySource=read("widgets/weather/StationMagickRetrogradeLanePolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const astrology=read("widgets/weather/StationMagickAstrologyPane.qml");
const deep=read("widgets/weather/StationMagickSubjectPane.qml");
const modelSource=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const ctx=vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*/m,""),ctx);
const P=ctx;
const t0=Date.UTC(2026,10,6,0,0,0);
const times=[0,12,24,48,60,72].map(hours=>t0+hours*3600000);
const rates=[0.20,0.05,-0.10,-0.25,0,0.12];
const body="mercury";
const sample=(rate,index)=>({
    unix_ms:times[index],
    longitude_rate_deg_per_day:rate,
    motion:rate>0?"direct":rate<0?"retrograde":"indeterminate"
});
const fixture=()=>({
    ready:true,source:"de440s.bsp",
    frame:"true-ecliptic-of-date",
    times:times.slice(),sampleCount:times.length,
    series:[
        {body,color:"#ED981A",rows:rates.map(sample)},
        {body:"sun",color:"#55CFCA",rows:times.map((_,i)=>sample(0.98,i))}
    ]
});
const view={from:0,to:times.length-1,count:times.length};

test("M6a rate chart takes only exact UTC JPL M4 sample rates",()=>{
    const m=fixture(),before=JSON.stringify(m);
    const d=P.build(m,view,2);
    assert.equal(d.ready,true,d.reason);
    assert.equal(d.frame,"true-ecliptic-of-date");
    assert.equal(d.source,"de440s.bsp");
    assert.equal(d.lanes.length,2);
    assert.equal(d.lanes[0].body,"mercury");
    assert.equal(d.lanes[0].points.length,6);
    assert.equal(d.lanes[0].focusRate,-0.10);
    assert.equal(d.lanes[0].focusMotion,"retrograde");
    assert.equal(d.focusMs,times[2]);
    assert.equal(d.lanes[0].points[3].unix_ms,times[3]);
    assert.equal(d.lanes[0].points[3].fraction,0.6666666666666666);
    assert.equal(JSON.stringify(m),before);
});

test("M6a marks only measured sign-change BRACKETS, not made-up station UTC",()=>{
    const d=P.build(fixture(),view,2);
    const changes=d.boundaries.filter(b=>b.body==="mercury");
    assert.equal(changes.length,3);
    assert.deepEqual(Array.from(changes,x=>x.fromIndex),[1,3,4]);
    assert.deepEqual(Array.from(changes,x=>x.toIndex),[2,4,5]);
    for(const bracket of changes){
        assert.equal(bracket.kind,"RATE TRANSITION WINDOW");
        assert.equal(bracket.fromMs,times[bracket.fromIndex]);
        assert.equal(bracket.toMs,times[bracket.toIndex]);
        assert.ok(bracket.toMs>bracket.fromMs);
        assert.ok(!("stationUtc" in bracket));
        assert.ok(!("estimatedStationMs" in bracket));
        assert.ok(!("instant" in bracket));
    }
    assert.equal(d.boundaries.filter(b=>b.body==="sun").length,0);
});

test("M6a sampled motion axes preserve actual irregular UTC spacing",()=>{
    const d=P.build(fixture(),view,2),rows=d.lanes[0].points;
    assert.equal(rows[1].fraction,1/6);
    assert.equal(rows[2].fraction,1/3);
    assert.equal(rows[3].fraction,2/3);
    assert.equal(rows[4].fraction,5/6);
    const g=P.layout(410,210,2);
    assert.ok(g);
    assert.equal(g.left,44);
    assert.equal(g.right,401);
    const a=P.samplePoint(rows[1],d.lanes[0],g,0);
    const b=P.samplePoint(rows[2],d.lanes[0],g,0);
    assert.ok(a.y<a.cy,"direct measured positive rate above zero line");
    assert.ok(b.y>b.cy,"retrograde negative rate below zero line");
    assert.ok(b.x>a.x);
    assert.equal(P.layout(120,80,2),null);
});

test("M6a rejects tampered rate/status, source frame and mismatched timestamps",()=>{
    function invalid(mutate){
        const f=fixture();mutate(f);
        return P.build(f,view,2).ready;
    }
    assert.equal(invalid(m=>{m.ready=false}),false);
    assert.equal(invalid(m=>{m.frame="j2000"}),false);
    assert.equal(invalid(m=>{m.series[0].rows[2].motion="direct"}),false);
    assert.equal(invalid(m=>{m.series[0].rows[2].longitude_rate_deg_per_day=NaN}),false);
    assert.equal(invalid(m=>{m.series[0].rows[2].unix_ms++}),false);
    assert.equal(invalid(m=>{m.times[2]=m.times[1]}),false);
    assert.equal(invalid(m=>{m.series.push(m.series[0])}),false);
    assert.equal(invalid(m=>{m.sampleCount=1000}),false);
    assert.equal(P.build(fixture(),{from:0,to:0},0).ready,false);
    assert.equal(P.build(fixture(),view,99).ready,false);
    assert.equal(P.build(null,view,2).ready,false);
    assert.equal(P.state(0),"indeterminate");
    assert.equal(P.state(-0.2),"retrograde");
    assert.equal(P.state(0.2),"direct");
    assert.equal(P.state(NaN),"");
});

test("M6a is an actual selectable Quickshell mode and retrograde INDEX route",()=>{
    assert.match(qml,/import "StationMagickRetrogradeLanePolicy\.js" as Retrograde/);
    assert.match(qml,/function paintRetrograde\(ctx\)/);
    assert.match(qml,/Retrograde\.build\(instrument\.graphModel,/);
    assert.match(qml,/Retrograde\.samplePoint\(/);
    assert.match(qml,/ctx\.moveTo\(p\.x,p\.cy\)/);
    assert.match(qml,/SAMPLED JPL RATES \/\/ EXACT STATION UTC UNKNOWN/);
    assert.match(qml,/id:"retro",label:"RETRO"/);
    assert.match(qml,/instrument\.mode==="retro"\)instrument\.paintRetrograde\(ctx\)/);
    assert.match(qml,/instrument\.compactMode \? 7 : 6/);
    assert.match(astrology,/magick\/astrology\/retrogrades"\s*\? "retro" : "wheel"/);
    assert.match(deep,/magick\/astrology\/retrogrades"\s*\? "retro" : "wheel"/);
    assert.match(qml,/StationCosmosCelestialNetwork\s*\{/);
    assert.match(qml,/instrument\.mode === "network"/);
    assert.match(modelSource,/longitude_rate_deg_per_day/);
    for(const source of [policySource,qml]){
        for(const forbidden of ["Process {","Timer {","XMLHttpRequest","fetch(",
                               "new WebSocket","curl "])
            assert.ok(!source.includes(forbidden),forbidden);
    }
});
