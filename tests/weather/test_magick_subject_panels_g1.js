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
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const network=read("widgets/weather/StationCosmosCelestialNetwork.qml");
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
  assert.doesNotMatch(overview,/id: interpretation/);
  assert.match(overview,/id: overviewChart/);
  assert.match(overview,/id: solarCanvas/);
  assert.match(overview,/readonly property var moonModel: CosmosVisual\.moonDisplay/);
  assert.match(overview,/readonly property var solarModel: CosmosVisual\.solarArc/);
  assert.match(overview,/sourceOnly: true/);
  assert.doesNotMatch(overview,/Flickable\s*\{/);
  assert.match(overview,/MAGICK \/\/ CELESTIAL CHART/);
  assert.match(overview,/SUN \/\/ DAYLIGHT/);
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
  assert.match(overview,/SYMBOLIC INTERPRETATION \/\/ NOT CONNECTED/);
  assert.match(overview,/StationMagickCelestialInstrument\s*\{/);
  assert.match(overview,/compactMode: true/);
  assert.match(overview,/deck\.celestialSource\.refresh\(\)/);
  assert.match(overview,/deck\.celestialSource\.configured/);
  assert.match(station,/subjectNavigator\.currentPath === "magick\/overview"/);
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

test("M30-B astro hero replaces solar hero without losing the Moon and Sun instruments", () => {
  assert.match(overview,/id: hero/);
  assert.match(overview,/text: "MAGICK \/\/ CELESTIAL CHART"/);
  assert.match(overview,/label: deck\.celestialSource && deck\.celestialSource\.loading\s*\? "CALCULATING" : "CALCULATE"/);
  assert.match(overview,/onClicked: deck\.celestialSource\.refresh\(\)/);
  assert.match(overview,/available: !!deck\.celestialSource\s*&& deck\.celestialSource\.active\s*&& deck\.celestialSource\.configured\s*&& !deck\.celestialSource\.loading/);
  assert.match(overview,/StationMagickCelestialInstrument\s*\{/);
  assert.match(overview,/visualData: deck\.celestialSource && deck\.celestialSource\.ready/);
  assert.match(overview,/id: heroFooter/);
  assert.match(overview,/SYMBOLIC INTERPRETATION \/\/ NOT CONNECTED/);
  assert.doesNotMatch(overview,/id: interpretation/);
  assert.match(overview,/anchors\.bottom: parent\.bottom\s*anchors\.topMargin: deck\.gutter/);
  assert.match(overview,/id: lunarCard/);
  assert.match(overview,/id: solarCard/);
  assert.match(overview,/id: solarCard[\s\S]*id: solarCanvas/);
  assert.match(overview,/onClicked: deck\.routeRequested\("magick\/lunar-solar\/moon"\)/);
  assert.match(overview,/onClicked: deck\.routeRequested\("magick\/planetary\/hours"\)/);
  assert.match(overview,/onClicked: deck\.routeRequested\("magick\/planetary\/correspondences"\)/);
  assert.doesNotMatch(overview,/Flickable\s*\{|Process\s*\{|Timer\s*\{/);
  assert.match(station,/MagickPanelPolicy\.visualForRoute\(subjectNavigator\.currentPath\)[\s\S]*?subjectNavigator\.currentPath === "magick\/overview"/);
  assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
});


test("M30-C compact overview hosts the existing interactive astrology modes", () => {
  assert.match(overview,/StationMagickCelestialInstrument\s*\{/);
  assert.match(overview,/id: overviewChart/);
  assert.match(overview,/compactMode: true/);
  assert.match(overview,/visualData: deck\.celestialSource && deck\.celestialSource\.ready/);
  assert.match(instrument,/property bool compactMode: false/);
  for(const token of ['id:"wheel"','id:"motion"','id:"aspects"',
                      'id:"relations"','id:"network"','id:"helio"'])
    assert.ok(instrument.includes(token),"mode missing "+token);
  assert.match(instrument,/displayMode: instrument\.compactMode && instrument\.mode === "helio"\s*\? "heliocentric" : "chords"/);
  assert.match(instrument,/onClicked: instrument\.mode = modelData\.id/);
  assert.match(network,/StationCosmosHeliocentricPane\s*\{/);
  assert.match(network,/visible: !graph\.compactMode/);
  assert.match(instrument,/id: chartFrame[\s\S]*height: instrument\.compactMode/);
  assert.match(instrument,/id: eventTimeline[\s\S]*visible: !instrument\.compactMode/);
  // Compact means visual controls take the screen; it cannot turn on a new engine.
  assert.equal((overview.match(/StationMagickCelestialInstrument\s*\{/g)||[]).length,1);
  assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
  assert.match(overview,/onClicked: deck\.celestialSource\.refresh\(\)/);
  assert.doesNotMatch(overview,/Process\s*\{|Timer\s*\{|FileView\s*\{/);
});

test("M30-C Moon phase selector previews references without changing observed data", () => {
  assert.match(overview,/property string inspectedPhaseId: ""/);
  assert.match(overview,/CosmosVisual\.phaseReference\(/);
  assert.match(overview,/id: phasePresetRow/);
  assert.match(overview,/model: CosmosVisual\.PHASES/);
  assert.match(overview,/deck\.inspectedPhaseId === modelData\.id \? ""/);
  assert.match(overview,/onClicked: deck\.inspectedPhaseId = ""/);
  assert.match(overview,/SCHEMATIC REFERENCE/);
  assert.match(overview,/deck\.displayedMoonIllumination/);
  assert.match(overview,/CosmosVisual\.illuminatedSpan/);
  assert.match(overview,/deck\.routeRequested\("magick\/lunar-solar\/moon"\)/);
  // Observed illumination stays derived from the original USNO/forecast model.
  assert.match(overview,/readonly property var moonModel: CosmosVisual\.moonDisplay/);
  assert.doesNotMatch(overview,/moonModel\.(?:illumination|phaseId)\s*=/);
});

test("M30-C Sun time controls select actual calibrated samples without refetching", () => {
  assert.match(overview,/id: solarPresetRow/);
  for(const time of ["00","06","12","18","NOW"])
    assert.ok(overview.includes('label:"'+time+'"'),time);
  assert.match(overview,/property real lockedSolarMinute: -1/);
  assert.match(overview,/property real hoveredSolarMinute: -1/);
  assert.match(overview,/CosmosVisual\.nearestSolar\(/);
  assert.match(overview,/CosmosVisual\.positionX\(rows\[i\]\.minute,w\)/);
  assert.match(overview,/deck\.lockedSolarMinute=modelData\.minute/);
  assert.match(overview,/deck\.selectedSolarMinute/);
  assert.match(overview,/CosmosVisual\.clockLabel\(/);
  assert.match(overview,/deck\.routeRequested\("magick\/planetary\/hours"\)/);
  assert.doesNotMatch(overview,/weatherService\.refresh\(|observationOwner\.refresh\(/);
});
