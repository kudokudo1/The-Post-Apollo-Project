"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");

const source=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const rail=read("widgets/weather/StationWorkspaceFamilyRail.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const treeSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const nav={};
const tree={};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m,""),nav);
vm.runInNewContext(treeSource.replace(/^\.pragma library\s*/m,""),tree);

const serviceFamilies=["home","weather","cosmos","earth","media","magick"];
const expected={
  home:"home/health",
  weather:"weather/services/health",
  cosmos:"cosmos/space-weather/overview",
  earth:"earth/services/health",
  media:"media/services/health",
  magick:"magick/services/health"
};

test("W27 uses existing canonical SERVICES destinations without new routes",()=>{
  for(const family of serviceFamilies) {
    const tab=nav.servicesTabFor(family);
    assert.ok(tab && tab.label==="SERVICES",family);
    assert.equal(tab.path,expected[family]);
    assert.equal(nav.familyFor(tab.path),family);
    assert.equal(nav.selectedGroup(tab.path),tab.key);
    if(family!=="home")assert.ok(tree.findRoute(tab.path),"not rendered "+tab.path);
    else assert.equal(nav.homeSectionFor(tab.path),"sources");
  }
  assert.equal(nav.servicesTabFor("tools"),null);
  assert.equal(nav.GROUPS.tools.some(x=>x.label==="SERVICES"),false);
  assert.equal(nav.GROUPS.tools[1].label,"SOURCES");
});

test("W27 SERVICES persists across every cross-family switch and chained swaps",()=>{
  for(const sourceFamily of serviceFamilies) {
    const sourceRoute=expected[sourceFamily];
    for(const destinationFamily of serviceFamilies) {
      const expectedPath=destinationFamily===sourceFamily
        ? nav.landingFor(destinationFamily) : expected[destinationFamily];
      assert.equal(nav.familySwitchTarget(sourceRoute,destinationFamily),
        expectedPath,sourceFamily+" → "+destinationFamily);
    }
  }
  let route=expected.weather;
  for(const family of ["cosmos","magick","earth","home","media","weather"]) {
    route=nav.familySwitchTarget(route,family);
    assert.equal(route,expected[family],"chained service "+family);
  }
});

test("W27 deep services, HOME alias and COSMOS space weather also follow",()=>{
  const deep=[
    "home/runtime","home/health",
    "weather/services/health",
    "cosmos/space-weather/overview","cosmos/space-weather/solar-wind",
    "earth/services/health",
    "media/services/health",
    "magick/services/health"
  ];
  for(const route of deep) {
    const sourceFamily=nav.familyFor(route);
    const target=sourceFamily==="weather"?"earth":"weather";
    assert.equal(nav.familySwitchTarget(route,target),expected[target],route);
  }
});

test("W27 non-SERVICES and non-cross-family choices keep old landing behavior",()=>{
  for(const src of nav.FAMILIES) {
    for(const from of nav.GROUPS[src.id]) {
      const isService=from.label==="SERVICES";
      if(isService) continue;
      for(const dest of nav.FAMILIES)
        assert.equal(nav.familySwitchTarget(from.path,dest.id),
          dest.landing,"nonservice "+from.path+" → "+dest.id);
    }
  }
  for(const from of ["weather/forecasts/hourly",
                     "cosmos/moon/ephemeris",
                     "earth/investigations/dossiers",
                     "magick/planetary/correspondences",
                     "media/news/viewer",
                     "tools/sources/health"]) {
    for(const dest of nav.FAMILIES)
      assert.equal(nav.familySwitchTarget(from,dest.id),dest.landing,from);
  }
  // The same selected family still resets to its normal Overview.
  for(const family of serviceFamilies)
    assert.equal(nav.familySwitchTarget(expected[family],family),
      nav.landingFor(family));
  // TOOLS has no SERVICES tab. It remains a normal landing, not a
  // newly invented service endpoint or an alias to its SOURCES section.
  for(const family of serviceFamilies)
    assert.equal(nav.familySwitchTarget(expected[family],"tools"),"tools/overview");
  assert.equal(nav.familySwitchTarget("tools/sources/health","weather"),
    "weather/overview");
});

test("W27 family rail and keyboard both use one navigator decision, other routes unchanged",()=>{
  assert.match(rail,/familyRail\.navigator\.chooseFamily\(modelData\.id\)/);
  assert.match(navigator,/function chooseFamily\(targetFamily\)/);
  assert.match(navigator,/Workspace\.familySwitchTarget\(currentPath,targetFamily\)/);
  assert.match(navigator,/return chooseFamily\("home"\)/);
  assert.match(navigator,/return chooseFamily\(subjectId\)/);
  assert.match(navigator,/return chooseFamily\(tabs\[\(Math\.max\(0,idx\)\+step\+tabs\.length\)%tabs\.length\]\.id\)/);
  assert.match(navigator,/if \(indexOpen\) \{/);
  assert.match(navigator,/function returnToWorkspace\(\)/);
  assert.match(navigator,/function goUp\(\)/);
  assert.match(surface,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
  assert.match(surface,/currentPath: "home\/overview"/);
  for(const text of [rail,source]) {
    for(const forbidden of ["FileView {","Process {","XMLHttpRequest","Qt.createQmlObject"])
      assert.doesNotMatch(text,new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")));
  }
});
