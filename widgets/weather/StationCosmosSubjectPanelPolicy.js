.pragma library

// COSMOS C1 // one subject across existing SKY and SPACE instruments.
// Empty route is CLASSIC, which retains every original section and source.
// Neither navigation nor this policy owns fetchers, cache files or sessions.
var FORMAT = "post-apollo.weather.cosmos-panels.c1.v1";
var ROUTES = {
  // M28-P: complete original SKY/SPACE instruments, including the artwork,
  // long-form charts, forecasts and provider provenance hidden by partial
  // overview routes. Only the selected full page is actually loaded.
  "cosmos/sky/full": {page:"sky",full:true},
  "cosmos/space-weather/full": {page:"space",full:true},
  "cosmos/overview": {page:"overview",
    sky:["header","astronomy","moon","twilight"],
    space:["header","solar","scales","aurora"]},

  "cosmos/sun/position": {page:"sky",sky:["header","astronomy"]},
  "cosmos/sun/twilight": {page:"sky",sky:["header","twilight"]},
  "cosmos/sun/photo-light": {page:"sky",sky:["header","twilight"]},
  "cosmos/moon/ephemeris": {page:"sky",sky:["header","moon"]},
  "cosmos/moon/position": {page:"sky",sky:["header","celestial-fix"]},
  "cosmos/planets-stars/celestial-fix": {page:"sky",sky:["header","celestial-fix"]},
  "cosmos/planets-stars/planet-clock": {page:"sky",sky:["header","planet-clock"]},
  "cosmos/planets-stars/constellations": {page:"sky",sky:["header","celestial-fix"]},
  "cosmos/events/eclipses": {page:"sky",sky:["header","eclipses"]},
  "cosmos/events/meteors": {page:"sky",sky:["header","meteor"]},
  "cosmos/events/iss": {page:"sky",sky:["header","iss"]},

  "cosmos/space-weather/overview": {page:"space",
    space:["header","solar","scales","field","aurora"]},
  "cosmos/space-weather/solar-wind": {page:"space",
    space:["header","solar","relation","field"]},
  "cosmos/space-weather/geomagnetic": {page:"space",
    space:["header","solar","scales","kp-history"]},
  "cosmos/space-weather/aurora": {page:"space",
    space:["header","aurora"]},
  "cosmos/space-weather/solar-activity": {page:"space",
    space:["header","suvi","xray","flares"]},
  "cosmos/space-weather/forecasts": {page:"space",
    space:["header","kp-forecast","watch"]},
  "cosmos/space-weather/bulletins": {page:"space",
    space:["header","warnings","bulletins"]},
  "cosmos/space-weather/history": {page:"space",
    space:["header","relation","cycle","kp-history"]}
};

function routeInfo(path) {
  return typeof path === "string"
      && Object.prototype.hasOwnProperty.call(ROUTES,path)
      ? ROUTES[path] : null;
}

function kindForRoute(path) {
  var row = routeInfo(path);
  return row ? row.page : "";
}

function visibleFor(page,path,section) {
  if (path === "") return true;
  if (page !== "sky" && page !== "space") return false;
  var row = routeInfo(path);
  if (!row) return false;
  // Full pages deliberately reproduce every section of the original
  // CLASSIC instrument in a SINGLE existing SKY or SPACE instance.
  if (row.full === true && row.page === page) return true;
  var values = row[page];
  return Array.isArray(values) && values.indexOf(section) >= 0;
}

// One deterministic source-activation gate for the original QML fetchers.
// CLASSIC is intentionally unconditional; non-COSMOS and unknown routes are
// refused rather than running an astronomy provider on a weather forecast.
var SKY_SOURCE_SECTION = {
  moon:"moon", eclipses:"eclipses", celnav:"celestial-fix",
  iss:"iss", planets:"planet-clock", meteor:"meteor"
};
var SPACE_SOURCE_SECTION = {
  aurora:"aurora", flares:"flares", xray:"xray", alerts:"bulletins",
  cycle:"cycle", scales:"scales", kpForecast:"kp-forecast"
};

function needsSource(path,source) {
  if (path === "") return true;
  if (!routeInfo(path)) return false;
  if (typeof source !== "string") return false;
  var row = routeInfo(path);
  // No new collectors: original panel-owned source services are active
  // only in their matching full native view. Unknown source keys fail shut.
  if (row.full === true) {
    if (row.page === "sky")
      return Object.prototype.hasOwnProperty.call(SKY_SOURCE_SECTION,source);
    if (row.page === "space")
      return Object.prototype.hasOwnProperty.call(SPACE_SOURCE_SECTION,source);
    return false;
  }
  var skySection = SKY_SOURCE_SECTION[source];
  if (skySection)
    return visibleFor("sky",path,skySection);
  var spaceSection = SPACE_SOURCE_SECTION[source];
  if (spaceSection)
    return visibleFor("space",path,spaceSection)
      || (source === "alerts" && visibleFor("space",path,"watch"));
  return false;
}

function titleFor(path) {
  if (!routeInfo(path)) return "";
  var chunks = path.split("/");
  return "COSMOS // " + chunks.slice(-2).join(" / ").replace(/-/g," ").toUpperCase();
}
