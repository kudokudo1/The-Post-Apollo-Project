"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const m5Policy=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const networkPolicy=read("widgets/weather/StationCosmosCelestialNetworkPolicy.js");
const qml=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const service=read("services/weather/CelestialVisualService.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const M5=vm.createContext({}),Net=vm.createContext({});
vm.runInContext(m5Policy.replace(/^\.pragma library\s*/m,""),M5);
vm.runInContext(networkPolicy.replace(/^\.pragma library\s*/m,""),Net);
const plain=v=>JSON.parse(JSON.stringify(v));

function fixture(extraBodies=0) {
    const ms=[0,1,2].map(h=>Date.parse("2026-11-04T0"+h+":00:00.000Z"));
    const definitions=[
        {body:"mercury",lons:[350,355,0],uw:[350,355,360]},
        {body:"venus",lons:[10,15,20],uw:[10,15,20]},
        {body:"moon",lons:[80,82,84],uw:[80,82,84]},
        {body:"sun",lons:[160,161,162],uw:[160,161,162]}
    ].slice(0,2+extraBodies);
    const rows=(body)=>body.lons.map((longitude_deg,i)=>({
        unix_ms:ms[i],time_utc:new Date(ms[i]).toISOString(),
        longitude_deg,
        unwrapped_longitude_deg:body.uw[i],
        latitude_deg:0.2, distance_au:1.5,
        longitude_rate_deg_per_day:1.0,motion:"direct"
    }));
    const series=definitions.map(d=>({body:d.body,samples:rows(d)}));
    const relations=[];
    for(let a=0;a<definitions.length;a++){
        for(let b=a+1;b<definitions.length;b++){
            relations.push({
                bodies:[definitions[a].body,definitions[b].body],
                samples:ms.map((unix_ms,i)=>({
                    unix_ms,
                    time_utc:new Date(unix_ms).toISOString(),
                    longitude_separation_deg:Math.abs((
                       (definitions[b].lons[i]-definitions[a].lons[i]+540)%360)-180),
                    aspects:[]
                }))
            });
        }
    }
    return {
        format:"post-apollo.weather.celestial-visual-data.v1",
        provenance:{
            engine:"skyfield",engine_version:"1",
            ephemeris_id:"de440",
            ephemeris_sha256:"abcdef0123".repeat(6)+"abcd",
            time_data_id:"test-utc"
        },
        query:{
            origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",
            bodies:definitions.map(x=>x.body)
        },
        sample_count:3,series,relationships:relations,event_markers:[]
    };
}
function scene(extra=0,index=2) {
    const model=M5.model(fixture(extra));
    assert.equal(model.ready,true,model.reason);
    return Net.network(model,index);
}

test("V4a consumes only M5-validated source M4 model with exact UTC",()=>{
    const f=fixture();
    const model=M5.model(f);
    assert.equal(model.ready,true,model.reason);
    assert.equal(model.series.length,2);
    const graph=plain(Net.network(model,2));
    assert.equal(Net.FORMAT,"post-apollo.weather.celestial-network.v4a.v1");
    assert.equal(graph.ready,true,graph.reason);
    assert.equal(graph.count,2);
    assert.equal(graph.nodes.length,2);
    assert.equal(graph.edges.length,1);
    assert.equal(graph.timeMs,Date.parse("2026-11-04T02:00:00.000Z"));
    assert.equal(graph.isoUtc,"2026-11-04T02:00:00.000Z");
    assert.equal(graph.frame,"true-ecliptic-of-date");
    assert.equal(graph.hash,"abcdef0123");
    assert.equal(graph.source,"de440");
    assert.deepEqual(graph.nodes.map(x=>x.longitude_deg),[0,20]);
    assert.equal(graph.edges[0].longitude_separation_deg,20);
    assert.equal(graph.edges[0].aspects.length,0);
    assert.match(Net.pairLabel(graph.edges[0]),/20.000° LONGITUDE SEPARATION/);
    assert.equal(Net.pairLabel(null),"NO SOURCE PAIR SELECTED");
});

test("V4a network supports only genuine indexed bodies, up to four",()=>{
    const g=plain(scene(2));
    assert.equal(g.ready,true,g.reason);
    assert.equal(g.count,4);
    assert.equal(g.edges.length,6);
    const keys=g.edges.map(x=>x.key);
    assert.equal(new Set(keys).size,6);
    assert.equal(Net.keyFor("venus","mercury"),"mercury|venus");
    assert.equal(Net.keyFor("mercury","mercury"),"");
    assert.equal(Net.edgeByKey(g,"sun|venus").longitude_separation_deg,142);
    assert.equal(Net.nodeByBody(g,"mercury").longitude_deg,0);
    assert.equal(Net.nodeByBody(g,"pluto"),null);
    assert.equal(Net.edgeByKey(g,"missing|venus"),null);
});

test("V4a refuses missing, mismatched, or invented source samples",()=>{
    assert.equal(Net.network(null,0).ready,false);
    assert.equal(Net.network({ready:true},0).ready,false);
    const m=M5.model(fixture());
    assert.equal(Net.network(m,-1).ready,false);
    assert.equal(Net.network(m,3).ready,false);
    assert.equal(Net.network(m,NaN).ready,false);
    assert.equal(Net.network({...m,frame:"heliocentric"},0).ready,false);
    assert.equal(Net.network({...m,hash:"unverified"},0).ready,false);
    const wrong=plain(m);
    wrong.series[0].rows[1].unix_ms+=1000;
    assert.equal(Net.network(wrong,1).ready,false);
    const forged=plain(m);
    forged.relationships[0].samples[2].longitude_separation_deg=40;
    assert.equal(Net.network(forged,2).ready,false);
    const missing=plain(m);
    missing.relationships=[];
    assert.equal(Net.network(missing,2).ready,false);
    const incomplete=fixture();
    incomplete.provenance.ephemeris_sha256="NOTAHEX";
    assert.equal(M5.model(incomplete).ready,false);
    assert.equal(Net.network(M5.model(incomplete),0).ready,false);
});

test("V4a longitude angles are categorical ecliptic geometry, not orbits",()=>{
    const g=Net.layout(400,240);
    assert.equal(g.ready,true);
    assert.equal(g.cx,156);
    assert.equal(g.cy,120);
    assert.ok(g.r>50);
    for(const [lon,x,y] of [
        [0,g.cx,g.cy-g.r],
        [90,g.cx+g.r,g.cy],
        [180,g.cx,g.cy+g.r],
        [270,g.cx-g.r,g.cy]
    ]){
        const p=Net.position(lon,400,240);
        assert.ok(Math.abs(p.x-x)<1e-8,String(lon)+" x");
        assert.ok(Math.abs(p.y-y)<1e-8,String(lon)+" y");
    }
    assert.equal(Net.position(360,400,240),null);
    assert.equal(Net.position(-1,400,240),null);
    assert.equal(Net.position(0,0,0),null);
    assert.equal(Net.separation(350,10),20);
    assert.equal(Net.separation(10,350),20);
    assert.equal(Net.separation(10,190),180);
    assert.equal(Net.separation(null,20),null);
});

test("Node and chord hitboxes agree with drawn source geometry",()=>{
    const data=scene();
    const a=Net.position(0,400,240);
    const b=Net.position(20,400,240);
    assert.equal(Net.bodyHit(data,a.x,a.y,400,240,11),"mercury");
    assert.equal(Net.bodyHit(data,b.x,b.y,400,240,11),"venus");
    assert.equal(Net.bodyHit(data,1,1,400,240,11),"");
    assert.equal(Net.bodyHit(data,156,120,400,240,-1),"");
    const mx=(a.x+b.x)/2,my=(a.y+b.y)/2;
    assert.equal(Net.edgeHit(data,mx,my,400,240,6),"mercury|venus");
    assert.equal(Net.edgeHit(data,5,5,400,240,6),"");
    assert.equal(Net.edgeHit(data,mx,my,400,240,0),"");
    assert.equal(Net.bodyHit({ready:false},a.x,a.y,400,240,11),"");
});

test("V4a QML changes only presentation, reuses the one on-demand M4 owner",()=>{
    assert.match(instrument,/StationCosmosCelestialNetwork\s*\{/);
    assert.match(instrument,/\{id:"network",label:"NETWORK"\}/);
    assert.match(instrument,/graphModel: instrument\.graphModel/);
    assert.match(instrument,/focusIndex: instrument\.focusIndex/);
    assert.match(instrument,/selectedBody: instrument\.selectedBody/);
    assert.match(instrument,/enabled: instrument\.graphModel\.ready && instrument\.mode !== "network"/);
    assert.match(instrument,/onSampleScrubbed: function\(originIndex,offsetPixels\)/);
    assert.match(instrument,/Celestial\.wheelDragIndex\(/);
    assert.match(qml,/Network\.network\(graphModel,focusIndex\)/);
    assert.match(qml,/Network\.bodyHit\(/);
    assert.match(qml,/Network\.edgeHit\(/);
    assert.match(qml,/onClicked: graph\.bodyPicked\(modelData\.body\)/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/GEOCENTRIC ECLIPTIC LONGITUDES/);
    assert.match(qml,/NOT PHYSICAL ORBITS/);
    assert.match(service,/property var visualData: null/);
    assert.match(service,/function refresh\(\)/);
    assert.match(station,/WeatherServices\.CelestialVisualService\s*\{/);
    assert.match(station,/celestialSource: celestialVisualService/);
    for(const code of [qml,networkPolicy]){
        for(const banned of ["Process {","Timer {","FileView {","XMLHttpRequest",
            "new WebSocket","swaymsg","Qt.callLater","Quickshell.Io",
            "fetch(","openUrlExternally"])
            assert.ok(!code.includes(banned),banned);
    }
});
