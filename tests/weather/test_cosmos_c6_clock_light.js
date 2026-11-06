"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function run(p) {
 const context=vm.createContext({});
 vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),context);
 return context;
}
const light=run("widgets/weather/StationCosmosLightDetailPolicy.js");
const clock=run("widgets/weather/StationCosmosPlanetEventPolicy.js");
const clockQml=read("widgets/weather/StationCosmosClockCompactPane.qml");
const lightQml=read("widgets/weather/StationCosmosLightDetailPane.qml");
const modes=read("widgets/weather/StationCosmosModesPane.qml");

test("four fixed solar-light modes preserve the legacy complete calibrated field set",()=>{
 const t={astronomicalDawn:"04:45",nauticalDawn:"05:15",civilDawn:"05:45",
    solarNoon:"12:00",civilDusk:"18:30",nauticalDusk:"19:00",
    astronomicalDusk:"19:30",
    blueMorningStart:"05:25",blueMorningEnd:"05:45",
    goldenMorningStart:"06:00",goldenMorningEnd:"06:45",
    goldenEveningStart:"17:15",goldenEveningEnd:"18:00",
    blueEveningStart:"18:30",blueEveningEnd:"18:50"};
 const a={sunrise:"06:20",sunset:"18:15",daylightLabel:"11H 55M"};
 const day=light.rows("DAY",t,a),dawn=light.rows("DAWN",t,a);
 const dusk=light.rows("DUSK",t,a),photo=light.rows("PHOTO",t,a);
 assert.equal(day.length+dawn.length+dusk.length+photo.length,16);
 assert.equal(dawn[1].value,"05:15");
 assert.equal(dusk[2].value,"19:00");
 assert.equal(dusk[3].value,"19:30");
 assert.equal(day[3].value,"11H 55M");
 assert.equal(photo[3].value,"18:30 → 18:50");
});

test("USNO supports bounded event zoom, kind filter, panning, source-specific angles",()=>{
 const rows=clock.clockRows([{name:"MERCURY",date:"2026-11-06",
  status:"NORMAL",rise:"06:15",transit:"12:00",set:"18:20",
  riseAzimuth:110,transitAltitude:60,transitHemisphere:"N",setAzimuth:250}],
  "2026-11-06");
 assert.equal(rows.length,5);
 assert.equal(rows[0].events.length,3);
 assert.equal(clock.viewportSpan(12),720);
 assert.equal(clock.orderedEvents(rows,"MERCURY","transit").length,1);
 const next=clock.stepEvent(clock.orderedEvents(rows,"ALL","ALL"),null,1);
 assert.equal(next.kind,"rise");
 assert.equal(next.azimuth,110);
 assert.equal(next.altitude,null);
 assert.equal(clock.panStart(300,720,150,300),0);
 assert.ok(clock.viewX(375,0,720,300,9)>0);
 assert.equal(clock.viewX(1100,0,720,300,9),null);
});

test("focused SUN LIGHT and ASTRONOMY CLOCK use real sources and stationary submode controls",()=>{
 assert.match(modes,/StationCosmosClockCompactPane\s*\{/);
 assert.match(modes,/clockRows: cosmosModePane\.planetRows/);
 assert.match(modes,/sourcePrecision: cosmosModePane\.planetSource/);
 assert.match(modes,/StationCosmosLightDetailPane\s*\{/);
 assert.match(modes,/twilight: cosmosModePane\.twilight/);
 for(const marker of [
   'objectName: "cosmos-c6-planet-clock"',
   "function setWindow(hours)", "function stepEvent(direction)",
   "Events.viewX(eventData.minute", "Events.panStart(",
   'objectName: "cosmos-c6-clock-fact"',
   'objectName: "cosmos-c5-planet-event-marker"'
 ]) assert.ok(clockQml.includes(marker),marker);
 assert.match(lightQml,/id: fieldRepeater/);
 assert.match(lightQml,/Light\.MODES/);
 for(const file of [clockQml,lightQml])
   for(const forbidden of ["Process {","FileView {","Flickable {","XMLHttpRequest","Timer {"])
     assert.ok(!file.includes(forbidden),forbidden);
});
