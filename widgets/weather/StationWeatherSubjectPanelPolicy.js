.pragma library

// Weather Station M2a: route-scoped reuse of existing, already-wired
// Weather panels. This policy performs no fetching, persistence or mutation.
// The empty subjectRoute is the untouched eight-mode CLASSIC presentation.
var FORMAT = "post-apollo.weather.subject-panels.m2a.v1";

var ROUTES = {
  "weather/conditions/current": {page:"sky", sections:["header","current"]},
  "weather/conditions/atmosphere": {page:"sky", sections:["header","atmosphere"]},
  "weather/conditions/air": {page:"ground", sections:["header","air-pm","air-gases"]},
  "weather/conditions/pollen": {page:"ground", sections:["header","air-gases","pollen"]},
  "weather/forecasts/hourly": {page:"sky", sections:["header","hourly"]},
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
    && info.sections.indexOf(section) >= 0;
}

function needsSource(path, source) {
  // Existing collector lifetimes remain untouched in classic mode.
  if (path === "") return true;
  if (kindForRoute(path) === "")
    return false;
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
