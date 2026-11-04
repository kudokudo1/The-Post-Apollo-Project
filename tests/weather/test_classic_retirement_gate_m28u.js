"use strict";
// M28-U was a reversible Classic-hiding pilot. M28-V removes the fallback.
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const ctx=vm.createContext({});
for(const p of ["widgets/weather/StationSubjectNavigationPolicy.js",
    "widgets/weather/StationSubjectNavigationPreviewPolicy.js"])
  vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),ctx);

test("M28-U pilot's 103-of-103 route accounting survives final retirement",()=>{
  assert.equal(Object.keys(ctx.PANELS).length,103);
  assert.equal(Object.keys(ctx.WIRED_IN_SUBJECTS).length,103);
  for(const id of Object.keys(ctx.PANELS))assert.ok(ctx.WIRED_IN_SUBJECTS[id],id);
  for(const family of ["weather","cosmos","earth","media","magick","tools"])
    assert.equal(ctx.remainingSourcePagesForPath(family,ctx.PANELS).length,0,family);
});
test("M28-V has no executable Classic view, toggle, rail or INDEX jump",()=>{
  for(const marker of ["id: railColumn","id: weatherContentLoader","id: subjectBrowserToggle",
    "switchToClassic(","openLegacyFromSubject(","currentView:","mainModes:"])
    assert.ok(!station.includes(marker),marker);
  assert.ok(!navigator.includes("legacyPageRequested"));
  assert.ok(!surface.includes("legacyPageRequested"));
  assert.match(station,/StationSubjectNavigator\s*\{/);
  assert.match(navigator,/model: browser\.nativeDestinations/);
});
test("the original engines remain mounted under SUBJECTS",()=>{
  assert.match(surface,/StationHome\s*\{/);
  for(const [p,sym] of [["StationWeatherSubjectPane.qml","StationGround"],
    ["StationCosmosSubjectPane.qml","StationSpace"],["StationEarthSubjectPane.qml","StationDiscovery"],
    ["StationMediaSubjectPane.qml","StationNewsHub"],["StationMediaSubjectPane.qml","StationRadio"]])
    assert.ok(read("widgets/weather/"+p).includes(sym+" {"),sym);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(read("widgets/weather/StationChannelScreen.qml"),/readonly property bool playbackAvailable: false/);
});
