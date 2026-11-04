"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const src=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const ctx=vm.createContext({Date,Math,isFinite,JSON});
vm.runInContext(src.replace(/^\.pragma library\s*/m,""),ctx);
const plain=x=>JSON.parse(JSON.stringify(x));
const base=Date.UTC(2026,10,1);

function fixture(){
    const times=Array.from({length:5},(_,i)=>base+i*86400000);
    const coord=(body,i)=>{
        const moon=body==="moon",longitude=moon?(350+15*i)%360:10+i;
        return {time_utc:new Date(times[i]).toISOString(),
            unix_ms:times[i],longitude_deg:longitude,
            unwrapped_longitude_deg:moon?350+15*i:10+i,
            latitude_deg:moon?2.0:0,distance_au:moon?0.0025:1,
            longitude_rate_deg_per_day:moon?15:1,motion:"direct"};
    };
    const a=times.map((_,i)=>coord("moon",i)),b=times.map((_,i)=>coord("sun",i));
    const sample=times.map((time,i)=>({
        time_utc:a[i].time_utc,unix_ms:time,
        longitude_separation_deg:Math.abs(
            ((a[i].longitude_deg-b[i].longitude_deg+540)%360)-180),
        aspects:i===1?[{name:"sextile"}]:[]
    }));
    return {format:ctx.FORMAT,
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",ephemeris_sha256:"a".repeat(64),
            time_data_id:"skyfield-1.55-builtin-timescale"},
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies:["moon","sun"]},
        sample_count:5,
        series:[{body:"moon",samples:a},{body:"sun",samples:b}],
        relationships:[{bodies:["moon","sun"],samples:sample}],
        event_markers:[
            {name:"opposition",type:"exact_longitude_aspect",
                contact_kind:"crossing",time_utc:new Date(base+3.75*86400000).toISOString(),
                bodies:["moon","sun"]},
            {name:"conjunction",type:"exact_longitude_aspect",
                contact_kind:"tangent_candidate",time_utc:new Date(base+.25*86400000).toISOString(),
                bodies:["moon","sun"]},
            {name:"direct_to_retrograde",type:"apparent_longitude_station",
                time_utc:new Date(base+1.5*86400000).toISOString(),
                bodies:["moon"]}
        ]
    };
}

test("RELATIONS dial displays only actual M4 separation and body identities",()=>{
    const m=ctx.model(fixture());
    assert.equal(m.ready,true,m.reason);
    assert.ok(ctx.MODES.includes("relations"));
    assert.equal(ctx.MODES.length,4);
    const r=ctx.relationAt(m,1);
    assert.deepEqual(plain(r.bodies),["moon","sun"]);
    assert.equal(r.first,"MOON");
    assert.equal(r.second,"SUN");
    assert.equal(r.firstColor,"#ED981A");
    assert.equal(r.secondColor,"#55CFCA");
    assert.equal(r.separation_deg,m.relationships[0].samples[1].longitude_separation_deg);
    assert.deepEqual(plain(r.aspects),["sextile"]);
    assert.equal(r.sample_utc,m.relationships[0].samples[1].time_utc);
    assert.equal(ctx.relationAt(m,-1),null);
    assert.equal(ctx.relationAt(m,999),null);
    assert.equal(ctx.relationAt(ctx.model(null),0),null);
});

test("gauge spans an honest 0 to 180 longitude-angle gap",()=>{
    const p0=ctx.relationArcPoint(0,400,200);
    const p90=ctx.relationArcPoint(90,400,200);
    const p180=ctx.relationArcPoint(180,400,200);
    assert.ok(p0.x<p90.x);
    assert.ok(p180.x>p90.x);
    assert.ok(Math.abs(p0.y-p180.y)<1e-9);
    assert.ok(p90.y<p0.y);
    assert.ok(Math.abs(p90.x-200)<1e-9);
    assert.deepEqual(plain(ctx.ASPECT_GUIDES.map(x=>x.angle)),[0,60,90,120,180]);
    for(const invalid of [-1,181,NaN,Infinity]) {
        assert.equal(ctx.relationArcPoint(invalid,400,200),null);
    }
    assert.equal(ctx.relationArcPoint(90,0,200),null);
    assert.equal(ctx.relationArcPoint(90,400,0),null);
});

test("timeline only contains source events inside exact visible UTC sample bounds",()=>{
    const m=ctx.model(fixture()),full=ctx.windowFor(m,1,0.5);
    const markers=ctx.timelineMarkers(m,full);
    assert.deepEqual(plain(markers.map(x=>x.name)),
        ["conjunction","direct_to_retrograde","opposition"]);
    assert.deepEqual(plain(markers.map(x=>x.kind)),
        ["candidate","station","crossing"]);
    assert.deepEqual(plain(markers.map(x=>x.ordinal)),[0,1,2]);
    assert.ok(markers.every(x=>x.fraction>=0 && x.fraction<=1));
    assert.deepEqual(plain(markers.map(x=>x.sampleIndex)),[0,1,4]);
    const middle={from:1,to:2,count:2};
    assert.deepEqual(plain(ctx.timelineMarkers(m,middle).map(x=>x.kind)),["station"]);
    const empty={from:2,to:3,count:2};
    assert.equal(ctx.timelineMarkers(m,empty).length,0);
    assert.deepEqual(plain(ctx.timelineMarkers(ctx.model(null),full)),[]);
});

