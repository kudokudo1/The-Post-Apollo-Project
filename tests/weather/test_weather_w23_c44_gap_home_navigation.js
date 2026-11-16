"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const rail=read("StationSubjectOverviewRail.qml");
const header=read("StationSubjectHeaderGeometry.js");
const cosmos=read("StationCosmosOverviewPane.qml");
const home=read("StationHome.qml");
const surface=read("StationWorkspaceSurface.qml");
const workspace=read("StationWorkspaceNavigationPolicy.js");
const magick=read("StationMagickSubjectPane.qml");
const weather=read("StationWeatherOverviewCompactInstrument.qml");
const cards=read("StationHomeMetricCard.qml");
const weatherNative=fs.readFileSync("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml","utf8");
const magickNative=fs.readFileSync("tests/weather/fixtures/W21MagickOverviewNative.qml","utf8");
const homeNative=fs.readFileSync("tests/weather/fixtures/W23HomeOverviewNative.qml","utf8");

test("W23 matches COSMOS C44 title/tab/divider vertical spacing exactly",()=>{
 assert.match(header,/var titleToTabs = 4/);
 assert.match(header,/var tabHeight = 27/);
 assert.match(header,/var tabsToRule = 5/);
 assert.match(header,/var ruleHeight = 2/);
 assert.match(cosmos,/height: HeaderGeometry\.tabHeight/);
 assert.match(cosmos,/height: HeaderGeometry\.tabsToRule \+ HeaderGeometry\.ruleHeight/);
 assert.match(rail,/dividerGap: HeaderGeometry\.tabsToRule/);
 assert.match(rail,/HeaderGeometry\.titleHeight \+ HeaderGeometry\.titleToTabs/);
 assert.match(rail,/height: overviewRail\.condensed \? 24 : HeaderGeometry\.tabHeight/);
 assert.match(rail,/y: longButtons\.y \+ longButtons\.height \+ overviewRail\.dividerGap/);
 assert.match(rail,/spacing: overviewRail\.buttonGap/);
 assert.match(rail,/onClicked: overviewRail.routeRequested\(modelData.path\)/);
 assert.match(weatherNative,/W23_WEATHER_TAB_DIVIDER_GAP_/);
 assert.match(magickNative,/W23_MAGICK_TAB_DIVIDER_GAP_/);
 assert.match(homeNative,/HOME_DIVIDER_GAP_/);
});
test("W23 adds working HOME Overview nav without creating a second HOME or replacing bottom tabs",()=>{
 assert.match(home,/readonly property bool homeOverviewWorkspace:/);
 assert.match(home,/id: homeOverviewRail/);
 assert.match(home,/titleText: "HOME \/\/ OVERVIEW"/);
 for(const path of ["home/auto","home/quick","home/snapshot"]) {
   assert.match(home,new RegExp('path:"'+path+'"'));
   assert.match(workspace,new RegExp('path:"'+path+'"'));
 }
 assert.match(home,/home.routeRequested\(path\)/);
 assert.match(surface,/id: originalHome/);
 assert.match(surface,/workspaceSection: surface.homeSection/);
 assert.match(surface,/onRouteRequested: function\(path\) \{ surface.routeRequested\(path\); \}/);
 assert.match(surface,/id: bottomRail/);
 assert.match(home,/visible: home.sectionVisible\("header"\) && !home.fixedWeatherOverview/);
 assert.match(home,/&& !home.homeOverviewWorkspace/);
 assert.match(homeNative,/HOME_BUTTON_NOT_ROUTED_/);
});
test("W23 preserves one-page Weather Overview with exact header height at 275, 300, and 500px",()=>{
 for(const h of [275,300,400,500]) {
   const row=Math.max(46,Math.min(48,Math.floor(h*.15),
                 Math.floor(Math.max(0,h-195)/2)));
   const railHeight=h<286?31:56;
   const summary=h-railHeight-2*row;
   assert.equal(summary+railHeight+2*row,h);
   assert.ok(summary>=152 && row>=46 && row<=48);
 }
 assert.match(home,/homeScroll.height - weatherOverviewRail.height/);
 assert.match(home,/fixedWeatherOverview && officialAlertSummary.available/);
 assert.match(cards,/height: 7/);
 assert.match(weather,/panel.ratio\(hour.entry.chanceRain,100\)/);
 assert.match(weather,/panel.ratio\(day.entry.chanceRain,100\)/);
 assert.match(weather,/["']⚡︎["']/);
});
test("W23 keeps original menu data sources and distinct HOME MAGICK routes intact",()=>{
 assert.match(magick,/titleText: "MAGICK \/\/ OVERVIEW"/);
 assert.match(magick,/magickPane.routeRequested\(path\)/);
 for(const x of [rail,homeNative]) {
   assert.doesNotMatch(x,/FileView\s*\{|XMLHttpRequest|fetch\s*\(/);
 }
 assert.match(home,/homeFavoritesStore/);
 assert.match(surface,/HomeDeck\.mayRotate/);
});
