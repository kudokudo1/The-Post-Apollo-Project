.pragma library

// COSMOS C1 // one subject across existing SKY and SPACE instruments.
// Empty route is CLASSIC, which retains every original section and source.
// Neither navigation nor this policy owns fetchers, cache files or sessions.
var FORMAT = "post-apollo.weather.cosmos-panels.c1.v1";
var ROUTES = {
  // M28-R: original SKY mixed terrestrial WEATHER and astronomy.
  // The comprehensive COSMOS page is astronomy-only. WEATHER owns
  // conditions, atmosphere, photo light, hourly/daily forecasts.
  "cosmos/sky/full": {page:"sky",full:true},
  "cosmos/space-weather/full": {page:"space",full:true},
  // C2: Overview shows the existing core spaceService telemetry directly.
  // Heavy auxiliary feeds (OVATION, NOAA scales, alerts) remain on SPACE
  // detail routes; opening OVERVIEW does not activate their collectors.
  "cosmos/overview": {page:"overview",
    sky:["header","astronomy","moon","twilight"],
    space:["header","solar"]},

  // The bottom SUN landing includes all original solar/time/light sections.
  "cosmos/sun/position": {page:"sky",sky:["header","astronomy","twilight"]},
  "cosmos/sun/live": {page:"space",space:["header","suvi","xray","flares"]},
  "cosmos/sun/twilight": {page:"sky",sky:["header","twilight"]},
  "cosmos/sun/photo-light": {page:"sky",sky:["header","twilight"]},
  // Physical solar activity is SUN-owned; reuse original NOAA sections.
  "cosmos/sun/activity": {page:"space",space:["header","xray","flares","cycle"]},
  "cosmos/sun/suvi": {page:"space",space:["suvi"]},
  "cosmos/sun/xray": {page:"space",space:["xray"]},
  "cosmos/sun/flares": {page:"space",space:["flares"]},
  "cosmos/sun/cycle": {page:"space",space:["header","cycle"]},
  // Annual instruments reuse the existing on-demand JPL calendar service.
  // Empty sky sections ensure no USNO/NOAA fetchers activate.
  "cosmos/sun/year": {page:"sky",sky:[]},
  // The bottom MOON landing pairs USNO ephemeris with its current sky fix.
  "cosmos/moon/ephemeris": {page:"sky",sky:["header","moon","moon-position"]},
  "cosmos/moon/year": {page:"sky",sky:[]},
  "cosmos/moon/position": {page:"sky",sky:["header","moon-position"]},
  // Native ASTRONOMY landing keeps the planet/constellation instruments;
  // the original comprehensive SKY page remains in INDEX unchanged.
  "cosmos/planets-stars/celestial-fix": {page:"sky",sky:["celestial-fix"]},
  "cosmos/planets-stars/planet-clock": {page:"sky",sky:["header","planet-clock"]},
  "cosmos/planets-stars/constellations": {page:"sky",sky:["header","celestial-fix"]},
  // Native EVENTS landing groups the real ISS, eclipse and meteor instruments.
  "cosmos/events/overview": {page:"sky",sky:["header","iss","eclipses","meteor"]},
  "cosmos/events/eclipses": {page:"sky",sky:["header","eclipses"]},
  "cosmos/events/meteors": {page:"sky",sky:["header","meteor"]},
  "cosmos/events/iss": {page:"sky",sky:["header","iss"]},

  // C4: fixed, read-only hub. Detailed providers activate only on click.
  "cosmos/space-weather/overview": {page:"space",space:[]},
  "cosmos/space-weather/solar-wind": {page:"space",
    space:["header","solar","relation","field"]},
  "cosmos/space-weather/geomagnetic": {page:"space",
    space:["header","scales","kp-history"]},
  "cosmos/space-weather/aurora": {page:"space",
    space:["header","aurora"]},
  "cosmos/space-weather/solar-activity": {page:"space",
    space:["header","suvi","xray","flares"]},
  "cosmos/space-weather/forecasts": {page:"space",
    space:["header","kp-forecast","watch"]},
  "cosmos/space-weather/bulletins": {page:"space",
    space:["header","warnings","bulletins"]},
  "cosmos/space-weather/history": {page:"space",
    space:["header","relation","kp-history"]}
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

// A full astronomical page is NOT the original weather+sky page.
var FULL_ASTRONOMY_SECTIONS = [
  "header","astronomy","moon","iss","eclipses",
  "celestial-fix","planet-clock","meteor"
];

function visibleFor(page,path,section) {
  if (path === "") return true;
  if (page !== "sky" && page !== "space") return false;
  var row = routeInfo(path);
  if (!row) return false;
  // The full SPACE instrument is entirely COSMOS. Original SKY is not:
  // prohibit terrestrial WEATHER widgets even on COSMOS/sky/full.
  if (row.full === true && row.page === page)
    return page === "space"
      || FULL_ASTRONOMY_SECTIONS.indexOf(section) >= 0;
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
  // No new collectors: original page-specific astronomy or space-weather
  // services are activated only for their exact selected full route.
  if (row.full === true) {
    if (row.page === "sky")
      return Object.prototype.hasOwnProperty.call(SKY_SOURCE_SECTION,source);
    if (row.page === "space")
      return Object.prototype.hasOwnProperty.call(SPACE_SOURCE_SECTION,source);
    return false;
  }
  // The dedicated Moon position subsection uses the same existing USNO
  // celestial-navigation source, without activating planetary presentations.
  if (source === "celnav" && visibleFor("sky",path,"moon-position"))
    return true;
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