test("clicking timeline finds nearest source event, or nearest actual sample",()=>{
    const m=ctx.model(fixture()),v=ctx.windowFor(m,1,0.5);
    const markers=ctx.timelineMarkers(m,v),width=400;
    const picked=ctx.timelinePick(m,v,markers[1].fraction*width+3,width,10);
    assert.equal(picked.name,"direct_to_retrograde");
    assert.equal(picked.ordinal,1);
    assert.equal(picked.sampleIndex,1);
    assert.equal(ctx.timelinePick(m,v,markers[1].fraction*width+15,width,10),null);
    assert.equal(ctx.timelinePick(ctx.model(null),v,200,width,10),null);
    assert.equal(ctx.timelinePick(m,v,100,0,10),null);
    assert.equal(ctx.timelinePick(m,v,100,width,-1),null);
    assert.equal(ctx.timelineSampleIndex(m,v,0,width),0);
    assert.equal(ctx.timelineSampleIndex(m,v,width,width),4);
    assert.equal(ctx.timelineSampleIndex(m,v,width/2,width),2);
    assert.equal(ctx.timelineSampleIndex(m,{from:1,to:2,count:2},-50,width),1);
    assert.equal(ctx.timelineSampleIndex(m,{from:1,to:2,count:2},width+50,width),2);
});

test("QML fourth mode, event strip and pointer handlers are actually wired",()=>{
    assert.match(qml,/\{id:"relations",label:"RELATIONS"\}/);
    assert.match(qml,/function paintRelations\(ctx\)/);
    assert.match(qml,/Celestial\.relationAt\(m,instrument\.focusIndex\)/);
    assert.match(qml,/Celestial\.relationArcPoint\(value\.separation_deg,width,height\)/);
    assert.match(qml,/instrument\.mode==="relations"/);
    assert.match(qml,/Celestial\.ASPECT_GUIDES/);
    assert.match(qml,/id: eventTimelineCanvas/);
    assert.match(qml,/Celestial\.timelineMarkers\(/);
    assert.match(qml,/Celestial\.timelinePick\(instrument\.graphModel,/);
    assert.match(qml,/Celestial\.timelineSampleIndex\(/);
    assert.match(qml,/instrument\.eventOrdinal=chosen\.ordinal/);
    assert.match(qml,/instrument\.lockedIndex=chosen\.sampleIndex/);
    assert.match(qml,/eventTimelineCanvas\.requestPaint\(\)/);
    assert.match(qml,/instrument\.mode==="wheel" \|\| instrument\.mode==="relations"/);
    assert.match(qml,/height: Math\.max\(150,instrument\.height-254\)/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/instrument\.stepToEvent\(1\)/);
    assert.match(qml,/instrument\.stepToEvent\(-1\)/);
    assert.match(qml,/instrument\.selectedBody=pair\.bodies/);
    for(const prohibited of ["Process {","Timer {","FileView {","XMLHttpRequest",
        "Math.random(","Date.now()","swaymsg"])
        assert.equal(qml.includes(prohibited),false,prohibited);
});

test("missing source produces no dial or event timeline or invented content",()=>{
    const m=ctx.model(null);
    assert.equal(ctx.relationAt(m,0),null);
    assert.deepEqual(plain(ctx.timelineMarkers(m,{from:0,to:1,count:2})),[]);
    assert.equal(ctx.timelineSampleIndex(m,{from:0,to:1,count:2},10,100),-1);
    const f=fixture();
    delete f.provenance;
    assert.equal(ctx.model(f).ready,false);
});

test("real M4 JPL relationship values and event times are preserved",{
    skip:!process.env.MAGICK_M5G_JSON_FILE
},()=>{
    const m4=JSON.parse(fs.readFileSync(process.env.MAGICK_M5G_JSON_FILE,"utf8"));
    const m=ctx.model(m4);
    assert.equal(m.ready,true,m.reason);
    assert.equal(m.source,"de440s.bsp");
    assert.equal(m.relationships.length,1);
    const v=ctx.windowFor(m,1,0.5);
    assert.ok(ctx.timelineMarkers(m,v).length>=3);
    for(let i=0;i<m.sampleCount;i++){
        const dial=ctx.relationAt(m,i);
        assert.equal(dial.separation_deg,m4.relationships[0].samples[i].longitude_separation_deg);
        assert.equal(dial.sample_utc,m4.relationships[0].samples[i].time_utc);
    }
    for(const marker of ctx.timelineMarkers(m,v)){
        const original=m4.event_markers.find(e=>
            e.time_utc===marker.time_utc && e.name===marker.name);
        assert.ok(original,"all plotted timeline markers must have M4 provenance");
        assert.ok(Math.abs(m.times[marker.sampleIndex]-Date.parse(marker.time_utc))<=
            (m.times[1]-m.times[0])/2+1);
    }
});
