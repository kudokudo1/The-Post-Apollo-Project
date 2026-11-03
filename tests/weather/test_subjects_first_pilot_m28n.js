"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policySource=read("widgets/weather/StationSubjectDefaultPolicy.js");
const station=read("widgets/weather/WeatherStationW.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const policy=vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m,""),policy);

test("M28-N pilot prefers SUBJECTS on explicit open and CLASSIC on opt-out",()=>{
  assert.equal(policy.FORMAT,"post-apollo.weather.subject-default.m28n.v1");
  assert.equal(policy.SUBJECTS_FIRST_PILOT,true);
  assert.equal(policy.preferredView(true),"subjects");
  assert.equal(policy.preferredView(false),"classic");
  for(const v of [true,false,null,undefined,1,"true"]){
    assert.equal(policy.onOpen(v),v===true);
    // In the 0x0 layer-shell window a closed menu must unload all workspaces.
    assert.equal(policy.onClose(v),false);
  }
});

test("Escape exits INDEX to its native workspace, never forces CLASSIC; other views close",()=>{
  assert.equal(policy.escapeAction(true,true),"workspace");
  assert.equal(policy.escapeAction(true,false),"close");
  assert.equal(policy.escapeAction(false,true),"close");
  assert.equal(policy.escapeAction(false,false),"close");
});

test("CLASSIC fallback stays unavailable during Kitty session and closed host",()=>{
  for(const [open,requested,state,result] of [
    [true,false,"IDLE",true],
    [true,true,"IDLE",false],
    [false,false,"IDLE",false],
    [true,false,"STARTING",false],
    [true,false,"VISIBLE",false],
    [true,false,"VERIFY ERROR",false]
  ]) assert.equal(policy.canSwitch(open,requested,state),result);
  assert.equal(policy.switchToClassic(true,true),true);
  assert.equal(policy.switchToClassic(true,false),false);
  assert.equal(policy.switchToClassic(false,true),false);
});

test("root opens into SUBJECTS, closes to unload, and retains direct CLASSIC fallback",()=>{
  assert.match(station,/import "StationSubjectDefaultPolicy\.js" as SubjectDefaultPolicy/);
  assert.match(station,/property bool subjectsFirstPilotEnabled:\s*SubjectDefaultPolicy\.SUBJECTS_FIRST_PILOT/);
  assert.match(station,/property bool subjectNavigationOpen: false/);
  assert.match(station,/function open\(\)\s*\{[\s\S]*?subjectNavigationOpen =\s*SubjectDefaultPolicy\.onOpen\(subjectsFirstPilotEnabled\)\s*&& terminalView\.terminalState === "IDLE";[\s\S]*?menuOpen = true;/);
  assert.match(station,/function close\(\)\s*\{[\s\S]*?closeContextTerminal\(\);[\s\S]*?subjectNavigationOpen =\s*SubjectDefaultPolicy\.onClose\(subjectsFirstPilotEnabled\);[\s\S]*?menuOpen = false;/);
  assert.match(station,/function openSubjectNavigation\(\)/);
  assert.match(station,/function openLegacyFromSubject\(pageId\)/);
  assert.match(station,/label: weatherStation\.subjectNavigationOpen\s*\? "CLASSIC" : "SUBJECTS"/);
  assert.match(station,/id: subjectBrowserToggle/);
  assert.match(station,/if \(weatherStation\.subjectNavigationOpen\)\s*weatherStation\.switchToClassic\(\);/);
  assert.match(station,/subjectNavigator\.openIndex\(\)/);
  assert.match(station,/onLegacyPageRequested: function\(pageId\)/);
  assert.match(station,/weatherStation\.openLegacyFromSubject\(pageId\)/);
  assert.match(station,/visible: weatherStation\.subjectNavigationOpen/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
});

test("root Escape is identical for real Qt Keys and WindowShortcut and leaves terminal ownership intact",()=>{
  assert.match(station,/function handleEscape\(\)\s*\{/);
  assert.match(station,/if \(providerDiagnosticsOpen\)\s*\{\s*providerDiagnosticsOpen = false;/);
  assert.match(station,/SubjectDefaultPolicy\.escapeAction\(\s*subjectNavigationOpen,\s*subjectNavigator\.indexOpen\s*\)/);
  assert.match(station,/subjectNavigator\.returnToWorkspace\(\)/);
  assert.equal((station.match(/weatherStation\.handleEscape\(\)/g)||[]).length,2);
  assert.match(station,/onCurrentViewChanged:\s*\{\s*subjectNavigationOpen = false;/);
  assert.match(station,/closeContextTerminal\(\);\s*\}/);
  assert.match(station,/terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station,/terminalMode: weatherStation\.subjectNavigationOpen/);
  assert.match(station,/stationRailWidth: modeRail\.width/);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(terminal,/function closeTerminal\(\)/);
});

test("one original data owner remains, no extra hidden CLASSIC workspace, no deleted original components",()=>{
  for(const n of [
    "WeatherServices.CelestialVisualService",
    "WeatherServices.WeatherHomeFavoritesStore",
    "WeatherServices.WeatherHistoryService",
    "WeatherServices.SeismicService",
    "WeatherServices.NowcoastLightningService",
    "WeatherServices.NwpsRiverService"
  ])assert.equal((station.split(n+" {").length-1),1,n);
  for(const page of ["home","ground","sky","space","map","news","radio","placeholder"])
    assert.ok(station.includes("id: "+page+"ViewComponent"),page);
  for(const original of [
    "StationHome {","StationGround {","StationSky {","StationSpace {",
    "StationDiscovery {","StationNewsHub {","StationRadio {"
  ])assert.ok(station.includes(original),original);
  assert.match(station,/implicitWidth: menuOpen \? 1000 : 0/);
  assert.match(station,/implicitHeight: menuOpen \? 700 : 0/);
  assert.match(station,/visible: true/);
  assert.match(browser,/active: browser\.visible/);
  assert.match(browser,/property string currentPath: "home\/overview"/);
  assert.match(workspace,/StationHome\s*\{/);
  assert.match(workspace,/StationWeatherSubjectPane\s*\{/);
  assert.match(workspace,/StationMediaSubjectPane\s*\{/);
  assert.match(workspace,/StationToolsSubjectPane\s*\{/);
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest","WeatherServices.","StationTerminal {"])
    assert.ok(!policySource.includes(forbidden),"unexpected controller in decision policy "+forbidden);
});

test("the default is reversible but not a production enable switch or CLASSIC removal authorization",()=>{
  assert.match(station,/subjectsFirstPilotEnabled:\s*SubjectDefaultPolicy\.SUBJECTS_FIRST_PILOT/);
  assert.match(station,/visible: !weatherStation\.subjectNavigationOpen/);
  assert.match(station,/weatherStation\.subjectNavigationOpen = false/);
  assert.match(station,/currentView === "terminal"/);
  assert.match(station,/WeatherServices\.WeatherHistoryService/);
  assert.match(station,/onNewsMapRequested: function\(payload\)/);
  assert.match(browser,/legacyPageRequested\(modelData\.id\)/);
  assert.match(station,/StationTerminal\s*\{/);
});
