"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const full=read("StationWeatherInstrumentTerminal.qml");
const compact=read("StationWeatherOverviewCompactInstrument.qml");
const rail=read("StationSubjectOverviewRail.qml");
const home=read("StationHome.qml");
const magick=read("StationMagickSubjectPane.qml");
const cards=read("StationHomeMetricCard.qml");
const weatherNative=fs.readFileSync("tests/weather/fixtures/W9FixedWeatherTerminalNative.qml","utf8");
const overviewNative=fs.readFileSync("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml","utf8");
const magickNative=fs.readFileSync("tests/weather/fixtures/W21MagickOverviewNative.qml","utf8");

test("W22 NOW icon becomes smaller and moves toward center without losing original artwork",()=>{
 assert.match(full,/anchors.rightMargin: 16/);
 assert.match(full,/Math.min\(158,currentPanel.height\+4,/);
 assert.match(full,/largeCurrent.width\*0.72/);
 assert.match(full,/currentPanel.height \* 1.08/);
 assert.match(full,/scale: 1.25/);
 assert.match(compact,/anchors.rightMargin: 18/);
 assert.match(compact,/Math.min\(112,47 \+ panel.expansion \* 0.37,/);
 assert.match(compact,/currentIcon.width \* 1.34/);
 assert.match(full,/terminal.sky.conditionState.icon/);
 assert.match(compact,/WeatherCyclePolicy.nightKind/);
 assert.match(weatherNative,/W22_NOW_ICON_NOT_REDUCED_AND_LEFT_SHIFTED/);
});
test("W22 Weather and MAGICK Overview share the C44-style titled tab rail",()=>{
 assert.match(rail,/property string titleText:/);
 assert.match(rail,/property bool condensed:/);
 assert.match(rail,/buttonGap: HeaderGeometry.tabSpacing \+ 4/);
 assert.match(rail,/height: visible \? \(condensed \? 31 : 49\) : 0/);
 assert.match(rail,/id: railHeading/);
 assert.match(rail,/HeaderGeometry.titleHeight/);
 assert.match(rail,/font.pixelSize: 12/);
 assert.match(rail,/color: Colors.magenta/);
 assert.match(rail,/spacing: overviewRail.buttonGap/);
 assert.match(rail,/height: HeaderGeometry.ruleHeight/);
 assert.match(rail,/onClicked: overviewRail.routeRequested\(modelData.path\)/);
 assert.match(home,/titleText: "WEATHER \/\/ OVERVIEW"/);
 assert.match(home,/condensed: homeScroll.height < 286/);
 assert.match(magick,/titleText: "MAGICK \/\/ OVERVIEW"/);
 assert.match(magick,/visible: magickPane.subjectRoute !== "magick\/overview"/);
 assert.match(overviewNative,/W22_WEATHER_OVERVIEW_HEADER_MISSING/);
 assert.match(overviewNative,/W22_WEATHER_TAB_GAP_TOO_NARROW/);
 assert.match(magickNative,/W22_MAGICK_HEADER_MISSING/);
 assert.match(magickNative,/W22_MAGICK_TAB_GAP_TOO_NARROW/);
});
test("W22 title/gap stages do not remove one-page Weather Overview or lower card meters",()=>{
 function budget(h) {
   const row=Math.max(h<286?46:48,Math.min(51,Math.floor(h*.16),
                    Math.floor(Math.max(0,h-195)/2)));
   const railHeight=h<286?31:49;
   return {row,railHeight,summary:h-railHeight-2*row};
 }
 for(const h of [275,300,400,500]) {
   const v=budget(h);
   assert.equal(v.summary+v.railHeight+2*v.row,h);
   assert.ok(v.summary>=152);
   assert.ok(v.row>=46 && v.row<=51);
 }
 assert.equal(budget(275).railHeight,31);
 assert.equal(budget(300).railHeight,49);
 assert.equal(budget(500).summary,349);
 assert.match(home,/homeScroll.height - weatherOverviewRail.height/);
 assert.match(cards,/height: 7/);
 assert.match(compact,/panel.ratio\(hour.entry.chanceRain,100\)/);
 assert.match(compact,/panel.ratio\(day.entry.chanceRain,100\)/);
 assert.match(compact,/["']⚡︎["']/);
 for(const source of [rail,full,compact]) {
   assert.doesNotMatch(source,/Process\s*\{|FileView\s*\{|XMLHttpRequest|fetch\s*\(/);
 }
});
