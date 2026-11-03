"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const ctx=vm.createContext({Date,Math,isFinite});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),ctx);

const T0=Date.UTC(2026,9,1);
function eventAtDays(days,name,type,kind){
    return {time_utc:new Date(T0+days*86400000).toISOString(),
        name,type,bodies:["moon","sun"],contact_kind:kind};
}
function payload(){
    const times=Array.from({length:5},(_,i)=>T0+i*86400000);
    function sample(body,i){
        const moon=body==="moon",lon=moon?(350+15*i)%360:10+i;
        return {time_utc:new Date(times[i]).toISOString(),
            unix_ms:times[i],longitude_deg:lon,
            unwrapped_longitude_deg:moon?350+15*i:10+i,
            latitude_deg:moon?2:-0.2,distance_au:moon?0.0027:1.0,
            longitude_rate_deg_per_day:moon?15:1,motion:"direct"};
    }
    const moon=times.map((_,i)=>sample("moon",i));
    const sun=times.map((_,i)=>sample("sun",i));
    const pair=times.map((ms,i)=>({
        time_utc:moon[i].time_utc,unix_ms:ms,
        longitude_separation_deg:Math.abs(((moon[i].longitude_deg-
            sun[i].longitude_deg+540)%360)-180),
        aspects:i===1?[{name:"sextile"}]:[],
    }));
    return {
        format:ctx.FORMAT,
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",ephemeris_sha256:"a".repeat(64),
            time_data_id:"skyfield-1.55-builtin-timescale"},
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies:["moon","sun"]},
        sample_count:5,
        series:[{body:"moon",samples:moon},{body:"sun",samples:sun}],
        relationships:[{bodies:["moon","sun"],samples:pair}],
        event_markers:[
            eventAtDays(3.75,"opposition","exact_longitude_aspect","crossing"),
            eventAtDays(0.25,"conjunction","exact_longitude_aspect","tangent_candidate"),
            eventAtDays(1.5,"direct_to_retrograde","apparent_longitude_station",undefined)
        ],
    };
}

test("event navigation sorts source events, never generates unseen positions",()=>{
    const m=ctx.model(payload());
    assert.equal(m.ready,true,m.reason);
    const view=ctx.windowFor(m,1,0.5);
    const ordered=ctx.visibleEvents(m,view);
    assert.deepEqual(JSON.parse(JSON.stringify(ordered.map(e=>e.name))),
         ["conjunction","direct_to_retrograde","opposition"]);
    assert.equal(ctx.eventAt(m,view,-1),null);
    assert.equal(ctx.eventAt(m,view,99),null);
    const first=ctx.stepEvent(m,view,-1,1);
    assert.equal(first.ordinal,0);
    assert.equal(first.event.name,"conjunction");
    assert.equal(first.sampleIndex,0); // 0.25 day nearest to day 0
    const second=ctx.stepEvent(m,view,first.ordinal,1);
    assert.equal(second.ordinal,1);
    assert.equal(second.sampleIndex,1); // 1.5-day tie prefers earlier sample
    const last=ctx.stepEvent(m,view,-1,-1);
    assert.equal(last.ordinal,2);
    assert.equal(last.event.name,"opposition");
    assert.equal(ctx.stepEvent(m,view,last.ordinal,1).ordinal,0);
    assert.equal(ctx.stepEvent(m,view,0,-1).ordinal,2);
});

test("nearest sample search is bounded, deterministic and tie-stable",()=>{
    const m=ctx.model(payload());
    assert.equal(ctx.nearestSampleIndex(m,T0),0);
    assert.equal(ctx.nearestSampleIndex(m,T0+86400000),1);
    assert.equal(ctx.nearestSampleIndex(m,T0+1.5*86400000),1);
    assert.equal(ctx.nearestSampleIndex(m,T0+1.6*86400000),2);
    assert.equal(ctx.nearestSampleIndex(m,T0-100000),0);
    assert.equal(ctx.nearestSampleIndex(m,T0+20*86400000),4);
    assert.equal(ctx.nearestSampleIndex(m,NaN),-1);
    assert.equal(ctx.nearestSampleIndex(ctx.model(null),T0),-1);
});

