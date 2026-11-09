"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const discovery=read("widgets/weather/StationDiscovery.qml");
const services=read("widgets/weather/StationEarthServicesPane.qml");
const earth=read("widgets/weather/StationEarthSubjectPane.qml");
const fixture=read("tests/weather/fixtures/E2EarthUnifiedNativeShell.qml");

test("E3 puts one fixed map-control deck between map and the independently scrolling records",()=>{
  assert.equal((discovery.match(/id: mapPlot\b/g)||[]).length,1);
  const map=discovery.indexOf("id: pinnedMapHost");
  const controls=discovery.indexOf("id: pinnedMapControls");
  const scroll=discovery.indexOf("id: discoveryScroll");
  assert.ok(map>=0 && map<controls && controls<scroll);
  assert.match(discovery,/objectName: "earth-e3-pinned-map-controls"/);
  assert.match(discovery,/anchors\.top: pinnedMapHost\.bottom/);
  assert.match(discovery,/anchors\.left: pinnedMapHost\.left/);
  assert.match(discovery,/anchors\.right: pinnedMapHost\.right/);
  assert.match(discovery,/anchors\.top: pinnedMapControls\.visible[\s\S]*?pinnedMapControls\.bottom : parent\.top/);
  assert.match(discovery,/height: visible \? 47 : 0/);
  assert.match(fixture,/root\.controlsY=controls\.mapToItem\(map,0,0\)\.y/);
  assert.match(fixture,/MAP_OR_E3_TOOLS_SCROLLED_OR_DUPLICATED/);
});

test("E3 keeps five map layers above and the actual display toggles below",()=>{
  for(const name of ["borders","states","places","quakes","gdacs","reset"])
    assert.ok(discovery.includes('"earth-e3-map-" + modelData'),name);
  assert.match(discovery,/model: \["borders","states","places","quakes","gdacs","reset"\]/);
  for(const field of ["mapShowCountryBorders","mapShowAdmin1","mapShowPlaces",
                       "mapShowEarthquakes","mapShowGdacs"])
    assert.ok(discovery.includes(field+" = !"+field),field);
  assert.match(discovery,/else if \(key === "reset"\) resetMapView\(\)/);
  assert.equal((discovery.match(/id: pinnedEarthFilters/g)||[]).length,1);
  assert.equal((discovery.match(/id: mapPlot\b/g)||[]).length,1);
});

test("E3 manual load and clear operate on the same services and preserve explicit consent",()=>{
  assert.match(discovery,/property string pinnedSourceMode: "mrms"/);
  for(const key of ["mrms","rainviewer","smoke","firms"])
    assert.ok(discovery.includes('key:"'+key+'"'),key);
  for(const action of ["loadRadarSnapshot","loadRainViewerFallback",
                        "loadSmokePolygons","fetchVisibleHotspots",
                        "clearRadarSnapshot","clearRainViewerFallback",
                        "clearSmokePolygons"])
    assert.ok(discovery.includes(action+"()"),action);
  assert.match(discovery,/firmsService\.configured && firmsAreaReady/);
  assert.match(discovery,/radarAreaReady && !mrmsRadarService\.loading/);
  assert.match(discovery,/!hmsSmokeService\.loading/);
  assert.match(discovery,/radarHistoryMinutes <= 120/);
  assert.match(discovery,/function nextPinnedRadarHistory\(\)/);
  assert.match(discovery,/function pinnedLoadSource\(\)/);
  assert.match(discovery,/function pinnedClearSource\(\)/);
  assert.match(discovery,/return false; \/\/ FIRMS previously had no clear action/);
  assert.equal((discovery.match(/WeatherServices\.GdacsService\s*\{/g)||[]).length,1);
  assert.equal((discovery.match(/WeatherServices\.FirmsHotspotService\s*\{/g)||[]).length,1);
  assert.equal((discovery.match(/WeatherServices\.MrmsRadarService\s*\{/g)||[]).length,1);
});

test("E3 removes redundant EONET category UI and ignores any hidden legacy category",()=>{
  assert.match(discovery,/id: mapFilterRail[\s\S]*?objectName: "earth-e3-legacy-eonet-filter"/);
  assert.match(discovery,/!stationDiscovery\.earthPinnedMap[\s\S]*?stationDiscovery\.earthLayerEnabled\("eonet"\)/);
  assert.match(discovery,/mapCategory: stationDiscovery\.earthPinnedMap[\s\S]*?\? "" : stationDiscovery\.mapCategoryForFilter\(/);
  assert.match(fixture,/legacyFilter\.visible/);
  assert.match(discovery,/function selectMapFilter\(id\)/);
});

test("E3 removes duplicate live runtime/source racks only from pinned EARTH MAP",()=>{
  assert.match(discovery,/objectName: "earth-e3-legacy-runtime-rack"/);
  assert.match(discovery,/objectName: "earth-e3-legacy-source-rack"/);
  assert.match(discovery,/visible: !stationDiscovery\.earthPinnedMap[\s\S]*?stationDiscovery\.weatherMapOnly/);
  assert.match(discovery,/rows: stationDiscovery\.runtimeRows/);
  assert.match(discovery,/model: stationDiscovery\.plannedSources/);
  assert.match(earth,/runtimeRows: earthLoader\.item \? earthLoader\.item\.runtimeRows : \[\]/);
  assert.match(earth,/sourceRows: earthLoader\.item \? earthLoader\.item\.plannedSources : \[\]/);
  assert.match(services,/LIVE FEED \/\/ RUNTIME/);
  assert.match(services,/LIVE FEED \/\/ CURRENT SOURCE REPORTS/);
  assert.match(services,/RuntimePolicy\.rowAgeLabel\(/);
  assert.match(services,/RuntimePolicy\.rowStateLabel\(/);
  assert.match(services,/RuntimePolicy\.cadenceLabel\(/);
  assert.match(fixture,/rack\.visible \|\| sources\.visible/);
});

test("E3 preserves old scrolling CLASSIC MAP tools outside the pinned route",()=>{
  assert.match(discovery,/function selectMapFilter\(id\)/);
  assert.match(discovery,/id: mapFilterRail/);
  assert.match(discovery,/!stationDiscovery\.earthPinnedMap/);
  assert.match(discovery,/onClicked: stationDiscovery\.mapShowCountryBorders =/);
  assert.match(discovery,/onClicked: stationDiscovery\.mapShowEarthquakes =/);
  assert.match(discovery,/onClicked: stationDiscovery\.fetchVisibleHotspots\(\)/);
  assert.match(discovery,/onClicked:\s*stationDiscovery\.loadRadarSnapshot\(\)/);
  assert.match(discovery,/onClicked:\s*stationDiscovery\.loadSmokePolygons\(\)/);
  assert.match(discovery,/ParentChange\s*\{/);
});
