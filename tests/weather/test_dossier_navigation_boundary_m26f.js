"use strict";

// M26-F boundary audit. A PASS means the KNOWN CLASSIC/EARTH gap has been
// identified precisely, not that cross-mode continuity is implemented.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const station=read("widgets/weather/WeatherStationW.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const earth=read("widgets/weather/StationEarthSubjectPane.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const archive=read("services/weather/WeatherDossierArchiveStore.qml");

test("CLASSIC MAP loader is deactivated when SUBJECTS opens",()=>{
  assert.match(station,/Loader\s*\{\s*id:\s*weatherContentLoader[\s\S]*?active:\s*!weatherStation\.subjectNavigationOpen/);
  assert.match(station,/id:\s*mapViewComponent[\s\S]*?StationDiscovery\s*\{/);
  assert.match(station,/function openSubjectNavigation\(\)[\s\S]*?subjectNavigationOpen\s*=\s*true/);
  assert.match(station,/StationSubjectNavigator\s*\{\s*id:\s*subjectNavigator/);
});

test("EARTH has a separate, internally persistent MAP loader",()=>{
  assert.match(navigator,/StationEarthSubjectPane\s*\{/);
  assert.match(earth,/Loader\s*\{\s*id:\s*earthLoader/);
  assert.match(earth,/active:\s*earthPane.visible\s*&&\s*earthPane.kind\s*===\s*"map"/);
  assert.match(earth,/sourceComponent:\s*earthMapComponent/);
  assert.match(earth,/id:\s*earthMapComponent[\s\S]*?StationDiscovery\s*\{/);
  assert.match(earth,/earthMapRoute:\s*earthPane.subjectRoute/);
  assert.match(discovery,/property var selectedMapGdacsEvent:\s*null/);
  assert.match(discovery,/property var selectedMapEarthquake:\s*null/);
});

test("selections and unsaved preview are not handed across CLASSIC/EARTH",()=>{
  // The parent and navigator have neither a selected-event relay nor a
  // snapshot/restoration contract. A second StationDiscovery begins with
  // null selectedMap fields. This assertion documents a missing feature.
  assert.equal(station.includes("selectedMap"),false);
  assert.equal(station.includes("selectedEventContext"),false);
  assert.equal(station.includes("selectedDossierPreview"),false);
  assert.equal(navigator.includes("selectedMap"),false);
  assert.equal(navigator.includes("selectedDossierPreview"),false);
  console.log("M26F_BLOCKED // CLASSIC_EARTH_SELECTION_HANDOFF_NOT_IMPLEMENTED");
});

test("saved dossier store is shared across CLASSIC and EARTH",()=>{
  const injections=(station.match(/dossierArchiveStore:\s*weatherStation\.dossierArchiveStore/g)||[]);
  assert.ok(injections.length>=2,"both root MAP and subject navigator require shared store");
  assert.match(earth,/dossierArchiveStore:\s*earthPane.dossierArchiveStore/);
  assert.match(navigator,/dossierArchiveStore:\s*browser.dossierArchiveStore/);
  assert.match(archive,/weather-dossier-archive-v1\.json/);
  console.log("M26F_SHARED // PERSISTENT_DOSSIER_STORE_BOTH_VIEW_FAMILIES");
});

test.todo("CLASSIC ↔ EARTH event/preview handoff requires an owning production change");
