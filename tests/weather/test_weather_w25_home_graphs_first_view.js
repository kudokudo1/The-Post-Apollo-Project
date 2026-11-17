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
test("W25 graph first; concise LIVE in middle; AUTO anchored bottom",()=>{
 const chart=home.indexOf('id: homeRelationsRow');
 const snapshot=home.indexOf('id: weatherSnapshotRow');
 const spacer=home.indexOf('objectName: "home-w25-auto-bottom-spacer"');
 const relevant=home.indexOf('id: weatherRelevantRow');
 assert.ok(chart>0 && chart<snapshot && snapshot<spacer && spacer<relevant);
 assert.match(home,/readonly property real homeInlineGraphHeight: 72/);
 assert.match(home,/readonly property real homeInlineLiveHeight: 46/);
 assert.match(home,/readonly property real homeInlineAutoHeight: 46/);
 assert.match(home,/readonly property real homeInlineAutoSpacerHeight:/);
 assert.match(home,/homeScroll\.height-homeInlineFixedContentHeight/);
 assert.match(home,/visible: home\.homeInlineDefault\s+&& home\.homeInlineAutoSpacerHeight > 0/);
 assert.match(fixture,/W25_GRAPHS_TOP_LIVE_MIDDLE_AUTO_BOTTOM/);
 assert.match(fixture,/W25_AUTO_NOT_BOTTOM_ANCHORED/);
 assert.match(fixture,/W25_CARD_ROWS_NOT_COMPACT/);
});
test("W25 fits 275 and 300 tall, with and without NWS alert, leaving original other views",()=>{
 for(const h of [275,300,380,500]) {
   for(const hasAlert of [false,true]) {
     const spacing=3,y=6,rail=56,graph=72,live=46,auto=46,title=14;
     const alert=hasAlert?15:0;
     const graphHeading=h>=290 && !hasAlert;
     const liveHeading=h>=290 || !hasAlert;
     const sections=5+Number(graphHeading)+Number(liveHeading)+Number(hasAlert);
     const fixed=y+rail+graph+live+auto+title
       +(graphHeading?title:0)+(liveHeading?title:0)
       +alert+(sections-1)*spacing;
     const spacer=Math.max(0,h-fixed-spacing-1);
     const total=fixed+(spacer>0?spacer+spacing:0);
     assert.ok(total<=h, "HOME overflows "+h+" alert="+hasAlert+": "+total);
     assert.ok(total>=h-10,"AUTO not bottom "+h+" alert="+hasAlert+": "+total);
     assert.ok(live>=46 && auto>=46);
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
