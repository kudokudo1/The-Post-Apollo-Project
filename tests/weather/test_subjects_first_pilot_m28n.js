"use strict";
// M28-N historically established SUBJECTS-first. M28-V makes it permanent.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const policy=vm.createContext({});
vm.runInContext(read("widgets/weather/StationSubjectDefaultPolicy.js").replace(/^\.pragma library\s*$/m,""),policy);

test("SUBJECTS-first pilot graduated to the only production navigation",()=>{
  assert.equal(policy.FORMAT,"post-apollo.weather.subject-lifecycle.m28v.v1");
  assert.ok(!station.includes("subjectsFirstPilotEnabled"));
  assert.ok(!station.includes("CLASSIC_RETIREMENT_PREVIEW"));
  assert.ok(!station.includes("subjectBrowserToggle"));
  assert.ok(!station.includes("weatherContentLoader"));
  assert.match(station,/subjectNavigationOpen = true;/);
});

test("Escape exits INDEX to workspace then closes, never switches to Classic",()=>{
  assert.equal(policy.escapeAction(true),"workspace");
  assert.equal(policy.escapeAction(false),"close");
  assert.match(station,/SubjectDefaultPolicy\.escapeAction\(subjectNavigator\.indexOpen\)/);
  assert.match(station,/subjectNavigator\.returnToWorkspace\(\)/);
  assert.match(station,/function handleEscape\(\)/);
});

test("root admission and cleanup respect the single active Kitty actor",()=>{
  assert.match(station,/function open\(\)\s*\{[\s\S]*?terminalView\.terminalState !== "IDLE"[\s\S]*?subjectNavigationOpen = true;[\s\S]*?menuOpen = true;/);
  assert.match(station,/function close\(\)\s*\{[\s\S]*?closeContextTerminal\(\);[\s\S]*?subjectNavigationOpen = false;[\s\S]*?menuOpen = false;/);
  assert.match(station,/terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station,/terminalMode: weatherStation\.subjectTerminalMode/);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  assert.match(terminal,/kittyActorConfirmed/);
});

test("one original data-owner family remains and all native panes are mounted",()=>{
  for(const n of ["CelestialVisualService","WeatherHomeFavoritesStore","WeatherHistoryService",
      "SeismicService","NowcoastLightningService","NwpsRiverService"])
    assert.equal(station.split("WeatherServices."+n+" {").length-1,1,n);
  assert.match(browser,/active: browser\.visible/);
  for(const n of ["StationHome","StationWeatherSubjectPane","StationCosmosSubjectPane",
      "StationEarthSubjectPane","StationMediaSubjectPane","StationMagickSubjectPane","StationToolsSubjectPane"])
    assert.ok(workspace.includes(n+" {"),n);
});

test("source migration is not equivalent to enabling unsafe video or workstation acceptance",()=>{
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(read("widgets/weather/StationChannelScreen.qml"),/readonly property bool playbackAvailable: false/);
  assert.match(station,/implicitWidth: menuOpen \? 1000 : 0/);
  assert.match(station,/implicitHeight: menuOpen \? 700 : 0/);
});
