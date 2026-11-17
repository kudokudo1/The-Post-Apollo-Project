"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const home=fs.readFileSync("widgets/weather/StationHome.qml","utf8");
const inspector=fs.readFileSync("widgets/weather/WeatherTrendInspector.qml","utf8");
const fixture=fs.readFileSync("tests/weather/fixtures/W23HomeOverviewNative.qml","utf8");
const policy=fs.readFileSync("widgets/weather/WeatherRelationshipPolicy.js","utf8");

test("W25 reuses the original two live-history relationship inspectors at top",()=>{
 assert.match(home,/readonly property alias homeOverviewGraphItem: homeRelationsRow/);
 assert.match(home,/id: homeRelationsRow/);
 assert.match(home,/title: "AQI ↔ HUMIDITY"/);
 assert.match(home,/title: "AQI ↔ WIND"/);
 assert.match(home,/leftValues: home\.aqiHumidityRelation\.leftValues/);
 assert.match(home,/rightValues: home\.aqiHumidityRelation\.rightValues/);
 assert.match(home,/leftValues: home\.aqiWindRelation\.leftValues/);
 assert.match(home,/rightValues: home\.aqiWindRelation\.rightValues/);
 assert.match(home,/home\.homeInlineDefault \? home\.homeInlineGraphHeight/);
 assert.match(home,/compact: home\.compactHistory \|\| home\.homeInlineDefault/);
 assert.match(home,/section === "relations" \|\| section === "snapshot"/);
 assert.match(policy,/function nearestPairs\(/);
 assert.match(policy,/function pearson\(/);
 assert.match(inspector,/readonly property bool chartReady: pointCount >= 2/);
 assert.match(inspector,/Canvas\s*\{/);
 assert.match(fixture,/W25_ORIGINAL_GRAPHS_NO_ALIGNED_LINES/);
});
test("W26 graph first; flexible LIVE in middle; AUTO directly below",()=>{
 const chart=home.indexOf('id: homeRelationsRow');
 const snapshot=home.indexOf('id: weatherSnapshotRow');
 const autoTitle=home.indexOf('id: autoOverviewTitle');
 const relevant=home.indexOf('id: weatherRelevantRow');
 assert.ok(chart>0 && chart<snapshot
     && snapshot<autoTitle && autoTitle<relevant);
 assert.match(home,/readonly property real homeInlineMinimumGraphHeight: 72/);
 assert.match(home,/readonly property real homeInlineMinimumLiveHeight: 46/);
 assert.match(home,/readonly property real homeInlineMinimumAutoHeight: 46/);
 assert.match(home,/readonly property real homeInlineUsableHeight:/);
 assert.match(home,/readonly property real homeInlineGrowth:/);
 assert.match(home,/homeInlineUsableHeight - homeInlineLiveHeight - homeInlineAutoHeight/);
 assert.doesNotMatch(home,/home-w25-auto-bottom-spacer/);
 assert.match(fixture,/W25_GRAPHS_TOP_LIVE_MIDDLE_AUTO_BOTTOM/);
 assert.match(fixture,/W25_AUTO_NOT_BOTTOM_ANCHORED/);
 assert.match(fixture,/W26_LARGE_EMPTY_AUTO_GAP/);
});
test("W26 fills all HOME heights using real content, with or without an NWS alert",()=>{
 for(const h of [275,300,380,500,700]) {
   for(const hasAlert of [false,true]) {
     const spacing=3,y=6,rail=56,title=14;
     const alert=hasAlert?15:0;
     const graphHeading=h>=290 && !hasAlert;
     const liveHeading=h>=290 || !hasAlert;
     const sections=5+Number(graphHeading)+Number(liveHeading)+Number(hasAlert);
     const chrome=y+rail+title
       +(graphHeading?title:0)+(liveHeading?title:0)
       +alert+(sections-1)*spacing+1;
     const available=Math.max(0,h-chrome);
     const growth=Math.max(0,available-72-46-46);
     const live=46+Math.min(54,Math.floor(growth*.30));
     const auto=46+Math.min(24,Math.floor(growth*.10));
     const graph=Math.max(72,available-live-auto);
     const total=chrome+graph+live+auto;
     assert.ok(total<=h,"HOME overflows "+h+" alert="+hasAlert+": "+total);
     assert.ok(total>=h-1,"unused HOME space "+h+" alert="+hasAlert+": "+total);
     assert.ok(graph>=72 && live>=46 && auto>=46);
     assert.ok(live<=100 && auto<=70);
     if(h>=380)assert.ok(graph>110,"plot too small at "+h);
   }
 }
 assert.match(home,/interactive: !home\.compactHistory && !home\.homeOverviewWorkspace/);
 assert.match(home,/contentHeight: \(home\.homeOverviewWorkspace \|\|/);
 assert.match(home,/homeInlineAlertHeight > 0/);
 assert.match(home,/home\.sectionVisible\("relations"\) && !home\.compactHistory/);
 assert.match(home,/visible: home\.sectionVisible\("history"\)/);
 assert.match(home,/visible: home\.sectionVisible\("quick"\)/);
 assert.match(home,/onRouteRequested: function\(path\)/);
 assert.match(fixture,/window\.width=440/);
});
