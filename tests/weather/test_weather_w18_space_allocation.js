"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const home=fs.readFileSync("widgets/weather/StationHome.qml","utf8");
const instrument=fs.readFileSync("widgets/weather/StationWeatherOverviewCompactInstrument.qml","utf8");
const native=fs.readFileSync("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml","utf8");

// Match the actual QML height budget, including the minimum W17 instrument.
function heights(viewport) {
 const row=Math.max(55,Math.min(88,Math.floor(viewport*0.18),
                            Math.floor(Math.max(0,viewport-164)/2)));
 return {summary:viewport-2*row,row};
}
test("W18 gives tall Overview space to WEATHER rather than empty cards",()=>{
 assert.match(home,/readonly property real overviewCardRowHeight:/);
 assert.match(home,/readonly property real overviewInstrumentHeight:/);
 assert.match(home,/height: visible \? home\.overviewInstrumentHeight : 0/);
 assert.equal((home.match(/\? home\.overviewCardRowHeight : 118/g)||[]).length,2);
 for(const viewport of [275,300,500,650]) {
   const {summary,row}=heights(viewport);
   assert.equal(summary+2*row,viewport);
   assert.ok(summary>=164);
   assert.ok(row<=88);
 }
 assert.ok(heights(500).summary>=300);
 assert.ok(heights(500).row<heights(300).summary/2);
});
test("W18 expands existing icons, forecast sections, not replacing artwork or bars",()=>{
 assert.match(instrument,/readonly property real expansion: Math.max\(0, height - 164\)/);
 assert.match(instrument,/height: 52 \+ panel\.expansion \* 0\.50/);
 assert.match(instrument,/height: 45 \+ panel\.expansion \* 0\.33/);
 assert.match(instrument,/height: 24 \+ panel\.expansion \* 0\.17/);
 assert.match(instrument,/WeatherDockPolicy\.classify/);
 assert.match(instrument,/WeatherCelestialGlyph/);
 assert.match(instrument,/id: telemetryMeter/);
 assert.match(instrument,/id: hourMeter/);
 assert.match(instrument,/["']⚡︎["']/);
 assert.match(native,/window\.height=500/);
 assert.match(native,/OVERSIZED_EMPTY_CARDS/);
 assert.match(native,/TALL_WEATHER_INSTRUMENT_STILL_TINY/);
});
