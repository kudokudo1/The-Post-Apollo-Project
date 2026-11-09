"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"../..");
const read = rel => fs.readFileSync(path.join(root,rel),"utf8");
const groundPolicySource = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const earthPolicySource = read("widgets/weather/StationEarthSubjectPanelPolicy.js");
const ground = read("widgets/weather/StationGround.qml");
const pane = read("widgets/weather/StationEarthSubjectPane.qml");
const weatherPane = read("widgets/weather/StationWeatherSubjectPane.qml");
const navigator = read("widgets/weather/StationSubjectNavigationPolicy.js");
function policy(source) {
    const context = vm.createContext({});
    vm.runInContext(source.replace(/^\.pragma library\s*$/m,""),context);
    return context;
}
const gp = policy(groundPolicySource);
const ep = policy(earthPolicySource);
const nav = policy(navigator);

test("E4 EARTH GROUND has two non-overlapping source-backed screens",()=>{
    const environment = ["alerts","heat-fire","seismic"];
    const air = ["air-pm","air-gases","pollen","air-forecast","source"];
    const sections = [...new Set([...environment,...air,
        "lightning","runtime","rivers","marine","coast","header"])];
    for (const section of sections) {
        assert.equal(gp.visibleFor("ground","earth/ground/full",section),
            environment.includes(section),"legacy GROUND "+section);
        assert.equal(gp.visibleFor("ground","earth/ground/environment",section),
            environment.includes(section),"environment "+section);
        assert.equal(gp.visibleFor("ground","earth/ground/air-pollen",section),
            air.includes(section),"air/pollen "+section);
    }
    assert.equal(gp.kindForRoute("earth/ground/environment"),"ground");
    assert.equal(gp.kindForRoute("earth/ground/air-pollen"),"ground");
    assert.equal(ep.kindForRoute("earth/ground/full"),"ground");
    assert.ok(nav.findRoute("earth/ground/full"),
        "Existing bottom navigation and bookmarks preserved");
});

test("E4 moves visible lightning exclusively to the existing WEATHER hazard page",()=>{
    assert.equal(gp.visibleFor("ground","earth/ground/full","lightning"),false);
    assert.equal(gp.visibleFor("ground","earth/ground/environment","lightning"),false);
    assert.equal(gp.visibleFor("ground","earth/ground/air-pollen","lightning"),false);
    assert.equal(gp.needsSource("earth/ground/full","lightning"),false);
    assert.equal(ep.needsSource("earth/ground/full","lightning"),false);
    assert.equal(ep.needsSource("earth/maps/events","lightning"),true,
        "EARTH map's preexisting event context preserved");
    assert.equal(gp.visibleFor("ground","weather/hazards/lightning","lightning"),true);
    assert.equal(gp.needsSource("weather/hazards/lightning","lightning"),true);
    assert.equal(gp.visibleFor("ground","weather/hazards/lightning","seismic"),false);
    assert.ok(nav.findRoute("weather/hazards/lightning"));
    assert.match(weatherPane,/StationGround\s*\{/);
    assert.match(ground,/title: "LIGHTNING \/\/ NOAA NOWCOAST"/);
});

test("E4 retains one fixed two-tab header and original Ground renderer",()=>{
    assert.equal((pane.match(/StationGround\s*\{/g)||[]).length,1);
    assert.match(pane,/property string groundViewMode: "environment"/);
    assert.match(pane,/objectName: "earth-e4-ground-shell"/);
    assert.match(pane,/objectName: "earth-e4-ground-tabs"/);
    assert.match(pane,/objectName: "earth-e4-ground-divider"/);
    assert.match(pane,/objectName: "earth-e4-one-ground-renderer"/);
    assert.match(pane,/model: \[\s*\{key:"environment",label:"ENVIRONMENT"\},\s*\{key:"air-pollen",label:"AIR \/\/ POLLEN"\}/);
    assert.match(pane,/HeaderGeometry\.buttonWidth\(groundModes\.width,2\)/);
    assert.match(pane,/onClicked: earthPane\.groundViewMode = modelData\.key/);
    assert.match(pane,/subjectRoute: earthPane\.groundViewMode === "air-pollen"[\s\S]*?"earth\/ground\/air-pollen" : "earth\/ground\/environment"/);
    assert.match(pane,/anchors\.top: groundRule\.bottom/);
    assert.match(pane,/weatherService: earthPane\.weatherService/);
    assert.match(pane,/seismicSource: earthPane\.seismicSource/);
    assert.match(pane,/persistentCacheStore: earthPane\.persistentCacheStore/);
    assert.match(ground,/onSubjectRouteChanged: \{/);
    assert.doesNotMatch(pane,/WeatherServices\.|\bProcess\s*\{|\bFileView\s*\{/);
});

test("E4 keeps CLASSIC and WEATHER full-source legacy presentation unchanged",()=>{
    for(const section of ["lightning","alerts","heat-fire","air-pm",
       "air-gases","pollen","air-forecast","seismic","source"]) {
       assert.equal(gp.visibleFor("ground","",section),true,section);
       assert.equal(gp.visibleFor("ground","weather/ground/full",section),true,section);
    }
    assert.equal(gp.needsSource("weather/ground/full","lightning"),true);
    assert.equal(gp.needsSource("earth/ground/environment","seismic"),true);
    assert.equal(gp.needsSource("earth/ground/air-pollen","seismic"),false);
    assert.equal(gp.needsSource("earth/ground/air-pollen","lightning"),false);
});
