"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const load=p=>{const c=vm.createContext({});vm.runInContext(
    read(p).replace(/^\.pragma library\s*$/m,""),c);return c;};
const modes=load("widgets/weather/StationCosmosModePolicy.js");
const gates=load("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const details=load("widgets/weather/StationCosmosDetailPolicy.js");
const ui=read("widgets/weather/StationCosmosModesPane.qml");
const strip=read("widgets/weather/StationCosmosPlanetsSkyStrip.qml");
const day=read("widgets/weather/StationCosmosPlanetsDayPane.qml");
const ring=read("widgets/weather/StationCosmosPlanetClockFace.qml");
const sky=read("widgets/weather/StationSky.qml");

test("C39 astronomy main modes are PLANETS and STARS, older CLOCK deep link still works",()=>{
 const names=Array.from(modes.modesFor("cosmos/planets-stars/celestial-fix"),x=>x.label);
 assert.deepEqual(names,["PLANETS","STARS"]);
 assert.equal(modes.kind("cosmos/planets-stars/planet-clock"),"planet-clock");
 assert.equal(modes.family("cosmos/planets-stars/planet-clock"),"astronomy");
 assert.equal(modes.kind("cosmos/planets-stars/celestial-fix"),"planets");
 assert.equal(modes.modesFor("cosmos/planets-stars/planet-clock").length,2);
 assert.ok(ui.includes('label: "DAY EVENTS"'));
 assert.ok(ui.includes('label: "DAY RING"'));
 assert.ok(!ui.includes('label: "DAY RING // CLOCK"'));
});

test("C39 one StationSky source host activates exactly both necessary USNO providers",()=>{
 const path="cosmos/planets-stars/celestial-fix";
 assert.equal(gates.needsSource(path,"planets"),true);
 assert.equal(gates.needsSource(path,"celnav"),true);
 for(const other of ["moon","iss","eclipses","meteor","twilight"])
   assert.equal(gates.needsSource(path,other),false);
 assert.equal((ui.match(/StationSky\s*\{/g)||[]).length,1);
 assert.equal((sky.match(/WeatherServices\.UsnoCelnavService\s*\{/g)||[]).length,1);
 assert.equal((sky.match(/WeatherServices\.UsnoPlanetRiseSetService\s*\{/g)||[]).length,1);
 assert.match(ui,/subjectRoute: Modes\.dataRoute\(cosmosModePane\.subjectRoute \|\| ""\)/);
 assert.doesNotMatch(ui,/planetSubmode === "day"\s*\? "cosmos\/planets-stars\/planet-clock"/);
});

test("C39 DAY RING stays in same PLANETS instrument loader",()=>{
 assert.match(ui,/property string planetSubmode: "day"/);
 assert.match(ui,/sourceComponent: cosmosModePane\.planetSubmode === "ring"\s*\? planetsRingComponent : planetsTimelineComponent/);
 assert.match(ui,/id: planetsRingComponent\s*StationCosmosPlanetClockFace/);
 assert.match(ui,/id: planetsTimelineComponent\s*StationCosmosPlanetsDayPane/);
 assert.match(ui,/compactInPlanets: true/);
 assert.match(ui,/controlledSelection: true/);
 assert.match(ui,/selectedPlanet: cosmosModePane\.planetSelection/);
 assert.match(ui,/onPlanetPicked: function\(name\)/);
 assert.match(day,/signal planetPicked\(string name\)/);
 assert.match(ring,/signal planetPicked\(string name\)/);
 assert.match(day,/if \(!controlledSelection\) selectedPlanet=name/);
 assert.match(ring,/if \(!controlledSelection\) selectedPlanet = name/);
 assert.match(ring,/face\.compactInPlanets \? 0 : 12/);
 assert.match(day,/day\.compactInPlanets \? 55 : 65/);
});

test("C39 SKY NOW stays a single row beneath the stage, all 12 facts are inspectable",()=>{
 assert.match(ui,/StationCosmosPlanetsSkyStrip\s*\{/);
 assert.match(ui,/objectName: "cosmos-c39-fixed-sky-now"/);
 assert.match(ui,/anchors\.bottom: skyNowStrip\.top/);
 assert.match(ui,/height: 38/);
 assert.match(ui,/objectName: "cosmos-c39-sky-detail-overlay"/);
 assert.match(ui,/objectName: "cosmos-c39-close-sky-details"/);
 assert.match(ui,/id: planetsSkyComponent\s*StationCosmosDetailPane/);
 assert.match(ui,/onDetailsRequested: function\(index\)/);
 assert.match(ui,/cosmosModePane\.skyDetailsExpanded = true/);
 assert.match(ui,/onClicked: cosmosModePane\.skyDetailsExpanded = false/);
 assert.match(strip,/readonly property var records: Details\.records\("planets"/);
 assert.match(strip,/readonly property int currentIndex:/);
 assert.match(strip,/readonly property var currentRecord:/);
 assert.match(strip,/text: strip\.selectedName/);
 assert.match(strip,/Details\.degrees\(strip\.currentRecord\.altitude\)/);
 assert.match(strip,/Details\.degrees\(strip\.currentRecord\.azimuth\)/);
 assert.match(strip,/strip\.currentRecord\.direction/);
 assert.match(strip,/strip\.reading\.stamp/);
 assert.match(strip,/sourceNote: reading\.sourceNote/);
 assert.match(strip,/signal planetPicked\(string name\)/);
 assert.match(strip,/signal detailsRequested\(int index\)/);
 for(const name of ["cosmos-c39-sky-prev","cosmos-c39-sky-next","cosmos-c39-sky-details"])
   assert.ok(strip.includes(name),name);
 assert.equal((strip.match(/\bRow\s*\{/g)||[]).length,1);
 for(const forbidden of ["Flickable {","UsnoCelnavService {","StationSky {","Timer {","Process {"])
   assert.ok(!strip.includes(forbidden),forbidden);
 const snapshot={date:"2026-11-08",time:"16:30",
   planets:[{name:"MARS",altitude:37.5,azimuth:203.4,direction:"SSW"}]};
 const records=details.records("planets",snapshot);
 assert.equal(records.length,1);
 const fields=details.fields("planets",records[0],{snapshot});
 assert.equal(fields.length,12);
 assert.equal(fields[0].value,"37.5°");
 assert.equal(fields[1].value,"203.4°");
 assert.equal(fields[2].value,"SSW");
 assert.equal(fields[4].value,"16:30");
 assert.equal(fields[9].value,"NOT VERIFIED");
});

test("C39 never substitutes the civil-day R/T/S times for instantaneous sky positions",()=>{
 assert.match(strip,/celestialSource\.snapshot/);
 assert.match(day,/Events\.visibleEvents\(/);
 assert.match(ring,/Day\.datedEvents\(/);
 assert.doesNotMatch(strip,/currentRecord\.(rise|transit|set)|calculateOrbit\(|ephemeris\(/);
 assert.match(strip,/SOURCE RECEIVING/);
 assert.match(strip,/sourceNote: reading\.sourceNote/);
});
