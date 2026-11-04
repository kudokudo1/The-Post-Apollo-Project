"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const hsrc=read("widgets/weather/StationCosmosPlanetHorizonPolicy.js");
const psrc=read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const pane=read("widgets/weather/StationCosmosPlanetHorizonPane.qml");
const parent=read("widgets/weather/StationCosmosPlanetEventClock.qml");
const sky=read("widgets/weather/StationSky.qml");
const h=vm.createContext({}),p=vm.createContext({});
vm.runInContext(hsrc.replace(/^\.pragma library\s*$/m,""),h);
vm.runInContext(psrc.replace(/^\.pragma library\s*$/m,""),p);

const mk=(name)=>({
  name,date:"2026-11-04",status:"NORMAL",
  rise:"06:10",riseAzimuth:90,
  transit:"12:00",transitAltitude:45,
  transitHemisphere:"S",
  set:"18:10",setAzimuth:270
});
const dated=()=>p.clockRows(h.PLANETS.map(name=>mk(name)),"2026-11-04");

test("V3b concentric rings distinguish five planets but never shift bearing",()=>{
  const radii=h.PLANETS.map(name=>h.laneRadius(name,240,240));
  assert.equal(radii.length,5);
  assert.ok(radii.every((r,i)=>r>0 && (i===0 || r>radii[i-1])));
  assert.equal(radii[0],96*0.40);
  assert.equal(radii[4],96);
  assert.equal(h.laneRadius("PLUTO",240,240),null);
  assert.equal(h.laneRadius("VENUS",0,240),null);
  for(const name of h.PLANETS) {
    const north=h.point(0,240,240,name);
    const east=h.point(90,240,240,name);
    const south=h.point(180,240,240,name);
    const west=h.point(270,240,240,name);
    assert.ok(Math.abs(north.x-120)<1e-8,name+" N");
    assert.ok(Math.abs(east.y-120)<1e-8,name+" E");
    assert.ok(Math.abs(south.x-120)<1e-8,name+" S");
    assert.ok(Math.abs(west.y-120)<1e-8,name+" W");
    assert.ok(north.y<120 && east.x>120 && south.y>120 && west.x<120);
  }
  assert.equal(h.point(90,240,240).x,216); // V3a original default.
});

test("All five same-angle events remain selectable on their own ring",()=>{
  const markers=h.markers(dated(),"ALL");
  assert.equal(markers.length,10);
  assert.ok(markers.every(marker=>marker.azimuth===90 || marker.azimuth===270));
  for(const planet of h.PLANETS) {
    for(const kind of ["rise","set"]) {
      const event=markers.find(m=>m.planet===planet && m.kind===kind);
      const point=h.point(event.azimuth,240,240,event.planet);
      const picked=h.pick(markers,point.x,point.y,240,240,8);
      assert.equal(picked && picked.id,event.id,
          planet+" "+kind+" should not be obscured by an adjacent ring");
    }
  }
  assert.equal(h.pick(markers,120,120,240,240,8),null);
});

test("Circular altitude dial is a source-backed 0 to 90 degree fraction",()=>{
  assert.equal(h.altitudeFraction(0),0);
  assert.equal(h.altitudeFraction(22.5),0.25);
  assert.equal(h.altitudeFraction(45),0.5);
  assert.equal(h.altitudeFraction(90),1);
  for(const value of [-1,91,null,"",undefined,Infinity,NaN])
    assert.equal(h.altitudeFraction(value),null,String(value));
  const actual=h.transits(dated());
  assert.equal(actual.length,5);
  assert.ok(actual.every(a=>h.altitudeFraction(a.altitude)===0.5));
  const absent=mk("VENUS");absent.transitAltitude=null;
  const rows=p.clockRows([absent],"2026-11-04");
  assert.equal(h.altitudeFraction(h.transits(rows)[1].altitude),null);
  const wrong=mk("MARS");wrong.date="2026-11-03";
  const off=p.clockRows([wrong],"2026-11-04");
  assert.equal(h.altitudeFraction(h.transits(off)[2].altitude),null);
});

test("V3b QML draws five real lanes and clickable circular data dials",()=>{
  assert.match(pane,/for\(let ring=0;ring<Horizon\.PLANETS\.length;ring\+\+\)/);
  assert.match(pane,/Horizon\.laneRadius\(planet,w,h\)/);
  assert.match(pane,/Horizon\.point\(marker\.azimuth,w,h,marker\.planet\)/);
  assert.match(pane,/Horizon\.pick\(/);
  assert.match(pane,/width,height,8\)/);
  assert.match(pane,/height: 194/);
  assert.match(pane,/height: 73/);
  assert.match(pane,/Horizon\.altitudeFraction\(/);
  assert.match(pane,/Canvas\s*\{/);
  assert.match(pane,/onClicked: horizonPane\.planetPicked\(\s*transitCard\.modelData\.planet\)/);
  assert.match(pane,/RING DEPTH IS DISPLAY ONLY, NOT DISTANCE/);
  assert.match(pane,/NO PLANET TRACK OR ECLIPTIC ALIGNMENT IMPLIED/);
  assert.match(parent,/StationCosmosPlanetHorizonPane\s*\{/);
  assert.match(parent,/height: 414/);
  assert.match(sky,/providerRows: planetRiseSetService\.rows/);
  assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
  for(const file of [pane,hsrc])for(const banned of [
    "Process {","Timer {","FileView {","XMLHttpRequest","new WebSocket",
    "UsnoPlanetRiseSetService {","zodiacLongitude","swaymsg"])
      assert.ok(!file.includes(banned),banned);
});
