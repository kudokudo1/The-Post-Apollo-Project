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
const helio=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const qml=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const networkQml=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const service=read("services/weather/CelestialVisualService.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const queryJs=read("services/weather/CelestialVisualQueryPolicy.js");
const python=read("scripts/weather/celestial_visual_data.py");
const spatialPython=read("scripts/weather/celestial_spatial_data.py");

const M=vm.createContext({}),N=vm.createContext({}),H=vm.createContext({}),Q=vm.createContext({});
vm.runInContext(m5.replace(/^\.pragma library\s*/m,""),M);
vm.runInContext(v4a.replace(/^\.pragma library\s*/m,""),N);
vm.runInContext(helio.replace(/^\.pragma library\s*/m,""),H);
vm.runInContext(queryJs.replace(/^\.pragma library\s*/m,""),Q);
const plain=x=>JSON.parse(JSON.stringify(x));
const SHA="abcdef0123".repeat(6)+"abcd";

function fixture(includeSun=false){
    const bodies=includeSun?["moon","sun"]:["mercury","venus"];
    const t=[0,1,2].map(h=>Date.parse("2026-11-04T0"+h+":00:00.000Z"));
    const geoLon=[[350,355,0],[10,15,20]];
    const sourceSeries=bodies.map((body,i)=>({
        body,samples:t.map((unix_ms,k)=>({
            unix_ms,time_utc:new Date(unix_ms).toISOString(),
            longitude_deg:geoLon[i][k],
            unwrapped_longitude_deg:i===0?[350,355,360][k]:geoLon[i][k],
            latitude_deg:0.2,distance_au:i===0?0.003:1.5,
            longitude_rate_deg_per_day:1,motion:"direct"
        }))
    }));
    const gap=(a,b)=>Math.abs(((b-a+540)%360)-180);
    const raw={
        format:"post-apollo.weather.celestial-visual-data.v1",
        provenance:{
            engine:"skyfield",engine_version:"1.55",ephemeris_id:"de440s.bsp",
            ephemeris_sha256:SHA,time_data_id:"builtin-1.55"
        },
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies,
            include_heliocentric_spatial:true},
        sample_count:3,
        series:sourceSeries,
        relationships:[{
            bodies:bodies.slice(),
            samples:t.map((unix_ms,k)=>({
                unix_ms,time_utc:new Date(unix_ms).toISOString(),
                longitude_separation_deg:gap(geoLon[0][k],geoLon[1][k]),
                aspects:[]
            }))
        }],
        event_markers:[]
    };
    raw.heliocentric_spatial={
        format:H.FORMAT,
        origin:"heliocentric",origin_body:"sun",position_model:"geometric",
        frame:H.FRAME,epoch:"per-sample-UTC",units:"AU",
        source:"same-JPL-kernel-as-M4",
        sample_count:3,
        series:bodies.map((body,i)=>({
            body,
            samples:t.map((unix_ms,k)=>{
                const vals=body==="sun" ? [0,0,0]
                    : i===0 ? [1+k*0.1,0,0] : [0,2+k*0.1,0];
                return {unix_ms,time_utc:new Date(unix_ms).toISOString(),
                    x_au:vals[0],y_au:vals[1],z_au:vals[2],
                    distance_au:Math.hypot(...vals)};
            })
        }))
    };
    return raw;
}
function evaluated(includeSun=false,index=2){
    const payload=fixture(includeSun);
    const model=M.model(payload);
    assert.equal(model.ready,true,model.reason);
    const network=N.network(model,index);
    assert.equal(network.ready,true,network.reason);
    return {payload,model,network,scene:H.verifiedScene(payload,model,network,index)};
}

test("V4c HELIO reads true geometric same-kernel M4 XYZ, not apparent longitude",()=>{
    const {scene,network,payload}=evaluated(),d=plain(scene);
    assert.equal(H.FORMAT,"post-apollo.weather.heliocentric-spatial.v1");
    assert.equal(d.ready,true,d.reason);
    assert.equal(d.origin,"sun");
    assert.equal(d.positionModel,"geometric");
    assert.equal(d.frame,"true-ecliptic-of-date");
    assert.equal(d.timeMs,network.timeMs);
    assert.equal(d.utc,"2026-11-04T02:00:00.000Z");
    assert.equal(d.hash,SHA.slice(0,10));
    assert.equal(d.source,"de440s.bsp");
    assert.equal(d.count,2);
    assert.equal(d.maxAu,2.2);
    assert.equal(d.points[0].body,"mercury");
    assert.equal(d.points[0].x_au,1.2);
    assert.equal(d.points[1].body,"venus");
    assert.equal(d.points[1].y_au,2.2);
    assert.notEqual(d.points[1].y_au,
        payload.series[1].samples[2].longitude_deg);
    assert.match(H.detail(d.points[1]),/VENUS \/\/ 2\.200000 AU/);
});

test("V4c Sun is a zero-vector origin, not a made-up planet orbit",()=>{
    const {scene}=evaluated(true);
    assert.equal(scene.ready,true,scene.reason);
    const moon=H.byBody(scene,"moon"),sun=H.byBody(scene,"sun");
    assert.equal(moon.origin,false);
    assert.equal(sun.origin,true);
    assert.equal(sun.distance_au,0);
    assert.equal(sun.x_au,0);
    assert.equal(H.detail(sun),"SUN // HELIOCENTRIC ORIGIN // 0 AU");
    assert.equal(H.byBody(scene,"pluto"),null);
    const bad=fixture(true);
    bad.heliocentric_spatial.series[1].samples[0].x_au=0.1;
    const model=M.model(bad),net=N.network(model,2);
    assert.equal(H.verifiedScene(bad,model,net,2).ready,false);
});

