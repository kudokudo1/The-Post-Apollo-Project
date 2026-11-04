"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
const m5=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const v4a=read("widgets/weather/StationCosmosCelestialNetworkPolicy.js");
const v4c=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const v4d=read("widgets/weather/StationCosmosSolarOverviewPolicy.js");
const pane=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const networkPane=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const service=read("services/weather/CelestialVisualService.qml");
const querySource=read("services/weather/CelestialVisualQueryPolicy.js");
const backend=read("scripts/weather/celestial_visual_data.py");
const overviewPy=read("scripts/weather/celestial_solar_overview.py");

const M=vm.createContext({}),N=vm.createContext({}),
      H=vm.createContext({}),S=vm.createContext({}),Q=vm.createContext({});
for(const [context,source] of [
    [M,m5],[N,v4a],[H,v4c],[S,v4d],[Q,querySource]]) {
    vm.runInContext(source.replace(/^\.pragma library\s*/m,""),context);
}
const plain=x=>JSON.parse(JSON.stringify(x));
const SHA="abcdef0123".repeat(6)+"abcd";
const BODY_IDS=plain(S.BODIES);

function fixture() {
    const times=[0,1,2].map(h=>Date.parse("2026-11-04T0"+h+":00:00.000Z"));
    const pair=["moon","sun"];
    const geo=[[350,355,0],[10,15,20]];
    const raw={
        format:"post-apollo.weather.celestial-visual-data.v1",
        provenance:{
            engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",
            ephemeris_sha256:SHA,time_data_id:"builtin-1.55"
        },
        query:{
            origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies:pair,
            include_heliocentric_spatial:true,
            solar_overview_bodies:BODY_IDS.slice()
        },
        sample_count:3,
        series:pair.map((body,i)=>({
            body,samples:times.map((unix_ms,k)=>({
                unix_ms,time_utc:new Date(unix_ms).toISOString(),
                longitude_deg:geo[i][k],
                unwrapped_longitude_deg:i===0?[350,355,360][k]:geo[i][k],
                latitude_deg:0,distance_au:i===0?0.0025:1.0,
                longitude_rate_deg_per_day:1,motion:"direct"
            }))
        })),
        relationships:[{
            bodies:pair.slice(),
            samples:times.map((unix_ms,i)=>({
                unix_ms,time_utc:new Date(unix_ms).toISOString(),
                longitude_separation_deg:Math.abs(
                    ((geo[1][i]-geo[0][i]+540)%360)-180),
                aspects:[]
            }))
        }],
        event_markers:[]
    };
    raw.solar_overview={
        format:S.FORMAT,origin:"heliocentric",origin_body:"sun",
        position_model:"geometric",frame:S.FRAME,
        epoch:"exact-m4-grid",units:"AU",source:"same-JPL-kernel-as-M4",
        sample_count:times.length,times_unix_ms:times.slice(),
        series:BODY_IDS.map((body,i)=>({
            body,
            vectors_au:times.map((_,k)=>[i+0.5+k*0.05,0.12,0.01])
        }))
    };
    return raw;
}
function valid(index=2) {
    const payload=fixture(),model=M.model(payload);
    assert.equal(model.ready,true,model.reason);
    const network=N.network(model,index);
    assert.equal(network.ready,true,network.reason);
    return {payload,model,network,
        scene:S.scene(payload,model,network,index)};
}

test("V4d source proves ten exact NAIF targets at same M4 UTC",()=>{
    const {scene,model,network}=valid();
    const data=plain(scene);
    assert.equal(S.FORMAT,"post-apollo.weather.solar-overview.v1");
    assert.equal(data.ready,true,data.reason);
    assert.equal(data.count,10);
    assert.equal(data.points.length,10);
    assert.equal(data.timeMs,model.times[2]);
    assert.equal(data.timeMs,network.timeMs);
    assert.equal(data.source,"de440s.bsp");
    assert.equal(data.hash,SHA.slice(0,10));
    assert.equal(data.origin,"sun");
    assert.equal(data.positionModel,"geometric");
    assert.equal(data.atlas,true);
    assert.equal(data.frame,"true-ecliptic-of-date");
    assert.deepEqual(data.points.map(p=>p.body),BODY_IDS);
    assert.equal(data.points[0].x_au,0.6);
    assert.equal(data.points.at(-1).x_au,9.6);
    assert.equal(data.points.at(-1).unix_ms,model.times[2]);
    assert.equal(data.maxAu,Math.hypot(9.6,0.12,0.01));
    assert.equal(data.points[4].label,"MARS SYS");
    assert.equal(data.points[5].label,"JUPITER SYS");
    assert.equal(data.points[9].label,"PLUTO SYS");
    assert.equal(S.label("jupiter"),"UNKNOWN");
    assert.equal(S.label("jupiter_barycenter"),"JUPITER SYS");
});

