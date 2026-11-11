"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");
const path="widgets/weather/";
const sky=read(path+"StationSky.qml");
const pane=read(path+"StationWeatherSubjectPane.qml");
const policy={};
vm.runInNewContext(read(path+"StationWeatherSubjectPanelPolicy.js")
  .replace(/^\.pragma library\s*/m,""),policy);

test("W9 keeps one original StationSky renderer and the source-owner wiring",()=>{
 assert.equal((pane.match(/StationSky\s*\{/g)||[]).length,1);
 assert.match(pane,/weatherService: weatherPane\.weatherService/);
 assert.match(pane,/runtimeNowMs: weatherPane\.runtimeNowMs/);
 assert.match(pane,/readonly property var runtimeRows: originalSky\.runtimeRows/);
 assert.match(pane,/sourceComponent: weatherPane\.kind === "ground"/);
 assert.match(pane,/weatherPane\.kind === "services"/);
 for(const denied of ["FileView {","Process {","XMLHttpRequest","fetch("])
   assert.ok(!pane.includes(denied),"unexpected provider "+denied);
});

test("W9 combined WEATHER navigation is four fixed internal instrument pages",()=>{
 assert.match(pane,/weatherPane\.subjectRoute === "weather\/conditions\/current"/);
 assert.match(pane,/id: instrumentRail/);
 assert.match(pane,/id: instrumentViewport/);
 assert.match(pane,/clip: true/);
 assert.match(pane,/selected: skyHost\.activeInstrument === modelData\.focus/);
 for(const [label,focus] of [
   ["NOW + AIR","now"],["HOURLY","hourly"],
   ["DAILY","daily"],["TWILIGHT","twilight"]])
   assert.ok(pane.includes('label:"'+label+'",focus:"'+focus+'"'));
 assert.match(pane,/onClicked: skyHost\.activeInstrument = modelData\.focus/);
 assert.match(pane,/weatherFocus: skyHost\.combined \? skyHost\.activeInstrument : ""/);
 assert.match(pane,/scale: skyHost\.combined/);
 assert.match(pane,/instrumentViewport\.height/);
 assert.match(pane,/focusedContentHeight/);
});

test("W9 only the unified WEATHER view paginates original sections",()=>{
 assert.match(sky,/property string weatherFocus: ""/);
 assert.match(sky,/if \(subjectRoute === "weather\/conditions\/current"/);
 assert.match(sky,/weatherFocus === "now"/);
 assert.match(sky,/section === "current" \|\| section === "atmosphere"/);
 assert.match(sky,/return section === weatherFocus/);
 assert.match(sky,/interactive: sky\.weatherFocus === ""/);
 assert.match(sky,/visible: !sky\.sourceOnly && scrollable\s+&& sky\.weatherFocus === ""/);
 assert.match(sky,/onWeatherFocusChanged:/);
 assert.match(sky,/readonly property alias visualScroll: skyScroll/);
 assert.match(sky,/StationWeatherTerminalSummary\s*\{/);
 assert.match(sky,/sky\.weatherFocus === ""/);
 for(const name of ["current","atmosphere","hourly","daily","twilight"])
   assert.ok(sky.includes('sky.sectionVisible("'+name+'")'),name);
 for(const path of ["weather/conditions/current","weather/forecasts/hourly",
                    "weather/forecasts/daily","weather/conditions/air",
                    "weather/forecasts/air"])assert.ok(policy.kindForRoute(path));
 for(const source of ["astronomy","river","marine","coastal","lightning","seismic"])
   assert.equal(policy.needsSource("weather/conditions/current",source),false);
});

test("W9 weather-only presentation does not alter other families or existing routes",()=>{
 assert.match(sky,/return SubjectPanelPolicy.visibleFor\("sky",subjectRoute,section\)/);
 assert.match(sky,/CosmosPanelPolicy.visibleFor\("sky",subjectRoute,section\)/);
 assert.equal(policy.visibleFor("sky","weather/forecasts/hourly","hourly"),true);
 assert.equal(policy.visibleFor("sky","weather/forecasts/hourly","daily"),true);
 assert.equal(policy.visibleFor("sky","weather/conditions/current","current"),true);
 assert.equal(policy.visibleFor("sky","weather/conditions/current","hourly"),true);
 assert.equal(policy.visibleFor("sky","weather/conditions/current","twilight"),true);
});
