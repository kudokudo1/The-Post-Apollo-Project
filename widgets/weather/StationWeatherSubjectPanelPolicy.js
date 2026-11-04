.pragma library

// Weather Station M2a: route-scoped reuse of existing, already-wired
// Weather panels. This policy performs no fetching, persistence or mutation.
// The empty subjectRoute is the untouched eight-mode CLASSIC presentation.
var FORMAT = "post-apollo.weather.subject-panels.m2a.v1";

var ROUTES = {
  // M28-Q: complete original GROUND surface, including its 16 source/visual
  // sections. Preserve one original StationGround instance and scrollbar.
  "weather/ground/full": {page:"ground",full:true},
  // NOW + AIR aggregates original terrestrial readings in one scrollable
  // StationSky view; detailed ground air/gas/pollen pages stay independent.
  "weather/conditions/current": {page:"sky", sections:["header","runtime","current","atmosphere"]},
  "weather/conditions/atmosphere": {page:"sky", sections:["header","atmosphere"]},
  "weather/conditions/air": {page:"ground", sections:["header","air-pm","air-gases"]},
  "weather/conditions/pollen": {page:"ground", sections:["header","air-gases","pollen"]},
  // FORECAST restores both original hourly/daily artwork plus the local
  // twilight/photo-light windows, without activating astronomy collectors.
  "weather/forecasts/hourly": {page:"sky", sections:["header","hourly","daily","twilight"]},
  "weather/forecasts/daily": {page:"sky", sections:["header","daily"]},
  "weather/forecasts/air": {page:"ground", sections:["header","air-forecast"]},
  "weather/water/rivers": {page:"ground", sections:["header","rivers"]},
  "weather/water/marine": {page:"ground", sections:["header","marine"]},
  "weather/water/coast": {page:"ground", sections:["header","coast"]},
  "weather/hazards/alerts": {page:"ground", sections:["header","alerts"]},
  "weather/hazards/lightning": {page:"ground", sections:["header","lightning"]},
  "weather/hazards/heat-fire": {page:"ground", sections:["header","heat-fire"]},
  // M2b reuses the original HOME and map renderers instead of cloning them.
  // M27-A: show HOME's existing adaptive AUTO RELEVANT cards on the WEATHER
  // overview. Reuse the original HOME ranker; no new fetch, timer or writer.
  // COSMOS signals remain under COSMOS: the WEATHER pane deliberately passes
  // a null spaceService to this shared renderer.
  "weather/overview": {page:"home", sections:["header","alerts","snapshot","relevant"]},
  "weather/history/historical-forecast": {page:"home", sections:["header","history"]},
  "weather/history/relationships": {page:"home", sections:["header","relations"]},
  "weather/history/relationships/aqi": {page:"home", sections:["header","relations"]},
  "weather/history/relationships/marine": {page:"ground", sections:["header","marine-rel"]},
  "weather/history/relationships/coastal": {page:"ground", sections:["header","coastal-rel"]},
  "weather/history/relationships/rivers": {page:"ground", sections:["header","rivers"]},
  "weather/maps": {page:"map", sections:["map"]},
  "weather/maps/radar": {page:"map", sections:["map","radar"]},
  "weather/maps/radar-fallback": {page:"map", sections:["map","rainviewer"]},
  "weather/maps/smoke": {page:"map", sections:["map","smoke"]},
  "weather/maps/lightning": {page:"ground", sections:["header","lightning"]},
  "weather/hazards/flood": {page:"ground", sections:["header","rivers"]},
  "weather/water/rivers/gauges": {page:"ground", sections:["header","rivers"]},
  "weather/water/rivers/nearby": {page:"ground", sections:["header","rivers"]},
  "weather/water/rivers/flood": {page:"ground", sections:["header","rivers"]},
  "weather/water/rivers/hydrograph": {page:"ground", sections:["header","rivers"]}
};

function kindForRoute(path) {
  if (typeof path !== "string"
      || !Object.prototype.hasOwnProperty.call(ROUTES,path))
    return "";
  return ROUTES[path].page;
}

function visibleFor(page, path, section) {
  if (path === "") return true;
  var info = typeof path === "string" ? ROUTES[path] : null;
  return !!info && info.page === page
    && (info.full === true || info.sections.indexOf(section) >= 0);
}

// M29-A: route-focused river presentations over the SAME one NWPS source.
// Parent RIVERS, full GROUND, historical relationships and flood hazards
// retain their existing combined panels and source activation.
var RIVER_ROUTE_FOCUS = {
  "weather/water/rivers/gauges":"gauges",
  "weather/water/rivers/nearby":"nearby",
  "weather/water/rivers/flood":"flood",
  "weather/water/rivers/hydrograph":"hydrograph"
};
function riverFocusForRoute(path) {
  return Object.prototype.hasOwnProperty.call(RIVER_ROUTE_FOCUS,path)
    ? RIVER_ROUTE_FOCUS[path] : "all";
}
function riverGroupVisible(path,group) {
  if (["nearby","flood","hydrograph"].indexOf(group)<0)
    return false;
  var focus=riverFocusForRoute(path);
  return focus==="all" || focus===group;
}
function needsSource(path, source) {
  // Existing collector lifetimes remain untouched in classic mode.
  if (path === "") return true;
  if (kindForRoute(path) === "")
    return false;
  // Full original GROUND includes all its established source-bound sections.
  // No second source owner; these gates feed the existing root services
  // and the original StationGround marine/coastal actors.
  if (path === "weather/ground/full")
    return ["river","lightning","marine","coastal","seismic"]
      .indexOf(source) >= 0;
  if (source === "river")
    return path === "weather/water/rivers"
      || path.indexOf("weather/water/rivers/") === 0
      || path === "weather/hazards/flood"
      || path === "weather/history/relationships/rivers";
  if (source === "lightning")
    return path === "weather/hazards/lightning"
      || path === "weather/maps/lightning";
  if (source === "marine")
    return path === "weather/water/marine"
      || path === "weather/history/relationships/marine";
  if (source === "coastal")
    return path === "weather/water/coast"
      || path === "weather/history/relationships/coastal";
  if (source === "history")
    return path === "weather/history/historical-forecast";
  if (source === "astronomy")
    return false;
  return false;
}

function titleFor(path) {
  if (kindForRoute(path) === "") return "";
  var final = path.split("/").slice(-2).join(" / ").replace(/-/g," ");
  return "WEATHER // " + final.toUpperCase();
}
