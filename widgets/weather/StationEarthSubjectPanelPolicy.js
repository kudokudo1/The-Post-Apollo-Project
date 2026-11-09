.pragma library

// EARTH E1 // subject-scoped reuse of the existing MAP event engine.
// This policy is passive: no new provider, writer, geolocation, or archive.
var FORMAT = "post-apollo.weather.earth-panels.e1.v1";

var ROUTES = {
  "earth/overview": {layers:["quakes","eonet","gdacs","firms","smoke"]},
  "earth/geography/basemap": {layers:[]},
  "earth/geology/earthquakes": {layers:["quakes"]},
  "earth/events/eonet": {layers:["eonet"]},
  "earth/events/gdacs": {layers:["gdacs"]},
  "earth/fires/hotspots": {layers:["firms","smoke"]},
  "earth/maps/overview": {layers:["quakes","eonet","gdacs","firms","smoke"]},
  // E2: one unified, pinned event map. The old deep routes remain valid.
  "earth/maps/events": {layers:["quakes","eonet","gdacs","firms","smoke"],pinned:true},
  // M28-S restores the complete original CLASSIC MAP presentation (radar,
  // smoke, weather context, geodata, map companion, native event inspectors)
  // in one existing StationDiscovery instance. No collector is copied.
  "earth/maps/full": {layers:["quakes","eonet","gdacs","firms","smoke"],full:true},
  "earth/investigations/context": {layers:["quakes","eonet","gdacs","firms","smoke"]},
  "earth/investigations/dossiers": {layers:["quakes","eonet","gdacs","firms","smoke"]},
  "earth/investigations/archive": {layers:["quakes","eonet","gdacs","firms","smoke"]},
  "earth/water/rivers": {page:"ground"},
  "earth/water/marine": {page:"ground"},
  "earth/water/coast": {page:"ground"},
  "earth/ground/full": {page:"ground"},
  "earth/services/health": {page:"services"}
};

function routeInfo(path) {
  return typeof path === "string"
    && Object.prototype.hasOwnProperty.call(ROUTES, path)
    ? ROUTES[path] : null;
}

function kindForRoute(path) {
  var info=routeInfo(path);
  return info ? (info.page || "map") : "";
}
function isPinnedMap(path) {
  var info=routeInfo(path);
  return !!info && info.pinned === true;
}
function isFullMap(path) {
  var info=routeInfo(path);
  return !!info && info.full === true;
}

function showsLayer(path, layer) {
  var info = routeInfo(path);
  return !!info && typeof layer === "string"
    && info.layers.indexOf(layer) >= 0;
}

// CLASSIC source lifetime remains owned by the original components.
// EARTH admission explicitly refuses unknown routes and other subjects.
function needsSource(path, source) {
  if (path === "") return true;
  if (!routeInfo(path)) return false;
  if (source === "seismic")
    return showsLayer(path,"quakes") || path === "earth/ground/full"
      || path === "earth/services/health";
  if (source === "eonet") return showsLayer(path,"eonet");
  if (source === "gdacs") return showsLayer(path,"gdacs");
  // Original CLASSIC MAP also gives flood/lightning event context from the
  // same root sources. They remain active only for this exact full route.
  if (source === "lightning")
    return isFullMap(path) || isPinnedMap(path)
      || path === "earth/ground/full" || path === "earth/services/health";
  if (source === "river")
    return isFullMap(path) || isPinnedMap(path)
      || path === "earth/ground/full" || path === "earth/services/health"
      || path === "earth/water/rivers";
  // FIRMS and NOAA HMS remain explicitly manually requested.
  return false;
}

function investigationRoute(path) {
  return typeof path === "string"
    && path.indexOf("earth/investigations/") === 0
    && !!routeInfo(path);
}

function routeLabel(path) {
  var data = {
    "earth/overview":"EARTH // CURRENT OBSERVATIONS",
    "earth/geography/basemap":"GEOGRAPHY // NATURAL EARTH",
    "earth/geology/earthquakes":"GEOLOGY // USGS EARTHQUAKES",
    "earth/events/eonet":"NATURAL EVENTS // NASA EONET",
    "earth/events/gdacs":"NATURAL EVENTS // GDACS",
    "earth/fires/hotspots":"FIRES // FIRMS + HMS SMOKE",
    "earth/maps/overview":"EARTH // EVENT MAP",
    "earth/maps/events":"EARTH // ONE LIVE EVENT MAP",
    "earth/maps/full":"MAP // ALL ORIGINAL INSTRUMENTS",
    "earth/investigations/context":"INVESTIGATIONS // EVENT CONTEXT",
    "earth/investigations/dossiers":"INVESTIGATIONS // DOSSIERS",
    "earth/investigations/archive":"INVESTIGATIONS // EVENT ARCHIVE",
    "earth/water/rivers":"EARTH // RIVERS + FLOOD",
    "earth/water/marine":"EARTH // MARINE",
    "earth/water/coast":"EARTH // COAST",
    "earth/ground/full":"EARTH // GROUND",
    "earth/services/health":"EARTH // SOURCE DIAGNOSTICS"
  };
  return routeInfo(path) ? data[path] : "";
}

function selectionHint(path) {
  if (!investigationRoute(path)) return "";
  if (path === "earth/investigations/dossiers")
    return "SELECT A USGS, EONET, GDACS OR FIRMS EVENT ON THE MAP TO INSPECT A DOSSIER. SAVE IS AN EXPLICIT ACTION.";
  if (path === "earth/investigations/archive")
    return "SELECT A PROVIDER-NATIVE EVENT FOR ITS STORED SNAPSHOTS AND REVISION COMPARISON. ARCHIVE IS MANUAL.";
  return "SELECT AN EVENT ON THE MAP FOR ITS CROSS-SOURCE EVIDENCE, TIMELINE AND RELATIONSHIPS.";
}
