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

function sourcePlanet(date="2026-11-04") {
    return {name:"VENUS",date,status:"NORMAL",
        rise:"00:10",riseAzimuth:90,
        transit:"12:15",transitAltitude:45,transitHemisphere:"S",
        set:"23:50",setAzimuth:260};
}

test("V2d 24h / 12h / 6h views are bounded within one civil day",()=>{
    assert.equal(p.viewportSpan(6),360);
    assert.equal(p.viewportSpan(12),720);
    assert.equal(p.viewportSpan(24),1440);
    assert.equal(p.viewportSpan(7),1440);
    assert.equal(p.clampViewStart(-100,360),0);
    assert.equal(p.clampViewStart(1200,360),1080);
    assert.equal(p.clampViewStart(1200,720),720);
    assert.equal(p.clampViewStart(500,1440),0);
    assert.equal(p.zoomStart(0,1440,720,720),360);
    assert.equal(p.zoomStart(360,720,360,720),540);
    assert.equal(p.zoomStart(540,360,1440,720),0);
    assert.equal(p.zoomStart(0,720,360,0),0);
    assert.equal(p.zoomStart(720,720,360,1440),1080);
});

test("drag pans the chart without shifting provider event times",()=>{
    assert.equal(p.panStart(360,360,100,200),180);
    assert.equal(p.panStart(360,360,-100,200),540);
    assert.equal(p.panStart(0,360,100,200),0);
    assert.equal(p.panStart(1080,360,-100,200),1080);
    assert.equal(p.panStart(360,360,100,0),360);
    const source=sourcePlanet(), rows=p.clockRows([source],"2026-11-04");
    const events=p.eventsFor(rows[1],"ALL");
    assert.deepEqual(events.map(e=>e.clock),["00:10","12:15","23:50"]);
    assert.deepEqual(p.visibleEvents(rows[1],"ALL",540,360).map(e=>e.clock),
       ["12:15"]);
    assert.deepEqual(events.map(e=>e.clock),["00:10","12:15","23:50"]);
    assert.deepEqual(p.visibleEvents(rows[1],"rise",0,360).map(e=>e.clock),
       ["00:10"]);
    assert.equal(p.visibleEvents(rows[1],"set",0,360).length,0);
    assert.equal(p.visibleEvents(rows[1],"ALL",1200,360).length,1);
});

test("labels and hit locations agree with source minute viewport",()=>{
    assert.deepEqual(p.rulerTicks(360,360).map(t=>t.label),
        ["06:00","07:30","09:00","10:30","12:00"]);
    assert.deepEqual(p.rulerTicks(0,1440).map(t=>t.label),
        ["00:00","06:00","12:00","18:00","24:00"]);
    assert.equal(p.localMinuteLabel(1440),"24:00");
    assert.equal(p.localMinuteLabel(-1),"--:--");
    assert.equal(p.viewX(360,360,360,362,20),1);
    assert.equal(p.viewX(540,360,360,362,20),171);
    assert.equal(p.viewX(720,360,360,362,20),null);
    assert.equal(p.viewX(0,360,360,362,20),null);
    assert.equal(p.viewX(1439,1080,360,362,20)>330,true);
    assert.equal(p.viewX(100,0,360,15,20),null);
    assert.equal(p.inWindow(1439,1080,360),true);
    assert.equal(p.inWindow(1440,1080,360),false);
});

test("stepping to offscreen event reveals it without fake samples",()=>{
    assert.equal(p.revealStart(600,540,360),540);
    assert.equal(p.revealStart(100,540,360),0);
    assert.equal(p.revealStart(1430,540,360),1080);
    assert.equal(p.revealStart(null,540,360),540);
    const rows=p.clockRows([sourcePlanet()],"2026-11-04");
    const all=p.orderedEvents(rows,"VENUS","ALL");
    const next=p.stepEvent(all,all[1],1);
    const view=p.revealStart(next.minute,540,360);
    assert.equal(next.clock,"23:50");
    assert.ok(p.inWindow(next.minute,view,360));
    assert.equal(all.length,3);
    const wrongDate=p.clockRows([sourcePlanet("2026-11-03")],"2026-11-04");
    assert.equal(p.visibleEvents(wrongDate[1],"ALL",0,1440).length,0);
    assert.equal(p.visibleEvents({events:[]},"ALL",0,1440).length,0);
});

test("QML exposes actual wheel/drag gestures and bounded viewport presets",()=>{
    assert.match(qml,/property int windowHours: 24/);
    assert.match(qml,/readonly property var viewTicks: PlanetPolicy\.rulerTicks\(/);
    assert.match(qml,/PlanetPolicy\.visibleEvents\(/);
    assert.match(qml,/PlanetPolicy\.viewX\(/);
    assert.match(qml,/PlanetPolicy\.panStart\(/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/onPositionChanged: function\(mouse\)/);
    assert.match(qml,/clock\.wheelZoom\(/);
    assert.match(qml,/clock\.setWindow\(/);
    assert.match(qml,/onLockedEventChanged/);
    assert.match(qml,/PlanetPolicy\.revealStart\(/);
    assert.match(qml,/NO MOTION BETWEEN EVENTS/);
    assert.match(qml,/height: 414/);
    assert.match(sky,/StationCosmosPlanetEventClock\s*\{/);
    assert.match(sky,/height: visible \? 414 : 0/);
    for(const forbidden of [
        "Process {","Timer {","FileView {","UsnoPlanetRiseSetService {",
        "XMLHttpRequest","new WebSocket","zodiacLongitude"
    ]) assert.ok(!qml.includes(forbidden),forbidden);
});
