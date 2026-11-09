"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=x=>fs.readFileSync(path.join(root,x),"utf8");
const policy=read("widgets/weather/StationSubjectHeaderGeometry.js");
const pages={
 modes:read("widgets/weather/StationCosmosModesPane.qml"),
 moon:read("widgets/weather/StationCosmosMoonCompactPane.qml"),
 year:read("widgets/weather/StationCosmosAnnualWheelPane.qml"),
 space:read("widgets/weather/StationCosmosSpaceWeatherHubPane.qml"),
 overview:read("widgets/weather/StationCosmosOverviewPane.qml")
};
const c=vm.createContext({Math,Number,isFinite});
vm.runInContext(policy.replace(/^\.pragma library\s*$/m,""),c);

test("C44 one shared page contract defines stable margins and title/tab/divider/content geometry",()=>{
 assert.deepEqual([
   c.inset,c.titleHeight,c.titleToTabs,c.tabHeight,c.tabSpacing,
   c.tabsToRule,c.ruleHeight,c.ruleToContent
 ],[6,18,4,27,4,5,2,3]);
 assert.equal(c.titleTop(),6);
 assert.equal(c.tabsTop(),28);
 assert.equal(c.ruleTop(),60);
 assert.equal(c.contentTop(),65);
 assert.equal(c.columnHeaderGap(),1);
 assert.equal(c.columnRuleSlotHeight(),4);
 for(const n of [2,3,4,5,6]) {
   const width=508, each=c.buttonWidth(width,n);
   assert.ok(Math.abs(n*each+(n-1)*c.tabSpacing-width)<0.001);
 }
 assert.equal(c.buttonWidth(0,2),1);
 assert.equal(c.buttonWidth(508,0),1);
});

test("C44 COSMOS family rail shares the contract without changing SUN, astronomy or events routes",()=>{
 const s=pages.modes;
 assert.match(s,/import "StationSubjectHeaderGeometry\.js" as HeaderGeometry/);
 assert.match(s,/objectName: "cosmos-c44-mode-title"/);
 assert.match(s,/objectName: "cosmos-c44-mode-tabs"/);
 assert.match(s,/objectName: "cosmos-c44-mode-divider"/);
 assert.match(s,/objectName: "cosmos-c44-mode-stage"/);
 assert.match(s,/height: HeaderGeometry\.titleHeight/);
 assert.match(s,/anchors\.topMargin: HeaderGeometry\.titleToTabs/);
 assert.match(s,/height: HeaderGeometry\.tabHeight/);
 assert.match(s,/width: HeaderGeometry\.buttonWidth\(modeRail\.width,/);
 assert.match(s,/anchors\.topMargin: HeaderGeometry\.tabsToRule/);
 assert.match(s,/height: HeaderGeometry\.ruleHeight/);
 assert.match(s,/anchors\.topMargin: HeaderGeometry\.ruleToContent/);
 assert.match(s,/onClicked: cosmosModePane\.routeRequested\(modelData\.route\)/);
});

test("C44 MOON overview and both annual subviews keep their original destinations",()=>{
 const m=pages.moon, y=pages.year;
 for(const x of [m,y]){
   assert.match(x,/import "StationSubjectHeaderGeometry\.js" as HeaderGeometry/);
   assert.match(x,/HeaderGeometry\.titleHeight/);
   assert.match(x,/height: HeaderGeometry\.tabHeight/);
   assert.match(x,/HeaderGeometry\.ruleHeight/);
   assert.match(x,/HeaderGeometry\.buttonWidth\(/);
   assert.match(x,/HeaderGeometry\.ruleToContent/);
 }
 assert.match(m,/objectName: "cosmos-c18-moon-fullwidth-mode-rail"/);
 assert.match(m,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.match(y,/objectName: "cosmos-c44-moon-year-header"/);
 assert.match(y,/objectName: "cosmos-c23-moon-year-divider"/);
 assert.match(y,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/ephemeris"\)/);
 assert.match(y,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.match(y,/subject: "moon"/);
 assert.match(y,/view: annualFocus\.annualView/);
});

test("C44 SPACE has the same centered two-button tab frame, no SERVICES mode reintroduction",()=>{
 const s=pages.space;
 assert.match(s,/anchors\.margins: HeaderGeometry\.inset/);
 assert.match(s,/objectName: "cosmos-c44-space-title"/);
 assert.match(s,/id: headerSpacer/);
 assert.match(s,/height: HeaderGeometry\.columnHeaderGap\(\)/);
 assert.match(s,/objectName: "cosmos-c42-space-view-modes"/);
 assert.match(s,/width: HeaderGeometry\.buttonWidth\(viewRail\.width,2\)/);
 assert.match(s,/objectName: "cosmos-c44-space-divider"/);
 assert.match(s,/height: HeaderGeometry\.columnRuleSlotHeight\(\)/);
 assert.match(s,/objectName: "cosmos-c42-space-metrics"/);
 assert.doesNotMatch(s,/kind:"services"|label:"SERVICES"/);
 assert.match(s,/kind:"dashboard"/);
 assert.match(s,/kind:"directory"/);
 assert.match(s,/readonly property var runtimeRows: statusOwner\.runtimeRows/);
 assert.match(s,/readonly property string serviceBrief/);
});

test("C44 OVERVIEW promotes three small shortcuts into full-width nav and retains both data bays",()=>{
 const s=pages.overview;
 assert.match(s,/objectName: "cosmos-c44-overview-title"/);
 assert.match(s,/objectName: "cosmos-c44-overview-mode-rail"/);
 assert.match(s,/width: HeaderGeometry\.buttonWidth\(overviewModeRail\.width,3\)/);
 assert.match(s,/height: HeaderGeometry\.tabHeight/);
 assert.match(s,/objectName: "cosmos-c44-overview-divider"/);
 assert.match(s,/height: HeaderGeometry\.columnRuleSlotHeight\(\)/);
 assert.match(s,/objectName: "cosmos-c44-overview-stage"/);
 for(const path of ["cosmos/sun/position","cosmos/moon/ephemeris",
        "cosmos/space-weather/overview","cosmos/space-weather/full"])
   assert.ok(s.includes(path),path);
 assert.match(s,/id: scientificVisuals/);
 assert.match(s,/id: spaceMetricRow/);
 assert.doesNotMatch(s,/width: 66\s*height: 18/);
});

test("C44 retains all existing source owners, and no new IO, scroll or files",()=>{
 const entire=Object.values(pages).join("\n");
 assert.doesNotMatch(policy,/XMLHttpRequest|Process\s*\{|Timer\s*\{|WebSocket|FileView/);
 assert.match(pages.modes,/id: skyLoader/);
 assert.match(pages.moon,/id: sourceSky/);
 assert.match(pages.overview,/id: sourceSky/);
 assert.match(pages.space,/id: statusOwner/);
 assert.match(pages.year,/id: annualWheel/);
 for(const word of ["cosmos-c44-mode-title","cosmos-c44-space-title",
    "cosmos-c44-moon-year-header","cosmos-c44-overview-title"])
   assert.ok(entire.includes(word),word);
});
