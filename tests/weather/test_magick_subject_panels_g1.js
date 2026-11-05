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
const standaloneAstro=read("widgets/weather/StationMagickAstrologyPane.qml");
const lensesPane=read("widgets/weather/StationMagickLensesPane.qml");
const workspacePolicy=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const overview=read("widgets/weather/StationMagickOverviewPane.qml");
const lunarSolar=read("widgets/weather/StationMagickLunarSolarPane.qml");
const lunarDetails=read("widgets/weather/StationMagickLunarSolarDetails.qml");
const cosmosVisual=read("widgets/weather/StationCosmosVisualInstruments.qml");
const instrument=read("widgets/weather/StationMagickCelestialInstrument.qml");
const network=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const browser=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const sky=read("widgets/weather/StationSky.qml");
const nav=vm.createContext({});
const magick=vm.createContext({});
const cosmos=vm.createContext({});
const wnav=vm.createContext({});
for(const [src,context] of [[navSource,nav],[magickSource,magick],[cosmosSource,cosmos]])
  vm.runInContext(src.replace(/^\.pragma library\s*$/m,""),context);
vm.runInContext(workspacePolicy.replace(/^\.pragma library\s*$/m,""),wnav);

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
  assert.doesNotMatch(overview,/moonModel\.(?:illumination|phaseId)\s*=(?!=)/);
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


