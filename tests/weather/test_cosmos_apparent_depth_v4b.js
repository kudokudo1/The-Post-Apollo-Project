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
const v4b=read("widgets/weather/StationCosmosCelestialDepthPolicy.js");
const depthQml=read("widgets/weather/StationCosmosCelestialDepthPane.qml");
const networkQml=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const service=read("services/weather/CelestialVisualService.qml");
const M=vm.createContext({}),N=vm.createContext({}),D=vm.createContext({});
vm.runInContext(m5.replace(/^\.pragma library\s*/m,""),M);
vm.runInContext(v4a.replace(/^\.pragma library\s*/m,""),N);
vm.runInContext(v4b.replace(/^\.pragma library\s*/m,""),D);
const plain=v=>JSON.parse(JSON.stringify(v));

function fixture(){
    const t=[0,1,2].map(h=>Date.parse("2026-11-04T0"+h+":00:00.000Z"));
    const defs=[
      {body:"mercury",lon:[350,355,0],uw:[350,355,360],lat:0,dist:1},
      {body:"venus",lon:[10,15,90],uw:[10,15,90],lat:0,dist:2}
    ];
    const series=defs.map(d=>({
      body:d.body,
      samples:t.map((unix_ms,i)=>({
        unix_ms,time_utc:new Date(unix_ms).toISOString(),
        longitude_deg:d.lon[i],unwrapped_longitude_deg:d.uw[i],
        latitude_deg:d.lat,distance_au:d.dist,
        longitude_rate_deg_per_day:1,motion:"direct"
      }))
    }));
    const relationships=[{
      bodies:["mercury","venus"],
      samples:t.map((unix_ms,i)=>({
        unix_ms,time_utc:new Date(unix_ms).toISOString(),
        longitude_separation_deg:Math.abs(
          ((defs[1].lon[i]-defs[0].lon[i]+540)%360)-180),
        aspects:[]
      }))
    }];
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
        bodies:defs.map(d=>d.body)
      },
      sample_count:3,series,relationships,event_markers:[]
    };
}
function get(index=2){
   const model=M.model(fixture());
   assert.equal(model.ready,true,model.reason);
   const verified=N.network(model,index);
   assert.equal(verified.ready,true,verified.reason);
   return {model,verified,result:D.depth(model,index,verified)};
}

test("V4b reuses exact validated M4 UTC, source and ecliptic coordinates",()=>{
    const {result,verified}=get(),d=plain(result);
    assert.equal(D.FORMAT,"post-apollo.weather.apparent-depth.v4b.v1");
    assert.equal(d.ready,true,d.reason);
    assert.equal(d.frame,"true-ecliptic-of-date");
    assert.equal(d.origin,"geocentric");
    assert.equal(d.positionModel,"apparent");
    assert.equal(d.timeMs,verified.timeMs);
    assert.equal(d.isoUtc,verified.isoUtc);
    assert.equal(d.source,verified.source);
    assert.equal(d.hash,verified.hash);
    assert.equal(d.count,2);
    assert.equal(d.maxDistanceAu,2);
    assert.deepEqual(d.points.map(p=>p.body),["mercury","venus"]);
    assert.deepEqual(d.points.map(p=>p.distance_au),[1,2]);
    assert.ok(Math.abs(d.points[0].x_au-1)<1e-9);
    assert.ok(Math.abs(d.points[0].y_au)<1e-9);
    assert.ok(Math.abs(d.points[1].x_au)<1e-9);
    assert.ok(Math.abs(d.points[1].y_au-2)<1e-9);
    assert.ok(Math.abs(d.points[1].z_au)<1e-9);
    assert.match(D.detail(d.points[1]),/2\.000000 AU \/\/ LAT 0\.000° \/\/ LON 90\.000°/);
});

test("V4b spherical vector retains real latitude and AU ray length",()=>{
    for(const [lon,lat,r,expected] of [
       [0,0,1,[1,0,0]],[90,0,2,[0,2,0]],
       [180,0,3,[-3,0,0]],[270,0,2,[0,-2,0]],
       [0,90,4,[0,0,4]],[0,-90,4,[0,0,-4]],
       [0,30,2,[Math.sqrt(3),0,1]]
    ]){
        const v=D.vector(lon,lat,r);
        assert.ok(v!==null);
        [v.x_au,v.y_au,v.z_au].forEach((c,i)=>{
            assert.ok(Math.abs(c-expected[i])<1e-8,
              String(lon)+"/"+String(lat)+"/"+String(r)+" index "+i);
        });
        assert.ok(Math.abs(Math.hypot(v.x_au,v.y_au,v.z_au)-r)<1e-8);
    }
    for(const x of [[-1,0,1],[360,0,1],[0,91,1],
         [0,-91,1],[0,0,0],[0,0,-1],[null,0,1],[0,null,1],
         [0,0,null],[NaN,0,1],[0,0,Infinity]])
        assert.equal(D.vector(...x),null,JSON.stringify(x));
});

