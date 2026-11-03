"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const navSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySource = read("widgets/weather/StationEarthSubjectPanelPolicy.js");
const discovery = read("widgets/weather/StationDiscovery.qml");
const earthPane = read("widgets/weather/StationEarthSubjectPane.qml");
const browser = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const nav = vm.createContext({});
const earth = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m,""),nav);
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m,""),earth);

test("ten EARTH routes are legitimate canonical descendants and never cross subjects", () => {
  assert.equal(earth.FORMAT,"post-apollo.weather.earth-panels.e1.v1");
  const routes = Object.keys(earth.ROUTES);
  assert.equal(routes.length,10);
  for(const route of routes) {
    const match = nav.findRoute(route);
    assert.ok(match,route);
    assert.equal(match.subject,"earth");
    assert.equal(earth.kindForRoute(route),"map");
    assert.ok(earth.routeLabel(route).startsWith("EARTH //") ||
              earth.routeLabel(route).startsWith("GEOLOGY //") ||
              earth.routeLabel(route).startsWith("GEOGRAPHY //") ||
              earth.routeLabel(route).startsWith("NATURAL EVENTS //") ||
              earth.routeLabel(route).startsWith("FIRES //") ||
              earth.routeLabel(route).startsWith("INVESTIGATIONS //"));
  }
  for(const route of ["earth","earth/geology","earth/events","earth/investigations",
                       "weather/overview","cosmos/overview","magick/astrology/charts",
                       "earth/events/not-real","earth/events/eonet/other"]) {
    assert.equal(earth.kindForRoute(route),"",route);
  }
});

test("overview and event map combine only EARTH observations in one subject", () => {
  const layers = ["quakes","eonet","gdacs","firms","smoke"];
  for (const route of ["earth/overview","earth/maps/overview"]) {
    for(const layer of layers)
      assert.ok(earth.showsLayer(route,layer),route+" "+layer);
  }
  for(const layer of layers)
    assert.equal(earth.showsLayer("earth/geography/basemap",layer),false);
  assert.ok(earth.showsLayer("earth/geology/earthquakes","quakes"));
  assert.equal(earth.showsLayer("earth/geology/earthquakes","eonet"),false);
  assert.ok(earth.showsLayer("earth/events/eonet","eonet"));
  assert.equal(earth.showsLayer("earth/events/eonet","gdacs"),false);
  assert.ok(earth.showsLayer("earth/events/gdacs","gdacs"));
  assert.equal(earth.showsLayer("earth/events/gdacs","quakes"),false);
  assert.ok(earth.showsLayer("earth/fires/hotspots","firms"));
  assert.ok(earth.showsLayer("earth/fires/hotspots","smoke"));
  assert.equal(earth.showsLayer("earth/fires/hotspots","eonet"),false);
});

