"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const earthPolicy=read("widgets/weather/StationEarthSubjectPanelPolicy.js");
const navigation=read("widgets/weather/StationSubjectNavigationPolicy.js");
const workspace=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const pane=read("widgets/weather/StationEarthSubjectPane.qml");
const original=read("widgets/weather/StationDiscovery.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
function load(src){
  const out=vm.createContext({});
  vm.runInContext(src.replace(/^\.pragma library\s*$/m,""),out);
  return out;
}
const earth=load(earthPolicy),nav=load(navigation),tabs=load(workspace);
const FULL="earth/maps/full";

test("M28-S full MAP is one native EARTH route, original 10 routes remain",()=>{
  assert.equal(Object.keys(earth.ROUTES).length,11);
  assert.equal(Object.keys(earth.ROUTES).filter(route=>!earth.isFullMap(route)).length,10);
  assert.equal(earth.kindForRoute(FULL),"map");
  assert.equal(earth.isFullMap(FULL),true);
  for(const path of ["earth/maps/overview","earth/overview","earth/geology/earthquakes",
                     "earth/investigations/context","earth/events/gdacs"]){
    assert.equal(earth.isFullMap(path),false,path+" must remain source-filtered");
  }
  for(const invalid of ["",null,undefined,"earth/maps/missing","weather/maps",
                         "media/news/reports","earth/maps/full/extra"]){
    assert.equal(earth.isFullMap(invalid),false);
    if(invalid!=="")assert.equal(earth.kindForRoute(invalid),"");
  }
  const node=nav.findRoute(FULL);
  assert.ok(node && node.group===false && node.subject==="earth");
  assert.equal(earth.routeLabel(FULL),"MAP // ALL ORIGINAL INSTRUMENTS");
  assert.equal(nav.findRoute("earth/maps").group,true);
  assert.equal(Object.keys(nav.PANELS).length,103,"historical source-control ledger unchanged");
  assert.equal(nav.PANELS["map-spatial-canvas"],"earth/maps/overview");
  assert.equal(nav.LEGACY_MODES.map,"earth/maps/overview");
});

test("EARTH bottom MAP // ALL is a real clickable native mode, original seven retained",()=>{
  const modes=JSON.parse(JSON.stringify(tabs.tabsFor(FULL)));
  assert.equal(modes.length,8);
  const full=modes.find(row=>row.key==="map");
  assert.deepEqual(full,{label:"MAP // ALL",path:FULL,key:"map"});
  assert.equal(tabs.familyFor(FULL),"earth");
  assert.equal(tabs.selectedGroup(FULL),"map");
  assert.equal(new Set(modes.map(x=>x.path)).size,modes.length);
  assert.deepEqual(modes.filter(x=>x.key!=="map").map(x=>x.path),
    ["earth/overview","earth/geography/basemap","earth/geology/earthquakes",
     "earth/events/eonet","earth/fires/hotspots","earth/maps/overview",
     "earth/investigations/context"]);
  assert.match(surface,/model: surface\.activeTabs/);
  assert.match(surface,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
});

test("exact MAP full route uses same original StationDiscovery with both map filters off",()=>{
  assert.equal((pane.match(/StationDiscovery\s*\{/g)||[]).length,1);
  assert.match(pane,/sourceComponent: earthMapComponent/);
  assert.match(pane,/earthMapOnly: !EarthPanelPolicy\.isFullMap\(earthPane\.subjectRoute\)/);
  assert.match(pane,/earthMapRoute: earthPane\.subjectRoute/);
  assert.match(pane,/stationOpen: earthPane\.visible/);
  assert.match(pane,/domain: "map"/);
  for(const binding of ["seismicSource","lightningSource","riverSource","weatherService",
                        "persistentCacheStore","eventArchiveStore","dossierArchiveStore"])
    assert.ok(pane.includes(binding+": earthPane."+binding),binding);
  for(const token of [
    "property bool earthMapOnly: false","property bool weatherMapOnly: false",
    "function earthLayerEnabled(layer)","function weatherLayerEnabled(layer)",
    "id: mapCanvasSection","id: mapFilterRail","id: mapPanArea",
    "SOURCE RACK // WHAT IS CONNECTED","SPATIAL PLOT",
    "RADAR // NOAA/NWS MRMS","RAINVIEWER","NOAA HMS",
    "WHEEL ZOOM // DRAG PAN","NeonScrollBar",
    "StationEventContextCard {","newsMentionOverlay"
  ])assert.ok(original.includes(token),"original MAP UI missing: "+token);
  for(const token of ["eventArchiveStore.archiveEvent(","dossierArchiveStore.capture(",
                      "EventContextPolicy.evidenceTimeline(",
                      "EventContextPolicy.evidenceRelationships("])
    assert.ok(original.includes(token),"original event inspection lost: "+token);
  for(const source of [pane,earthPolicy,workspace])
    for(const forbidden of ["WeatherServices.","FileView {","Process {",
                             "XMLHttpRequest","swaymsg","curl "])
      assert.equal(source.includes(forbidden),false,
        "new writer/collector in passive MAP routing: "+forbidden);
});

test("one original root source for seismic lightning and river; full route enables all five existing source families",()=>{
  for(const key of ["seismic","eonet","gdacs","lightning","river"])
    assert.equal(earth.needsSource(FULL,key),true,"original MAP must admit "+key);
  for(const key of ["firms","smoke","astronomy","news","media","unknown"])
    assert.equal(earth.needsSource(FULL,key),false,
      "manual or unrelated source must not auto-start: "+key);
  for(const key of ["lightning","river"])
    assert.equal(earth.needsSource("earth/maps/overview",key),false,
      "source-scoped EARTH route must not gain MAP-wide polling");
  for(const key of ["seismic","eonet","gdacs"])
    assert.equal(earth.needsSource("weather/maps",key),false);
  for(const token of ["WeatherServices.SeismicService {",
                      "WeatherServices.NowcoastLightningService {",
                      "WeatherServices.NwpsRiverService {"])
    assert.equal(station.split(token).length-1,1,
      "same original root controller "+token);
  for(const source of ["lightning","river"])
    assert.ok(station.includes('subjectNavigator.currentPath, "'+source+'"'),
      "root source has an active route guard: "+source);
  assert.match(station,/EarthPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath, "lightning"\)/);
  assert.match(station,/EarthPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath, "river"\)/);
  assert.match(station,/EarthPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath, "seismic"\)/);
  assert.match(original,/!stationDiscovery\.earthMapOnly\s*\|\|\s*EarthPanelPolicy\.needsSource/);
  assert.match(original,/stationDiscovery\.stationOpen && stationDiscovery\.visible/);
  assert.match(original,/WeatherServices\.StationDiscoveryService\s*\{/);
  assert.match(original,/WeatherServices\.GdacsService\s*\{/);
  assert.match(original,/WeatherServices\.MrmsRadarService\s*\{/);
  assert.match(original,/WeatherServices\.RainViewerRadarService\s*\{/);
});

test("original focused EARTH controls remain, full route does not turn FIRMS/HMS automatic",()=>{
  for(const key of ["quakes","eonet","gdacs","firms","smoke"])
    assert.equal(earth.showsLayer(FULL,key),true);
  assert.equal(earth.showsLayer("earth/geography/basemap","quakes"),false);
  assert.equal(earth.needsSource("earth/fires/hotspots","firms"),false);
  assert.equal(earth.needsSource("earth/fires/hotspots","smoke"),false);
  assert.equal(earth.investigationRoute(FULL),false);
  assert.equal(earth.investigationRoute("earth/investigations/dossiers"),true);
  assert.match(original,/onArchiveRequested:/);
  assert.match(original,/onDossierSaveRequested:/);
  assert.match(original,/signal newsMapClearRequested\(\)/);
  assert.match(pane,/onNewsMapClearRequested: earthPane\.newsMapClearRequested\(\)/);
});
