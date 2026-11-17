#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

const policy = fs.readFileSync("widgets/weather/StationWorkspaceNavigationPolicy.js","utf8")
  .replace(/^\.pragma library\s*/m,"");
const navigator = fs.readFileSync("widgets/weather/StationSubjectNavigator.qml","utf8");
const station = fs.readFileSync("widgets/weather/WeatherStationW.qml","utf8");
const p={};
vm.runInNewContext(policy,p,{filename:"StationWorkspaceNavigationPolicy.js"});

function next(path,direction) {
  const tabs=p.tabsFor(path);
  const group=p.selectedGroup(path);
  const idx=tabs.findIndex(x=>x.key===group);
  const step=direction<0?-1:1;
  return tabs[(Math.max(0,idx)+step+tabs.length)%tabs.length].path;
}
test("Ctrl+Left/Right uses real bottom navigation for all 7 workspace families",()=>{
  for(const family of p.FAMILIES) {
    const paths=p.GROUPS[family.id];
    assert.ok(paths.length>=2,family.id);
    for(let i=0;i<paths.length;i++) {
      assert.equal(next(paths[i].path,1),paths[(i+1)%paths.length].path);
      assert.equal(next(paths[i].path,-1),
        paths[(i+paths.length-1)%paths.length].path);
    }
  }
});
test("Deep links cycle from the correct visible lower group, not arbitrary INDEX",()=>{
  for(const [from,expected] of [
    ["weather/forecasts/hourly","weather/hazards/alerts"],
    ["earth/maps/events","earth/water/rivers"],
    ["cosmos/planets-stars/celestial-fix","cosmos/events/overview"],
    ["magick/planetary/correspondences","magick/astrology/charts"],
    ["home/health","home/overview"]
  ])
    assert.equal(next(from,1),expected,from);
});
test("Mode cycles are strictly window-local and preview/action remain separate",()=>{
  assert.match(navigator,/function cycleWorkspaceTab\(direction\)/);
  assert.match(navigator,/if\(indexOpen\) return false/);
  assert.match(navigator,/return chooseRoute\(tabs\[next\]\.path\)/);
  assert.match(station,/function cycleBottomSubMode\(direction\)/);
  assert.match(station,/if \(!standardKeysAvailable \|\| subjectNavigator\.indexOpen\)/);
  assert.match(station,/Qt\.ControlModifier/);
  for(const key of ["Ctrl+Left","Ctrl+Right"])
    assert.match(station,new RegExp('sequence: "'+key.replace("+","\\+")+'"'));
  assert.doesNotMatch(station,/sequence: "Shift\+Left"/);
  assert.doesNotMatch(station,/sequence: "Shift\+Right"/);
  assert.match(station,/subjectNavigator\.activateCursor\(\)/);
});