test("seismic, EONET and GDACS use existing fetchers and only poll on admitted routes", () => {
  const cases = {
    "earth/overview":["seismic","eonet","gdacs"],
    "earth/geography/basemap":[],
    "earth/geology/earthquakes":["seismic"],
    "earth/events/eonet":["eonet"],
    "earth/events/gdacs":["gdacs"],
    "earth/fires/hotspots":[],
    "earth/maps/overview":["seismic","eonet","gdacs"]
  };
  for(const [route,sources] of Object.entries(cases)) {
    for(const source of ["seismic","eonet","gdacs"])
      assert.equal(earth.needsSource(route,source),
        sources.includes(source),route+" "+source);
  }
  for(const source of ["seismic","eonet","gdacs"]) {
    assert.equal(earth.needsSource("",source),true,"CLASSIC "+source);
    assert.equal(earth.needsSource("weather/maps",source),false);
    assert.equal(earth.needsSource("cosmos/overview",source),false);
    assert.equal(earth.needsSource("earth/unknown",source),false);
  }
  assert.match(station,/WeatherServices\.SeismicService\s*\{/);
  assert.match(station,/EarthPanelPolicy\.needsSource\(\s*subjectNavigator\.currentPath, "seismic"\)/);
  assert.match(discovery,/WeatherServices\.StationDiscoveryService\s*\{/);
  assert.match(discovery,/EarthPanelPolicy\.needsSource\(\s*stationDiscovery\.earthMapRoute,"eonet"\)/);
  assert.match(discovery,/WeatherServices\.GdacsService\s*\{/);
  assert.match(discovery,/EarthPanelPolicy\.needsSource\(\s*stationDiscovery\.earthMapRoute,"gdacs"\)/);
  assert.match(discovery,/WeatherServices\.FirmsHotspotService\s*\{/);
  assert.match(discovery,/WeatherServices\.HmsSmokeService\s*\{/);
  for(const s of ["firms","smoke"])
    assert.equal(earth.needsSource("earth/fires/hotspots",s),false,
      "FIRMS/HMS must remain manual");
});

test("EARTH map excludes unrelated weather radar and MEDIA news", () => {
  assert.match(discovery,/property bool earthMapOnly: false/);
  assert.match(discovery,/function earthLayerEnabled\(layer\)/);
  assert.match(discovery,/weatherMapOnly \? \[\] : MapProjection\.plottable\(source/);
  assert.match(discovery,/stationDiscovery\.earthLayerEnabled\("eonet"\)/);
  assert.match(discovery,/!weatherMapOnly && mapShowEarthquakes/);
  assert.match(discovery,/earthLayerEnabled\("quakes"\)/);
  assert.match(discovery,/!weatherMapOnly && mapShowGdacs/);
  assert.match(discovery,/earthLayerEnabled\("gdacs"\)/);
  assert.match(discovery,/earthLayerEnabled\("firms"\)/);
  assert.match(discovery,/earthLayerEnabled\("smoke"\)/);
  assert.match(discovery,/!stationDiscovery\.earthMapOnly\s*&& stationDiscovery\.weatherLayerEnabled\("radar"\)/);
  assert.match(discovery,/&& !stationDiscovery\.earthMapOnly\s*\? rainViewerRadarService\.strips/);
  assert.match(discovery,/!stationDiscovery\.earthMapOnly/);
  assert.match(discovery,/source\.ready \? stationDiscovery\.visibleRows : \[\]/);
  assert.match(discovery,/newsMentionInspectorOpen\s*&& !stationDiscovery\.earthMapOnly/);
  assert.match(discovery,/stationDiscovery\.weatherMapOnly \? "RADAR \+ SMOKE \/\/ MANUAL"/);
  assert.match(discovery,/WHEEL ZOOM \/\/ DRAG PAN/);
});

test("EARTH investigations reuse selected original context with dossier and archive stores", () => {
  const modes=["context","dossiers","archive"];
  for(const mode of modes) {
    const route="earth/investigations/"+mode;
    assert.ok(earth.investigationRoute(route));
    assert.match(earth.selectionHint(route),/SELECT/);
    for(const layer of ["quakes","eonet","gdacs","firms"])
      assert.ok(earth.showsLayer(route,layer));
  }
  assert.equal(earth.investigationRoute("earth/fires/hotspots"),false);
  assert.ok(discovery.includes("selectedMapEarthquake"));
  assert.ok(discovery.includes("selectedMapGdacsEvent"));
  assert.ok(discovery.includes("selectedMapEvent"));
  assert.ok(discovery.includes("selectedMapHotspot"));
  for(const token of [
    "EventContextPolicy.normalizeSelected(","DossierPreviewPolicy.preview(",
    "DossierCapturePolicy.review(","eventArchiveStore.archiveEvent(",
    "dossierArchiveStore.capture(","StationEventContextCard {",
    "onDossierSaveRequested:","onArchiveRequested:","onArchivePairRequested:"
  ]) assert.ok(discovery.includes(token),token);
  assert.match(discovery,/visible: stationDiscovery\.earthInvestigationRoute/);
  assert.match(discovery,/EarthPanelPolicy\.selectionHint\(/);
});

test("one EARTH map instance persists event selection and zoom while navigating routes", () => {
  assert.match(earthPane,/Loader\s*\{/);
  assert.match(earthPane,/sourceComponent: earthMapComponent/);
  assert.match(earthPane,/earthMapRoute: earthPane\.subjectRoute/);
  assert.match(earthPane,/stationOpen: earthPane\.visible/);
  assert.equal((earthPane.match(/StationDiscovery\s*\{/g)||[]).length,1);
  for(const bind of [
    "seismicSource: earthPane.seismicSource",
    "eventArchiveStore: earthPane.eventArchiveStore",
    "dossierArchiveStore: earthPane.dossierArchiveStore",
    "persistentCacheStore: earthPane.persistentCacheStore",
    "weatherService: earthPane.weatherService"
  ])assert.ok(earthPane.includes(bind),bind);
  const changed=discovery.slice(discovery.indexOf("onEarthMapRouteChanged:"),
                                discovery.indexOf("property bool stationOpen:",discovery.indexOf("onEarthMapRouteChanged:")));
  for(const name of ["selectedMapEvent =","selectedMapEarthquake =","selectedMapHotspot =",
                     "selectedMapGdacsEvent =","mapCenterLon =","mapCenterLat =","mapZoom =","resetMapView()"])
    assert.ok(!changed.includes(name),"EARTH route wrongly resets "+name);
  assert.ok(!earthPane.includes("newsMentionOverlay:"),
    "EARTH must not receive the MEDIA news overlay binding");
});

test("CLASSIC, WEATHER, COSMOS, the terminal and data store ownership remain intact", () => {
  assert.match(discovery,/property bool weatherMapOnly: false/);
  assert.match(discovery,/property bool earthMapOnly: false/);
  assert.match(discovery,/domain === "map" \? "⌖  MAP \/\/ EVENT SOURCES"/);
  assert.match(discovery,/title: "SPATIAL PLOT \/\/ GDACS \+ USGS QUAKES \+ EONET \+ FIRMS \+ NEWS"/);
  assert.match(discovery,/title: "RADAR \/\/ NOAA\/NWS MRMS BASE REFLECTIVITY \+ 4H HISTORY"/);
  assert.match(browser,/StationWeatherSubjectPane\s*\{/);
  assert.match(browser,/StationCosmosSubjectPane\s*\{/);
  assert.match(browser,/StationEarthSubjectPane\s*\{/);
  assert.match(browser,/visible: browser\.visible && browser\.liveEarthKind !== ""/);
  assert.match(station,/property bool subjectNavigationOpen: false/);
  assert.match(station,/eventArchiveStore: weatherStation\.eventArchiveStore/);
  assert.match(station,/dossierArchiveStore: weatherStation\.dossierArchiveStore/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/onNewsMapRequested: function\(payload\)/);
  assert.match(station,/return "INDEX \/\/ PREVIEW"/);
  assert.ok(!earthPane.includes("WeatherServices."));
  for(const forbidden of ["FileView {","Process {","XMLHttpRequest","swaymsg","curl ","save("])
    assert.ok(!policySource.includes(forbidden),"policy side effect "+forbidden);
});
