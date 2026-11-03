"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const rail=read("widgets/weather/StationWorkspaceFamilyRail.qml");
const classicRail=read("widgets/weather/StationSubjectRail.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const routes=read("widgets/weather/StationWorkspaceNavigationPolicy.js");

test("seven main family ModeButtons use the original Station left rail",()=>{
  assert.match(rail,/model: Workspace\.FAMILIES/);
  assert.match(rail,/delegate: ModeButton\s*\{/);
  assert.match(rail,/height: 48/);
  assert.match(rail,/labelText: modelData\.label/);
  assert.match(rail,/Workspace\.familyFor\(familyRail\.navigator\.currentPath\)/);
  assert.match(rail,/familyRail\.navigator\.chooseRoute\(modelData\.landing\)/);
  assert.match(station,/StationWorkspaceFamilyRail\s*\{/);
  assert.match(station,/visible: weatherStation\.subjectNavigationOpen\s*&& !subjectNavigator\.indexOpen/);
  assert.match(station,/navigator: subjectNavigator/);
  assert.match(routes,/\{id:"home",label:"HOME",landing:"home\/overview"\}/);
  assert.match(routes,/\{id:"tools",label:"TOOLS",landing:"tools\/overview"\}/);
  assert.equal((station.match(/ModeButton\s*\{/g)||[]).length,1,
    "the original main Mode delegate remains exactly one in root station");
});

test("workspace does not duplicate top family strip and retains bottom submodes",()=>{
  assert.ok(!surface.includes("id: topRail"));
  assert.ok(!surface.includes("model: Workspace.FAMILIES"));
  assert.ok(!surface.includes('label: "MORE"'));
  assert.match(surface,/id: bottomRail/);
  assert.match(surface,/model: surface\.activeTabs/);
  assert.match(surface,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
  assert.match(surface,/anchors\.top: parent\.top/);
  assert.match(surface,/StationHome\s*\{/);
  assert.match(surface,/id: originalHome/);
});

test("existing header INDEX takes over old MORE action and toggles detailed index",()=>{
  assert.match(station,/id: contextTerminalLaunch/);
  assert.match(station,/label: weatherStation\.subjectNavigationOpen\s*\? "INDEX"/);
  assert.match(station,/available: weatherStation\.menuOpen\s*&& terminalView\.terminalState === "IDLE"/);
  assert.match(station,/if \(weatherStation\.subjectNavigationOpen\)\s*\{/);
  assert.match(station,/if \(subjectNavigator\.indexOpen\)\s*subjectNavigator\.returnToWorkspace\(\);\s*else\s*subjectNavigator\.openIndex\(\);/);
  assert.match(station,/weatherStation\.launchContextTerminal\(\);/);
  assert.match(navigator,/function openIndex\(\)/);
  assert.match(navigator,/function returnToWorkspace\(\)/);
  assert.ok(!navigator.includes("onIndexRequested:"));
  assert.match(navigator,/id: legacyIndexLayer/);
});

test("CLASSIC toggle remains on left rail, detailed INDEX also retains its own rail",()=>{
  assert.match(station,/width: 160/);
  assert.match(station,/id: subjectBrowserToggle/);
  assert.match(station,/\? "CLASSIC" : "SUBJECTS"/);
  assert.match(station,/StationSubjectRail\s*\{/);
  assert.match(station,/visible: weatherStation\.subjectNavigationOpen\s*&& subjectNavigator\.indexOpen/);
  assert.match(classicRail,/model: SubjectRoutes\.SUBJECTS/);
  assert.match(station,/visible: !weatherStation\.subjectNavigationOpen/);
});

test("Kitty and home session lifetimes and source owners remain intact",()=>{
  assert.match(station,/terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station,/stationRailWidth: modeRail\.width/);
  assert.match(station,/onCurrentViewChanged:\s*\{\s*subjectNavigationOpen = false/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/WeatherServices\.WeatherHistoryService\s*\{/);
  assert.match(station,/onNewsMapRequested: function\(payload\)/);
  assert.match(navigator,/active: browser\.visible/);
  assert.match(surface,/workspaceSection: surface\.homeSection === "overview"/);
  for(const x of [surface,rail]) {
    for(const token of ["FileView {","Process {","WeatherServices.","swaymsg","StationTerminal {"])
      assert.ok(!x.includes(token),"unexpected new owner "+token);
  }
});
