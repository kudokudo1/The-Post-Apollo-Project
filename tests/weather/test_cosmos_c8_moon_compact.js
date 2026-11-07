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
   "cosmos-c9-moon-hero-row",
   "cosmos-c8-moon-readings"
 ]) {
   const start=moon.indexOf('objectName: "'+objectName+'"');
   assert.ok(start>0,objectName);
   const next=moon.slice(start,start+450);
   assert.match(next,/anchors\.leftMargin: moonPane\.contentInset/);
   assert.match(next,/anchors\.rightMargin: moonPane\.contentInset/);
 }
 assert.match(moon,/anchors\.topMargin: moonPane\.contentInset/);
 assert.match(moon,/anchors\.bottomMargin: moonPane\.contentInset/);
});

test("C18 MOON uses three equal-width SUN-style modes above phase instruments",()=>{
 assert.match(moon,/objectName: "cosmos-c18-moon-fullwidth-mode-rail"/);
 assert.match(moon,/id: moonModeRail/);
 assert.match(moon,/anchors\.top: titleRail\.bottom/);
 assert.match(moon,/anchors\.top: moonModeRail\.bottom/);
 assert.match(moon,/height: Math\.min\(166,Math\.max\(0,moonPane\.height-138\)\)/);
 for(const name of [
   "cosmos-c18-moon-observation-tab",
   "cosmos-c11-open-moon-year",
   "cosmos-c17-open-moon-forecast"
 ])assert.ok(moon.includes('objectName: "'+name+'"'),name);
 assert.equal((moon.match(/\(moonModeRail\.width-2\*moonModeRail\.spacing\)\/3/g)||[]).length,3);
 assert.equal((moon.match(/height: 27/g)||[]).length,4);
 assert.match(moon,/label: "PHASE \+ POSITION"[\s\S]*?selected: true/);
 assert.match(moon,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.match(moon,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/forecast"\)/);
 const title=moon.slice(moon.indexOf('id: titleRail'),moon.indexOf('id: moonModeRail'));
 assert.doesNotMatch(title,/ActionButton/);
 assert.match(title,/USNO /);
 assert.doesNotMatch(moon,/Flickable\s*\{|ScrollView\s*\{/);
});
