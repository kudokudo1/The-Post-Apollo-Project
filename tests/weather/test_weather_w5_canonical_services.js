"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = p => fs.readFileSync(p,"utf8");
const pane = read("widgets/weather/StationWeatherServicesPane.qml");
const owner = read("widgets/weather/StationWeatherSubjectPane.qml");
const runtime = read("services/weather/WeatherRuntimePolicy.js");

test("WEATHER SERVICES has a single dark fixed-header station surface",()=>{
  assert.match(pane,/Rectangle\s*\{[\s\S]*?objectName: "weather-w5-services-pane"[\s\S]*?color: Colors.black/);
  assert.match(pane,/import "StationSubjectHeaderGeometry.js" as HeaderGeometry/);
  assert.match(pane,/objectName: "weather-w5-fixed-header"/);
  assert.match(pane,/objectName: "weather-w5-status-strips"/);
  assert.match(pane,/objectName: "weather-w5-summary-cards"/);
  assert.match(pane,/objectName: "weather-w5-detail-scroll"/);
  assert.match(pane,/objectName: "weather-w5-selected-report"/);
  assert.match(pane,/anchors.top: fixedTop.bottom/);
  assert.match(pane,/anchors.bottom: selectedReport.top/);
  assert.match(pane,/boundsBehavior: Flickable.StopAtBounds/);
  assert.match(pane,/NeonScrollBar/);
});

test("Only source rows scroll; selected service report uses real owner rows",()=>{
  assert.match(pane,/readonly property var runtimeRows:/);
  assert.match(pane,/Object\.prototype\.hasOwnProperty\.call\(ids,id\)/);
  assert.match(pane,/RuntimePolicy\.summarizeRows\(runtimeRows\)/);
  assert.match(pane,/model: services\.runtimeRows/);
  assert.match(pane,/selectedServiceId = entry\.modelData\.id/);
  assert.match(pane,/RuntimePolicy\.rowStateLabel/);
  assert.match(pane,/RuntimePolicy\.rowAgeLabel/);
  assert.match(pane,/RuntimePolicy\.cadenceLabel/);
  assert.match(pane,/RuntimePolicy\.retentionLabel/);
  for (const name of ["READY","READING","CACHE","STALE","OFFLINE","ERROR"])
    assert.ok(pane.includes('label:"'+name+'"'));
  assert.match(owner,/StationWeatherServicesPane\s*\{/);
  assert.match(owner,/skyRows: weatherServicesSky\.item/);
  assert.match(owner,/groundRows: weatherServicesGround\.item/);
  assert.equal((owner.match(/StationSky\s*\{/g)||[]).length,1);
  assert.equal((owner.match(/StationGround\s*\{/g)||[]).length,1);
  assert.doesNotMatch(pane,/WeatherServices\.|Process\s*\{|FileView\s*\{/);
  assert.match(runtime,/function summarizeRows\(rows\)/);
});