test("V4b circles scale linearly to farthest included source distance",()=>{
    const d=get().result,g=D.layout(400,240);
    assert.equal(g.ready,true);
    assert.equal(g.cx,156);
    assert.equal(g.cy,120);
    assert.equal(g.r,98);
    const first=D.projected(d,d.points[0],400,240);
    const second=D.projected(d,d.points[1],400,240);
    assert.ok(Math.abs(first.x-156)<1e-8);
    assert.ok(Math.abs(first.y-71)<1e-8);
    assert.ok(Math.abs(second.x-254)<1e-8);
    assert.ok(Math.abs(second.y-120)<1e-8);
    assert.equal(D.hit(d,first.x,first.y,400,240,10),"mercury");
    assert.equal(D.hit(d,second.x,second.y,400,240,10),"venus");
    assert.equal(D.hit(d,1,1,400,240,10),"");
    assert.equal(D.hit(d,0,0,400,240,-1),"");
    assert.equal(D.byBody(d,"venus").distance_au,2);
    assert.equal(D.byBody(d,"missing"),null);
    assert.equal(D.projected(d,d.points[0],0,0),null);
});

test("V4b rejects missing source, wrong UTC and forged coordinates",()=>{
    const {model,verified}=get();
    assert.equal(D.depth(null,2,verified).ready,false);
    assert.equal(D.depth(model,-1,verified).ready,false);
    assert.equal(D.depth(model,3,verified).ready,false);
    assert.equal(D.depth(model,1,verified).ready,false);
    assert.equal(D.depth({...model,frame:"heliocentric"},2,verified).ready,false);
    assert.equal(D.depth(model,2,{...verified,ready:false}).ready,false);
    assert.equal(D.depth(model,2,{...verified,hash:"tampered"}).ready,false);
    const bad=plain(model);
    bad.series[1].rows[2].distance_au=null;
    assert.equal(D.depth(bad,2,verified).ready,false);
    bad.series[1].rows[2].distance_au=2;
    bad.series[0].rows[2].latitude_deg=99;
    assert.equal(D.depth(bad,2,verified).ready,false);
    bad.series[0].rows[2].latitude_deg=0;
    bad.series[0].rows[2].unix_ms+=1000;
    assert.equal(D.depth(bad,2,verified).ready,false);
    const input=fixture();
    input.query.frame="heliocentric";
    assert.equal(M.model(input).ready,false);
    assert.equal(D.depth(M.model(input),2,verified).ready,false);
});

test("V4b links CHORDS and DEPTH with one MAGICK M4 source owner",()=>{
    assert.match(networkQml,/property string displayMode: "chords"/);
    assert.match(networkQml,/StationCosmosCelestialDepthPane\s*\{/);
    assert.match(networkQml,/graphModel: graph\.graphModel/);
    assert.match(networkQml,/verifiedScene: graph\.scene/);
    assert.match(networkQml,/focusIndex: graph\.focusIndex/);
    assert.match(networkQml,/selectedBody: graph\.selectedBody/);
    assert.match(networkQml,/onClicked: graph\.displayMode="chords"/);
    assert.match(networkQml,/onClicked: graph\.displayMode="depth"/);
    assert.match(networkQml,/enabled: graph\.scene\.ready && graph\.displayMode === "chords"/);
    assert.match(depthQml,/Depth\.depth\(\s*graphModel,focusIndex,verifiedScene\)/);
    assert.match(depthQml,/Depth\.projected\(/);
    assert.match(depthQml,/Depth\.hit\(/);
    assert.match(depthQml,/onClicked: function\(mouse\)/);
    assert.match(depthQml,/depthPane\.bodyPicked\(body\)/);
    assert.match(depthQml,/depthPane\.sampleScrubbed\(originIndex,dx\)/);
    assert.match(depthQml,/depthPane\.zoomRequested\(wheel\.angleDelta\.y>0\?1:-1\)/);
    assert.match(depthQml,/APPARENT GEOCENTRIC/);
    assert.match(depthQml,/NO PHYSICAL ORBITS/);
    assert.match(instrument,/StationCosmosCelestialNetwork\s*\{/);
    assert.match(service,/property var visualData: null/);
    assert.match(station,/WeatherServices\.CelestialVisualService\s*\{/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
    for(const code of [depthQml,v4b]){
        for(const banned of ["Process {","Timer {","FileView {","XMLHttpRequest",
            "new WebSocket","Quickshell.Io","Qt.callLater","swaymsg","fetch("])
            assert.ok(!code.includes(banned),banned);
    }
});
