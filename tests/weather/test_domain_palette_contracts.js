#!/usr/bin/env node
"use strict";

// Weather Station palette contract after domain separation. This pass protects
// semantic identities and telemetry severity colors while layout polish remains
// intentionally deferred.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");

function read(relative) {
    return fs.readFileSync(path.join(root, relative), "utf8");
}

const windowSource = read("widgets/weather/WeatherStationW.qml");
const homeSource = read("widgets/weather/StationHome.qml");
const homeCardSource = read("widgets/weather/StationHomeMetricCard.qml");
const homePolicySource = read("widgets/weather/StationHomePolicy.js");
const groundSource = read("widgets/weather/StationGround.qml");
const skySource = read("widgets/weather/StationSky.qml");
const spaceSource = read("widgets/weather/StationSpace.qml");
const dividerSource = read("widgets/weather/StationSectionDivider.qml");
const weatherServiceSource = read("services/weather/WeatherService.qml");
const spaceServiceSource = read("services/weather/SpaceService.qml");

const weatherTerminalSource = read("widgets/weather/StationTerminal.qml");
const geometrySource = read("widgets/weather/StationTerminalGeometry.js");
assert.match(weatherTerminalSource, /SwayGeometry\.position\s*\(/);
assert.match(weatherTerminalSource, /command:\s*\["swaymsg", "-t", "get_outputs"\]/);
assert.match(weatherTerminalSource, /move absolute position /);
assert.doesNotMatch(weatherTerminalSource, /terminalBay\.mapToGlobal\s*\(/);
assert.doesNotMatch(weatherTerminalSource, /"\s*,\s*scratchpad show"/);
for (const name of ["bayX", "bayY", "bayWidth", "bayHeight"])
    assert.match(weatherTerminalSource, new RegExp("readonly property real " + name + ": terminalBay\\."));
assert.match(windowSource, /readonly property real terminalHoleX:\s*modeRail\.width \+ terminalView\.visibleBayX/);
assert.match(windowSource, /readonly property real terminalHoleY:\s*header\.height \+ terminalView\.visibleBayY/);
assert.match(windowSource, /readonly property real terminalHoleWidth:\s*terminalView\.visibleBayWidth/);
assert.match(windowSource, /readonly property real terminalHoleHeight:\s*terminalView\.visibleBayHeight/);
assert.match(windowSource, /readonly property bool terminalHoleActive:/);
assert.match(windowSource, /mask:\s*Region[\s\S]*?width:\s*weatherStation\.terminalHoleActive/);
assert.match(windowSource, /fillVisible:\s*!weatherStation\.terminalHoleActive/);
assert.match(windowSource, /StationChassisCutout\s*\{[\s\S]*?visible:\s*weatherStation\.terminalHoleActive/);
assert.match(windowSource, /holeX:\s*weatherStation\.terminalHoleX/);
assert.match(windowSource, /holeY:\s*weatherStation\.terminalHoleY/);
assert.match(windowSource, /holeWidth:\s*weatherStation\.terminalHoleWidth/);
assert.match(windowSource, /holeHeight:\s*weatherStation\.terminalHoleHeight/);
assert.match(windowSource, /surfaceFormat\.opaque:\s*false/);
const chassisCutout = read("widgets/weather/StationChassisCutout.qml");
assert.match(chassisCutout, /readonly property bool holeValid:/);
assert.match(chassisCutout, /holeX \+ holeWidth <= width/);
assert.match(chassisCutout, /holeY \+ holeHeight <= height/);
assert.equal((chassisCutout.match(/Rectangle\s*\{/g) || []).length, 4);
assert.match(chassisCutout, /x:\s*chassis\.holeX \+ chassis\.holeWidth/);
assert.match(chassisCutout, /y:\s*chassis\.holeY \+ chassis\.holeHeight/);
assert.match(chassisCutout, /color:\s*chassis\.panelColor/);
assert.match(chassisCutout, /opacity:\s*chassis\.panelOpacity/);
assert.match(weatherTerminalSource, /color:\s*terminalView\.terminalState === "VISIBLE"\s*\? "transparent" : Colors\.black/);
assert.match(geometrySource, /function position\(outputs, outputName/);



const headerActionsStart = windowSource.indexOf("id: headerActions");
const sourceBadgeStart = windowSource.indexOf("id: sourceStatusIndicator", headerActionsStart);
assert.ok(headerActionsStart >= 0 && sourceBadgeStart > headerActionsStart);
const headerControls = windowSource.slice(headerActionsStart, sourceBadgeStart);
assert.match(headerControls, /id:\s*contextTerminalLaunch/);
assert.match(headerControls, /id:\s*contextTerminalClose/);
assert.match(headerControls, /"STAR MAP" : weatherStation\.currentViewName/);
assert.match(headerControls, /label:\s*"CLOSE"/);
assert.match(headerControls, /destructive:\s*true/);
assert.match(headerControls, /accentColor:\s*Colors\.red/);
assert.doesNotMatch(windowSource, /id:\s*observatoryButton/);
assert.match(windowSource, /function launchContextTerminal\(\)/);
assert.match(windowSource, /function closeContextTerminal\(\)/);
assert.match(windowSource, /onCurrentViewChanged:/);
assert.match(windowSource, /terminalMode:\s*weatherStation\.currentView/);
assert.match(windowSource, /terminalHoleActive:[\s\S]*?terminalView\.sessionMode === currentView/);
assert.match(windowSource, /visible:\s*weatherStation\.currentView !== "terminal"\s*&& !weatherStation\.contextTerminalRequested/);
assert.match(weatherTerminalSource, /property string sessionMode:\s*"terminal"/);
assert.match(weatherTerminalSource, /function supportedMode\(mode\)/);
assert.match(weatherTerminalSource, /sessionMode === "terminal" \? "weather-screen"/);
assert.match(weatherTerminalSource, /"weather-screen-" \+ sessionMode/);
assert.match(weatherTerminalSource, /weatherstation-starmap/);
assert.match(weatherTerminalSource, /"\/usr\/bin\/bash -l"/);
assert.match(weatherTerminalSource, /sessionMode = terminalMode/);
assert.match(weatherTerminalSource, /y:\s*terminalTitleDivider\.y \+ terminalTitleDivider\.height \+ verticalClearance/);
assert.match(weatherTerminalSource, /parent\.width - 16/);
assert.match(weatherTerminalSource, /parent\.height - y - verticalClearance/);

// Shared terminal title header appears on STAR MAP and all other context
// consoles via the SAME StationTerminal, not a one-off STAR MAP exception.
assert.match(weatherTerminalSource, /text:\s*terminalView\.sessionTitle/);
assert.match(weatherTerminalSource, /id:\s*terminalTitleDivider/);
assert.match(weatherTerminalSource, /readonly property real verticalClearance:\s*8/);
assert.match(weatherTerminalSource, /x:\s*8/);
assert.match(weatherTerminalSource, /terminalTitleDivider\.y \+ terminalTitleDivider\.height \+ verticalClearance/);
assert.match(weatherTerminalSource, /height:\s*Math\.max\(0, parent\.height - y - verticalClearance\)/);
assert.match(weatherTerminalSource, /id:\s*terminalTitleDivider[\s\S]*?x:\s*14[\s\S]*?y:\s*64[\s\S]*?height:\s*2[\s\S]*?color:\s*Colors\.cyan/);
const titleDividerAt = weatherTerminalSource.indexOf("id: terminalTitleDivider");
const bayAt = weatherTerminalSource.indexOf("id: terminalBay");
assert.ok(titleDividerAt > 0 && titleDividerAt < bayAt);
assert.match(weatherTerminalSource, /y:\s*terminalTitleDivider\.y \+ terminalTitleDivider\.height \+ verticalClearance/);
assert.match(weatherTerminalSource, /visibleBayY:\s*bayY \+ verifiedOffsetY/);
assert.match(windowSource, /terminalHoleY:\s*header\.height \+ terminalView\.visibleBayY/);

assert.doesNotMatch(weatherTerminalSource, /id:\s*stationActionRow/);
assert.match(weatherTerminalSource, /pendingClose/);
assert.match(weatherTerminalSource, /terminalView\.terminalAppId/);


// Header divider belongs between terminal controls and source-status badge.
// Do not add a second decorative footer/header line in another component.
const dividerAt = headerControls.indexOf("id: terminalHeaderDivider");
assert.ok(dividerAt > headerControls.indexOf("id: contextTerminalClose"));
assert.ok(dividerAt < headerControls.length);
assert.match(headerControls, /id:\s*terminalHeaderDivider[\s\S]*?width:\s*2[\s\S]*?height:\s*25/);
assert.match(headerControls, /id:\s*terminalHeaderDivider[\s\S]*?color:\s*Colors\.cyan/);
assert.match(weatherTerminalSource, /id:\s*verifyProcess/);
assert.match(weatherTerminalSource, /command:\s*\["swaymsg", "-t", "get_tree"\]/);
assert.match(weatherTerminalSource, /SwayGeometry\.observedContentWindow\(/);
assert.match(weatherTerminalSource, /SwayGeometry\.visibleIntersection\(/);
assert.match(weatherTerminalSource, /resize set width /);
assert.match(weatherTerminalSource, /property string fitStatus:\s*"UNVERIFIED"/);
assert.match(weatherTerminalSource, /fitStatus = overlap\.exact \? "ALIGNED" : "PARTIAL"/);
assert.match(weatherTerminalSource, /terminalState = "VISIBLE"/);
assert.match(weatherTerminalSource, /visibleBayWidth:\s*verifiedWidth/);
assert.match(geometrySource, /function observedWindow\(tree, appId\)/);
assert.match(geometrySource, /function visibleIntersection\(desired, actual\)/);

// Kitty and Sway must agree on the same viewport; a successful IPC exit
// alone is not proof the Wayland surface resized. The retry is bounded and
// a smaller confirmed window is centered without enlarging the alpha hole.
assert.match(weatherTerminalSource, /--override remember_window_size=no /);
assert.match(weatherTerminalSource, /--override initial_window_width=/);
assert.match(weatherTerminalSource, /--override initial_window_height=/);
assert.match(weatherTerminalSource, /--override resize_in_steps=no /);
assert.match(weatherTerminalSource, /Math\.round\(terminalBay\.width\)/);
assert.match(weatherTerminalSource, /Math\.round\(terminalBay\.height\)/);
assert.match(weatherTerminalSource, /id:\s*verifyDelay[\s\S]*?interval:\s*250/);
assert.match(weatherTerminalSource, /verifyDelay\.restart\(\)/);
assert.match(weatherTerminalSource, /fitResizeRetries < 1/);
assert.match(weatherTerminalSource, /fitResizeRetries \+= 1/);
assert.match(weatherTerminalSource, /id:\s*centerProcess/);
assert.match(weatherTerminalSource, /SwayGeometry\.centeredPosition\(requested, actual\)/);
assert.match(weatherTerminalSource, /fitCenterAttempted = true/);

// A close during Wayland's asynchronous configure must not orphan Kitty.
assert.match(weatherTerminalSource, /property bool kittyActorConfirmed:\s*false/);
assert.match(weatherTerminalSource, /terminalView\.kittyActorConfirmed = true/);
assert.match(weatherTerminalSource, /if \(terminalState === "STARTING" && !kittyActorConfirmed\)/);
assert.match(weatherTerminalSource, /terminalView\.kittyActorConfirmed = false/);

assert.match(weatherTerminalSource, /centerProcess\.targetX = centered\.x/);
assert.match(weatherTerminalSource, /centerProcess\.targetY = centered\.y/);
assert.match(weatherTerminalSource, /if \(!overlap\)\s*throw new Error/);
assert.match(weatherTerminalSource, /terminalView\.verifiedWidth = overlap\.width/);
assert.doesNotMatch(weatherTerminalSource, /setInterval|Qt\.openUrlExternally/);
assert.match(geometrySource, /function centeredPosition\(desired, actual\)/);

assert.match(geometrySource, /function observedContentWindow\(tree, appId\)/);
assert.match(geometrySource, /actor\.window_rect/);
assert.match(geometrySource, /window\.x \+ window\.width > outer\.width/);
assert.match(weatherTerminalSource, /centerProcess\.targetWidth = actual\.width/);
assert.match(weatherTerminalSource, /centerProcess\.targetHeight = actual\.height/);
assert.match(weatherTerminalSource, /targetWidth \+ " px height " \+ targetHeight/);
assert.match(weatherTerminalSource, /SwayGeometry\.visibleIntersection\(requested, actual\)/);



const discoveryViewSource = read("widgets/weather/StationDiscovery.qml");
const discoveryServiceSource = read("services/weather/StationDiscoveryService.qml");
// MAP remains the direct discovery page. NEWS now mounts an expandable
// catalog, while keeping the same GDELT discovery service under REPORTS.
assert.match(windowSource, /id:\s*mapViewComponent[\s\S]*?StationDiscovery\s*\{[\s\S]*?domain: "map"/);
assert.match(windowSource, /id:\s*newsViewComponent[\s\S]*?StationNewsHub\s*\{/);
const newsHubSource = read("widgets/weather/StationNewsHub.qml");
assert.match(newsHubSource, /StationDiscovery\s*\{[\s\S]*?domain: "news"/);
assert.match(newsHubSource, /section === "REPORTS"/);
assert.ok(windowSource.includes("id: radioViewComponent"));
assert.match(windowSource, /id:\s*radioViewComponent[\s\S]*?StationRadio\s*\{/);
assert.ok(!windowSource.includes('domain: "radio"'));
const stationRadioSource = read("widgets/weather/StationRadio.qml");
const mediaBridgeSource = read("services/media/HeadlessMediaController.qml");
assert.match(stationRadioSource, /SHARED HI-FI \/\/ RADIO BROWSER \/\/ MPD/);
assert.match(stationRadioSource, /NEWS FIRST/);
assert.match(stationRadioSource, /pollingInterval:\s*6000/);
assert.match(stationRadioSource, /radioClient:\s*"weather-radio"/);
assert.match(mediaBridgeSource, /property string radioClient:\s*"default"/);
assert.match(windowSource, /weatherStation\.currentView === "map"[\s\S]*?\? mapViewComponent/);
assert.match(windowSource, /weatherStation\.currentView === "news"[\s\S]*?\? newsViewComponent/);
assert.match(windowSource, /weatherStation\.currentView === "radio"[\s\S]*?\? radioViewComponent/);
assert.match(discoveryViewSource, /SOURCE RACK \/\/ WHAT IS CONNECTED/);
assert.match(discoveryViewSource, /STATION DIRECTORY \/\/ PERSISTENT PLAYBACK NOT YET WIRED/);
assert.match(discoveryViewSource, /SPATIAL PLOT \/\/ USGS QUAKES \+ EONET \+ FIRMS \+ NEWS/);
assert.match(discoveryViewSource, /NATURAL EARTH LAND \+ CONTEXT \/\/ LAT\/LON GRID \/\/ RADAR \+ SMOKE OVERLAYS/);
assert.match(discoveryViewSource, /NATURAL EARTH 1:110m LAND BASEMAP", state:"CONNECTED"/);
assert.match(discoveryViewSource, /OTHER POLYGON LAYERS", state:"NOT WIRED"/);
assert.match(discoveryViewSource, /WeatherServices\.StationDiscoveryService/);
assert.match(discoveryServiceSource, /eonet\.gsfc\.nasa\.gov\/api\/v3\/events/);
assert.match(discoveryServiceSource, /gdeltproject\.org\/api\/v2\/doc\/doc/);
assert.match(discoveryServiceSource, /de1\.api\.radio-browser\.info\/json\/stations\/topvote/);
assert.match(discoveryServiceSource, /interval:\s*900000/);
assert.match(discoveryServiceSource, /running:\s*discovery\.active/);


const mainHeaderStart = windowSource.indexOf("id: header");
const mainHeaderEnd = windowSource.indexOf("// NAVIGATION", mainHeaderStart);
assert.ok(mainHeaderStart >= 0 && mainHeaderEnd > mainHeaderStart);
const header = windowSource.slice(mainHeaderStart, mainHeaderEnd);
assert.match(
    header,
    /text: "WEATHER STATION \/\/ " \+ weatherStation\.currentContext[\s\S]*?color: Colors\.magenta/
);
assert.doesNotMatch(header, /text:\s*weatherStation\.currentContext/);
assert.match(header, /height: 2\s+color: Colors\.cyan/);
assert.match(header, /border\.color: weatherStation\.sourceStatusColor/);
assert.match(header, /accentColor: Colors\.red/);

// HOME is now a mixed-source dashboard instead of a placeholder or a
// duplicated copy of the three full domain pages.
for (const title of ["⌁  GROUND", "☁  SKY", "✦  SPACE"])
    assert.ok(!homeSource.includes(title), "HOME still contains " + title);

for (const title of [
    "SNAPSHOT // NOW",
    "QUICK // CONDITIONS",
    "AUTO // RELEVANT",
])
    assert.ok(homeSource.includes('title: "' + title + '"'), title);

for (const cardTitle of [
    "CURRENT WEATHER",
    "NEXT HOURS",
    "AIR QUALITY",
    "HUMIDITY",
    "WIND",
    "UV INDEX",
    "SPACE WEATHER",
])
    assert.ok(homeSource.includes('title: "' + cardTitle + '"'), cardTitle);

assert.ok(homeSource.includes("StationHomePolicy.rankRelevant"));
assert.ok(homeSource.includes("activeWatchIds"));
assert.ok(homeSource.includes("temperatureDelta"));
assert.ok(homeSource.includes("pressureDelta"));
assert.ok(homeSource.includes("rainChanceDelta"));
assert.ok(homeSource.includes("aqiDelta"));
assert.ok(homeSource.includes("kpDelta"));
assert.ok(homeSource.includes("solarWindDelta"));
assert.ok(homeSource.includes("bzDelta"));
assert.ok(homeSource.includes("Repeater {"));
assert.ok(homeSource.includes("kpStaleAfterMinutes: 360"));
assert.ok(homeSource.includes("solarWindStaleAfterMinutes: 45"));
assert.ok(homeSource.includes("magneticFieldStaleAfterMinutes: 45"));
assert.ok(homeSource.includes("solarFluxStaleAfterMinutes: 2160"));
assert.ok(homeSource.includes('"spaceStale": spaceStale'));
assert.ok(!homeSource.includes("FAVORITES // RELEVANT // AUTO"));

assert.match(homeCardSource, /border\.color:\s*Colors\.cyan/);
assert.match(homeCardSource, /border\.color:\s*Colors\.cyan[\s\S]*?meterFillColor/);
assert.match(homePolicySource, /function chooseRelevant\(input\)/);
assert.match(homePolicySource, /function rankRelevant\(input, previousIds, limit\)/);
assert.match(homePolicySource, /function activeAbove\(/);
assert.match(homePolicySource, /function activeBelow\(/);
assert.match(homePolicySource, /SPACE WEATHER STACK/);
assert.match(homePolicySource, /HOT \/\/ HUMID/);
assert.match(homePolicySource, /WIND \+ RAIN/);
assert.match(homePolicySource, /PRESSURE TREND/);
assert.match(homePolicySource, /SUNRISE/);
assert.match(homePolicySource, /SUNSET/);

// HOME consumes both source families, so the header badge must describe the
// aggregate rather than pretending HOME is Weather-only.
assert.match(windowSource, /readonly property bool usesHomeSources:/);
assert.match(windowSource, /HOME LIVE \/\/ 2 FEEDS/);
assert.match(windowSource, /PARTIAL \/\/ WEATHER/);
assert.match(windowSource, /PARTIAL \/\/ SPACE/);

// Footer is source-level freshness, not a duplicate of the aggregate HOME badge.
assert.match(windowSource, /readonly property int spaceAgeMinutes:/);
assert.match(windowSource, /function compactAge\(ageMinutes\)/);
assert.match(
    windowSource,
    /"WEATHER " \+ compactAge\(weatherAgeMinutes\)[\s\S]*?" \/\/ SPACE " \+ compactAge\(spaceAgeMinutes\)/
);
assert.match(windowSource, /text:\s*weatherStation\.footerSourceStatus/);
assert.match(
    windowSource,
    /Row \{[\s\S]*?anchors\.leftMargin:\s*20[\s\S]*?spacing:\s*8[\s\S]*?text:\s*"◉"[\s\S]*?color:\s*Colors\.red[\s\S]*?text:\s*weatherStation\.footerSourceStatus[\s\S]*?color:\s*Colors\.cyan/
);
assert.doesNotMatch(windowSource, /WEATHER LINK ONLINE/);
assert.match(spaceServiceSource, /property date lastUpdated/);
assert.ok(
    spaceServiceSource.split("lastUpdated = receivedAt;").length - 1 >= 4,
    "each successful Space parser refreshes aggregate local receive age"
);
for (const sourceClock of [
    "kpLastUpdated",
    "solarWindLastUpdated",
    "magneticFieldLastUpdated",
    "solarFluxLastUpdated",
]) {
    assert.match(
        spaceServiceSource,
        new RegExp(sourceClock + " = receivedAt;"),
        sourceClock + " shares the successful receive timestamp"
    );
}

// Stable domain identities survive the structural split.
assert.match(groundSource, /text: "⌁  GROUND"[\s\S]*?color: Colors\.green/);
assert.match(skySource, /text: "☁  SKY"[\s\S]*?color: Colors\.cyan/);
assert.match(spaceSource, /text: "✦  SPACE"[\s\S]*?color: Colors\.magenta/);

// Station data groups use one reusable divider: orange section label with
// the same 2 px cyan structural rule already used by the Weather header/footer.
assert.match(dividerSource, /font\.pixelSize:\s*11/);
assert.match(dividerSource, /property color labelColor:\s*Colors\.orange/);
assert.match(dividerSource, /property color lineColor:\s*Colors\.cyan/);
assert.match(dividerSource, /height:\s*2[\s\S]*?color:\s*divider\.lineColor/);

for (const title of [
    "AIR // PARTICULATES",
    "GASES // POLLEN",
])
    assert.ok(groundSource.includes('title: "' + title + '"'), title);

for (const title of [
    "CURRENT // CONDITIONS",
    "ATMOSPHERE // OBSERVATION",
    "FORECAST // NEXT HOURS",
    "FORECAST // DAILY",
])
    assert.ok(skySource.includes('title: "' + title + '"'), title);

for (const title of [
    "SOLAR // GEOMAGNETIC",
    "FIELD // SOURCE TIMES",
])
    assert.ok(spaceSource.includes('title: "' + title + '"'), title);

// Ground/Space retain their stationary geometry. SKY scrolls its measured
// expanded forecast so daily weather, rain and sunrise/sunset stay reachable.
assert.match(groundSource, /Flickable\s*\{\s*id:\s*groundScroll/);
assert.match(groundSource, /clip:\s*true[\s\S]*?contentHeight:\s*Math\.max\(height, groundContent\.y \+ groundContent\.implicitHeight \+ 12\)/);
assert.match(groundSource, /id:\s*groundContent[\s\S]*?x:\s*20[\s\S]*?y:\s*12[\s\S]*?spacing:\s*10/);
assert.match(groundSource, /NeonScrollBar\s*\{[\s\S]*?flickable:\s*groundScroll[\s\S]*?handleStyle:\s*"star"/);
assert.match(groundSource, /id:\s*airQualityInstrument[\s\S]*?width:\s*248[\s\S]*?height:\s*166/);
assert.match(groundSource, /id:\s*aqiReadingText[\s\S]*?font\.pixelSize:\s*68/);
assert.match(groundSource, /safeSource:\s*aqiReadingText/);
assert.match(groundSource, /TOP GAS SUBINDEX/);
assert.match(groundSource, /function particulateText\(value\)/);
assert.match(groundSource, /title:\s*"ENVIRONMENT \/\/ SOURCE"/);
assert.match(groundSource, /weatherService\.airQualitySourceTime/);
assert.match(groundSource, /OF OZONE \/ NO₂ \/ CO/);
assert.match(groundSource, /title:\s*"AIR \/\/ NEXT 12 HOURS"/);
assert.match(groundSource, /ground\.airQualityForecastReady/);
assert.match(groundSource, /OPEN-METEO MODEL \/\/ LOCAL HOURS/);
assert.match(groundSource, /FORECAST UNAVAILABLE/);
assert.match(groundSource, /WeatherServices\.SeismicService\s*\{[\s\S]*?active:\s*ground\.visible/);
assert.match(groundSource, /SEISMIC \/\/ WORLDWIDE 24H/);
assert.match(groundSource, /quakeService\.events/);
assert.match(groundSource, /ground\.distanceLabel\(/);
assert.match(groundSource, /NOT AN EARTHQUAKE WARNING/);
assert.match(groundSource, /aqiSeverityColor\(modelData\.aqi\)/);
assert.match(weatherServiceSource, /&hourly=us_aqi,pm2_5,pm10/);
assert.match(weatherServiceSource, /&forecast_hours=12/);
assert.match(weatherServiceSource, /WeatherDataPolicy\.parseAirQualityForecast\(root\.hourly, 12\)/);
assert.match(skySource, /Flickable\s*\{\s*id:\s*skyScroll/);
assert.match(skySource, /clip:\s*true[\s\S]*?contentHeight:\s*Math\.max\(height, skyContent\.y \+ skyContent\.implicitHeight \+ 12\)/);
assert.match(skySource, /id:\s*skyContent[\s\S]*?x:\s*20[\s\S]*?y:\s*12[\s\S]*?spacing:\s*6/);
assert.match(skySource, /height:\s*74[\s\S]*?id:\s*hourlyIconGlyph/);
assert.match(skySource, /id:\s*hourlyIconGlyph\s+anchors\.centerIn:\s*parent\s+anchors\.verticalCenterOffset:\s*-8/);
assert.match(skySource, /id:\s*dailyForecastArtwork[\s\S]*?height:\s*116/);
assert.match(skySource, /id:\s*dailyWeatherDetails[\s\S]*?anchors\.top:\s*parent\.top/);
assert.match(skySource, /id:\s*dailyWeatherDetails[\s\S]*?text:\s*"SUN "/);
assert.match(skySource, /id:\s*dailyRainMeter\s+anchors\.bottom:\s*parent\.bottom[\s\S]*?modelData\.chanceRain/);
assert.match(skySource, /width:\s*110\s+height:\s*parent\.height\s+anchors\.horizontalCenter:\s*parent\.horizontalCenter\s+anchors\.horizontalCenterOffset:\s*-24/);
assert.match(skySource, /height:\s*116[\s\S]*?id:\s*dailyIconGlyph/);
assert.match(skySource, /id:\s*hourlyRainLabel/);
assert.ok(!skySource.includes("weather / atmosphere / radar / aviation"));
assert.match(skySource, /NeonScrollBar\s*\{[\s\S]*?flickable:\s*skyScroll[\s\S]*?handleStyle:\s*"star"/);
assert.match(spaceSource, /Flickable\s*\{\s*id:\s*spaceScroll/);
assert.match(spaceSource, /clip:\s*true[\s\S]*?contentHeight:\s*Math\.max\(height, spaceContent\.y \+ spaceContent\.implicitHeight \+ 12\)/);
assert.match(spaceSource, /id:\s*spaceContent[\s\S]*?x:\s*20[\s\S]*?y:\s*12[\s\S]*?spacing:\s*10/);
assert.match(spaceSource, /NeonScrollBar\s*\{[\s\S]*?flickable:\s*spaceScroll[\s\S]*?handleStyle:\s*"star"/);
assert.match(spaceSource, /WeatherServices\.AuroraService\s*\{[\s\S]*?active:\s*space\.visible/);
assert.match(spaceSource, /title:\s*"AURORA \/\/ 30-90 MIN FORECAST"/);
assert.match(spaceSource, /BOREALIS \/\/ NORTH PEAK/);
assert.match(spaceSource, /AUSTRALIS \/\/ SOUTH PEAK/);
assert.match(spaceSource, /NOAA OVATION GRID/);
assert.match(spaceSource, /WEATHER FIX \/\/ NEAREST OVATION CELL/);
assert.match(spaceSource, /NOT A LOCAL OBSERVATION/);
assert.match(spaceSource, /NOT A GUARANTEE OF VISIBLE AURORA/);
assert.match(spaceSource, /WeatherServices\.SolarFlareService\s*\{[\s\S]*?active:\s*space\.visible/);
assert.match(spaceSource, /title:\s*"SOLAR \/\/ GOES X-RAY FLARES"/);
assert.match(spaceSource, /LATEST DETECTED \/\/ PEAK/);
assert.match(spaceSource, /OBSERVED \/\/ LAST 24H/);
assert.match(spaceSource, /flareService\.cPlus24h/);
assert.match(spaceSource, /flareService\.events/);
assert.match(spaceSource, /EVENT PEAKS \/\/ NOT LIVE X-RAY FLUX/);
assert.match(spaceSource, /OBSERVATIONS, NOT ALERTS OR PREDICTIONS/);
assert.match(spaceSource, /WeatherServices\.XrayFluxService\s*\{[\s\S]*?active:\s*space\.visible/);
assert.match(spaceSource, /title:\s*"SOLAR \/\/ LIVE X-RAY FLUX"/);
assert.match(spaceSource, /LONG BAND \/\/ 0\.1-0\.8 NM/);
assert.match(spaceSource, /SHORT BAND \/\/ 0\.05-0\.4 NM/);
assert.match(spaceSource, /xrayService\.classEquivalent\.label/);
assert.match(spaceSource, /xrayService\.fluxLong/);
assert.match(spaceSource, /xrayService\.fluxShort/);
assert.match(spaceSource, /xrayService\.sampleFresh/);
assert.match(spaceSource, /xrayService\.trend/);
assert.match(spaceSource, /30-MIN SAMPLES \/\/ LOG SCALE/);
assert.match(spaceSource, /FLUX-CLASS EQUIVALENT, NOT A FLARE ALERT/);
assert.match(spaceSource, /WeatherServices\.SwpcAlertService\s*\{[\s\S]*?active:\s*space\.visible/);
assert.match(spaceSource, /title:\s*"SPACE WEATHER \/\/ NOAA BULLETINS"/);
assert.match(spaceSource, /OFFICIAL WATCHES \/\/ WARNINGS \/\/ ALERTS/);
assert.match(spaceSource, /alertService\.count48h/);
assert.match(spaceSource, /alertService\.bulletins/);
assert.match(spaceSource, /modelData\.issueUtc/);
assert.match(spaceSource, /modelData\.scale/);
assert.match(spaceSource, /NOT NECESSARILY ACTIVE/);
assert.match(spaceSource, /NOAA \/\/ WARNING VALIDITY REVIEW/);
assert.match(spaceSource, /EXPLICIT VALIDITY WINDOWS/);
assert.match(spaceSource, /alertService\.validity\.windowCount/);
assert.match(spaceSource, /alertService\.validity\.uncertainCount/);
assert.match(spaceSource, /model:\s*alertService\.ready && alertService\.fresh[\s\S]*?alertService\.validity\.windows/);
assert.match(spaceSource, /NO OPEN EXPLICIT WARNING WINDOWS FOUND \/\/ NOT AN ALL CLEAR/);
assert.match(spaceSource, /GEOMAGNETIC \/\/ WATCH-DAY OUTLOOK/);
assert.match(spaceSource, /id:\s*watchForecastRow/);
assert.match(spaceSource, /alertService\.watchForecast\.projectedDays/);
assert.match(spaceSource, /alertService\.watchForecast\.unresolvedCount/);
assert.match(spaceSource, /alertService\.watchForecast\.days/);
assert.match(spaceSource, /BELOW G1|modelData\.levelLabel/);
assert.match(spaceSource, /NO CURRENT WATCH-DAY PRODUCTS FOUND \/\/ NOT AN ALL CLEAR/);
assert.match(spaceSource, /NOAA WATCH FORECAST \/\/ SUPERSESSION \+ CANCELLATION/);
assert.match(spaceSource, /NOT OBSERVED STORM/);
assert.match(spaceSource, /SWPC WARNING WINDOW CHECK/);
assert.match(spaceSource, /NOT VERIFIED ACTIVE/);
assert.ok(!spaceSource.includes('"NO ACTIVE ALERTS"'));
assert.match(spaceSource, /id:\s*kpInstrument[\s\S]*?width:\s*236[\s\S]*?height:\s*184/);
assert.match(spaceSource, /id:\s*kpHeroReading[\s\S]*?font\.pixelSize:\s*74/);
assert.match(spaceSource, /safeSource:\s*kpHeroReading/);
assert.match(spaceSource, /PLANETARY \/\/ KP INDEX/);
assert.match(spaceSource, /STREAM SPEED/);
assert.match(spaceSource, /10\.7 CM RADIO FLUX/);
assert.match(spaceSource, /font\.pixelSize:\s*30[\s\S]*?TOTAL FIELD/);
assert.match(spaceSource, /NOAA SWPC \/\/ FOUR LIVE PRODUCTS/);

for (const [id, size] of [["conditionIconGlyph", 104], ["hourlyIconGlyph", 80], ["dailyIconGlyph", 100]]) {
    assert.match(skySource, new RegExp("id: " + id + "[\\s\\S]*?font\\.pixelSize: " + size));
}
for (const id of ["conditionIconGlyph", "hourlyIconGlyph", "dailyIconGlyph"])
    assert.match(skySource, new RegExp("safeSource: " + id));
assert.match(skySource, /Row\s*\{\s*anchors\.horizontalCenter:\s*parent\.horizontalCenter\s+spacing:\s*12[\s\S]*?text:\s*modelData\.date/);
assert.match(skySource, /height:\s*88[\s\S]*?anchors\.horizontalCenter:\s*parent\.horizontalCenter[\s\S]*?id:\s*conditionIconGlyph/);
assert.match(skySource, /width:\s*110[\s\S]*?font\.pixelSize:\s*104/);
// Daily rain and SUN belong inside the unchanged 116px icon frame,
// not below it where they push the next section out of view.
const dailySlice = skySource.slice(skySource.indexOf("id: dailyForecastArtwork"));
assert.ok(dailySlice.includes("modelData.chanceRain"));
assert.ok(dailySlice.includes("modelData.sunrise"));
assert.ok(dailySlice.includes("modelData.sunset"));
assert.ok(dailySlice.indexOf("dailyWeatherDetails") < dailySlice.indexOf("dailyIconGlyph"));

// Existing semantic telemetry severity remains independent from page identity.
assert.match(groundSource, /readonly property color aqiColor:/);
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(groundSource.includes("Colors." + color));

for (const property of ["kpColor", "solarWindColor", "bzColor"])
    assert.ok(spaceSource.includes("readonly property color " + property));
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(spaceSource.includes("Colors." + color));

// Current weather content remains on SKY rather than being lost in the split.
for (const token of [
    "weatherService.tempF",
    "weatherService.feelsLikeF",
    "weatherService.condition",
    "weatherService.humidity",
    "weatherService.windMph",
])
    assert.ok(skySource.includes(token), token);

// The first expansion pass wires real provider fields before redesigning
// the instruments around them.
for (const token of [
    "pressureHpa",
    "visibilityMiles",
    "cloudCover",
    "precipMm",
    "hourlyForecast",
    "dailyForecast",
])
    assert.ok(weatherServiceSource.includes(token), "weather service " + token);

for (const token of [
    "carbonMonoxide",
    "nitrogenDioxide",
    "ozone",
    "carbonMonoxideAqi",
    "nitrogenDioxideAqi",
    "ozoneAqi",
    "dust",
    "grassPollen",
    "ragweedPollen",
    "pollenAvailable",
])
    assert.ok(weatherServiceSource.includes(token), "air quality " + token);

for (const token of [
    "weatherService.pressureHpa",
    "weatherService.visibilityMiles",
    "weatherService.cloudCover",
    "weatherService.precipMm",
    "weatherService.uvIndex",
    "weatherService.hourlyForecast",
    "weatherService.dailyForecast",
    "FORECAST // NEXT HOURS",
    "FORECAST // DAILY",
])
    assert.ok(skySource.includes(token), "SKY expansion " + token);

for (const token of [
    "weatherService.ozone",
    "weatherService.nitrogenDioxide",
    "weatherService.carbonMonoxide",
    "weatherService.dust",
    "weatherService.pollenAvailable",
    "POLLEN // PEAK",
])
    assert.ok(groundSource.includes(token), "GROUND expansion " + token);

for (const token of [
    "spaceService.magneticFieldBt",
    "spaceService.kpTime",
    "spaceService.solarWindTime",
    "spaceService.magneticFieldTime",
    "spaceService.solarFluxTime",
    "IMF BT",
])
    assert.ok(spaceSource.includes(token), "SPACE expansion " + token);

for (const token of [
    "property real magneticFieldBt",
    "property string kpTime",
    "property string solarWindTime",
    "property string magneticFieldTime",
    "property string solarFluxTime",
])
    assert.ok(spaceServiceSource.includes(token), "space service " + token);

// Restored bars are not decorative/random meters. Their fill widths remain
// direct normalized functions of the real telemetry already displayed.
const meterSpecs = [
    {
        source: groundSource,
        objectName: "ground",
        fill: "green",
        meters: {
            aqi: "aqiValue / 500",
            pm25: "pm25Value / 100",
            pm10: "pm10Value / 150",
            ozone: "ozoneAqiValue / 500",
            nitrogenDioxide: "nitrogenDioxideAqiValue / 500",
            carbonMonoxide: "carbonMonoxideAqiValue / 500",
        },
    },
    {
        source: skySource,
        objectName: "sky",
        fill: "orange",
        meters: {
            temperature: "temperatureValue / 120",
            aqi: "aqiValue / 500",
            humidity: "humidityValue / 100",
            wind: "windValue / 50",
            cloudCover: "cloudCoverValue / 100",
            uv: "uvValue / 11",
        },
    },
    {
        source: spaceSource,
        objectName: "space",
        fill: "magenta",
        meters: {
            kp: "kpValue / 9",
            solarWind: "solarWindValue / 1000",
            bz: "Math.abs(bzValue) / 20",
            bt: "btValue / 20",
            solarFlux: "solarFluxValue / 300",
        },
    },
];

for (const spec of meterSpecs) {
    for (const [name, scale] of Object.entries(spec.meters)) {
        assert.ok(
            spec.source.includes("readonly property real " + name + "Meter"),
            name + " meter property"
        );
        assert.ok(spec.source.includes(scale), name + " real telemetry scale");
        assert.ok(
            spec.source.includes(
                "width: (parent.width - 4) * " +
                (spec.source === groundSource ? "ground."
                 : spec.source === skySource ? "sky." : "space.") +
                name + "Meter"
            ),
            name + " live fill width"
        );
    }

    assert.match(
        spec.source,
        new RegExp(
            "readonly property color meterBorderColor:\\s*Colors\\.cyan"
        )
    );
    assert.match(
        spec.source,
        new RegExp(
            "readonly property color meterFillColor:\\s*Colors\\."
            + spec.fill
        )
    );

    const borderBinding =
        "border.color: " + spec.objectName + ".meterBorderColor";
    const fillBinding =
        "color: " + spec.objectName + ".meterFillColor";

    assert.ok(
        spec.source.split(borderBinding).length - 1 >=
            Object.keys(spec.meters).length,
        spec.objectName + " meter border identity"
    );
    assert.ok(
        spec.source.split(fillBinding).length - 1 >=
            Object.keys(spec.meters).length,
        spec.objectName + " meter fill identity"
    );
}


// Forecast probability bars use their intrinsic 0-100 percent scale. There
// should be one meter path in each hourly and daily forecast delegate.
assert.match(
    skySource,
    /function chanceMeter\(value\)[\s\S]*?number \/ 100/
);
assert.ok(
    skySource.split("sky.chanceMeter(").length - 1 >= 2,
    "hourly and daily rain chance meters"
);
assert.ok(
    skySource.split("border.color: sky.meterBorderColor").length - 1 >= 8,
    "all SKY meter exteriors use cyan"
);
assert.ok(
    skySource.split("color: sky.meterFillColor").length - 1 >= 8,
    "all SKY meter interiors use orange"
);

// Fields without a defensible intrinsic/provider scale stay numeric for now.
// Do not invent pressure, visibility, precipitation, dust, pollen, or sample-time meters.
for (const forbidden of [
    "pressureMeter",
    "visibilityMeter",
    "precipMeter",
    "dustMeter",
    "pollenMeter",
    "sampleTimeMeter",
])
    assert.ok(!groundSource.includes(forbidden)
              && !skySource.includes(forbidden)
              && !spaceSource.includes(forbidden),
              forbidden + " should not be an arbitrary meter");

console.log("Weather Station domain palette contracts: PASS");
