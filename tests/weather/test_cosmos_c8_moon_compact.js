"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const subject=read("widgets/weather/StationCosmosSubjectPane.qml");
const moon=read("widgets/weather/StationCosmosMoonCompactPane.qml");
const sky=read("widgets/weather/StationSky.qml");
const magick=read("widgets/weather/StationMagickLunarSolarPane.qml");
const panelPolicy=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");

test("only COSMOS Moon ephemeris swaps its long SKY report for fixed Moon",()=>{
 assert.match(subject,/cosmosPane\.subjectRoute === "cosmos\/moon\/ephemeris"/);
 assert.match(subject,/\? moonCompactComponent/);
 assert.match(subject,/id: moonCompactComponent\s*StationCosmosMoonCompactPane/);
 assert.match(subject,/id: skyComponent\s*StationSky/);
 assert.match(subject,/id: overviewComponent\s*StationCosmosOverviewPane/);
 assert.match(subject,/cosmosPane\.kind === "sky" \? skyComponent/);
});

test("MAGICK compact phase controls and all original USNO source readings remain",()=>{
 for(const field of ["moonReady: moonPane.moonReady","moonEphemeris: moonPane.moonEphemeris",
   "compactMode: true","showMoon: true","showSun: false",
   "MOONRISE","UPPER TRANSIT","MOONSET","VISIBILITY",
   "ALTITUDE // HC","AZIMUTH // ZN","SOURCE DATE",
   "CIVIL OFFSET","OFFSET ORIGIN","moonEphemeris.noRiseSet",
   "moonCivilOffsetSource","moonCivilOffsetMinutes",
   "moonPosition.altitude","moonPosition.azimuth","moonPosition.direction",
   "positionSnapshot.time","positionSnapshot.date",
   'objectName: "cosmos-c8-moon-phase"',
   'objectName: "cosmos-c8-moon-readings"'])
    assert.ok(moon.includes(field),field);
 assert.match(magick,/StationCosmosVisualInstruments\s*\{/);
 assert.match(magick,/compactMode: true/);
 assert.match(moon,/readonly property int renderedFactCount: 9/);
 assert.match(moon,/id: heroRow/);
 assert.match(moon,/id: positionColumn/);
 assert.match(moon,/id: eventRibbon/);
 assert.match(moon,/id: provenanceRow/);
 assert.match(moon,/model: 3/);
 assert.doesNotMatch(moon,/Grid \\{|model: 9|Flickable \\{/);
});

test("new Moon pane starts no new services and never scrolls",()=>{
 assert.match(moon,/StationSky\s*\{/);
 assert.match(moon,/sourceOnly: true/);
 assert.match(moon,/subjectRoute: "cosmos\/moon\/ephemeris"/);
 assert.match(sky,/CosmosPanelPolicy\.needsSource\(sky\.subjectRoute,"moon"\)/);
 assert.match(panelPolicy,/"cosmos\/moon\/ephemeris": \{page:"sky",sky:\["header","moon","moon-position"\]\}/);
 for(const token of ["Flickable {","ScrollView {","Process {","FileView {","XMLHttpRequest","Timer {",
   "UsnoMoonService {","UsnoCelnavService {","NasaEclipseService {"])
   assert.ok(!moon.includes(token),token);
});

test("source status remains visible and unavailable facts do not invent readings",()=>{
 assert.match(moon,/moonSource\.failed/);
 assert.match(moon,/positionSource\.failed/);
 assert.match(moon,/moonSource\.errorText/);
 assert.match(moon,/positionSource\.errorText/);
 assert.match(moon,/NO RISE OR SET FOR THIS CIVIL DATE/);
 assert.match(moon,/NOT IN USNO LIST/);
 assert.match(moon,/if \(value === null \|\| value === undefined/);
 assert.match(moon,/!isFinite\(Number\(value\)\)/);
});

test("Moon C10 matches the six-pixel COSMOS overview and mode-page stage gutter",()=>{
 const overview=read("widgets/weather/StationCosmosOverviewPane.qml");
 const modes=read("widgets/weather/StationCosmosModesPane.qml");
 assert.match(overview,/anchors\.margins: 6/);
 assert.match(modes,/anchors\.margins: 6/);
 assert.match(moon,/readonly property int contentInset: 6/);
 for(const objectName of [
   "cosmos-c9-moon-free-header",
   "cosmos-c9-moon-hero-row"
 ]) {
   const start=moon.indexOf('objectName: "'+objectName+'"');
   assert.ok(start>0,objectName);
   const next=moon.slice(start,start+580);
   assert.match(next,/anchors\.leftMargin: moonPane\.contentInset/);
   assert.match(next,/anchors\.rightMargin: moonPane\.contentInset/);
 }
 assert.match(moon,/id: compactReadings[\s\S]*?width: Math\.max\(1,heroRow\.width-moonMain\.width-heroRow\.spacing\)/);
 assert.match(moon,/anchors\.topMargin: moonPane\.contentInset/);
 assert.match(moon,/anchors\.bottomMargin: moonPane\.contentInset/);
});

test("C19 MOON overview and year share top modes above source-backed forecast",()=>{
 assert.match(moon,/objectName: "cosmos-c18-moon-fullwidth-mode-rail"/);
 assert.match(moon,/id: moonModeRail/);
 assert.match(moon,/anchors\.top: titleRail\.bottom/);
 assert.match(moon,/anchors\.top: moonModeRail\.bottom/);
 assert.match(moon,/objectName: "cosmos-c20-moon-primary-instruments"/);
 assert.match(moon,/anchors\.bottom: parent\.bottom/);
 for(const name of [
   "cosmos-c18-moon-observation-tab",
   "cosmos-c11-open-moon-year"
 ])assert.ok(moon.includes('objectName: "'+name+'"'),name);
 assert.equal((moon.match(/\(moonModeRail\.width-moonModeRail\.spacing\)\/2/g)||[]).length,2);
 assert.equal((moon.match(/height: 27/g)||[]).length,3);
 assert.match(moon,/label: "OVERVIEW"[\s\S]*?selected: true/);
 assert.match(moon,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.doesNotMatch(moon,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/forecast"\)/);
 assert.match(moon,/StationCosmosMoonForecastStrip\s*\{/);
 assert.match(moon,/verticalMode: true/);
 assert.match(moon,/id: compactReadings[\s\S]*?id: moonForecastStrip/);
 assert.match(moon,/id: provenanceRow/);
 assert.match(moon,/id: eventRibbon/);
 const title=moon.slice(moon.indexOf('id: titleRail'),moon.indexOf('id: moonModeRail'));
 assert.doesNotMatch(title,/ActionButton/);
 assert.match(title,/USNO /);
 assert.doesNotMatch(moon,/Flickable\s*\{|ScrollView\s*\{/);
});

test("C20 instrument-first Moon overview has separate visual, forecast and event hierarchies",()=>{
 const strip=read("widgets/weather/StationCosmosMoonForecastStrip.qml");
 for(const name of ["cosmos-c20-moon-primary-instruments",
   "cosmos-c9-moon-tall-position","cosmos-c9-moon-free-provenance",
   "cosmos-c20-moon-event-ledger","cosmos-c8-moon-source-note"])
   assert.ok(moon.includes(name),name);
 assert.match(moon,/moonMain\.height-2\*moonMain\.spacing\)\*0\.62/);
 assert.match(moon,/compactReadings\.height-2\*compactReadings\.spacing\)\*0\.65/);
 assert.match(strip,/property bool verticalMode: false/);
 assert.match(strip,/objectName: "cosmos-c20-moon-vertical-forecast"/);
 assert.match(strip,/objectName: "cosmos-c20-forecast-day-row"/);
 assert.match(strip,/objectName: "cosmos-c20-forecast-selected-daylight"/);
 assert.match(strip,/modelData\.illumination\/100/);
 assert.match(strip,/modelData\.dayFraction/);
 assert.match(strip,/ForecastCalendar\.build/);
 assert.match(strip,/onClicked: forecastStrip\.selectedDate=modelData\.date/);
 assert.match(moon,/verticalMode: true/);
 assert.equal((moon.match(/objectName: "cosmos-c8-moon-fact"/g)||[]).length,3);
 assert.doesNotMatch(moon,/Flickable\s*\{|ScrollView\s*\{|Process\s*\{/);
});
