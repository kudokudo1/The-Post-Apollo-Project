"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const newPolicy=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const treeSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const familyRail=read("widgets/weather/StationWorkspaceFamilyRail.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const home=read("widgets/weather/StationHome.qml");
const homePolicy=read("widgets/weather/StationHomePolicy.js");
const tree=vm.createContext({}),nav=vm.createContext({});
vm.runInContext(treeSource.replace(/^\.pragma library\s*$/m,""),tree);
vm.runInContext(newPolicy.replace(/^\.pragma library\s*$/m,""),nav);

test("seven main-mode families open real landing pages, not route-directory root previews",()=>{
  const rows=JSON.parse(JSON.stringify(nav.FAMILIES));
  assert.deepEqual(rows.map(x=>x.id),
    ["home","weather","cosmos","earth","media","magick","tools"]);
  assert.deepEqual(rows.map(x=>x.landing),
    ["home/overview","weather/overview","cosmos/overview",
     "earth/overview","media/overview","magick/overview","tools/overview"]);
  for (const entry of rows) {
    assert.equal(nav.landingFor(entry.id),entry.landing);
    assert.equal(nav.familyFor(entry.landing),entry.id);
    if(entry.id!=="home")assert.ok(tree.findRoute(entry.landing),entry.landing);
  }
  assert.equal(nav.landingFor("unknown"),"home/overview");
});

test("bottom row modes are navigable real paths with clear family grouping",()=>{
  const sizes={home:8,weather:8,cosmos:6,earth:7,media:5,magick:6,tools:5};
  for(const family of nav.FAMILIES) {
    const modes=JSON.parse(JSON.stringify(nav.tabsFor(family.landing)));
    assert.equal(modes.length,sizes[family.id],family.id);
    assert.equal(modes[0].path,family.landing);
    assert.equal(modes[0].key,"overview");
    assert.equal(new Set(modes.map(x=>x.path)).size,modes.length);
    for(const mode of modes) {
      assert.equal(nav.familyFor(mode.path),family.id,mode.path);
      assert.ok(mode.label&&mode.key,mode.path);
      if(family.id==="home")
        assert.equal(nav.isHomeRoute(mode.path),true,mode.path);
      else assert.ok(tree.findRoute(mode.path),mode.path);
      assert.equal(nav.selectedGroup(mode.path),mode.key,mode.path);
    }
  }
  assert.equal(nav.selectedGroup("earth/investigations/dossiers"),"investigations");
  assert.equal(nav.selectedGroup("weather/water/rivers/hydrograph"),"water");
  assert.equal(nav.selectedGroup("cosmos/space-weather/solar-wind"),"space-weather");
  assert.equal(nav.selectedGroup("media/news/viewer"),"news");
});

test("HOME tab focus is bounded to the existing ten section families",()=>{
  assert.deepEqual(["overview","auto","quick","snapshot","history","runtime","health","magick"],
    JSON.parse(JSON.stringify(nav.GROUPS.home.map(x=>x.key))));
  for(const mode of nav.GROUPS.home)
    assert.equal(nav.homeSectionFor(mode.path),mode.key);
  assert.equal(nav.homeSectionFor("weather/overview"),"");
  assert.match(home,/property string subjectRoute: ""/);
  assert.match(home,/property string workspaceSection: ""/);
  assert.match(home,/SubjectPanelPolicy\.visibleFor\("home", subjectRoute, section\)/);
  assert.match(home,/workspaceSection === "auto"/);
  assert.match(home,/section === "relevant" \|\| section === "alerts"/);
  for(const section of ["quick","snapshot","history","runtime","health"])
    assert.ok(home.includes('workspaceSection === "'+section+'"'),section);
  assert.match(home,/onWorkspaceSectionChanged:/);
});