test("V4c projection uses real AU and keeps latitude Z for tilted view",()=>{
    const scene=evaluated().scene;
    const p=H.position(scene,scene.points[0],400,240,1,false);
    const g=H.layout(400,240,1);
    assert.equal(g.cx,156);
    assert.equal(g.cy,120);
    assert.equal(g.r,96);
    assert.ok(Math.abs(p.x-156)<1e-9);
    assert.ok(Math.abs(p.y-(120-96*1.2/2.2))<1e-9);
    const p2=H.position(scene,scene.points[1],400,240,1,false);
    assert.ok(Math.abs(p2.x-252)<1e-9);
    assert.ok(Math.abs(p2.y-120)<1e-9);
    assert.equal(H.hit(scene,p.x,p.y,400,240,1,false,12),"mercury");
    assert.equal(H.hit(scene,p2.x,p2.y,400,240,1,false,12),"venus");
    assert.equal(H.hit(scene,10,10,400,240,1,false,12),"");
    assert.equal(H.hit(scene,p.x,p.y,400,240,1,false,0),"");
    assert.equal(H.position(scene,scene.points[0],0,0,1,false),null);
    const zScene=plain(scene);
    zScene.points[0].z_au=0.6;
    const tilted=H.position(zScene,zScene.points[0],400,240,1,true);
    const top=H.position(zScene,zScene.points[0],400,240,1,false);
    assert.notEqual(tilted.y,top.y);
});

test("V4c refuses every malformed time/source/vector without partial rows",()=>{
    const {payload,model,network}=evaluated();
    const altered=(mutate)=>{
        const data=plain(payload);
        mutate(data);
        return H.verifiedScene(data,model,network,2).ready;
    };
    assert.equal(H.verifiedScene(null,model,network,2).ready,false);
    assert.equal(H.verifiedScene(payload,model,network,-1).ready,false);
    assert.equal(H.verifiedScene(payload,model,network,3).ready,false);
    assert.equal(altered(d=>{delete d.heliocentric_spatial}),false);
    assert.equal(altered(d=>{d.query.include_heliocentric_spatial=false}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.origin="geocentric"}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.position_model="apparent"}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.frame="ecliptic-j2000"}),false);
    assert.equal(altered(d=>{d.provenance.ephemeris_sha256="1".repeat(64)}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[0].samples[0].unix_ms+=1}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[0].samples[1].distance_au=0}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[1].samples[2].z_au=5}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[0].body="pluto"}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[0].samples=[]}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.sample_count=722}),false);
    assert.equal(altered(d=>{d.heliocentric_spatial.series[0].samples[2].x_au=null}),false);
});

test("V4c shares one on-demand CALCULATE and keeps older modes separate",()=>{
    assert.match(queryJs,/include_heliocentric_spatial:true/);
    const req=Q.requestFor("2026-11-04",0,"moon-sun",29);
    assert.equal(req.include_heliocentric_spatial,true);
    assert.match(python,/sun_origin = _target\(kernel, "sun"\)/);
    assert.match(python,/_position\(sun_origin, targets\[body\], t, "geometric"\)/);
    assert.match(python,/position\.frame_xyz\(frame\)\.au/);
    assert.match(spatialPython,/same-JPL-kernel-as-M4/);
    assert.match(instrument,/spatialPayload: instrument\.visualData/);
    assert.match(networkQml,/property var spatialPayload: null/);
    assert.match(networkQml,/StationCosmosHeliocentricPane\s*\{/);
    assert.match(networkQml,/visualData: graph\.spatialPayload/);
    assert.match(networkQml,/onClicked: graph\.displayMode="heliocentric"/);
    assert.match(networkQml,/onClicked: graph\.displayMode="chords"/);
    assert.match(networkQml,/onClicked: graph\.displayMode="depth"/);
    assert.match(qml,/Helio\.verifiedScene\(\s*visualData,graphModel,verifiedNetwork,focusIndex\)/);
    assert.match(qml,/Helio\.position\(/);
    assert.match(qml,/Helio\.hit\(/);
    assert.match(qml,/onClicked: spatial\.tiltView=true/);
    assert.match(qml,/onClicked: spatial\.tiltView=false/);
    assert.match(qml,/onClicked: function\(mouse\)/);
    assert.match(qml,/spatial\.sampleScrubbed\(originalIndex,dx\)/);
    assert.match(qml,/spatial\.bodyPicked\(body\)/);
    assert.match(qml,/ONE UTC SNAPSHOT \/\/ NO ORBITS/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
    assert.match(service,/function refresh\(\)/);
    assert.match(service,/onCurrentKeyChanged: clearState\(\)/);
    for(const src of [qml,helio,spatialPython]){
        for(const prohibited of ["Process {","Timer {","XMLHttpRequest",
             "Qt.callLater","new WebSocket","swaymsg","curl ","fetch("])
            assert.ok(!src.includes(prohibited),prohibited);
    }
});
