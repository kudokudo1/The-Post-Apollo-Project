.pragma library

// Weather Station // subject-first navigation contract v1.
// Pure metadata and routing only: no QML instances, fetches, writes, or live activation.
// All routes are SPEC_ONLY until a separate UI integration is approved and verified.
var FORMAT = "post-apollo.weather.subject-navigation.v1";

var SUBJECTS = [
  {id:"weather", label:"WEATHER", sections:[
    {id:"overview", label:"OVERVIEW"},
    {id:"conditions", label:"CONDITIONS", children:[
      {id:"current",label:"CURRENT"}, {id:"atmosphere",label:"ATMOSPHERE"},
      {id:"air",label:"AIR QUALITY"}, {id:"pollen",label:"POLLEN"}]},
    {id:"forecasts", label:"FORECASTS", children:[
      {id:"hourly",label:"HOURLY"}, {id:"daily",label:"DAILY"},
      {id:"air",label:"AIR QUALITY"}]},
    {id:"water",label:"WATER", children:[
      {id:"rivers",label:"RIVERS", children:[
        {id:"gauges",label:"GAUGES"}, {id:"nearby",label:"NEARBY COMPARISON"},
        {id:"flood",label:"FLOOD IMPACTS"}, {id:"hydrograph",label:"HYDROGRAPH"}]},
      {id:"marine",label:"MARINE"}, {id:"coast",label:"COAST AND TIDES"}]},
    {id:"hazards",label:"HAZARDS", children:[
      {id:"alerts",label:"OFFICIAL ALERTS"}, {id:"lightning",label:"LIGHTNING"},
      {id:"heat-fire",label:"HEAT AND FIRE WEATHER"}, {id:"flood",label:"FLOODING"}]},
    {id:"maps",label:"MAPS", children:[
      {id:"radar",label:"RADAR"}, {id:"radar-fallback",label:"RADAR FALLBACK"},
      {id:"smoke",label:"SMOKE"}, {id:"lightning",label:"LIGHTNING"}]},
    {id:"history",label:"HISTORY AND ANALYSIS", children:[
      {id:"historical-forecast",label:"HISTORICAL FORECAST"},
      {id:"relationships",label:"RELATIONSHIPS", children:[
      {id:"aqi",label:"AQI + WEATHER"},
      {id:"marine",label:"MARINE + WAVES"},
      {id:"coastal",label:"PRESSURE + WATER LEVEL"},
      {id:"rivers",label:"PRECIP + RIVER STAGE"}]}]}
  ]},
  {id:"cosmos",label:"COSMOS",sections:[
    {id:"overview",label:"OVERVIEW"},
    {id:"sun",label:"SUN",children:[
      {id:"position",label:"POSITION"}, {id:"twilight",label:"TWILIGHT"},
      {id:"photo-light",label:"PHOTO LIGHT"}]},
    {id:"moon",label:"MOON",children:[
      {id:"ephemeris",label:"PHASE AND RISE/SET"},
      {id:"position",label:"CURRENT POSITION"}]},
    {id:"planets-stars",label:"PLANETS AND STARS",children:[
      {id:"celestial-fix",label:"CURRENT SKY"},
      {id:"planet-clock",label:"PLANET RISE/SET"},
      {id:"constellations",label:"CONSTELLATIONS"}]},
    {id:"events",label:"CELESTIAL EVENTS",children:[
      {id:"eclipses",label:"ECLIPSES"}, {id:"meteors",label:"METEOR SHOWERS"},
      {id:"iss",label:"ISS PASSES"}]},
    {id:"space-weather",label:"SPACE WEATHER",children:[
      {id:"overview",label:"OVERVIEW"}, {id:"solar-wind",label:"SOLAR WIND AND FIELD"},
      {id:"geomagnetic",label:"GEOMAGNETIC"}, {id:"aurora",label:"AURORA"},
      {id:"solar-activity",label:"SOLAR ACTIVITY"},
      {id:"forecasts",label:"FORECASTS"}, {id:"bulletins",label:"BULLETINS"},
      {id:"history",label:"HISTORY AND CYCLE"}]}
  ]},
  {id:"earth",label:"EARTH",sections:[
    {id:"overview",label:"OVERVIEW"},
    {id:"geography",label:"GEOGRAPHY",children:[
      {id:"basemap",label:"BASEMAP AND BOUNDARIES"}]},
    {id:"geology",label:"GEOLOGY",children:[{id:"earthquakes",label:"EARTHQUAKES"}]},
    {id:"events",label:"NATURAL EVENTS",children:[
      {id:"eonet",label:"NASA EONET"}, {id:"gdacs",label:"GDACS"}]},
    {id:"fires",label:"FIRES",children:[{id:"hotspots",label:"NASA FIRMS HOTSPOTS"}]},
    {id:"maps",label:"MAPS",children:[{id:"overview",label:"EVENT MAP"}]},
    {id:"investigations",label:"INVESTIGATIONS",children:[
      {id:"context",label:"EVENT CONTEXT"}, {id:"dossiers",label:"DOSSIERS"},
      {id:"archive",label:"EVENT ARCHIVE"}]}
  ]},
  {id:"media",label:"MEDIA",sections:[
    {id:"overview",label:"OVERVIEW"},
    {id:"news",label:"NEWS",children:[
      {id:"reports",label:"REPORTS"}, {id:"filters",label:"FILTERS"},
      {id:"trends",label:"REPORTING TRENDS"}, {id:"stories",label:"STORY FAMILIES"},
      {id:"locations",label:"MENTIONED LOCATIONS"}, {id:"viewer",label:"ARTICLE INSPECTOR"}]},
    {id:"watch",label:"WATCH",children:[
      {id:"live",label:"LIVE NEWS"}, {id:"congress",label:"CONGRESS"},
      {id:"reports",label:"PUBLISHER DESTINATIONS"},
      {id:"compare",label:"SOURCE COMPARISON"}, {id:"satire",label:"SATIRE"}]},
    {id:"radio",label:"RADIO",children:[
      {id:"directory",label:"STATION DIRECTORY"},
      {id:"saved",label:"FAVORITES AND RECENTS"},
      {id:"transport",label:"PLAYBACK"}]},
    {id:"creators",label:"CREATORS",children:[
      {id:"saved",label:"SAVED CHANNELS"}, {id:"uploads",label:"RECENT UPLOADS"}]}
  ]},
  {id:"magick",label:"MAGICK",sections:[
    {id:"overview",label:"OVERVIEW"},
    {id:"astrology",label:"ASTROLOGY",children:[
      {id:"charts",label:"CHARTS"}, {id:"zodiac",label:"ZODIAC"},
      {id:"aspects",label:"ASPECTS"}, {id:"retrogrades",label:"RETROGRADES"},
      {id:"transits",label:"TRANSITS"}]},
    {id:"planetary",label:"PLANETARY MAGICK",children:[
      {id:"hours",label:"PLANETARY HOURS"}, {id:"correspondences",label:"CORRESPONDENCES"},
      {id:"timing",label:"TRADITIONAL TIMING"}]},
    {id:"lunar-solar",label:"LUNAR AND SOLAR",children:[
      {id:"moon",label:"LUNAR CYCLES"}, {id:"seasons",label:"SOLSTICES AND EQUINOXES"},
      {id:"calendar",label:"PRACTICE CALENDAR"}]},
    {id:"divination",label:"DIVINATION",children:[
      {id:"tarot",label:"TAROT"}, {id:"symbolism",label:"SYMBOLISM"}]},
    {id:"grimoire",label:"GRIMOIRE",children:[
      {id:"references",label:"REFERENCES"}, {id:"journal",label:"JOURNAL"}]}
  ]},
  {id:"tools",label:"TOOLS",sections:[
    {id:"overview",label:"OVERVIEW"},
    {id:"terminal",label:"TERMINAL",children:[
      {id:"star-map",label:"STAR MAP"}, {id:"consoles",label:"CONSOLES"}]},
    {id:"sources",label:"DATA SOURCES",children:[
      {id:"health",label:"SOURCE HEALTH"}, {id:"provenance",label:"PROVENANCE"}]},
    {id:"storage",label:"STORAGE",children:[
      {id:"cache",label:"SOURCE CACHE"}, {id:"history",label:"LIVE HISTORY"},
      {id:"events",label:"EVENT ARCHIVE"}, {id:"frames",label:"FRAME CACHE"}]},
    {id:"settings",label:"SETTINGS",children:[
      {id:"location",label:"LOCATION"}, {id:"display",label:"UNITS AND DISPLAY"}]}
  ]}
];

