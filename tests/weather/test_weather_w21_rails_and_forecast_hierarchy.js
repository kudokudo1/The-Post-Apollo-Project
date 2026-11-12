"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const rail=read("StationSubjectOverviewRail.qml");
const home=read("StationHome.qml");
const weatherHost=read("StationWeatherSubjectPane.qml");
const magick=read("StationMagickSubjectPane.qml");
const full=read("StationWeatherInstrumentTerminal.qml");
const overview=read("StationWeatherOverviewCompactInstrument.qml");
const card=read("StationHomeMetricCard.qml");
const header=read("StationSubjectHeaderGeometry.js");
const native=fs.readFileSync("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml","utf8");

test("W21 shares full-width C44 cyan-divider navigation across WEATHER and MAGICK",()=>{
  assert.match(rail,/id: overviewRail/);
  assert.match(rail,/id: longButtons/);
  assert.match(rail,/overviewRail.buttonGap/);
  assert.match(rail,/HeaderGeometry.ruleHeight/);
  assert.match(rail,/color: Colors.cyan/);
  assert.match(rail,/onClicked: overviewRail.routeRequested\(modelData.path\)/);
  assert.match(header,/var tabSpacing = 4/);
 assert.match(rail,/property string titleText:/);
 assert.match(rail,/id: railHeading/);
  assert.match(home,/id: weatherOverviewRail/);
  assert.match(home,/weather-w21-overview-top-rail/);
  assert.match(weatherHost,/onRouteRequested: function\(path\)/);
  assert.match(magick,/id: magickOverviewRail/);
  assert.match(magick,/magick-w21-overview-top-rail/);
  assert.match(magick,/onRouteRequested: function\(path\)/);
  const expected=[
    [home,"weather/conditions/current"],[home,"weather/forecasts/hourly"],
    [home,"weather/hazards/alerts"],[magick,"magick/lunar-solar/moon"],
    [magick,"magick/astrology/charts"],
    [magick,"magick/planetary/correspondences"]
  ];
  for(const [source,path] of expected)
    assert.ok(source.includes('path:"'+path+'"'),"missing real route "+path);
  assert.match(native,/W21_OVERVIEW_RAIL_MISSING/);
  assert.match(native,/W21_RAIL_BUTTON_NOT_FULL_WIDTH/);
});
test("W21 transfers full Weather NOW space to six forecast readings without replacing glyphs",()=>{
  assert.match(full,/Math.round\(budget\*0.48\)/);
  assert.match(full,/Math.round\(budget\*0.42\)/);
  assert.match(full,/currentPanel.height \* 1.08/);
  assert.match(full,/scale: 1.25/);
  assert.match(full,/terminal.sky.conditionState.icon/);
  assert.match(full,/id: hourInstrumentStack/);
  assert.match(full,/id: dayRainMeter/);
  assert.doesNotMatch(full,/Process\s*\{|FileView\s*\{|Timer\s*\{|XMLHttpRequest/);
});
test("W21 fits Overview rail and supporting cards into compact and tall viewports",()=>{
  const budget=h=>{
    const row=Math.max(h<286?46:48,Math.min(51,Math.floor(h*.16),
                             Math.floor(Math.max(0,h-195)/2)));
    const railHeight=h<286?31:49;
    const summary=h-railHeight-2*row;
    return {row,summary,railHeight,deficit:Math.max(0,164-summary)};
  };
  for(const h of [275,300,500]){
    const a=budget(h);
    assert.equal(a.summary+2*a.row+a.railHeight,h);
    assert.ok(a.row<=51);
    assert.ok(a.summary>=152);
  }
  assert.equal(budget(500).row,51);
  assert.ok(budget(500).summary>=349);
  assert.match(home,/weatherOverviewRail.height/);
  assert.match(overview,/compactDeficit: Math.max\(0,164-height\)/);
  assert.match(overview,/Math.max\(0,panel.compactDeficit-8\)/);
  assert.match(overview,/id: hourMeter/);
  assert.match(overview,/id: dayRainMeter/);
});
test("W21 makes Overview NOW art bigger, three-day art smaller, leaves lower data bars alone",()=>{
  assert.match(overview,/Math.min\(112,47 \+ panel.expansion \* 0.37,/);
  assert.match(overview,/Math.min\(156,currentIcon.width \* 1.34\)/);
  assert.match(overview,/scale: 1.25/);
  assert.match(overview,/width: parent.width\*0.49-6/);
  assert.match(overview,/anchors.rightMargin: 18/);
  assert.match(overview,/Math.min\(35,20 \+ \(dayStrip.height - 24\) \* 0.54\)/);
  assert.match(overview,/Math.min\(40,22 \+ panel.expansion \* 0.11\)/);
  assert.match(overview,/["']⚡︎["']/);
  assert.match(card,/height: 7/);
  assert.match(card,/property real meterValue: 0/);
  assert.match(home,/overviewDense: home.fixedWeatherOverview/);
});
