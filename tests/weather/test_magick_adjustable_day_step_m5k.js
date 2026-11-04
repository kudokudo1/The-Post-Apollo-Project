"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
const code=read("services/weather/CelestialVisualQueryPolicy.js");
const service=read("services/weather/CelestialVisualService.qml");
const pane=read("widgets/weather/StationMagickSubjectPane.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const ctx=vm.createContext({Date,Math,isFinite,JSON});
vm.runInContext(code.replace(/^\.pragma library\s*/m,""),ctx);
const plain=x=>JSON.parse(JSON.stringify(x));

test("the day jump defaults to five days but accepts exact typed values",()=>{
    assert.equal(ctx.DEFAULT_DAY_STEP,5);
    for(const v of [1,5,10,30,365,3650]){
        assert.equal(ctx.parseDayStep(v),v);
        assert.equal(ctx.parseDayStep(String(v)),v);
        assert.equal(ctx.parseDayStep(" "+v+" "),v);
    }
    for(const v of [0,-1,3651,10000,1.5,"5.0","5d","5 days","",
                     "0","01","+5","--5","1e3","5\n6",NaN,
                     Infinity,null,undefined,{},[]])
        assert.equal(ctx.parseDayStep(v),null,String(v));
});

test("minus/plus calibrators change the step only in safe one-day increments",()=>{
    assert.equal(ctx.adjustDayStep(5,-1),4);
    assert.equal(ctx.adjustDayStep(5,1),6);
    assert.equal(ctx.adjustDayStep(1,-1),1);
    assert.equal(ctx.adjustDayStep(3650,1),3650);
    assert.equal(ctx.adjustDayStep(10,1),11);
    assert.equal(ctx.adjustDayStep(30,-1),29);
    assert.equal(ctx.adjustDayStep(0,1),null);
    assert.equal(ctx.adjustDayStep("5",1),null);
    assert.equal(ctx.adjustDayStep(5,5),null);
    assert.equal(ctx.adjustDayStep(5,-5),null);
    assert.equal(ctx.adjustDayStep(5,0),null);
    assert.equal(ctx.adjustDayStep(5,NaN),null);
});

test("5/10/30-day leaps preserve exact UTC dates and offset bounds",()=>{
    const today="2026-11-04";
    for(const step of [1,5,10,30]){
        const forward=ctx.shiftOffset(0,step);
        const backward=ctx.shiftOffset(0,-step);
        assert.equal(forward,step);
        assert.equal(backward,-step);
        const a=Date.parse(ctx.dayFor(today,forward)+"T00:00:00Z");
        const b=Date.parse(ctx.dayFor(today,backward)+"T00:00:00Z");
        const mid=Date.parse(today+"T00:00:00Z");
        assert.equal(a-mid,step*ctx.DAY_MS);
        assert.equal(mid-b,step*ctx.DAY_MS);
    }
    assert.equal(ctx.dayFor("2024-02-28",1),"2024-02-29");
    assert.equal(ctx.dayFor("2026-03-08",5),"2026-03-13");
    assert.equal(ctx.shiftOffset(3649,10),3650);
    assert.equal(ctx.shiftOffset(-3649,-10),-3650);
});

test("changing the calibrator never changes graph span, data contract or source",()=>{
    const a=plain(ctx.requestFor("2026-11-04",0,"moon-sun",29));
    // UI jump steps of different sizes leave the existing M4 request identical
    // until the user actually presses one of the date navigation arrows.
    for(const step of [1,5,10,30,365]){
        assert.equal(ctx.parseDayStep(step),step);
        assert.deepEqual(plain(ctx.requestFor("2026-11-04",0,"moon-sun",29)),a);
    }
    const jumped=plain(ctx.requestFor("2026-11-04",5,"moon-sun",29));
    assert.notEqual(jumped.start_utc,a.start_utc);
    assert.equal(Date.parse(jumped.start_utc)-Date.parse(a.start_utc),
                 5*ctx.DAY_MS);
    assert.equal(jumped.step_hours,12);
    assert.equal((Date.parse(jumped.end_utc)-Date.parse(jumped.start_utc))
                 /ctx.DAY_MS,29);
    assert.deepEqual(jumped.bodies,["moon","sun"]);
    assert.doesNotMatch(service,/dateStepDays.*\+.*currentKey/);
    assert.match(service,/onCurrentKeyChanged: clearState\(\)/);
    assert.match(service,/function jumpDate\(direction\)/);
    assert.match(service,/return shiftDate\(direction\*dateStepDays\)/);
    assert.match(service,/property int dateStepDays: Query\.DEFAULT_DAY_STEP/);
    const routeReset=service.slice(service.indexOf("onRouteChanged:"),
                                   service.indexOf("onCurrentKeyChanged:"));
    assert.doesNotMatch(routeReset,/dateStepDays\s*=/);
    assert.match(service,/function returnToToday\(\) \{ dateOffsetDays=0; \}/);
});

test("compact editor and dynamic arrows are wired into the shared M5c service",()=>{
    assert.match(pane,/id: jumpStepInput/);
    assert.match(pane,/TextInput\s*\{/);
    assert.match(pane,/maximumLength: 4/);
    assert.match(pane,/IntValidator \{ bottom: 1; top: 3650 \}/);
    assert.match(pane,/function applyStep\(\)/);
    assert.match(pane,/source\.setDateStepDays\(text\)/);
    assert.match(pane,/Keys\.onEscapePressed: function\(event\)/);
    assert.match(pane,/Keys\.onUpPressed: function\(event\)/);
    assert.match(pane,/Keys\.onDownPressed: function\(event\)/);
    assert.match(pane,/onDateStepDaysChanged\(\)/);
    assert.match(pane,/jumpStepInput\.activeFocus/);
    assert.match(pane,/magickPane\.celestialSource\.jumpDate\(-1\)/);
    assert.match(pane,/magickPane\.celestialSource\.jumpDate\(1\)/);
    assert.match(pane,/magickPane\.celestialSource\.adjustDateStepDays\(-1\)/);
    assert.match(pane,/magickPane\.celestialSource\.adjustDateStepDays\(1\)/);
    assert.match(pane,/magickPane\.celestialSource\.returnToToday\(\)/);
    assert.match(pane,/magickPane\.celestialSource\.spanDays/);
    assert.match(pane,/contentHeight: Math\.max\(height, 620\)/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
    assert.equal((service.match(/Process\s*\{/g)||[]).length,1);
    for(const banned of ["Process {","Timer {","FileView {",
                         "XMLHttpRequest","curl ","swaymsg"])
        assert.equal(pane.includes(banned),false,banned);
});