// Legacy page IDs are landing hints only; individual panels override these.
// The mixed SKY/GROUND/MAP screens cannot be accurately moved as single pages.
var LEGACY_MODES = {
  home:"weather/overview", ground:"weather/overview",
  sky:"cosmos/overview", space:"cosmos/space-weather/overview",
  map:"earth/maps/overview", news:"media/news/reports",
  radio:"media/radio/directory", terminal:"tools/terminal/star-map"
};

// Exact source-section / control-family migration targets.
// Intentional semantic reuse is handled through RELATED, not duplicate ownership.
var PANELS = {
  "home-official-alert":"weather/hazards/alerts",
  "home-aqi-humidity":"weather/history/relationships",
  "home-aqi-wind":"weather/history/relationships",
  "home-current-weather":"weather/overview",
  "home-next-hours":"weather/forecasts/hourly",
  "home-air-quality":"weather/conditions/air",
  "home-historical-forecast":"weather/history/historical-forecast",
  "home-quick-conditions":"weather/conditions/current",
  "home-space-weather":"cosmos/space-weather/overview",
  "home-source-health":"tools/sources/health",
  "home-auto-relevant":"weather/overview",
  "ground-official-alerts":"weather/hazards/alerts",
  "ground-coastal-relationship":"weather/history/relationships",
  "ground-marine-relationships":"weather/history/relationships",
  "ground-river-nwps":"weather/water/rivers/gauges",
  "ground-river-nearby":"weather/water/rivers/nearby",
  "ground-river-flood-context":"weather/water/rivers/flood",
  "ground-river-stageflow":"weather/water/rivers/hydrograph",
  "ground-marine-ndbc":"weather/water/marine",
  "ground-coast-coops":"weather/water/coast",
  "ground-lightning-nowcoast":"weather/hazards/lightning",
  "ground-heat-fire-weather":"weather/hazards/heat-fire",
  "ground-air-particulates":"weather/conditions/air",
  "ground-gases":"weather/conditions/air",
  "ground-pollen-peak":"weather/conditions/pollen",
  "ground-pollen-species":"weather/conditions/pollen",
  "ground-air-12-hour":"weather/forecasts/air",
  "ground-usgs-seismic":"earth/geology/earthquakes",
  "ground-source":"tools/sources/health",
  "sky-current-conditions":"weather/conditions/current",
  "sky-atmosphere":"weather/conditions/atmosphere",
  "sky-sun-moon":"cosmos/overview",
  "sky-iss-passes":"cosmos/events/iss",
  "sky-moon-usno":"cosmos/moon/ephemeris",
  "sky-eclipses":"cosmos/events/eclipses",
  "sky-celestial-fix":"cosmos/planets-stars/celestial-fix",
  "sky-planet-clock":"cosmos/planets-stars/planet-clock",
  "sky-meteor-showers":"cosmos/events/meteors",
  "sky-twilight":"cosmos/sun/twilight",
  "sky-photo-light":"cosmos/sun/photo-light",
  "sky-current-sun":"cosmos/sun/position",
  "sky-hourly-forecast":"weather/forecasts/hourly",
  "sky-hour-inspector":"weather/forecasts/hourly",
  "sky-daily-forecast":"weather/forecasts/daily",
  "space-geomagnetic-core":"cosmos/space-weather/overview",
  "space-solar-context":"cosmos/space-weather/history",
  "space-noaa-scales":"cosmos/space-weather/geomagnetic",
  "space-solar-cycle":"cosmos/space-weather/history",
  "space-kp-history":"cosmos/space-weather/history",
  "space-kp-forecast":"cosmos/space-weather/forecasts",
  "space-field-times":"tools/sources/provenance",
  "space-suvi-imager":"cosmos/space-weather/solar-activity",
  "space-aurora":"cosmos/space-weather/aurora",
  "space-xray-flux":"cosmos/space-weather/solar-activity",
  "space-goes-flares":"cosmos/space-weather/solar-activity",
  "space-watch-day":"cosmos/space-weather/forecasts",
  "space-warning-validity":"cosmos/space-weather/bulletins",
  "space-bulletins":"cosmos/space-weather/bulletins",
  "map-source-rack":"tools/sources/health",
  "map-natural-earth":"earth/geography/basemap",
  "map-spatial-canvas":"earth/maps/overview",
  "map-earthquake-layer":"earth/geology/earthquakes",
  "map-eonet-layer":"earth/events/eonet",
  "map-gdacs-layer":"earth/events/gdacs",
  "map-firms-hotspots":"earth/fires/hotspots",
  "map-mrms-radar":"weather/maps/radar",
  "map-rainviewer":"weather/maps/radar-fallback",
  "map-hms-smoke":"weather/maps/smoke",
  "map-news-mentions":"media/news/locations",
  "map-event-context":"earth/investigations/context",
  "map-dossier-preview":"earth/investigations/dossiers",
  "map-event-archive":"earth/investigations/archive",
  "map-gdacs-inspector":"earth/events/gdacs",
  "map-usgs-inspector":"earth/geology/earthquakes",
  "map-eonet-inspector":"earth/events/eonet",
  "map-firms-inspector":"earth/fires/hotspots",
  "map-news-inspector":"media/news/locations",
  "news-topic-filter":"media/news/filters",
  "news-publisher-country-filter":"media/news/filters",
  "news-language-time-region-filter":"media/news/filters",
  "news-reporting-trend":"media/news/trends",
  "news-story-families":"media/news/stories",
  "news-article-viewer":"media/news/viewer",
  "news-live":"media/watch/live",
  "news-congress":"media/watch/congress",
  "news-reports-catalog":"media/watch/reports",
  "news-compare":"media/watch/compare",
  "news-satire":"media/watch/satire",
  "news-creators":"media/creators/saved",
  "news-uploads":"media/creators/uploads",
  "radio-directory":"media/radio/directory",
  "radio-search-presets":"media/radio/directory",
  "radio-paging":"media/radio/directory",
  "radio-favorites-recent":"media/radio/saved",
  "radio-select-load-enter":"media/radio/transport",
  "radio-play-pause-stop":"media/radio/transport",
  "terminal-star-map":"tools/terminal/star-map",
  "terminal-context-console":"tools/terminal/consoles",
  "station-source-badge":"tools/sources/health",
  "station-frame-cache":"tools/storage/frames",
  "station-persistent-cache":"tools/storage/cache",
  "station-live-history":"tools/storage/history",
  "station-event-store":"tools/storage/events"
};

