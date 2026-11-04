"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const navSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const magickSource=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const cosmosSource=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const pane=read("widgets/weather/StationMagickSubjectPane.qml");
const overview=read("widgets/weather/StationMagickOverviewPane.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const sky=read("widgets/weather/StationSky.qml");
const nav=vm.createContext({});
const magick=vm.createContext({});
const cosmos=vm.createContext({});
for(const [src,context] of [[navSource,nav],[magickSource,magick],[cosmosSource,cosmos]])
  vm.runInContext(src.replace(/^\.pragma library\s*$/m,""),context);

test("all 16 MAGICK destinations exist in the canonical subject tree", () => {
  assert.equal(magick.FORMAT,"post-apollo.weather.magick-reference.g1.v1");
  const routes=Object.keys(magick.ROUTES);
  assert.equal(routes.length,16);
  assert.equal(new Set(routes).size,16);
  for(const route of routes) {
    const found=nav.findRoute(route);
    assert.ok(found,"route not in existing subject tree: "+route);
    assert.equal(found.subject,"magick",route);
    assert.equal(magick.kindForRoute(route),"reference");
    assert.ok(magick.titleFor(route).startsWith("MAGICK //")
      || /^(ASTROLOGY|PLANETARY MAGICK|LUNAR AND SOLAR|DIVINATION|GRIMOIRE) \/\//.test(magick.titleFor(route)),route);
    assert.ok(magick.noteFor(route).length>=35,"missing limitation note: "+route);
    assert.equal(magick.isInterpretationImplemented(route),false,route);
  }
  for(const invalid of ["magick","magick/astrology","magick/foo",
                        "magick/grimoire/foo","weather/overview","cosmos/overview",
                        "earth/overview","media/overview","tools/overview"]) {
    assert.equal(magick.kindForRoute(invalid),"",invalid);
    assert.equal(magick.hasObservation(invalid),false,invalid);
  }
});

test("eight MAGICK routes reuse actual observational COSMOS SKY views", () => {
  const expected={
    "magick/overview":"cosmos/moon/ephemeris",
    "magick/astrology/charts":"cosmos/planets-stars/celestial-fix",
    "magick/planetary/hours":"cosmos/sun/twilight",
    "magick/planetary/correspondences":"cosmos/planets-stars/planet-clock",
    "magick/planetary/timing":"cosmos/sun/twilight",
    "magick/lunar-solar/moon":"cosmos/moon/ephemeris",
    "magick/lunar-solar/seasons":"cosmos/sun/position",
    "magick/lunar-solar/calendar":"cosmos/moon/ephemeris"
  };
  assert.equal(Object.keys(expected).length,8);
  for(const [route,source] of Object.entries(expected)) {
    assert.equal(magick.sourceFor(route),source,route);
    assert.equal(magick.hasObservation(route),true);
    assert.equal(cosmos.kindForRoute(source),"sky","not an existing SKY route: "+source);
  }
  assert.equal(magick.secondarySourceFor("magick/overview"),"cosmos/sun/twilight");
  assert.equal(cosmos.kindForRoute(magick.secondarySourceFor("magick/overview")),"sky");
  assert.match(pane,/StationSky\s*\{/);
  assert.match(pane,/subjectRoute: magickPane\.primaryObservation/);
  assert.match(pane,/StationMagickOverviewPane\s*\{/);
  assert.match(overview,/subjectRoute: "cosmos\/moon\/ephemeris"/);
  assert.match(pane,/weatherService: magickPane\.weatherService/);
  assert.match(sky,/CosmosPanelPolicy\.visibleFor\("sky",subjectRoute,section\)/);
  assert.match(sky,/CosmosPanelPolicy\.needsSource\(sky\.subjectRoute,"moon"\)/);
  assert.match(sky,/CosmosPanelPolicy\.needsSource\(sky\.subjectRoute,"celnav"\)/);
});

test("all interpretive-only routes explicitly refuse invented live output", () => {
  const planned=[
    "magick/astrology/zodiac","magick/astrology/aspects",
    "magick/astrology/retrogrades","magick/astrology/transits",
    "magick/divination/tarot","magick/divination/symbolism",
    "magick/grimoire/references","magick/grimoire/journal"
  ];
  assert.equal(planned.length,8);
  for(const route of planned) {
    assert.equal(magick.hasObservation(route),false,route);
    assert.equal(magick.sourceFor(route),"",route);
    assert.equal(magick.secondarySourceFor(route),"",route);
    assert.match(magick.noteFor(route),/NO |NOT |REQUIRE|UNIMPLEMENTED|NONE|NEVER/);
  }
  assert.match(magick.noteFor("magick/astrology/retrogrades"),/TIME SERIES/);
  assert.match(magick.noteFor("magick/astrology/charts"),/NOTHING|NONE OF WHICH/);
  assert.match(magick.noteFor("magick/planetary/hours"),/NO TRADITIONAL PLANETARY-HOUR/);
  assert.match(magick.noteFor("magick/lunar-solar/calendar"),/NO PLANNER/);
  assert.match(magick.noteFor("magick/grimoire/journal"),/NEVER WRITES/);
});

test("MAGICK keeps source evidence visibly separated from symbolic interpretation", () => {
  assert.match(pane,/OBSERVATION \/\/ EXISTING COSMOS DATA/);
  assert.match(pane,/INTERPRETATION \/\/ NOT CONNECTED/);
  assert.match(pane,/NO CONNECTED INSTRUMENT/);
  assert.match(pane,/DOES NOT GENERATE ASTROLOGY, TAROT/);
  assert.match(pane,/SCIENTIFIC SKY DATA REMAINS AVAILABLE UNDER COSMOS/);
  assert.match(overview,/id: hero/);
  assert.match(overview,/id: lunarCard/);
  assert.match(overview,/id: solarCard/);
  assert.match(overview,/id: interpretation/);
  assert.match(overview,/readonly property var moonModel: CosmosVisual\.moonDisplay/);
  assert.match(overview,/readonly property var solarModel: CosmosVisual\.solarArc/);
  assert.match(overview,/sourceOnly: true/);
  assert.doesNotMatch(overview,/Flickable\s*\{/);
  assert.match(overview,/MOON \+ SUN OBSERVATIONS|SOLAR DAY ARC/);
  assert.match(pane,/onRouteRequested: function\(path\)/);
  assert.match(pane,/active: magickPane\.visible && magickPane\.kind === "reference"/);
  assert.match(pane,/MagickPolicy\.noteFor\(magickPane\.subjectRoute\)/);
});


test("M30-A overview is compact, routed and source-honest", () => {
  for(const route of [
    "magick/astrology/charts",
    "magick/lunar-solar/moon",
    "magick/planetary/hours",
    "magick/planetary/correspondences"
  ]) {
    assert.ok(nav.findRoute(route),"destination missing "+route);
    assert.ok(overview.includes('deck.routeRequested("'+route+'")'),
      "overview action missing "+route);
  }
  assert.match(pane,/signal routeRequested\(string path\)/);
  assert.match(surface,/subjectRoute: "magick\/overview"\s*onRouteRequested:/);
  assert.match(surface,/visible: surface\.activeFamily === "magick"\s*subjectRoute: surface\.currentPath\s*onRouteRequested:/);
  assert.match(browser,/id: magickReferencePane\s*onRouteRequested:/);
  assert.match(sky,/property bool sourceOnly: false/);
  assert.match(sky,/readonly property var moonObservation: moonService/);
  assert.match(sky,/visible: !sky\.sourceOnly/);
  assert.match(sky,/visible: !sky\.sourceOnly && scrollable/);
  assert.match(overview,/CosmosVisual\.illuminatedSpan/);
  assert.match(overview,/TwilightPolicy\.solarPosition/);
  assert.match(overview,/TRADITIONS \/ CORRESPONDENCES \/\/ NOT CONNECTED/);
  assert.doesNotMatch(overview,/Process\s*\{|FileView\s*\{|Timer\s*\{|curl /);
  assert.equal((overview.match(/StationSky\s*\{/g)||[]).length,1);
  assert.equal((pane.match(/StationSky\s*\{/g)||[]).length,1);
});

test("the new MAGICK view is routed only through SUBJECTS; CLASSIC unchanged", () => {
  assert.match(browser,/StationMagickSubjectPane\s*\{/);
  assert.match(browser,/visible: browser\.visible && browser\.liveMagickKind !== ""/);
  assert.match(browser,/weatherService: browser\.weatherService/);
  assert.match(browser,/MagickPanelPolicy\.kindForRoute\(currentPath\)/);
  assert.match(station,/subjectNavigator\.liveMagickKind !== ""/);
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.ok(!station.includes("weatherContentLoader"));
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(browser,/function showNewsMentionsOnEarth\(payload\)/);
  assert.match(browser,/StationCosmosSubjectPane\s*\{/);
  assert.match(browser,/StationEarthSubjectPane\s*\{/);
  assert.match(browser,/StationMediaSubjectPane\s*\{/);
  assert.equal(nav.findRoute("magick/astrology/retrogrades").status,"SPEC_ONLY");
});

test("MAGICK creates no standalone service, side-effect writer or secret storage", () => {
  for(const src of [magickSource,pane,overview]) {
    for(const token of ["WeatherServices.","FileView {","Process {","XMLHttpRequest",
      "HeadlessMediaController","writeAdapter()","eventArchiveStore:",
      "dossierArchiveStore:","savedCard","journalPath","Date.now()",
      "curl ","swaymsg"])
      assert.ok(!src.includes(token),"unexpected ownership/write: "+token);
  }
  for(const key of Object.keys(magick.ROUTES))
    assert.equal(magick.isInterpretationImplemented(key),false);
});
