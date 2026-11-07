"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(p){
    const ctx=vm.createContext({});
    vm.runInContext(read(p).replace(/^\.pragma library\s*/,""),ctx);
    return ctx;
}
const Browse=policy("widgets/weather/StationMagickTransitEventBrowserPolicy.js");
const Multi=policy("widgets/weather/StationMagickTransitMultiPolicy.js");
function mockModel(){
    const start=Date.parse("2026-11-07T00:00:00Z");
    const events=Array.from({length:29},(_,i)=>{
        const t=new Date(start+i*3*3600000).toISOString().slice(0,19)+"Z";
        if(i%7===3)return {
            utc:t,ms:Date.parse(t),type:"station",transit_body:"mercury",
            natal_body:"sun",aspect:"",degrees:null,
            direction:i%2?"retrograde":"direct",
            residual_deg:null,longitude_deg:100+i,
            velocity_deg_day:0.00001
        };
        return {
            utc:t,ms:Date.parse(t),type:"aspect",
            transit_body:i%2?"venus":"moon",natal_body:"sun",
            aspect:i%3===0?"square":"sextile",degrees:i%3===0?90:60,
            direction:i%2?"retrograde":"prograde",
            residual_deg:0.00002,longitude_deg:null,velocity_deg_day:null
        };
    });
    return {ready:true,series:[{id:"moon"},{id:"venus"},{id:"mercury"}],
        events};
}
test("M8j pages a bounded chronological JPL event list without mutating model",()=>{
    const model=mockModel(),snapshot=JSON.stringify(model);
    const first=Browse.page(model,"ALL","",false,"ALL","ALL",0);
    assert.equal(first.total,29);
    assert.equal(first.pages,3);
    assert.equal(first.index,0);
    assert.equal(first.items.length,12);
    assert.equal(first.first,1);
    assert.equal(first.last,12);
    assert.equal(Browse.page(model,"ALL","",false,"ALL","ALL",1).items.length,12);
    const last=Browse.page(model,"ALL","",false,"ALL","ALL",2);
    assert.equal(last.items.length,5);
    assert.equal(last.first,25);
    assert.equal(last.last,29);
    assert.equal(Browse.page(model,"ALL","",false,"ALL","ALL",100).index,2);
    assert.equal(Browse.page(model,"ALL","",false,"ALL","ALL",-4).index,0);
    assert.equal(Browse.page(model,"ALL","",true,"ALL","ALL",0).items[0].utc,
        model.events[28].utc);
    assert.equal(JSON.stringify(model),snapshot,"browser changed source data");
});
test("M8j aspect/motion filters are source-derived; stations remain visible in ALL mode",()=>{
    const model=mockModel();
    const stations=Browse.filtered(model,"station","",false,"ALL","ALL");
    assert.ok(stations.length>0);
    assert.ok(stations.every(e=>e.type==="station"));
    const squares=Browse.filtered(model,"aspect","",false,"square","ALL");
    assert.ok(squares.length>0);
    assert.ok(squares.every(e=>e.aspect==="square"));
    const combined=Browse.filtered(model,"ALL","",false,"square","ALL");
    assert.ok(combined.some(e=>e.type==="station"));
    assert.ok(combined.some(e=>e.type==="aspect"&&e.aspect==="square"));
    const retrograde=Browse.filtered(model,"ALL","",false,"ALL","retrograde");
    assert.ok(retrograde.every(e=>e.direction==="retrograde"));
    const perPlanet=Browse.filtered(model,"ALL","moon",false,"ALL","ALL");
    assert.ok(perPlanet.every(e=>e.transit_body==="moon"));
    assert.equal(Browse.filtered(model,"ALL","fake",false,"ALL","ALL").length,0);
    assert.equal(Browse.filtered(model,"fake","",false,"ALL","ALL").length,0);
    assert.equal(Browse.filtered(model,"ALL","",false,"bad","ALL").length,0);
    assert.equal(Browse.filtered(model,"ALL","",false,"ALL","bad").length,0);
});
test("M8j pagination handles zero matches and partial source safely",()=>{
    const model=mockModel();
    assert.deepEqual(JSON.parse(JSON.stringify(Browse.page(model,
        "station","moon",false,"ALL","ALL",3))),{
        ready:true,index:0,pages:1,total:0,first:0,last:0,items:[]});
    assert.equal(Browse.page(null,"ALL","",false,"ALL","ALL",0).ready,false);
    assert.equal(Browse.inspect(null,"anything"),null);
    assert.equal(Browse.inspect({ready:false,events:model.events},"anything"),null);
    assert.equal(Browse.nextOption(Browse.ASPECTS,"ALL"),"conjunction");
    assert.equal(Browse.nextOption(Browse.ASPECTS,"opposition"),"ALL");
    assert.equal(Browse.nextOption(Browse.MOTIONS,"stationary"),"ALL");
});
test("M8j inspector preserves exact UTC, angle residual and bounded station method",()=>{
    const model=mockModel();
    const a=model.events.find(e=>e.type==="aspect");
    const s=model.events.find(e=>e.type==="station");
    const aspect=Browse.inspect(model,Browse.eventKey(a));
    assert.equal(aspect.type,"aspect");
    assert.equal(aspect.utc,a.utc);
    assert.equal(aspect.planet,a.transit_body);
    assert.equal(aspect.aspect,a.aspect);
    assert.equal(aspect.residual_deg,a.residual_deg);
    assert.equal(aspect.numerical_bracket_seconds,1);
    assert.equal(aspect.exact_astronomical_time,false);
    const station=Browse.inspect(model,Browse.eventKey(s));
    assert.equal(station.type,"station");
    assert.equal(station.direction,s.direction);
    assert.equal(station.velocity_deg_day,s.velocity_deg_day);
    assert.equal(station.numerical_bracket_seconds,60);
    assert.equal(Browse.inspect(model,"invented"),null);
});
test("M8j QML preserves old wheel click; INFO is explicitly separate and does not call Python",()=>{
    const pane=read("widgets/weather/StationMagickTransitMultiPane.qml");
    const service=read("services/weather/CelestialTransitMultiService.qml");
    assert.match(pane,/StationMagickTransitEventBrowserPolicy\.js" as Browser/);
    assert.match(pane,/Browser\.filtered\(/);
    assert.match(pane,/Browser\.page\(/);
    assert.match(pane,/Browser\.inspect\(/);
    assert.match(pane,/property int pageIndex:0/);
    assert.match(pane,/id:advancedFilters/);
    assert.match(pane,/id:pageControls/);
    assert.match(pane,/model:atlas\.pageData\.items/);
    assert.match(pane,/label:"PREV"/);
    assert.match(pane,/label:"NEXT"/);
    assert.match(pane,/label:"INFO"/);
    assert.match(pane,/onClicked:atlas\.inspectEvent\(modelData\)/);
    assert.match(pane,/onClicked:atlas\.chooseEvent\(modelData\)/);
    assert.match(pane,/NUMERICAL BRACKET ≤60S/);
    assert.match(pane,/NUMERICAL BRACKET ≤1S/);
    assert.match(pane,/atlas\.goPage\(-1\)/);
    assert.match(pane,/atlas\.goPage\(1\)/);
    assert.match(pane,/function resetBrowse\(\)/);
    assert.match(pane,/onBrowserMotionChanged:resetBrowse\(\)/);
    assert.match(pane,/onBrowserAspectChanged:resetBrowse\(\)/);
    assert.match(pane,/signal eventRequested\(string exactUtc,string body,string kind\)/);
    assert.match(service,/stdinEnabled:true/);
    for(const forbidden of ["Process {","XMLHttpRequest","FileView {",
        "localStorage","Qt.openUrlExternally","writeFile(","console.log(",
        "Date.now()","Math.random("]){
        assert.ok(!pane.includes(forbidden),"UI side effect "+forbidden);
    }
});