test("zoom excludes events outside the actual viewed time window",()=>{
    const m=ctx.model(payload());
    const narrow={from:1,to:2,count:2};
    const events=ctx.visibleEvents(m,narrow);
    assert.deepEqual(JSON.parse(JSON.stringify(events.map(e=>e.name))),
                     ["direct_to_retrograde"]);
    assert.match(ctx.eventLabel(m,narrow,-1),/1 EVENTS/);
    assert.match(ctx.eventLabel(m,narrow,0),/ESTIMATED STATION/);
    assert.equal(ctx.eventLabel(m,{from:2,to:3,count:2},0),
                 "NO CALCULATED EVENTS IN VIEW");
    assert.equal(ctx.stepEvent(m,{from:2,to:3,count:2},-1,1),null);
});

test("event inspector discloses crossing, station and grazing candidate status",()=>{
    const m=ctx.model(payload()),view=ctx.windowFor(m,1,0.5);
    assert.match(ctx.eventLabel(m,view,0),/GRAZING CANDIDATE/);
    assert.match(ctx.eventLabel(m,view,1),/ESTIMATED STATION/);
    assert.match(ctx.eventLabel(m,view,2),/ANGLE CROSSING/);
    assert.match(ctx.eventLabel(m,view,2),/2026-10-04/);
    assert.match(ctx.eventLabel(m,view,2),/OPPOSITION/);
});

test("coordinate inspector uses measured longitudes and correct zodiac sector",()=>{
    const m=ctx.model(payload());
    const moon0=ctx.bodyDetails(m,0,"moon");
    const moon1=ctx.bodyDetails(m,1,"moon");
    assert.match(moon0,/350\.000° PI 20\.00°/);
    assert.match(moon1,/5\.000° AR 5\.00°/);
    assert.match(moon0,/LAT 2\.00°/);
    assert.match(moon0,/0\.0027 AU/);
    assert.match(ctx.pairDetails(m,1),/SEPARATION/);
    assert.match(ctx.pairDetails(m,1),/SEXTILE/);
    assert.match(ctx.pairDetails(m,0),/NO ASPECT IN ORB/);
    assert.equal(ctx.bodyDetails(m,0,"unknown"),"NO POSITION SELECTED");
    assert.equal(ctx.bodyDetails(ctx.model(null),0,"moon"),"NO POSITION SELECTED");
});

test("standalone instrument wires event buttons and preserves time/zoom actions",()=>{
    assert.match(qml,/property int eventOrdinal: -1/);
    assert.match(qml,/readonly property var eventsInView: Celestial\.visibleEvents/);
    assert.match(qml,/function stepToEvent\(direction\)/);
    assert.match(qml,/Celestial\.stepEvent\(graphModel,viewWindow,eventOrdinal,direction\)/);
    assert.match(qml,/instrument\.lockedIndex=chosen\.sampleIndex/);
    assert.match(qml,/onClicked: instrument\.stepToEvent\(-1\)/);
    assert.match(qml,/onClicked: instrument\.stepToEvent\(1\)/);
    assert.match(qml,/Celestial\.eventLabel\(instrument\.graphModel/);
    assert.match(qml,/Celestial\.bodyDetails\(instrument\.graphModel/);
    assert.match(qml,/Celestial\.pairDetails\(instrument\.graphModel/);
    assert.match(qml,/CALCULATED EVENT TIME \/\/ PLANET POSITIONS USE NEAREST SAMPLE/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/instrument\.panPosition=Celestial\.clamp\(/);
    assert.match(qml,/instrument\.lockedIndex=Celestial\.indexAtFraction\(/);
    assert.match(qml,/instrument\.eventOrdinal=-1;/);
    assert.match(qml,/graphCanvas\.requestPaint\(\)/);
    assert.match(qml,/Station|GEOCENTRIC \/ TROPICAL REFERENCE/);
    for(const prohibited of ["Process {","Timer {","FileView {",
         "XMLHttpRequest","Date.now()","Math.random("])
        assert.equal(qml.includes(prohibited),false,prohibited);
});
