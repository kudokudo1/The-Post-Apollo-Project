"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const source=read("widgets/weather/StationCosmosPlanetDayWheelPolicy.js");
const clockSource=read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const ringQml=read("widgets/weather/StationCosmosPlanetDayWheel.qml");
const parent=read("widgets/weather/StationCosmosPlanetEventClock.qml");
const horizon=read("widgets/weather/StationCosmosPlanetHorizonPane.qml");
const sky=read("widgets/weather/StationSky.qml");
const P=vm.createContext({}),D=vm.createContext({});
vm.runInContext(clockSource.replace(/^\.pragma library\s*$/m,""),P);
vm.runInContext(source.replace(/^\.pragma library\s*$/m,""),D);
const plain=value=>JSON.parse(JSON.stringify(value));

function raw(name,date="2026-11-04"){
  return {name,date,status:"NORMAL",
          rise:"00:00",riseAzimuth:90,
          transit:"06:00",transitAltitude:45,transitHemisphere:"S",
          set:"12:00",setAzimuth:270};
}
function projected(){
  return P.clockRows(["MERCURY","VENUS","MARS","JUPITER","SATURN"]
    .map(name=>raw(name)),"2026-11-04");
}
const events=()=>D.datedEvents(P.orderedEvents(projected(),"ALL","ALL"),
  "2026-11-04");

test("V3d clock angle is real 00/06/12/18 LOCAL time, not azimuth",()=>{
  assert.equal(D.FORMAT,"post-apollo.weather.cosmos-day-wheel.v3d.v1");
  for(const [minute,angle] of [
      [0,0],[360,Math.PI/2],[720,Math.PI],[1080,Math.PI*1.5]]) {
    assert.ok(Math.abs(D.timeAngle(minute)-angle)<1e-9);
  }
  for(const bad of [-1,1440,NaN,Infinity,"",null,30.5])
    assert.equal(D.timeAngle(bad),bad===null||bad===""?0:null,
      String(bad)); // empty-like primitive Number() compatibility
  assert.equal(D.timeLabel(0),"00:00");
  assert.equal(D.timeLabel(360),"06:00");
  assert.equal(D.timeLabel(720),"12:00");
  assert.equal(D.timeLabel(1080),"18:00");
  assert.equal(D.timeLabel(1440),"24:00");
  assert.equal(D.timeLabel(-1),"--:--");
});

test("Five categorical circles separate simultaneous planet events",()=>{
  const g=D.geometry(240,240);
  assert.equal(g.radius,97);
  const rings=D.PLANETS.map(name=>D.ringRadius(name,240,240));
  assert.equal(rings.length,5);
  assert.ok(rings.every((radius,i)=>radius>0&&(i===0||radius>rings[i-1])));
  assert.equal(rings.at(-1),97);
  assert.equal(D.ringRadius("PLUTO",240,240),null);
  assert.equal(D.ringRadius("VENUS",0,240),null);
  const all=events();
  assert.equal(all.length,15);
  assert.equal(D.countKind(all,"rise"),5);
  assert.equal(D.countKind(all,"transit"),5);
  assert.equal(D.countKind(all,"set"),5);
  assert.equal(D.countKind(all,"aspects"),0);
  for(const event of all){
    const pt=D.point(event,240,240);
    assert.ok(pt!==null);
    const hit=D.pick(all,pt.x,pt.y,240,240,8);
    assert.equal(hit&&hit.id,event.id,
       event.planet+" "+event.kind+" same-time circle hit");
  }
  assert.equal(D.pick(all,120,120,240,240,8),null);
  assert.equal(D.pick(all,300,300,240,240,8),null);
  assert.equal(D.pick(all,120,120,240,240,0),null);
});

test("Clicking the empty circular lane selects the matching planet",()=>{
  for(const planet of D.PLANETS){
    const radius=D.ringRadius(planet,240,240);
    assert.equal(D.pickRing(120+radius,120,240,240,5),planet);
  }
  assert.equal(D.pickRing(120,120,240,240,5),"");
  assert.equal(D.pickRing(0,0,240,240,5),"");
  assert.equal(D.pickRing(120,120,0,240,5),"");
  assert.equal(D.pickRing(120,120,240,240,-1),"");
});

