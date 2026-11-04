"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const source = read("widgets/weather/StationCosmosPlanetEventPolicy.js");
const qml = read("widgets/weather/StationCosmosPlanetEventClock.qml");
const sky = read("widgets/weather/StationSky.qml");
const p = vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*$/m, ""), p);

const mk = (name, rise, transit, set) => ({
    name, date:"2026-11-03", status:"NORMAL",
    rise, transit, set,
    riseAzimuth:90, transitAltitude:50, transitHemisphere:"S", setAzimuth:270
});
const projected = () => p.clockRows([
    mk("MERCURY","22:30","03:15","10:00"),
    mk("VENUS","07:45","12:00","19:30"),
    mk("MARS","06:45","11:00","17:45"),
    mk("JUPITER","21:50","02:20","08:30"),
    mk("SATURN","05:55","10:10","16:50")
], "2026-11-03");

test("V2c glyphs remain paired with explicit original planet names", () => {
    assert.equal(p.planetLabel("MERCURY"),"☿ MERCURY");
    assert.equal(p.planetLabel("VENUS"),"♀ VENUS");
    assert.equal(p.planetLabel("MARS"),"♂ MARS");
    assert.equal(p.planetLabel("JUPITER"),"♃ JUPITER");
    assert.equal(p.planetLabel("SATURN"),"♄ SATURN");
    assert.equal(p.planetLabel("UNKNOWN"),"UNKNOWN");
    assert.match(qml, /PlanetPolicy\.planetLabel\(/);
});

test("V2c inspector steps only actual dated source event markers", () => {
    const rows = projected();
    const ordered = p.orderedEvents(rows, "ALL", "ALL");
    assert.equal(ordered.length,15);
    assert.ok(ordered.every(e=>e.date==="2026-11-03" && e.source==="USNO MRST"));
    assert.ok(ordered.every((e,i)=>i===0 || ordered[i-1].minute<=e.minute));
    assert.equal(ordered[0].clock,"02:20");
    assert.equal(ordered[ordered.length-1].clock,"22:30");
    assert.equal(p.stepEvent(ordered,null,1).id,ordered[0].id);
    assert.equal(p.stepEvent(ordered,null,-1).id,ordered.at(-1).id);
    assert.equal(p.stepEvent(ordered,ordered[0],1).id,ordered[1].id);
    assert.equal(p.stepEvent(ordered,ordered[0],-1).id,ordered.at(-1).id);
    assert.equal(p.stepEvent(ordered,ordered.at(-1),1).id,ordered[0].id);
    assert.equal(p.stepEvent(ordered,ordered[1],0),null);
    assert.equal(p.eventOrdinal(ordered,ordered[1]),"2/15");
    assert.equal(p.eventOrdinal(ordered,null),"—/15");
});

test("V2c obeys planet and event-kind filters; special-status planets stay absent",()=>{
    const rows=projected();
    const venusRise=p.orderedEvents(rows,"VENUS","rise");
    assert.equal(venusRise.length,1);
    assert.equal(venusRise[0].clock,"07:45");
    const filtered=p.orderedEvents(rows,"ALL","transit");
    assert.equal(filtered.length,5);
    assert.ok(filtered.every(e=>e.kind==="transit"));
    assert.equal(p.orderedEvents(rows,"PLUTO","ALL").length,0);
    assert.equal(p.stepEvent([],null,1),null);
    assert.equal(p.eventOrdinal([],null),"—/0");
    const broken=p.clockRows([{name:"VENUS",date:"2026-11-03",status:"UNAVAILABLE"}],"2026-11-03");
    assert.equal(p.orderedEvents(broken,"ALL","ALL").length,0);
    const wrongDay=p.clockRows([mk("VENUS","07:45","12:00","19:30")],"2026-11-04");
    assert.equal(p.orderedEvents(wrongDay,"ALL","ALL").length,0);
});

test("V2c native QML keeps original geometry, source owner and real marker actions",()=>{
    assert.match(qml,/readonly property var inspectableEvents: PlanetPolicy\.orderedEvents\(/);
    assert.match(qml,/onClicked: clock\.lockedEvent = PlanetPolicy\.stepEvent\(/);
    assert.match(qml,/PlanetPolicy\.eventOrdinal\(/);
    assert.match(qml,/label: "PREV"/);
    assert.match(qml,/label: "NEXT"/);
    assert.match(qml,/clock\.inspectedEvent\.id/);
    assert.match(qml,/Behavior on scale/);
    assert.match(qml,/preventStealing: true/);
    assert.match(qml,/height: 414/);
    assert.match(sky,/StationCosmosPlanetEventClock\s*\{/);
    assert.match(sky,/providerRows: planetRiseSetService\.rows/);
    for(const banned of [
      "Process {","Timer {","FileView {","UsnoPlanetRiseSetService {",
      "XMLHttpRequest","new WebSocket","zodiacLongitude","onWheel:"
    ]) assert.ok(!qml.includes(banned),banned);
});