test("M30-D LUNAR + SOLAR uses focused top tabs, no page scroll and no new collectors", () => {
  for(const route of [
    "magick/lunar-solar/moon",
    "magick/lunar-solar/seasons",
    "magick/lunar-solar/calendar"
  ]) {
    assert.ok(nav.findRoute(route),"missing existing source route "+route);
    assert.ok(lunarSolar.includes('{id:"'+route+'"'),
      "missing tab "+route);
  }
  assert.match(pane,/magickPane\.subjectRoute\.indexOf\("magick\/lunar-solar\/"\) === 0\s*\? lunarSolarReference/);
  assert.match(pane,/id: lunarSolarReference[\s\S]*StationMagickLunarSolarPane\s*\{/);
  assert.match(lunarSolar,/id: focusTabs/);
  assert.match(lunarSolar,/onClicked: lunarSolarPane\.routeRequested\(modelData\.id\)/);
  assert.match(lunarSolar,/StationSky\s*\{/);
  assert.match(lunarSolar,/sourceOnly: true/);
  assert.match(lunarSolar,/subjectRoute: lunarSolarPane\.isSolar\s*\? "cosmos\/sun\/position" : "cosmos\/moon\/ephemeris"/);
  assert.match(lunarSolar,/StationCosmosVisualInstruments\s*\{/);
  assert.match(lunarSolar,/compactMode: true/);
  assert.match(lunarSolar,/showMoon: !lunarSolarPane\.isSolar/);
  assert.match(lunarSolar,/showSun: lunarSolarPane\.isSolar/);
  assert.match(lunarSolar,/moonEphemeris: sourceSky\.moonObservation/);
  assert.match(lunarSolar,/currentSolarPosition: sourceSky\.currentSolarPosition/);
  assert.match(lunarSolar,/solarCivilOffsetMinutes: sourceSky\.moonCivilOffsetMinutes/);
  assert.match(lunarSolar,/PRACTICE CALENDAR \/\/ NOT CONNECTED/);
  assert.match(lunarSolar,/NO SAVED RITUAL EVENTS|NO SAVED/);
  assert.doesNotMatch(lunarSolar,/Flickable\s*\{|ScrollView\s*\{|Process\s*\{|FileView\s*\{|Timer\s*\{/);
  assert.doesNotMatch(lunarSolar,/Date\.now\(|XMLHttpRequest|writeAdapter/);
  // The original full COSMOS visual retains its exact default height.
  assert.match(cosmosVisual,/property bool compactMode: false/);
  assert.match(cosmosVisual,/height: compactMode \? 204 : 304/);
  assert.match(cosmosVisual,/readonly property var visibleIllumination: previewReference/);
  assert.match(cosmosVisual,/onInspectedPhaseIdChanged: moonCanvas\.requestPaint\(\)/);
  assert.match(cosmosVisual,/visual\.previewReference\s*\? visual\.referenceWaxing : info\.waxing/);
  assert.match(cosmosVisual,/id: phaseButtonRow/);
  assert.match(cosmosVisual,/id: solarPresetRow/);
  assert.match(cosmosVisual,/onClicked: visual\.inspectedPhaseId = modelData\.id/);
  assert.match(cosmosVisual,/visual\.lockedMinute = modelData\.id === "now"/);
});


test("M30-E returns Moon and solar details to the non-scrolling lower viewport", () => {
  assert.match(lunarSolar,/StationMagickLunarSolarDetails\s*\{/);
  assert.match(lunarSolar,/id: detailRack/);
  assert.match(lunarSolar,/anchors\.top: focusedInstrument\.bottom/);
  assert.match(lunarSolar,/anchors\.bottom: parent\.bottom/);
  assert.match(lunarSolar,/height: Math\.min\(186,Math\.max\(0,/);
  assert.match(lunarSolar,/skySource: sourceSky/);
  assert.match(lunarSolar,/isSolar: lunarSolarPane\.isSolar/);
  assert.match(lunarSolar,/visible: !lunarSolarPane\.isCalendar/);
  assert.match(lunarDetails,/moonActor: skySource \? skySource\.moonObservation : null/);
  assert.match(lunarDetails,/moonReady: !!moonActor && moonActor\.ready/);
  assert.match(lunarDetails,/moonReady \? field\(moon\.rise\) : "--"/);
  assert.match(lunarDetails,/moonReady \? field\(moon\.transit\) : "--"/);
  assert.match(lunarDetails,/moonReady \? field\(moon\.set\) : "--"/);
  assert.match(lunarDetails,/moonReady \? field\(moon\.sourceDate\) : "--"/);
  assert.match(lunarDetails,/moon\.noRiseSet/);
  assert.match(lunarDetails,/NO TIMES INVENTED/);
  for(const key of [
    "astronomicalDawn", "nauticalDawn", "civilDawn",
    "solarNoon", "civilDusk", "nauticalDusk",
    "astronomicalDusk", "blueMorningStart", "blueMorningEnd",
    "goldenMorningStart", "goldenMorningEnd",
    "goldenEveningStart", "goldenEveningEnd",
    "blueEveningStart", "blueEveningEnd",
    "altitudeDegrees", "azimuthDegrees"
  ]) assert.ok(lunarDetails.includes(key),"restored source field missing: "+key);
  assert.match(lunarDetails,/readonly property bool twilightReady: !!twilight && twilight\.available/);
  assert.match(lunarDetails,/return twilightReady \? field\(value\) : "--"/);
  assert.match(lunarDetails,/TWILIGHT \+ PHOTO LIGHT \/\/ LOCAL/);
  assert.match(lunarDetails,/PHOTO LIGHT \/\/ BLUE \+ GOLDEN WINDOWS/);
  assert.match(lunarDetails,/SUN NOW \/\/ CALIBRATED POSITION NOT AVAILABLE/);
  assert.doesNotMatch(lunarDetails,/Flickable\s*\{|ScrollView\s*\{|Process\s*\{|Timer\s*\{|FileView\s*\{/);
  assert.doesNotMatch(lunarDetails,/XMLHttpRequest|\.refresh\(|writeAdapter\(/);
  assert.equal((lunarSolar.match(/StationSky\s*\{/g)||[]).length,1);
  assert.equal((lunarSolar.match(/StationCosmosVisualInstruments\s*\{/g)||[]).length,1);
});


test("M30-F ASTROLOGY is an independent, non-scrolling, source-owned instrument", () => {
  assert.match(pane,/readonly property bool standaloneAstrology:\s*subjectRoute === "magick\/astrology\/charts"/);
  assert.match(pane,/readonly property bool independentScreen:\s*standaloneAstrology \|\| lensesLanding/);
  assert.match(pane,/sourceComponent: magickPane\.standaloneAstrology\s*\? standaloneAstrologyReference/);
  assert.match(pane,/id: standaloneAstrologyReference[\s\S]*StationMagickAstrologyPane\s*\{/);
  assert.match(pane,/visible: !magickPane\.independentScreen/);
  assert.match(pane,/anchors\.margins: magickPane\.independentScreen \? 0 : 4/);
  assert.doesNotMatch(standaloneAstro,/Flickable\s*\{|ScrollView\s*\{|Process\s*\{|Timer\s*\{|FileView\s*\{/);
  assert.match(standaloneAstro,/StationMagickCelestialInstrument\s*\{/);
  assert.match(standaloneAstro,/compactMode: true/);
  assert.match(standaloneAstro,/anchors\.top: pairControls\.bottom/);
  assert.match(standaloneAstro,/anchors\.bottom: eventAndTimeControls\.top/);
  assert.match(standaloneAstro,/visualData: astrology\.calculated\s*\? astrology\.celestialSource\.visualData : null/);
  assert.match(standaloneAstro,/label: astrology\.celestialSource && astrology\.celestialSource\.loading\s*\? "CALCULATING" : "CALCULATE"/);
  assert.match(standaloneAstro,/available: astrology\.chartAvailable/);
  assert.match(standaloneAstro,/onClicked: astrology\.celestialSource\.refresh\(\)/);
  for(const control of ["jumpDate(-1)","jumpDate(1)","returnToToday()","adjustDateStepDays(-1)","adjustDateStepDays(1)","cyclePair(-1)","cyclePair(1)","cycleSpan()"])
    assert.ok(standaloneAstro.includes(control),"missing verified source control "+control);
  for(const control of ["◀ EVENT","EVENT ▶","◀ TIME","TIME ▶","UNLOCK","RESET"])
    assert.ok(standaloneAstro.includes(control),"missing chart control "+control);
  assert.match(standaloneAstro,/instrument\.stepToEvent\(-1\)/);
  assert.match(standaloneAstro,/instrument\.stepToEvent\(1\)/);
  assert.match(standaloneAstro,/astrology\.stepSample\(-1\)/);
  assert.match(standaloneAstro,/astrology\.stepSample\(1\)/);
  assert.equal((standaloneAstro.match(/StationMagickCelestialInstrument\s*\{/g)||[]).length,1);
  assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
  // Old detailed deep INDEX modes remain available for step input + timelines.
  assert.match(pane,/id: celestialReference[\s\S]*Flickable\s*\{/);
  assert.match(pane,/contentHeight: Math\.max\(height, 620\)/);
  assert.match(pane,/id: jumpStepInput/);
  assert.match(pane,/height: 466/);
});

test("M30-F replaces PLANETARY bottom category with source-honest LENSES", () => {
  vm.runInContext(workspacePolicy.replace(/^\.pragma library\s*$/m,""),wnav);
  const modes=JSON.parse(JSON.stringify(wnav.GROUPS.magick));
  assert.equal(modes.length,6);
  assert.deepEqual(modes.map(m=>m.label),
    ["OVERVIEW","LUNAR + SOLAR","LENSES","ASTROLOGY","DIVINATION","GRIMOIRE"]);
  assert.equal(modes[2].path,"magick/planetary/correspondences");
  assert.equal(modes[2].key,"lenses");
  assert.equal(wnav.selectedGroup("magick/planetary/hours"),"lenses");
  assert.equal(wnav.selectedGroup("magick/planetary/timing"),"lenses");
  assert.ok(nav.findRoute("magick/planetary/hours"),"historical planetary route removed");
  assert.match(pane,/readonly property bool lensesLanding:\s*subjectRoute === "magick\/planetary\/correspondences"/);
  assert.match(pane,/id: lensesReference[\s\S]*StationMagickLensesPane\s*\{/);
  assert.match(pane,/onRouteRequested: function\(path\)\s*\{\s*magickPane\.routeRequested\(path\)/);
  assert.match(lensesPane,/signal routeRequested\(string path\)/);
  for(const route of [
    "magick/astrology/charts",
    "magick/lunar-solar/moon",
    "magick/grimoire/references"
  ]) {
    assert.ok(lensesPane.includes('path:"'+route+'"'),route);
    assert.ok(nav.findRoute(route),route);
  }
  assert.match(lensesPane,/LIBRARY NOT CONNECTED/);
  assert.match(lensesPane,/SCIENTIFIC OBSERVATIONS ARE NOT EVIDENCE OF SYMBOLIC CAUSATION/);
  assert.doesNotMatch(lensesPane,/Flickable\s*\{|ScrollView\s*\{|Process\s*\{|Timer\s*\{|FileView\s*\{/);
});


test("M30-G ASTROLOGY restores its inset without changing other MAGICK screens",()=>{
  assert.match(pane,/anchors\.topMargin: magickPane\.standaloneAstrology \? 7/);
  assert.match(pane,/anchors\.leftMargin: magickPane\.standaloneAstrology \? 9/);
  assert.match(pane,/anchors\.rightMargin: magickPane\.standaloneAstrology \? 9/);
  assert.match(pane,/anchors\.bottomMargin: magickPane\.standaloneAstrology \? 8/);
  assert.match(pane,/anchors\.margins: magickPane\.standaloneAstrology \? 3/);
  assert.match(pane,/border\.width: magickPane\.lensesLanding \? 0 : 1/);
  assert.match(standaloneAstro,/showCompactHelioControls: true/);
  assert.match(instrument,/property bool showCompactHelioControls: false/);
  assert.match(instrument,/showCompactHelioControls: instrument\.showCompactHelioControls/);
  // The small overview does not opt in to these larger view controls.
  assert.doesNotMatch(overview,/showCompactHelioControls: true/);
  assert.match(standaloneAstro,/anchors\.bottom: eventAndTimeControls\.top/);
  assert.doesNotMatch(standaloneAstro,/Flickable\s*\{|ScrollView\s*\{/);
});

test("M30-G compact HELIO buttons control the real embedded JPL projection",()=>{
  assert.match(network,/property bool showCompactHelioControls: false/);
  assert.match(network,/id: compactHelioToolbar/);
  assert.match(network,/visible: graph\.compactMode && graph\.showCompactHelioControls\s*&& graph\.displayMode === "heliocentric"/);
  assert.match(network,/anchors\.topMargin: compactHelioToolbar\.visible \? 27 : 0/);
  assert.match(network,/embedded: true/);
  for(const label of ["TOP","TILT","ALL AU","INNER 4 AU"])
    assert.ok(network.includes('label:"'+label+'"'),"missing compact HELIO control "+label);
  assert.match(network,/heliocentricPane\.tiltView=false/);
  assert.match(network,/heliocentricPane\.tiltView=true/);
  assert.match(network,/heliocentricPane\.atlasRange=modelData\.id/);
  assert.match(network,/selected: modelData\.id==="top"/);
  assert.match(network,/visible: !graph\.compactMode/); // original inspector unchanged
  assert.match(network,/visualData: graph\.spatialPayload/);
  assert.match(network,/graphModel: graph\.graphModel/);
  assert.match(network,/focusIndex: graph\.focusIndex/);
  assert.match(network,/selectedBody: graph\.selectedBody/);
  assert.doesNotMatch(network,/Process\s*\{|Timer\s*\{|FileView\s*\{|XMLHttpRequest/);
});
