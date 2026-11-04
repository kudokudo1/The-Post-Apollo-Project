"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const navSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const previewSource=read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const workspaceSource=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const rail=read("widgets/weather/StationSubjectRail.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const home=read("widgets/weather/StationHome.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const m0=vm.createContext({}),preview=vm.createContext({}),workspace=vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m,""),m0);
vm.runInContext(previewSource.replace(/^\.pragma library\s*$/m,""),preview);
vm.runInContext(workspaceSource.replace(/^\.pragma library\s*$/m,""),workspace);
const plain=x=>JSON.parse(JSON.stringify(x));
const legacy=[
  ["home-aqi-humidity","weather/history/relationships","home/history","relations"],
  ["home-aqi-wind","weather/history/relationships","home/history","relations"],
  ["home-quick-conditions","weather/conditions/current","home/quick","quick"],
  ["home-space-weather","cosmos/space-weather/overview","home/quick","quick"]
];

test("M28-K reconciles exactly four original HOME controls without mutating M0 source hints",()=>{
  const selected=Object.keys(preview.WIRED_IN_SUBJECTS)
    .filter(id=>preview.WIRED_IN_SUBJECTS[id]==="M28-K").sort();
  assert.deepEqual(selected,legacy.map(row=>row[0]).sort());
  assert.equal(Object.keys(m0.PANELS).length,103);
  assert.equal(Object.values(preview.WIRED_IN_SUBJECTS).filter(v=>v==="M28-K").length,4,
    "M28-K original four HOME semantic controls remain exact");
  assert.ok(Object.keys(preview.WIRED_IN_SUBJECTS).length>=100,
    "later independently reviewed SOURCE controls may increase the ledger");
  for(const [id,historical,native,section] of legacy){
    assert.equal(m0.PANELS[id],historical,id+" M0 original historical hint");
    assert.equal(preview.HOME_SOURCE_HINTS[id],historical);
    assert.equal(preview.HOME_NATIVE_ROUTES[id],native);
    assert.equal(workspace.isHomeRoute(native),true);
    assert.equal(workspace.homeSectionFor(native),native==="home/history" ? "history" : "quick");
    assert.ok(section==="relations"||section==="quick", "original HOME subpanel remains identified");
    assert.equal(m0.findRoute(native),null,"M0 remains a six-subject taxonomy");
  }
  assert.deepEqual(plain(m0.SUBJECTS.map(x=>x.id)),
    ["weather","cosmos","earth","media","magick","tools"]);
});

test("INDEX resolves HOME QUICK/HISTORY to real native HOME routes, not misleading WEATHER or COSMOS pages",()=>{
  const links=plain(preview.nativeDestinationsForPath("home",m0.PANELS));
  assert.deepEqual(links,[
    {path:"home/history",panels:2,milestones:["M28-K"]},
    {path:"home/quick",panels:2,milestones:["M28-K"]}
  ]);
  assert.deepEqual(plain(preview.nativeDestinationsForPath("home/history",m0.PANELS)),[
    {path:"home/history",panels:2,milestones:["M28-K"]}
  ]);
  assert.deepEqual(plain(preview.nativeDestinationsForPath("home/quick",m0.PANELS)),[
    {path:"home/quick",panels:2,milestones:["M28-K"]}
  ]);
  assert.ok(!plain(preview.nativeDestinationsForPath("weather",m0.PANELS))
    .some(x=>x.path==="home/quick"||x.path==="home/history"),
    "do not misrepresent HOME sections as WEATHER");
  assert.deepEqual(plain(preview.remainingSourcePagesForPath("weather",m0.PANELS)),[]);
  assert.deepEqual(plain(preview.remainingSourcePagesForPath("cosmos",m0.PANELS)),[]);
  assert.deepEqual(plain(preview.sourcePagesForPath("home",m0.PANELS)),[],
    "M0 historical mapping remains untouched; HOME belongs to W1 workspace");
  assert.ok(preview.sourcePagesForPath("weather",m0.PANELS).some(x=>x.id==="home"),
    "old original provenance still visible for audit");
});

test("HOME index is navigable in the same seven-family rail without modifying the M0 six subjects",()=>{
  assert.match(browser,/currentPath === "home"/);
  assert.match(browser,/label:"HOME \/\/ ORIGINAL WORKSPACE"/);
  assert.match(browser,/Workspace\.GROUPS\.home\.map\(function\(entry\)/);
  assert.match(browser,/path:"home",label:"HOME"/);
  assert.match(browser,/if \(indexOpen && path === "home"\)/);
  assert.match(browser,/function selectSubject\(subjectId\)/);
  assert.match(browser,/if \(subjectId === "home"\)/);
  assert.match(browser,/currentPath = family === "home" \? "home" : family/);
  assert.match(browser,/const names = \[\{id:"home"\}\]\.concat\(SubjectRoutes\.SUBJECTS\)/);
  assert.match(browser,/onClicked: browser\.chooseRoute\(modelData\.path\)/);
  assert.match(rail,/model: \[\{id:"home",label:"HOME"\}\]\.concat\(SubjectRoutes\.SUBJECTS\)/);
  assert.equal((rail.match(/ModeButton\s*\{/g)||[]).length,1);
  assert.match(browser,/function returnToWorkspace\(\)/);
  assert.match(station,/subjectNavigator\.openIndex\(\)/);
});

test("HOME QUICK and HISTORY retain the single original StationHome with real source observations",()=>{
  assert.equal((surface.match(/StationHome\s*\{/g)||[]).length,1);
  assert.match(surface,/id: originalHome/);
  assert.match(surface,/workspaceSection: surface\.homeSection === "overview"/);
  assert.match(surface,/weatherService: surface\.weatherService/);
  assert.match(surface,/spaceService: surface\.spaceService/);
  assert.match(surface,/liveHistoryStore: surface\.liveHistoryStore/);
  assert.match(home,/if \(workspaceSection === "quick"\)/);
  assert.match(home,/return section === "quick" \|\| section === "relations"/);
  assert.match(home,/if \(workspaceSection === "history"\)/);
  assert.match(home,/return section === "history" \|\| section === "relations"/);
  for(const label of [
    'title: "QUICK // CONDITIONS"',
    'title: "HUMIDITY"',
    'title: "WIND"',
    'title: "UV INDEX"',
    'title: "SPACE WEATHER"',
    'title: "LIVE HISTORY // AQI RELATIONSHIPS"',
    'title: "AQI ↔ HUMIDITY"',
    'title: "AQI ↔ WIND"'
  ]) assert.ok(home.includes(label),label);
  assert.match(home,/spaceService && spaceService\.kpReady/);
  assert.match(home,/home\.sectionVisible\("quick"\)/);
  assert.match(home,/home\.sectionVisible\("relations"\)/);
  assert.match(home,/interval: 60000/);
});

test("no ghost HOME destination is created from forged source metadata or malformed paths",()=>{
  for(const pathId of [null,"HOME","home//quick","../home","home?quick=1"])
    assert.deepEqual(plain(preview.nativeDestinationsForPath(pathId,m0.PANELS)),[]);
  const injected=Object.assign({},plain(m0.PANELS),{
    "home-aqi-humidity":"wrong/route",
    "home-quick-conditions":"weather/unknown"
  });
  const links=plain(preview.nativeDestinationsForPath("home",injected));
  assert.deepEqual(links,[
    {path:"home/history",panels:1,milestones:["M28-K"]},
    {path:"home/quick",panels:1,milestones:["M28-K"]}
  ]);
  assert.deepEqual(plain(preview.nativeDestinationsForPath("home",null)),[]);
});

test("later M28-L source review does not erase M28-K HOME or historic source provenance",()=>{
  assert.deepEqual(Object.keys(m0.PANELS).filter(id=>!preview.WIRED_IN_SUBJECTS[id]),[]);
  assert.deepEqual(plain(preview.remainingSourcePagesForPath("tools/sources/health",m0.PANELS)),[]);
  assert.deepEqual(plain(preview.sourcePagesForPath("tools/sources/health",m0.PANELS)
    .map(x=>x.id)),["home","ground","map"]);
  assert.ok(preview.nativeDestinationsForPath("tools/sources/health",m0.PANELS).length>0);
  assert.ok(!station.includes("weatherContentLoader"));
  assert.match(station,/subjectNavigationOpen = true;/);
  assert.match(station,/StationTerminal\s*\{/);
  for(const forbidden of ["Process {","FileView {","XMLHttpRequest","Qt.callLater"])
    assert.ok(!browser.includes(forbidden),"INDEX must not become a service owner: "+forbidden);
});
