"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const shell=read("shell.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const policy={};
vm.runInNewContext(read("widgets/weather/StationSubjectDefaultPolicy.js").replace(/^\.pragma library\s*$/m,""),policy);
const routes={};
for(const p of ["widgets/weather/StationSubjectNavigationPolicy.js","widgets/weather/StationSubjectNavigationPreviewPolicy.js"])
  vm.runInNewContext(read(p).replace(/^\.pragma library\s*$/m,""),routes);

test("M28-V removes Classic-only root presentation without deleting original screen engines",()=>{
  for(const removed of ["id: railColumn","id: weatherContentLoader","id: subjectBrowserToggle",
    "mainModes:", "currentView:", "switchToClassic(","openLegacyFromSubject(",
    "homeViewComponent","groundViewComponent","skyViewComponent","spaceViewComponent",
    "mapViewComponent","newsViewComponent","radioViewComponent","placeholderViewComponent"])
    assert.ok(!station.includes(removed),"obsolete root entry: "+removed);
  assert.match(station,/StationSubjectNavigator\s*\{/);
  assert.match(surface,/StationHome\s*\{/);
  for(const [p,engine] of [
    ["StationWeatherSubjectPane.qml","StationGround"],
    ["StationWeatherSubjectPane.qml","StationSky"],
    ["StationCosmosSubjectPane.qml","StationSpace"],
    ["StationEarthSubjectPane.qml","StationDiscovery"],
    ["StationMediaSubjectPane.qml","StationNewsHub"],
    ["StationMediaSubjectPane.qml","StationRadio"]])
    assert.match(read("widgets/weather/"+p),new RegExp(engine+"\\s*\\{"),engine);
});

test("all 103 historical controls keep their native destination and immutable source provenance",()=>{
  const legacy=Object.keys(routes.PANELS);
  assert.equal(legacy.length,103);
  assert.equal(Object.keys(routes.WIRED_IN_SUBJECTS).length,103);
  for(const id of legacy) {
    assert.ok(routes.WIRED_IN_SUBJECTS[id],id);
    assert.ok(routes.findRoute(routes.PANELS[id]),id);
  }
  assert.ok(!navigator.includes("legacyPageRequested"));
  assert.ok(!navigator.includes("classicSources"));
  assert.ok(!surface.includes("legacyPageRequested"));
  assert.match(navigator,/PreviewRoutes\.nativeDestinationsForPath\(currentPath, SubjectRoutes\.PANELS\)/);
});

test("shell Weather notifications open native routes instead of old mainModes",()=>{
  assert.match(shell,/if \(!weatherStationWindow\.openNotificationView\(view\)\)/);
  assert.ok(!shell.includes("weatherStationWindow.currentView = view"));
  assert.ok(!shell.includes("weatherStationWindow.mainModes"));
  const block=station.slice(station.indexOf("function openNotificationView(view)"),
    station.indexOf("function open()"));
  for(const route of ["home/overview","weather/ground/full","weather/conditions/current",
    "cosmos/space-weather/full","earth/maps/full","media/news/full",
    "media/radio/full","tools/terminal/star-map"])
    assert.ok(block.includes('"'+route+'"'),route);
  assert.match(block,/subjectNavigator\.chooseRoute\(target\)/);
});

test("one source and terminal owner, source badge and exact terminal hole survive",()=>{
  for(const owner of ["CelestialVisualService","WeatherHomeFavoritesStore","WeatherHistoryService",
    "SeismicService","NowcoastLightningService","NwpsRiverService"])
    assert.equal(station.split("WeatherServices."+owner+" {").length-1,1,owner);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  assert.match(station,/terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station,/terminalMode: weatherStation\.subjectTerminalMode/);
  assert.match(station,/id: sourceStatusIndicator/);
  assert.match(station,/sourceStatusDisplay: sourceStatusText/);
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(terminal,/function closeTerminal\(\)/);
});

test("Escape, INDEX, close and keyboard are Subjects-only with no hidden mode cursor",()=>{
  assert.equal(policy.escapeAction(true),"workspace");
  assert.equal(policy.escapeAction(false),"close");
  assert.match(station,/function cycleMainMode\(direction\)\s*\{\s*subjectNavigator\.cycleSubjects\(direction\);/);
  assert.match(station,/function moveNavigationCursor\(direction\)\s*\{\s*subjectNavigator\.moveCursor\(direction\);/);
  assert.match(station,/function activateNavigationCursor\(\)\s*\{\s*subjectNavigator\.activateCursor\(\);/);
  assert.match(station,/function open\(\)\s*\{[\s\S]*?terminalView\.terminalState !== "IDLE"[\s\S]*?subjectNavigationOpen = true;[\s\S]*?menuOpen = true;/);
  assert.match(station,/function close\(\)\s*\{[\s\S]*?subjectNavigationOpen = false;[\s\S]*?menuOpen = false;/);
  assert.match(station,/label: "INDEX"/);
  assert.ok(!station.includes("CLASSIC_RETIREMENT_PREVIEW"));
});
