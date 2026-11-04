"use strict";
// M26-F previously documented an unsynchronized duplicate Classic/EARTH map.
// M28-V removes that duplicate. Keep testing the surviving EARTH map and store.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const earth=read("widgets/weather/StationEarthSubjectPane.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const archive=read("services/weather/WeatherDossierArchiveStore.qml");

test("only the single SUBJECTS navigator hosts original map views",()=>{
  assert.match(station,/StationSubjectNavigator\s*\{\s*id:\s*subjectNavigator/);
  assert.ok(!station.includes("id: mapViewComponent"));
  assert.ok(!station.includes("weatherContentLoader"));
  assert.match(navigator,/StationEarthSubjectPane\s*\{/);
});
test("EARTH retains a route-scoped single original StationDiscovery loader",()=>{
  assert.match(earth,/Loader\s*\{\s*id:\s*earthLoader/);
  assert.match(earth,/active:\s*earthPane.visible\s*&&\s*earthPane.kind\s*===\s*"map"/);
  assert.match(earth,/sourceComponent:\s*earthMapComponent/);
  assert.match(earth,/id:\s*earthMapComponent[\s\S]*?StationDiscovery\s*\{/);
  assert.match(earth,/earthMapRoute:\s*earthPane.subjectRoute/);
  assert.match(discovery,/property var selectedMapGdacsEvent:\s*null/);
  assert.match(discovery,/property var selectedMapEarthquake:\s*null/);
});
test("unsaved map selection remains panel-local without cross-family mutation",()=>{
  for(const marker of ["selectedMap","selectedEventContext","selectedDossierPreview"])
    assert.ok(!station.includes(marker),marker);
  assert.ok(!navigator.includes("selectedDossierPreview"));
  assert.match(navigator,/function showNewsMentionsOnEarth\(payload\)/);
});
test("the single EARTH map uses the root's persistent dossier store",()=>{
  assert.equal((station.match(/dossierArchiveStore:\s*weatherStation\.dossierArchiveStore/g)||[]).length,1);
  assert.match(earth,/dossierArchiveStore:\s*earthPane.dossierArchiveStore/);
  assert.match(navigator,/dossierArchiveStore:\s*browser.dossierArchiveStore/);
  assert.match(archive,/weather-dossier-archive-v1\.json/);
});
test.todo("operator live reopen and map selection persistence acceptance");
