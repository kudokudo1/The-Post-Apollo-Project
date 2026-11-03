"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("widgets/weather/StationCosmosVisualPolicy.js");
const qml=read("widgets/weather/StationCosmosVisualInstruments.qml");
const sky=read("widgets/weather/StationSky.qml");
const button=read("components/ActionButton.qml");
const solar=read("widgets/weather/StationSkyTwilightPolicy.js");
const p=vm.createContext({}),sun=vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*$/m,""),p);
vm.runInContext(solar.replace(/^\.pragma library\s*$/m,""),sun);

test("eight Moon markers now have unique short labels and actual button handlers",()=>{
  assert.equal(p.PHASES.length,8);
  assert.equal(new Set(p.PHASES.map(x=>x.short)).size,8);
  assert.ok(p.PHASES.every(x=>x.short.length===2));
  assert.match(qml,/id: phaseButtonRow/);
  assert.match(qml,/model: VisualPolicy\.PHASES/);
  assert.match(qml,/delegate: ActionButton\s*\{/);
  assert.match(qml,/label: modelData\.short/);
  assert.match(qml,/onClicked: visual\.inspectedPhaseId = modelData\.id/);
  assert.match(qml,/selected: visual\.inspectedPhaseId !== ""/);
  assert.match(button,/signal clicked\(var mouseEvent\)/);
});

test("Moon selection opens reference text but cannot overwrite real source data",()=>{
  for(const phase of p.PHASES){
    const info=p.phaseReference(phase.id);
    assert.equal(info.valid,true);
    assert.equal(info.isReference,true);
    assert.ok(info.description.length>25);
  }
  assert.equal(p.phaseReference("unknown").valid,false);
  const current=p.moonDisplay(true,{
    available:true,phase:"WAXING GIBBOUS",
    illumination:71,sourceDate:"2026-11-03"
  },null);
  const other=p.phaseReference("waning-crescent");
  assert.equal(current.illumination,71);
  assert.equal(current.phaseId,"waxing-gibbous");
  assert.equal(other.id,"waning-crescent");
  assert.match(qml,/VisualPolicy\.phaseReference\(/);
  assert.match(qml,/REFERENCE \/\/ /);
  assert.match(qml,/label: "CURRENT"/);
  assert.match(qml,/onClicked: visual\.inspectedPhaseId = ""/);
  assert.match(qml,/anchors\.fill: moonCanvas/);
  assert.match(qml,/visual\.inspectedPhaseId === visual\.moonData\.phaseId/);
  assert.match(qml,/CURRENT PHASE UNAVAILABLE/);
});

test("Sun plot accepts pointer control inside scrolling SKY page",()=>{
  assert.match(qml,/anchors\.fill: solarCanvas/);
  assert.match(qml,/preventStealing: true/);
  assert.match(qml,/hoverEnabled: true/);
  assert.match(qml,/onPositionChanged: function\(mouse\)/);
  assert.match(qml,/onPressed: function\(mouse\)/);
  assert.match(qml,/onClicked: function\(mouse\)/);
  assert.match(qml,/visual\.lockedMinute=Math\.max\(/);
  assert.match(qml,/onClicked: visual\.lockedMinute=-1/);
});

test("Sun 00/06/12/18/NOW actions have real handlers and safe availability",()=>{
  assert.match(qml,/id: solarPresetRow/);
  for(const [id,minute] of [["midnight",0],["morning",360],["noon",720],["evening",1080]]){
    assert.ok(qml.includes('id:"'+id+'"'));
    assert.ok(qml.includes("minute:"+minute));
  }
  assert.match(qml,/id:"now",label:"NOW",minute:-1/);
  assert.match(qml,/available: visual\.solarData\.ready/);
  assert.match(qml,/visual\.providerLocalMinute >= 0/);
  assert.match(qml,/onClicked: \{\s*visual\.lockedMinute = modelData\.id/);
  assert.match(qml,/label: "UNLOCK"/);
  assert.match(qml,/MODEL "/);
});

test("existing civil-time source allows valid Sun model without sunrise-calibration prerequisite",()=>{
  assert.match(sky,/solarDate: sky\.astronomySummary\.date/);
  assert.match(sky,/solarCivilOffsetMinutes: sky\.moonCivilOffsetMinutes/);
  assert.match(sky,/solarOffsetSource: sky\.moonCivilOffsetSource/);
  assert.match(qml,/solarDate,latitude,longitude,solarCivilOffsetMinutes/);
  const arc=p.solarArc("2026-11-03",39,-77,-300,
    (minute,date,lat,lon,offset)=>sun.solarPosition(date,minute,lat,lon,offset));
  assert.equal(arc.ready,true);
  assert.equal(arc.rows.length,73);
  assert.ok(arc.rows.some(x=>x.altitude>0));
  assert.ok(arc.rows.some(x=>x.altitude<0));
  assert.equal(p.solarUnavailableReason("--",39,-77,-300),"PROVIDER DATE UNAVAILABLE");
  assert.equal(p.solarUnavailableReason("2026-11-03","",-77,-300),"WEATHER LOCATION UNAVAILABLE");
  assert.equal(p.solarUnavailableReason("2026-11-03",39,-77,null),"CIVIL TIME OFFSET UNAVAILABLE");
  assert.match(qml,/VisualPolicy\.solarUnavailableReason\(/);
});

test("source and CLASSIC ownership stay unchanged",()=>{
  assert.match(sky,/visible: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
  assert.match(sky,/height: visible \? 304 : 0/);
  assert.equal((sky.match(/sky\.sectionVisible\("([^"]+)"\)/g)||[]).length,27);
  for(const content of [qml,policy]){
    for(const forbidden of ["Process {","FileView {","WeatherServices.","XMLHttpRequest",
      "Timer {","StationTerminal {","swaymsg","Qt.callLater","new WebSocket"]){
      assert.ok(!content.includes(forbidden),forbidden);
    }
  }
});
