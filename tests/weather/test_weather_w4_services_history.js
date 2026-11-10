const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function read(path) { return fs.readFileSync(path, "utf8"); }
const navText = read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const routeText = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const pane = read("widgets/weather/StationWeatherSubjectPane.qml");
const home = read("widgets/weather/StationHome.qml");
const chart = read("widgets/weather/WeatherTrendInspector.qml");
function policy(code) {
    const sandbox={};
    vm.runInNewContext(code.replace(/^\\.pragma library\\s*/m, ""), sandbox);
    return sandbox;
}

test("WEATHER has one final SERVICES tab and NOW + AIR is data-only", () => {
    const nav=policy(navText);
    const route=policy(routeText);
    const tabs=nav.GROUPS.weather;
    assert.equal(tabs.at(-1).key,"services");
    assert.equal(tabs.at(-1).path,"weather/services/health");
    assert.equal(nav.selectedGroup("weather/services/health"),"services");
    assert.equal(route.kindForRoute("weather/services/health"),"services");
    assert.equal(route.visibleFor("sky","weather/conditions/current","runtime"),false);
    assert.equal(route.visibleFor("sky","weather/conditions/current","current"),true);
    assert.equal(route.visibleFor("sky","weather/conditions/current","atmosphere"),true);
    assert.equal(route.visibleFor("sky","weather/services/sky","runtime"),false);
    assert.equal(route.visibleFor("ground","weather/services/ground","runtime"),false);
    for(const source of ["marine","coastal","river","lightning","astronomy"])
        assert.equal(route.needsSource("weather/services/ground",source),false);
});

test("SERVICES reuses existing telemetry without additional fetching", () => {
    assert.match(pane,/id: servicesPanel/);
    assert.match(pane,/weatherPane.kind === "services"/);
    assert.match(pane,/rows: weatherServicesSky.runtimeRows/);
    assert.match(pane,/rows: weatherServicesGround.runtimeRows/);
    assert.match(pane,/subjectRoute: "weather\\/services\\/sky"/);
    assert.match(pane,/subjectRoute: "weather\\/services\\/ground"/);
    assert.doesNotMatch(pane,/WeatherServices\\.|Process\\s*\\{|FileView\\s*\\{/);
});

test("HOME HISTORY improves the actual plot, keeps no-scroll minimum", () => {
    assert.match(home,/Math\\.max\\(72, Math\\.min\\(108, home\\.height - 188\\)\\)/);
    assert.match(home,/interactive: !home\\.compactHistory/);
    assert.match(chart,/height: inspector\\.compact \\? 36 : 94/);
    assert.match(chart,/visible: !inspector\\.compact/);
    assert.match(chart,/anchors\\.margins: inspector\\.compact \\? 3 : 7/);
});
