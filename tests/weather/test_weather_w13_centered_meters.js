"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const src = fs.readFileSync("widgets/weather/StationWeatherCombinedPane.qml","utf8");

test("W13 keeps original weather categories but centers terminal heading",()=>{
 assert.match(src,/id: terminalHeading/);
 assert.match(src,/id: terminalTitle/);
 assert.match(src,/text: "WEATHER \/\/ CONDITIONS \+ HOURLY \+ DAILY"/);
 assert.match(src,/horizontalAlignment: Text.AlignHCenter/);
 assert.match(src,/verticalAlignment: Text.AlignVCenter/);
 assert.match(src,/text: panel.currentReady \? "WEATHER ONLINE" : "CURRENT WAITING"/);
});

test("W13 current and air/wind telemetry form vertically centered readout stacks",()=>{
 assert.match(src,/id: conditionStack/);
 assert.match(src,/id: metricStack/);
 assert.match(src,/anchors.verticalCenter: parent.verticalCenter/);
 assert.match(src,/id: conditionCaption/);
 assert.match(src,/id: metricCaption/);
 assert.match(src,/id: temperatureBar/);
 assert.match(src,/id: metricMeter/);
 assert.match(src,/panel.sky.temperatureMeter/);
 assert.match(src,/panel.sky.aqiMeter/);
 assert.match(src,/panel.sky.humidityMeter/);
 assert.match(src,/panel.sky.windMeter/);
 assert.match(src,/panel.sky.windAngle\(/);
 assert.match(src,/sky.currentCelestialMode/);
});

test("W13 hours keep glyph, rain reading and meter adjacent instead of bottom-anchored",()=>{
 assert.match(src,/id: hourTime/);
 assert.match(src,/id: hourArtwork/);
 assert.match(src,/id: hourlyRainReading/);
 assert.match(src,/id: hourlyRainMeter/);
 assert.match(src,/anchors.top: hourTime.bottom/);
 assert.match(src,/anchors.top: hourArtwork.bottom/);
 assert.match(src,/anchors.top: hourlyRainReading.bottom/);
 assert.doesNotMatch(src,/id: hourlyRainMeter\s+anchors.bottom: parent.bottom/);
 assert.match(src,/panel.chanceRatio\(hourCell.entry.chanceRain\)/);
 assert.match(src,/panel.sky.inspectedHourIndex=index/);
});

test("W13 remains one original SKY source, no extra fetcher or clock",()=>{
 const pane=fs.readFileSync("widgets/weather/StationWeatherSubjectPane.qml","utf8");
 assert.match(pane,/sky: originalSky/);
 assert.match(pane,/weatherService: weatherPane.weatherService/);
 assert.equal((pane.match(/StationSky\s*\{/g)||[]).length,1);
 assert.doesNotMatch(src,/Process\s*\{|Timer\s*\{|XMLHttpRequest|FileView\s*\{|fetch\(/);
});
