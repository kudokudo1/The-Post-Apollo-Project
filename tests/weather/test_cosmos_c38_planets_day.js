"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const run=p=>{const ctx=vm.createContext({});
  vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),ctx);
  return ctx;
};
const policy=run("widgets/weather/StationCosmosPlanetEventPolicy.js");
const modes=read("widgets/weather/StationCosmosModesPane.qml");
const day=read("widgets/weather/StationCosmosPlanetsDayPane.qml");
const sky=read("widgets/weather/StationSky.qml");
const source=run("widgets/weather/StationCosmosSubjectPanelPolicy.js");

function example(name,date="2026-11-08"){
 return {name,date,status:"NORMAL",
  rise:"06:14",riseAzimuth:88,
  transit:"12:43",transitAltitude:45,transitHemisphere:"S",
  set:"19:21",setAzimuth:274};
}
test("C38 retains five dated USNO event rows with precision and null gaps",()=>{
 const rows=policy.clockRows([example("MERCURY"),example("SATURN")],"2026-11-08");
 assert.equal(rows.length,5);
 assert.equal(rows[0].events.length,3);
 assert.equal(rows[1].events.length,0);
 assert.equal(rows[4].events[0].minute,374);
 const all=policy.orderedEvents(rows,"ALL","ALL");
 assert.equal(all.length,6);
 assert.equal(policy.orderedEvents(rows,"SATURN","transit").length,1);
 const bad=policy.clockRows([example("MARS","2026-11-09")],"2026-11-08");
 assert.equal(bad[2].available,false);
 assert.equal(policy.eventDetail(all[0]).includes("LOCAL"),true);
});

test("C38 PLANETS has two local views and a link to existing circular CLOCK",()=>{
 assert.match(modes,/property string planetSubmode: "sky"/);
 assert.match(modes,/kind === "planets" \? planetsComposite/);
 assert.match(modes,/id: planetsComposite/);
 assert.match(modes,/objectName: "cosmos-c38-planets-inner-modes"/);
 assert.match(modes,/label: "SKY NOW"/);
 assert.match(modes,/label: "DAY EVENTS"/);
 assert.match(modes,/label: "DAY RING \/\/ CLOCK"/);
 assert.match(modes,/id: planetsSkyComponent\s*StationCosmosDetailPane/);
 assert.match(modes,/kind: "planets"/);
 assert.match(modes,/id: planetsTimelineComponent\s*StationCosmosPlanetsDayPane/);
 assert.match(modes,/datedRows: cosmosModePane\.planetRows/);
 assert.match(modes,/civilDate: cosmosModePane\.civilDate/);
});

test("C38 activates one existing route-scoped USNO service only on DAY EVENTS",()=>{
 assert.match(modes,/cosmosModePane\.kind === "planets"\s*&& cosmosModePane\.planetSubmode === "day"\s*\? "cosmos\/planets-stars\/planet-clock"/);
 assert.match(modes,/kind === "planets" && planetSubmode === "day"/);
 assert.match(modes,/kind === "planets" && planetSubmode === "day"\)\s*\? planetSource/);
 assert.match(modes,/sourceOnly: true/);
 assert.match(sky,/id: planetRiseSetService/);
 assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
 assert.equal(source.needsSource("cosmos/planets-stars/planet-clock","planets"),true);
 assert.equal(source.needsSource("cosmos/planets-stars/celestial-fix","planets"),false);
 assert.equal(source.needsSource("cosmos/planets-stars/celestial-fix","celnav"),true);
 assert.doesNotMatch(day,/UsnoPlanetRiseSetService|StationSky\s*\{|XMLHttpRequest|Process\s*\{|new WebSocket/);
});

test("C38 fixed clipped viewport has five lanes, event focus and bounded zoom/pan",()=>{
 for(const name of ["cosmos-c38-planets-day-events","cosmos-c38-planet-selectors",
  "cosmos-c38-6-12-24-hour-windows","cosmos-c38-five-planet-event-lanes",
  "cosmos-c38-dated-event-track","cosmos-c38-rise-transit-set-controls",
  "cosmos-c38-selected-source-event"])
   assert.ok(day.includes(name),name);
 assert.match(day,/model: Events\.WINDOW_HOURS/);
 assert.match(day,/model: day\.rows/);
 assert.match(day,/model: Events\.visibleEvents\(/);
 assert.match(day,/Events\.viewX\(modelData\.minute/);
 assert.match(day,/Events\.zoomStart\(/);
 assert.match(day,/Events\.panStart\(/);
 assert.match(day,/Events\.revealStart\(/);
 assert.match(day,/Events\.eventDetail\(day\.inspectedEvent\)/);
 assert.match(day,/Events\.stepEvent\(events,inspectedEvent,direction\)/);
 assert.match(day,/clip: true/);
 assert.doesNotMatch(day,/Flickable\s*\{|ScrollView\s*\{|Timer\s*\{|Window\s*\{/);
 const events=policy.clockRows([example("MERCURY")],"2026-11-08")[0].events;
 assert.equal(policy.viewportSpan(6),360);
 assert.equal(policy.viewportSpan(12),720);
 assert.equal(policy.viewportSpan(24),1440);
 assert.equal(policy.rulerTicks(0,1440).length,5);
 assert.equal(policy.visibleEvents({events},"ALL",0,1440).length,3);
 assert.equal(policy.zoomStart(0,1440,360,720),540);
 assert.equal(policy.panStart(540,360,100,400),450);
});