test("Source gates reject wrong date, damaged minute and forged provenance",()=>{
  const all=plain(events());
  assert.equal(D.datedEvents(all,"2026-11-04").length,15);
  assert.equal(D.datedEvents(all,"2026-11-03").length,0);
  assert.equal(D.datedEvents(all,"2026-02-30").length,0);
  const forged=plain(all);
  forged[0].minute=2; // clock still 00:00
  forged[1].source="UNVERIFIED";
  forged[2].clock="25:00";
  forged[3].date="2026-11-03";
  forged[4].id="";
  forged[5].planet="PLUTO";
  forged[6].kind="aspect";
  assert.equal(D.datedEvents(forged,"2026-11-04").length,8);
  assert.equal(D.datedEvents({0:all[0],length:100},"2026-11-04").length,0);
  assert.equal(D.datedEvents("not a list","2026-11-04").length,0);
  const wrongRows=P.clockRows([raw("MERCURY","2026-11-03")],"2026-11-04");
  assert.equal(D.datedEvents(P.orderedEvents(wrongRows,"ALL","ALL"),
    "2026-11-04").length,0);
  const unavailable=raw("MERCURY");
  unavailable.status="CONTINUOUSLY BELOW HORIZON";
  const refused=P.clockRows([unavailable],"2026-11-04");
  assert.equal(D.datedEvents(P.orderedEvents(refused,"ALL","ALL"),
    "2026-11-04").length,0);
});

test("QML indexed-list and chronological event stepping stay available",()=>{
  const all=events(),variant={length:all.length};
  all.forEach((v,i)=>{variant[i]=v});
  assert.equal(Array.isArray(variant),false);
  assert.equal(D.datedEvents(variant,"2026-11-04").length,15);
  assert.equal(D.ordinal(all,all[0]),"1/15");
  assert.equal(D.ordinal(all,all.at(-1)),"15/15");
  assert.equal(D.ordinal(all,null),"—/15");
  const next=P.stepEvent(all,all[0],1);
  assert.equal(next.clock,"00:00");
  assert.notEqual(next.id,all[0].id);
  assert.equal(P.stepEvent(all,all.at(-1),1).id,all[0].id);
});

test("V3d creates genuine clickable ring and preserves existing source owner",()=>{
  assert.match(ringQml,/Day\.datedEvents\(/);
  assert.match(ringQml,/PlanetPolicy\.orderedEvents\(/);
  assert.match(ringQml,/Day\.ringRadius\(/);
  assert.match(ringQml,/Day\.point\(/);
  assert.match(ringQml,/Day\.pick\(/);
  assert.match(ringQml,/Day\.pickRing\(/);
  assert.match(ringQml,/onClicked: dayWheel\.planetPicked\(/);
  assert.match(ringQml,/onClicked: dayWheel\.kindPicked\(/);
  assert.match(ringQml,/onClicked: dayWheel\.lockedEvent=PlanetPolicy\.stepEvent\(/);
  assert.match(ringQml,/onClicked: dayWheel\.returnToTimeline\(\)/);
  assert.match(ringQml,/onClicked: dayWheel\.showHorizon\(\)/);
  assert.match(ringQml,/height: 414/);
  assert.match(ringQml,/ANGLE IS TIME, RADIUS IS PLANET/);
  assert.match(ringQml,/NO PLANET TRACKS, SKY POSITIONS OR ASPECTS/);
  assert.match(parent,/StationCosmosPlanetDayWheel\s*\{/);
  assert.match(parent,/onDayRingRequested: clock\.displayMode = "dayRing"/);
  assert.match(parent,/onKindPicked: function\(kind\) \{ clock\.selectedKind = kind; \}/);
  assert.match(horizon,/signal dayRingRequested\(\)/);
  assert.match(parent,/height: 414/);
  assert.match(sky,/providerRows: planetRiseSetService\.rows/);
  assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
  for(const code of [source,ringQml])for(const banned of [
    "Process {","Timer {","FileView {","XMLHttpRequest",
    "new WebSocket","UsnoPlanetRiseSetService {",
    "zodiacLongitude","Qt.callLater","swaymsg","fetch("
  ])assert.ok(!code.includes(banned),banned);
});