test("V4d keeps 2-body pair, separate source-only 10-body atlas",()=>{
    const request=plain(Q.requestFor("2026-11-04",0,"moon-sun",29));
    assert.deepEqual(request.bodies,["moon","sun"]);
    assert.equal(request.include_events,true);
    assert.equal(request.include_heliocentric_spatial,true);
    assert.deepEqual(request.solar_overview_bodies,BODY_IDS);
    assert.equal(BODY_IDS.length,10);
    assert.equal(Q.PAIRS.length,6);
    assert.match(backend,/build_solar_overview\(/);
    assert.match(backend,/overview_targets = \{/);
    assert.match(backend,/\"geometric\"/);
    assert.match(overviewPy,/MAX_SAMPLES = 181/);
    assert.match(overviewPy,/exact-m4-grid/);
    assert.match(overviewPy,/same-JPL-kernel-as-M4/);
    assert.match(service,/function refresh\(\)/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
});

test("V4d rejects all wrong sources, incomplete grid, forged XYZ",()=>{
    const {payload,model,network}=valid();
    const changed=mutate=>{
        const p=plain(payload);
        mutate(p);
        return S.scene(p,model,network,2).ready;
    };
    assert.equal(S.scene(null,model,network,2).ready,false);
    assert.equal(S.scene(payload,model,network,-1).ready,false);
    assert.equal(S.scene(payload,model,network,3).ready,false);
    assert.equal(changed(p=>{delete p.solar_overview}),false);
    assert.equal(changed(p=>{p.solar_overview.origin="earth"}),false);
    assert.equal(changed(p=>{p.solar_overview.position_model="apparent"}),false);
    assert.equal(changed(p=>{p.solar_overview.frame="j2000"}),false);
    assert.equal(changed(p=>{p.provenance.ephemeris_sha256="1".repeat(64)}),false);
    assert.equal(changed(p=>{p.solar_overview.times_unix_ms[1]+=3600000}),false);
    assert.equal(changed(p=>{p.solar_overview.times_unix_ms[0]="bad"}),false);
    assert.equal(changed(p=>{p.solar_overview.series[1].body="jupiter"}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].body="venus"}),false);
    assert.equal(changed(p=>{p.solar_overview.series.pop()}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].vectors_au.pop()}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].vectors_au[1]=[0,0,0]}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].vectors_au[1]=[NaN,1,1]}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].vectors_au[2]=[null,1,1]}),false);
    assert.equal(changed(p=>{p.solar_overview.series[0].vectors_au[2]=[1,1]}),false);
    assert.equal(changed(p=>{p.solar_overview.sample_count=182}),false);
    assert.equal(changed(p=>{p.query.solar_overview_bodies.pop()}),false);
});

test("V4d ALL and INNER ranges preserve correct AU and clickable positions",()=>{
    const {scene}=valid();
    const earth=scene.points.find(p=>p.body==="earth");
    const g=H.layout(400,240,1);
    assert.equal(g.ready,true);
    const all=H.position(scene,earth,400,240,1,false);
    const inner=H.position(scene,earth,400,240,1,false,4);
    assert.ok(inner!==null && all!==null);
    assert.ok(Math.abs(inner.y-g.cy)>Math.abs(all.y-g.cy));
    assert.equal(H.hit(scene,inner.x,inner.y,400,240,1,false,12,4),"earth");
    assert.equal(H.hit(scene,inner.x,inner.y,400,240,1,false,0,4),"");
    assert.equal(H.position(scene,earth,400,240,1,false,-1),null);
    const tilted=H.position(scene,earth,400,240,1,true,4);
    assert.notEqual(tilted.y,inner.y);
    assert.equal(H.byBody(scene,"jupiter_barycenter").label,"JUPITER SYS");
    assert.equal(H.byBody(scene,"sun"),null);
});

test("V4d QML has real ten-body selector and a scrollable inspector",()=>{
    assert.match(pane,/import "StationCosmosSolarOverviewPolicy\.js" as Solar/);
    assert.match(pane,/Solar\.scene\(visualData,graphModel,verifiedNetwork,focusIndex\)/);
    assert.match(pane,/property string atlasRange: "all"/);
    assert.match(pane,/spatial\.radialDomainAu/);
    assert.match(pane,/onClicked: spatial\.atlasRange="inner"/);
    assert.match(pane,/onClicked: spatial\.atlasRange="all"/);
    assert.match(networkPane,/Flickable\s*\{/);
    assert.match(networkPane,/contentHeight: inspectorColumn\.implicitHeight/);
    assert.match(networkPane,/heliocentricPane\.scene\.points/);
    assert.match(networkPane,/graph\.bodyPicked\(modelData\.body\)/);
    assert.match(networkPane,/heliocentricPane\.tiltView=true/);
    assert.match(networkPane,/heliocentricPane\.tiltView=false/);
    assert.match(networkPane,/heliocentricPane\.atlasRange=modelData\.id/);
    assert.match(networkPane,/x_au\.toFixed\(3\)/);
    assert.match(instrument,/spatialPayload: instrument\.visualData/);
    assert.match(pane,/ONE UTC SNAPSHOT/);
    assert.match(pane,/no orbital paths/i);
    for(const text of [pane,v4d,overviewPy]){
        for(const forbidden of ["Process {","Timer {","new WebSocket",
            "XMLHttpRequest","Qt.callLater","swaymsg","fetch(","curl "])
            assert.ok(!text.includes(forbidden),forbidden);
    }
});
