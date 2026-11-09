"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname,"../..");
const read = rel => fs.readFileSync(path.join(root,rel),"utf8");
const ground = read("widgets/weather/StationGround.qml");
const pane = read("widgets/weather/StationEarthSubjectPane.qml");
const fixture = read("tests/weather/fixtures/E5GroundNoScroll.qml");
test("E5 keeps only two EARTH GROUND routes non-scrolling, not CLASSIC or WEATHER",()=>{
    assert.match(ground,/compactEarthAir: subjectRoute === "earth\/ground\/air-pollen"/);
    assert.match(ground,/compactEarthEnvironment: subjectRoute === "earth\/ground\/environment"/);
    assert.match(ground,/compactEarthGround: compactEarthAir \|\| compactEarthEnvironment/);
    assert.match(ground,/interactive: !ground\.compactEarthGround/);
    assert.match(ground,/visible: !ground\.compactEarthGround && scrollable/);
    assert.match(ground,/requiredContentHeight:/);
    assert.match(ground,/contentHeight: Math\.max\(height, groundContent\.y \+ groundContent\.implicitHeight \+ 12\)/);
    assert.match(ground,/onSubjectRouteChanged: \{/);
    assert.match(pane,/subjectRoute: earthPane\.groundViewMode === "air-pollen"/);
    assert.equal((pane.match(/StationGround\s*\{/g)||[]).length,1);
});
test("E5 adjusts existing cards without changing the data meaning or source ownership",()=>{
    for(const token of [
        "compactEarthAir ? 106 : 166",
        "compactEarthAir ? 50 : 68",
        "compactEarthAir ? 18 : 22",
        "compactEarthEnvironment ? 82 : 112",
        "compactEarthEnvironment ? 78 : 112",
        "visible: !ground.compactEarthEnvironment || index < 2",
        "SHOWING 2 OF",
        "MORE: WEATHER / HAZARDS / ALERTS",
        "ground.airQualityForecast",
        "ground.pollenSpecies",
        "ground.recentSeismicEvents"
    ]) assert.ok(ground.includes(token),token);
    assert.match(ground,/title: "AIR \/\/ PARTICULATES"/);
    assert.match(ground,/title: "GASES \/\/ POLLEN"/);
    assert.match(ground,/title: "POLLEN \/\/ SPECIES"/);
    assert.match(ground,/title: "AIR \/\/ NEXT 12 HOURS"/);
    assert.match(ground,/title: "SEISMIC \/\/ WORLDWIDE 24H"/);
    assert.match(ground,/title: "HEAT \+ FIRE WEATHER \/\/ NWS CONTEXT"/);
    assert.doesNotMatch(pane,/WeatherServices\.|\bProcess\s*\{|\bFileView\s*\{/);
});
test("E5 native sample explicitly checks full-content fit in both no-scroll pages",()=>{
    for(const label of [
        "earth/ground/air-pollen","earth/ground/environment",
        "E5_NATIVE_PASS","E5_NATIVE_FAIL",
        "requiredContentHeight","ground.height",
        "earth-e5-ground-viewport","contentY",
        "airQualityForecast","alertList","events"
    ]) assert.ok(fixture.includes(label),label);
});
