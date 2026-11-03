.pragma library

// Passive routes-to-legacy-page discovery for the M1 subject browser.
// No data fetching, writes, or reparenting. The old pages remain explicitly CLASSIC.
var ORDER = ["home","ground","sky","space","map","news","radio","terminal"];
var LABELS = {
  home:"HOME", ground:"GROUND", sky:"SKY", space:"SPACE",
  map:"MAP", news:"NEWS", radio:"RADIO", terminal:"TERMINAL"
};

function legacyPageForPanel(panelId) {
  if (typeof panelId !== "string") return "";
  var prefix = panelId.split("-")[0];
  return ORDER.indexOf(prefix) >= 0 ? prefix : "";
}

function sourcePagesForPath(path, panelRoutes) {
  if (typeof path !== "string"
      || !/^[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)
      || !panelRoutes || typeof panelRoutes !== "object")
    return [];
  var counts = {};
  for (var i = 0; i < ORDER.length; i++) counts[ORDER[i]] = 0;
  var keys = Object.keys(panelRoutes);
  for (var j = 0; j < keys.length; j++) {
    var panel = keys[j];
    var target = panelRoutes[panel];
    if (typeof target !== "string"
        || (target !== path && target.indexOf(path + "/") !== 0))
      continue;
    var oldPage = legacyPageForPanel(panel);
    if (oldPage) counts[oldPage]++;
  }
  return ORDER.filter(function(key) {return counts[key] > 0;})
    .map(function(key) {
      return {id:key, label:LABELS[key], panels:counts[key], status:"CLASSIC_SOURCE"};
    });
}

// M28-D/F: These exact original control families have route-specific SUBJECTS
// source wiring and tests. Original pages are still available until final parity.
// NOT operator acceptance, native Sway/Kitty acceptance, or whole-page parity.
// Do not add other panels merely because a destination appears in PANELS.
var WIRED_IN_SUBJECTS = {
  "map-news-mentions":"M28-A",
  "map-news-inspector":"M28-A",
  "news-topic-filter":"M28-B",
  "news-publisher-country-filter":"M28-B",
  "news-language-time-region-filter":"M28-B",
  "news-reporting-trend":"M28-B",
  "news-story-families":"M28-B",
  "news-article-viewer":"M28-B",
  "terminal-star-map":"M28-C",
  "terminal-context-console":"M28-C",
  // M28-E: reuse StationRadio, shared Hi-Fi/MPD and its existing memory.
  "radio-directory":"M28-E",
  "radio-search-presets":"M28-E",
  "radio-paging":"M28-E",
  "radio-favorites-recent":"M28-E",
  "radio-select-load-enter":"M28-E",
  "radio-play-pause-stop":"M28-E",
  // M28-F: existing HOME/GROUND/SKY filtered WEATHER sections and map layers.
  // Wired does not certify provider availability or live operator acceptance.
  "home-official-alert":"M28-F",
  "home-current-weather":"M28-F",
  "home-next-hours":"M28-F",
  "home-air-quality":"M28-F",
  "home-historical-forecast":"M28-F",
  "home-auto-relevant":"M28-F",
  "ground-official-alerts":"M28-F",
  "ground-coastal-relationship":"M28-F",
  "ground-marine-relationships":"M28-F",
  "ground-river-nwps":"M28-F",
  "ground-river-nearby":"M28-F",
  "ground-river-flood-context":"M28-F",
  "ground-river-stageflow":"M28-F",
  "ground-marine-ndbc":"M28-F",
  "ground-coast-coops":"M28-F",
  "ground-lightning-nowcoast":"M28-F",
  "ground-heat-fire-weather":"M28-F",
  "ground-air-particulates":"M28-F",
  "ground-gases":"M28-F",
  "ground-pollen-peak":"M28-F",
  "ground-pollen-species":"M28-F",
  "ground-air-12-hour":"M28-F",
  "sky-current-conditions":"M28-F",
  "sky-atmosphere":"M28-F",
  "sky-hourly-forecast":"M28-F",
  "sky-hour-inspector":"M28-F",
  "sky-daily-forecast":"M28-F",
  "map-mrms-radar":"M28-F",
  "map-rainviewer":"M28-F",
  "map-hms-smoke":"M28-F",
  // M28-G: original filtered SKY celestial and SPACE SWPC sections in COSMOS.
  // The mixed SKY WEATHER forecast controls remain M28-F; SPACE provenance
  // is a separate TOOLS review, not silently included here.
  "sky-sun-moon":"M28-G",
  "sky-iss-passes":"M28-G",
  "sky-moon-usno":"M28-G",
  "sky-eclipses":"M28-G",
  "sky-celestial-fix":"M28-G",
  "sky-planet-clock":"M28-G",
  "sky-meteor-showers":"M28-G",
  "sky-twilight":"M28-G",
  "sky-photo-light":"M28-G",
  "sky-current-sun":"M28-G",
  "space-geomagnetic-core":"M28-G",
  "space-solar-context":"M28-G",
  "space-noaa-scales":"M28-G",
  "space-solar-cycle":"M28-G",
  "space-kp-history":"M28-G",
  "space-kp-forecast":"M28-G",
  "space-suvi-imager":"M28-G",
  "space-aurora":"M28-G",
  "space-xray-flux":"M28-G",
  "space-goes-flares":"M28-G",
  "space-watch-day":"M28-G",
  "space-warning-validity":"M28-G",
  "space-bulletins":"M28-G"
};

function remainingSourcePagesForPath(path, panelRoutes) {
  // Retain the M1 historical source map unchanged. Only exact reviewed
  // cutovers stop offering a redundant jump to the whole CLASSIC page.
  if (!panelRoutes || typeof panelRoutes !== "object") return [];
  var unresolved = {};
  Object.keys(panelRoutes).forEach(function(panel) {
    if (!Object.prototype.hasOwnProperty.call(WIRED_IN_SUBJECTS, panel))
      unresolved[panel] = panelRoutes[panel];
  });
  return sourcePagesForPath(path, unresolved);
}

function nativeDestinationsForPath(path, panelRoutes) {
  if (typeof path !== "string"
      || !/^[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)
      || !panelRoutes || typeof panelRoutes !== "object")
    return [];
  var destinations = {};
  Object.keys(panelRoutes).sort().forEach(function(panel) {
    if (!Object.prototype.hasOwnProperty.call(WIRED_IN_SUBJECTS, panel))
      return;
    var target = panelRoutes[panel];
    if (typeof target !== "string"
        || (target !== path && target.indexOf(path + "/") !== 0))
      return;
    if (!Object.prototype.hasOwnProperty.call(destinations, target))
      destinations[target] = {path:target, panels:0, milestones:[]};
    var item = destinations[target];
    item.panels++;
    var milestone = WIRED_IN_SUBJECTS[panel];
    if (item.milestones.indexOf(milestone) < 0)
      item.milestones.push(milestone);
  });
  return Object.keys(destinations).sort().map(function(target) {
    return destinations[target];
  });
}