test("single original HOME retains ranking, timer, snapshots, history and runtime racks",()=>{
  assert.equal((workspace.match(/StationHome\s*\{/g)||[]).length,1);
  assert.match(workspace,/id: originalHome/);
  assert.match(workspace,/workspaceSection: surface\.homeSection === "overview"/);
  assert.match(workspace,/StationMagickSubjectPane\s*\{/);
  for(const value of [
    "StationHomePolicy.rankRelevant(","activeWatchIds","relevanceClockMs",
    "captureWeatherSnapshot(","captureAqiSnapshot(","captureKpSnapshot(",
    "captureSolarWindSnapshot(","captureBzSnapshot(","historyDaily",
    "liveWeatherHistory","StationRuntimeRack {",
    'title: "AUTO // RELEVANT"','title: "RECENT HISTORY // ARCHIVED MODEL"',
    'title: "SNAPSHOT // NOW"'
  ])assert.ok(home.includes(value),"original HOME mechanism lost: "+value);
  assert.match(home,/interval: 60000/);
  assert.match(homePolicy,/function rankRelevant\(/);
  assert.match(homePolicy,/function activeAbove\(/);
  assert.match(homePolicy,/function activeBelow\(/);
  assert.match(station,/subjectNavigator\.liveHomeKind !== ""/);
  assert.match(station,/subjectNavigator\.currentPath, "history"/);
});

test("left family rail and bottom workspace buttons switch immediate working panels",()=>{
  assert.equal((workspace.match(/Repeater\s*\{/g)||[]).length,1);
  assert.match(familyRail,/model: Workspace\.FAMILIES/);
  assert.match(workspace,/model: surface\.activeTabs/);
  assert.match(familyRail,/familyRail\.navigator\.chooseRoute\(modelData\.landing\)/);
  assert.match(workspace,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
  for(const name of ["Weather","Cosmos","Earth","Media","Magick","Tools"])
    assert.ok(workspace.includes("Station"+name+"SubjectPane {"),name);
  assert.ok(!workspace.includes("id: topRail"));
  assert.match(workspace,/id: bottomRail/);
  assert.match(station,/\? "INDEX"/);
  assert.match(station,/\? "CLASSIC" : "SUBJECTS"/);
  assert.match(browser,/property string currentPath: "home\/overview"/);
  assert.match(browser,/Workspace\.landingFor\(subjectId\)/);
  assert.match(browser,/id: legacyIndexLayer/);
  assert.match(browser,/if \(indexOpen && !home && candidate\.group\)/);
  assert.match(browser,/function returnToWorkspace\(\)/);
  assert.match(station,/subjectNavigator\.openIndex\(\)/);
  assert.match(browser,/onLegacyPageRequested: function\(pageId\)/);
  assert.match(station,/StationSubjectNavigator\s*\{/);
  assert.match(station,/width: 160/);
});

test("source owners and 160px CLASSIC terminal geometry remain unchanged",()=>{
  assert.match(browser,/active: browser\.visible/);
  assert.match(station,/active: !weatherStation\.subjectNavigationOpen/);
  assert.match(station,/stationRailWidth: modeRail\.width/);
  assert.match(station,/weatherStation\.openLegacyFromSubject\(pageId\)/);
  assert.match(station,/onCurrentViewChanged:\s*\{\s*subjectNavigationOpen = false/);
  assert.match(station,/terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/WeatherServices\.SeismicService\s*\{/);
  assert.match(station,/WeatherServices\.WeatherHistoryService\s*\{/);
  assert.match(workspace,/liveHistoryStore: surface\.liveHistoryStore/);
  assert.match(workspace,/eventArchiveStore: surface\.eventArchiveStore/);
  assert.match(workspace,/dossierArchiveStore: surface\.dossierArchiveStore/);
  assert.match(workspace,/newsMapRequested\(payload\)/);
});

test("W1 moves controls and panels, not additional data collectors or new settings writers",()=>{
  for(const source of [newPolicy,workspace]) {
    for(const pattern of ["WeatherServices.","FileView {","Process {",
      "XMLHttpRequest","Qt.createQmlObject","StationTerminal {",
      "swaymsg","curl ","saveCreator(","archiveEvent(","capture("])
      assert.ok(!source.includes(pattern),"unexpected owner "+pattern);
  }
  // W2b adds explicit card pins via a single Weather-root writer, not
  // via HOME itself. The original W1 source ownership remains unchanged.
  assert.match(home,/property var homeFavoritesStore: null/);
  assert.match(home,/CardProvenance\.provenance\(\s*modelData,\s*home\.sourceHealthRows\s*\)/);
  assert.ok(!home.includes("FileView {"));
  assert.ok(!home.includes("Process {"));
});
