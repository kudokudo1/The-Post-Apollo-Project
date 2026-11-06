"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const ctx=vm.createContext({});
vm.runInContext(read("widgets/weather/StationCosmosSolarDetailPolicy.js")
    .replace(/^\.pragma library\s*$/m,""),ctx);
const pane=read("widgets/weather/StationCosmosSunInstrumentPane.qml");
const fixture=read("tests/weather/fixtures/C6SolarNativeShell.qml");

test("NOAA monthly model ranges and outlook retain every published summary field",()=>{
 const s={modelMonth:"2026-11",targetMonth:"2026-11",exactMonth:true,
    predictedSsn:82.5,predictedFlux:121.1,lowSsn:75,highSsn:90,
    ssnRangeValid:true,lowFlux:115,highFlux:131,fluxRangeValid:true,
    nextMonth:"2026-12",nextPredictedSsn:81.7,
    peakMonth:"2025-03",peakPredictedSsn:163.1,rowCount:108};
 assert.equal(ctx.cyclePage(s,0)[1].value,"82.5");
 assert.equal(ctx.cyclePage(s,1)[0].value,"75.0 - 90.0");
 assert.equal(ctx.cyclePage(s,1)[1].value,"115.0 - 131.0");
 assert.equal(ctx.cyclePage(s,1)[2].value,"YES");
 assert.equal(ctx.cyclePage(s,2)[1].value,"81.7");
 assert.equal(ctx.cyclePage(s,2)[2].value,"163.1");
 s.ssnRangeValid=false;
 assert.equal(ctx.cyclePage(s,1)[0].value,"INVALID SOURCE RANGE");
 s.exactMonth=false;
 assert.equal(ctx.cyclePage(s,1)[2].value,"NO // NEAREST");
});

test("all returned NOAA flare peaks can be inspected with begin/peak/end and flux",()=>{
 const source={ready:true,events:[
    {classLabel:"M1.2",satellite:"GOES-19",beginUtc:"11:00Z",
       peakUtc:"11:10Z",endUtc:"11:25Z",ended:true,flux:0.000012},
    {classLabel:"C4.1",satellite:"GOES-18",beginUtc:"12:00Z",
       peakUtc:"12:20Z",endUtc:"12:30Z",ended:false,flux:0.0000041}]};
 assert.equal(ctx.flareCount(source),2);
 assert.equal(ctx.flareAt(source,1).classLabel,"C4.1");
 assert.equal(ctx.flarePage(source.events[0],0)[2].value,"11:00Z");
 assert.equal(ctx.flarePage(source.events[0],1)[0].value,"11:25Z");
 assert.equal(ctx.flarePage(source.events[0],1)[1].value,"0.000012000");
 assert.equal(ctx.flarePage(source.events[1],1)[2].value,"NO");
 assert.equal(ctx.flareAt({ready:false,events:source.events},0),null);
});

test("GOES X-ray diagnostics use actual source fields and distinguish stale",()=>{
 const src={fluxLong:0.00000231,fluxShort:0.00000042,
    classEquivalent:{label:"C2.3"},satellite:"GOES-19",
    sampleUtc:"2026-11-06 05:15Z",sampleFresh:true,
    trend:[1,2,3],ready:true,loading:false,failed:false};
 assert.equal(ctx.xrayPage(src,0)[0].value,"0.000002310 W/M²");
 assert.equal(ctx.xrayPage(src,0)[3].value,"GOES-19");
 assert.equal(ctx.xrayPage(src,1)[0].value,"2026-11-06 05:15Z");
 assert.equal(ctx.xrayPage(src,1)[1].value,"CURRENT");
 src.sampleFresh=false;src.failed=true;
 assert.equal(ctx.xrayPage(src,1)[1].value,"STALE OR UNKNOWN");
 assert.equal(ctx.xrayPage(src,1)[3].value,"FAILED // CHECK SOURCE");
 assert.equal(ctx.num(-1,2),"--");
});

test("SUN remains one instrument, one legacy source, and no scroll; native fixture validates rendered cells",()=>{
 for(const value of ["solarFocus.xrayPage","solarFocus.flareIndex","solarFocus.flareDataPage",
   "solarFocus.cyclePage","cosmos-c6-xray-detail","cosmos-c6-flare-detail",
   "cosmos-c6-cycle-detail","focusedSuviImage","solarFocus.sourceSpace"])
   assert.ok(pane.includes(value),value);
 for(const forbidden of ["Flickable {","Process {","FileView {","XMLHttpRequest"])
   assert.ok(!pane.includes(forbidden),forbidden);
 for(const marker of ["XRAY_DIAGNOSTICS_NOT_VISIBLE","FLARE_FULL_EVENT_NOT_VISIBLE",
   "CYCLE_PUBLISHED_RANGES_MISSING","CYCLE_OUTLOOK_MISSING"])
   assert.ok(fixture.includes(marker),marker);
});
