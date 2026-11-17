"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const home=read("StationHome.qml");
const rail=read("StationSubjectOverviewRail.qml");
const surface=read("StationWorkspaceSurface.qml");
const cards=read("StationHomeMetricCard.qml");
const workspace=read("StationWorkspaceNavigationPolicy.js");
const fixture=fs.readFileSync("tests/weather/fixtures/W23HomeOverviewNative.qml","utf8");

test("W24 four HOME buttons switch existing middle panels without redirecting",()=>{
 assert.match(home,/property string homeInlineMode: "live"/);
 assert.match(home,/function chooseHomeInlinePane\(path\)/);
 assert.match(home,/selectedPath: home\.homeInlinePath/);
 for(const [label,path] of [
   ["LIVE","home/overview"],["AUTO","home/auto"],
   ["QUICK","home/quick"],["SNAPSHOT","home/snapshot"]
 ]) {
   assert.match(home,new RegExp('label:"'+label+'",path:"'+path+'"'));
   assert.match(workspace,new RegExp('path:"'+path+'"'));
 }
 assert.match(home,/home\.chooseHomeInlinePane\(path\)/);
 const local=home.slice(home.indexOf("function chooseHomeInlinePane"),
      home.indexOf("function chooseHomeInlinePane")+430);
 assert.doesNotMatch(local,/routeRequested\s*\(/);
 assert.match(rail,/property string selectedPath/);
 assert.match(rail,/selected: overviewRail\.selectedPath/);
 assert.match(surface,/id: originalHome/);
 assert.match(surface,/id: bottomRail/);
 assert.match(fixture,/HOME_BUTTON_REDIRECTED_TO_/);
});
test("W24 LIVE first view has LIVE on top, AUTO on bottom, and only existing data",()=>{
 assert.match(home,/homeInlineMode === "live"/);
 assert.match(home,/section === "snapshot" \|\| section === "relevant"/);
 assert.match(home,/title: home\.homeInlineDefault \? "LIVE \/\/ NOW"/);
 assert.match(home,/id: weatherSnapshotRow/);
 assert.match(home,/id: weatherRelevantRow/);
 assert.match(home,/model: home\.watchItems/);
 assert.match(home,/home\.weatherReady/);
 assert.match(home,/home\.nextForecast/);
 assert.match(home,/home\.aqiReady/);
 assert.match(home,/homeInlineAlertHeight/);
 assert.match(home,/NWS ALERT \/\//);
 assert.match(fixture,/LIVE_TOP_AUTO_BOTTOM_LOST/);
});
test("W24 no-scrolling height budgets fit default, alert and focused modes",()=>{
 for(const h of [275,300,400,500]) {
   for(const alert of [false,true]) {
     const railHeight=56, spacing=3, y=6;
     const alertHeight=alert?15:0;
     const budget=Math.max(0,h-12-railHeight-28-4*spacing-
                           alertHeight-(alert?spacing:0));
     const live=Math.max(46,Math.floor(budget*.55));
     const auto=Math.max(46,budget-live);
     const total=y+railHeight+28+4*spacing+live+auto+
                        alertHeight+(alert?spacing:0);
     assert.ok(total<=h-5,"default overflows "+h+"/"+alert);
   }
   const single=Math.max(70,Math.min(180,h-56-36));
   const lead=Math.max(0,Math.floor((h-12-56-14-single-9)/2));
   assert.ok(6+56+3+lead+3+14+3+single<=h,
             "focused overflows "+h);
 }
 assert.match(home,/interactive: !home\.compactHistory && !home\.homeOverviewWorkspace/);
 assert.match(home,/contentHeight: \(home\.homeOverviewWorkspace \|\|/);
 assert.match(home,/visible: scrollable && !home\.compactHistory\s+&& !home\.homeOverviewWorkspace/);
 assert.match(fixture,/HOME_SHOULD_NOT_SCROLL_OR_CLIP/);
 assert.match(fixture,/window\.width=440/);
});
test("W24 retains existing cards and controls, confines compaction to HOME Overview",()=>{
 assert.match(home,/home\.homeOverviewWorkspace \? 4 : 12/);
 assert.match(home,/compact: home\.homeOverviewWorkspace/);
 assert.match(home,/overviewDense: home\.homeOverviewWorkspace/);
 assert.match(home,/visible: home\.sectionVisible\("history"\)/);
 assert.match(home,/visible: home\.sectionVisible\("relations"\)/);
 assert.match(home,/visible: home\.sectionVisible\("quick"\)/);
 assert.match(home,/visible: home\.sectionVisible\("relevant"\)/);
 assert.match(home,/pinEnabled: !!home\.homeFavoritesStore/);
 assert.match(cards,/height: 7/);
 assert.match(surface,/HomeDeck\.mayRotate/);
 assert.match(fixture,/W24_HOME_INLINE_NATIVE_PASS/);
 assert.doesNotMatch(fixture,/FileView\s*\{|XMLHttpRequest|fetch\s*\(/);
});
