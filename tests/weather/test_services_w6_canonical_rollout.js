"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = path => fs.readFileSync(path,"utf8");
const navSource = read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const nav={};
vm.runInNewContext(navSource.replace(/^\.pragma library\s*$/m,""),nav);

const consoleQml=read("widgets/weather/StationServicesConsole.qml");
const home=read("widgets/weather/StationHome.qml");
const earth=read("widgets/weather/StationEarthServicesPane.qml");
const earthOwner=read("widgets/weather/StationEarthSubjectPane.qml");
const media=read("widgets/weather/StationMediaServicesPane.qml");
const mediaOwner=read("widgets/weather/StationMediaSubjectPane.qml");
const cosmos=read("widgets/weather/StationCosmosSpaceWeatherHubPane.qml");

test("W6 preserves every established final route and standardizes visible SERVICES naming",()=>{
  for (const family of ["home","weather","cosmos","earth","media"])
    assert.equal(nav.GROUPS[family].at(-1).label,"SERVICES",family);
  assert.equal(nav.GROUPS.home.at(-1).path,"home/health");
  assert.equal(nav.homeSectionFor("home/runtime"),"sources");
  assert.equal(nav.homeSectionFor("home/health"),"sources");
  assert.equal(nav.GROUPS.cosmos.at(-1).path,"cosmos/space-weather/overview");
  assert.equal(nav.selectedGroup("cosmos/space-weather/overview"),"space-weather");
  assert.equal(nav.GROUPS.tools[1].label,"SOURCES","TOOLS intentionally unchanged");
  assert.match(cosmos,/text: "COSMOS \/\/ SERVICES"/);
  assert.match(cosmos,/kind:"dashboard"/);
  assert.match(cosmos,/kind:"directory"/);
});

test("W6 canonical console retains WEATHER's palette and pins its sections",()=>{
  for(const text of [
    'objectName: "station-services-console"',
    'color: Colors.black',
    'objectName: "services-console-fixed-header"',
    'objectName: "services-console-summary-cards"',
    'objectName: "services-console-detail-scroll"',
    'objectName: "services-console-selected-report"',
    'anchors.top: fixedTop.bottom',
    'anchors.bottom: selectedReport.top',
    'boundsBehavior: Flickable.StopAtBounds',
    'NeonScrollBar',
    'StationHomeMetricCard {'
  ]) assert.ok(consoleQml.includes(text),text);
  assert.match(consoleQml,/model: services\.runtimeRows/);
  assert.match(consoleQml,/model: services\.directoryRows/);
  assert.match(consoleQml,/RuntimePolicy\.rowAgeLabel/);
  assert.match(consoleQml,/RuntimePolicy\.rowStateLabel/);
  assert.match(consoleQml,/RuntimePolicy\.cadenceLabel/);
  assert.match(consoleQml,/RuntimePolicy\.retentionLabel/);
  assert.doesNotMatch(consoleQml,/WeatherServices\.|Process\s*\{|FileView\s*\{|XMLHttpRequest|Timer\s*\{/);
});

test("W6 HOME keeps all six original provider health cards but shrinks and pins them",()=>{
  assert.match(home,/StationServicesConsole\s*\{/);
  assert.match(home,/objectName: "home-w6-services-console"/);
  assert.match(home,/homeCards: true/);
  assert.match(home,/home\.sourceHealthRows\.map/);
  assert.match(home,/label: row\.title/);
  assert.match(home,/value: row\.state/);
  assert.match(home,/detail: row\.detail/);
  assert.match(home,/footer: row\.footer/);
  assert.match(home,/visible: !home\.sourcesWorkspace/);
  assert.match(home,/model: home\.sourceHealthRows/);
  assert.equal((home.match(/StationHome\s*\{/g)||[]).length,0);
});

test("W6 EARTH uses original MAP runtime and source snapshots, not new polling",()=>{
  assert.match(earth,/StationServicesConsole\s*\{/);
  assert.match(earth,/familyLabel: "EARTH"/);
  assert.match(earth,/runtimeRows: services\.runtimeRows/);
  assert.match(earth,/directoryRows: services\.sourceDirectory/);
  assert.match(earth,/sourceRows: \[\]/);
  assert.match(earthOwner,/runtimeRows: earthLoader\.item \? earthLoader\.item\.runtimeRows : \[\]/);
  assert.match(earthOwner,/sourceRows: earthLoader\.item \? earthLoader\.item\.plannedSources : \[\]/);
  assert.doesNotMatch(earth,/WeatherServices\.|StationDiscovery\s*\{|Process\s*\{|FileView\s*\{/);
});

test("W6 MEDIA combines source ownership and last-observed diagnostics without reactivating NEWS",()=>{
  assert.match(media,/StationServicesConsole\s*\{/);
  assert.match(media,/embeddedHeader: services\.embeddedHeader/);
  assert.match(media,/directoryRows: services\.directoryRows/);
  assert.match(media,/GDELT \/\/ SOURCE RACK \/\/ LAST OBSERVED/);
  assert.match(media,/NOT MOUNTED ON SERVICES/);
  assert.match(media,/LAST OBSERVED \/\/ /);
  assert.match(media,/newsObservedMs>0/);
  assert.match(media,/Catalog\.channels\.length/);
  assert.match(media,/Object\.keys\(MediaPolicy\.ROUTES\)\.length/);
  assert.match(mediaOwner,/lastNewsRuntimeRows = runtime\.map/);
  assert.match(mediaOwner,/lastNewsSourceRows = sources\.map/);
  assert.doesNotMatch(media,/StationPublisherFeeds\s*\{|StationDiscovery\s*\{|StationRadio\s*\{|StationNewsHub\s*\{|Process\s*\{|XMLHttpRequest/);
});
