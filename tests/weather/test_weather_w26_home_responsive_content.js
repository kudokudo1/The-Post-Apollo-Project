"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const home=fs.readFileSync("widgets/weather/StationHome.qml","utf8");
const trend=fs.readFileSync("widgets/weather/WeatherTrendInspector.qml","utf8");
const card=fs.readFileSync("widgets/weather/StationHomeMetricCard.qml","utf8");
const native=fs.readFileSync("tests/weather/fixtures/W23HomeOverviewNative.qml","utf8");

function budget(height, alert=false) {
  const relationHeading=height>=290 && !alert;
  const liveHeading=height>=290 || !alert;
  const sectionCount=5+Number(relationHeading)+Number(liveHeading)+Number(alert);
  const chrome=6+56+14+(relationHeading?14:0)
    +(liveHeading?14:0)+(alert?15:0)+(sectionCount-1)*3+1;
  const remaining=Math.max(0,height-chrome);
  const growth=Math.max(0,remaining-72-46-46);
  const live=46+Math.min(54,Math.floor(growth*.30));
  const auto=46+Math.min(24,Math.floor(growth*.10));
  const graph=Math.max(72,remaining-live-auto);
  return {height,alert,chrome,remaining,growth,live,auto,graph,
          bottom:chrome+live+auto+graph};
}

test("W26 only HOME default redistributes height instead of using spacer",()=>{
  assert.match(home,/readonly property real homeInlineChromeHeight:/);
  assert.match(home,/readonly property real homeInlineUsableHeight:/);
  assert.match(home,/readonly property real homeInlineGrowth:/);
  assert.match(home,/readonly property real homeInlineGraphHeight: Math.max/);
  assert.match(home,/homeInlineUsableHeight - homeInlineLiveHeight - homeInlineAutoHeight/);
  assert.match(home,/homeInlineGrowth \* 0.30/);
  assert.match(home,/homeInlineGrowth \* 0.10/);
  assert.doesNotMatch(home,/homeInlineAutoSpacerHeight|home-w25-auto-bottom-spacer/);
  assert.match(home,/home\.homeInlineDefault \? home\.homeInlineGraphHeight/);
  assert.match(home,/home\.homeInlineDefault \? home\.homeInlineLiveHeight/);
  assert.match(home,/home\.homeInlineDefault \? home\.homeInlineAutoHeight/);
  assert.match(native,/W26_LARGE_EMPTY_AUTO_GAP/);
  assert.match(native,/W26_UNUSED_VERTICAL_VIEWPORT_SPACE/);
});
test("W26 original line plots expand with graphs and HISTORY plot stays unchanged",()=>{
  assert.match(trend,/property bool fluidCompactPlot: false/);
  assert.match(trend,/readonly property alias plotAreaItem: plotArea/);
  assert.match(trend,/height: inspector\.compact\s+\? \(inspector\.fluidCompactPlot/);
  assert.match(trend,/Math.max\(36,inspector.height - 36\) : 36/);
  assert.match(trend,/onHeightChanged: chart\.requestPaint\(\)/);
  assert.match(home,/fluidCompactPlot: home\.homeInlineDefault/g);
  assert.match(home,/leftValues: home\.aqiHumidityRelation\.leftValues/);
  assert.match(home,/rightValues: home\.aqiWindRelation\.rightValues/);
  assert.match(native,/W26_GRAPH_PLOT_STILL_FIXED_36PX_/);
});
test("W26 uses full 275–700px viewport with no dead gaps or oversized cards",()=>{
  for(const height of [275,300,360,380,500,700]) {
    for(const alert of [false,true]) {
      const b=budget(height,alert);
      assert.ok(b.graph>=72 && b.live>=46 && b.auto>=46);
      assert.ok(b.live<=100 && b.auto<=70);
      assert.ok(b.bottom<=height && height-b.bottom<=1,
        JSON.stringify(b));
    }
  }
  assert.ok(budget(500).graph>budget(380).graph);
  assert.ok(budget(380).graph>budget(300).graph);
  assert.ok(budget(380).live>budget(300).live);
  assert.match(home,/interactive: !home\.compactHistory && !home\.homeOverviewWorkspace/);
  assert.match(home,/contentHeight: \(home\.homeOverviewWorkspace \|\|/);
  assert.match(native,/window.height=500/);
  assert.match(native,/W26_HOME_RESPONSIVE_NATIVE_PASS/);
});
test("W26 preserves original weather/relevance data, meters, navigation and alerts",()=>{
  assert.match(home,/title: "AQI ↔ HUMIDITY"/);
  assert.match(home,/title: "AQI ↔ WIND"/);
  assert.match(home,/id: weatherSnapshotRow/);
  assert.match(home,/id: weatherRelevantRow/);
  assert.match(home,/NWS ALERT \/\//);
  assert.match(home,/home\.chooseHomeInlinePane\(path\)/);
  assert.match(home,/homeInlineMode === "live"/);
  assert.match(home,/id: homeQuickRow/);
  assert.match(home,/home\.homeFavoritesStore\.toggleCardFavorite\(/);
  assert.match(card,/height: 7/);
  assert.match(trend,/Canvas\s*\{/);
  assert.match(native,/HOME_BUTTON_REDIRECTED_TO_/);
});
