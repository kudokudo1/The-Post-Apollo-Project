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
 assert.match(moon,/model: 9/);
 assert.match(moon,/columns: 3/);
 assert.match(moon,/height: Math\.max\(1,\(factGrid\.height-2\*factGrid\.spacing\)\/3\)/);
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