// Cross-domain references are links, not migrations or new fetch ownership.
var RELATED = {
  moon:["cosmos/moon","magick/lunar-solar/moon","magick/astrology/charts"],
  sun:["cosmos/sun","magick/lunar-solar/seasons","magick/planetary/hours"],
  planets:["cosmos/planets-stars","magick/astrology/retrogrades","magick/astrology/aspects"],
  aurora:["cosmos/space-weather/aurora","weather/conditions/current"],
  "river-flood":["weather/water/rivers/flood","earth/events/gdacs"],
  wildfire:["earth/fires/hotspots","weather/hazards/heat-fire","weather/maps/smoke"],
  "news-location":["media/news/locations","earth/maps/overview"]
};

function safePath(value) {
  if (typeof value !== "string" || !/^[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(value))
    return "";
  return value;
}

function findRoute(path) {
  var key = safePath(path);
  if (!key) return null;
  var ids = key.split("/");
  var root = null;
  for (var i = 0; i < SUBJECTS.length; i++)
    if (SUBJECTS[i].id === ids[0]) { root = SUBJECTS[i]; break; }
  if (!root) return null;
  var node = root;
  for (var j = 1; j < ids.length; j++) {
    var children = j === 1 ? root.sections : node.children;
    if (!Array.isArray(children)) return null;
    node = null;
    for (var k = 0; k < children.length; k++)
      if (children[k].id === ids[j]) { node = children[k]; break; }
    if (!node) return null;
  }
  return {
    path:key, subject:root.id, label:node.label,
    depth:ids.length-1, group:ids.length === 1 || Array.isArray(node.children),
    status:"SPEC_ONLY"
  };
}

function childrenOf(path) {
  var item = findRoute(path);
  if (!item) return [];
  var ids = item.path.split("/");
  var node = SUBJECTS.find(function(x){ return x.id === ids[0]; });
  for (var i = 1; i < ids.length; i++) {
    var children = i === 1 ? node.sections : node.children;
    node = children.find(function(x){ return x.id === ids[i]; });
  }
  var descendants = ids.length === 1 ? node.sections : (node.children || []);
  return descendants.map(function(x) {
    return findRoute(item.path + "/" + x.id);
  });
}

function breadcrumbs(path) {
  var info = findRoute(path);
  if (!info) return [];
  var bits = info.path.split("/");
  var out = [];
  for (var i = 0; i < bits.length; i++)
    out.push(findRoute(bits.slice(0,i+1).join("/")));
  return out;
}

function defaultForSubject(subject) {
  var info = findRoute(subject);
  return info && info.depth === 0 ? subject + "/overview" : "";
}

function resumeSubject(subject, remembered) {
  var fallback = defaultForSubject(subject);
  if (!fallback) return "";
  var candidate = remembered && typeof remembered === "object"
    ? remembered[subject] : "";
  var info = findRoute(candidate);
  return info && info.subject === subject ? info.path : fallback;
}

function legacyLanding(mode) {
  var path = typeof mode === "string" ? LEGACY_MODES[mode] : "";
  return findRoute(path) ? path : "";
}

function panelLanding(panel) {
  var path = typeof panel === "string" ? PANELS[panel] : "";
  return findRoute(path) ? path : "";
}

function relatedRoutes(topic) {
  var keys = typeof topic === "string" ? RELATED[topic] : null;
  return Array.isArray(keys)
    ? keys.filter(function(path){ return !!findRoute(path); }).slice() : [];
}
