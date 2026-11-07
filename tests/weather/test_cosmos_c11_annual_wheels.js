"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const base=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(base,p),"utf8");
const policy=p=>{
 const v=vm.createContext({});
 vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),v);
 return v;
};
const modes=policy("widgets/weather/StationCosmosModePolicy.js");
const routes=policy("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const host=read("widgets/weather/StationCosmosAnnualWheelPane.qml");
const subject=read("widgets/weather/StationCosmosSubjectPane.qml");
const focus=read("widgets/weather/StationCosmosModesPane.qml");
const moon=read("widgets/weather/StationCosmosMoonCompactPane.qml");
const magick=read("widgets/weather/StationMagickAnnualCalendarPane.qml");
const service=read("services/weather/CelestialAnnualCalendarService.qml");

test("Sun retains its YEAR instrument alongside three composite terminal modes",()=>{
 assert.equal(modes.family("cosmos/sun/year"),"sun");
 assert.equal(modes.kind("cosmos/sun/year"),"annual-solar");
 assert.equal(modes.usesSky("cosmos/sun/year"),false);
 assert.equal(modes.modesFor("cosmos/sun/year").length,3);
 for(const name of ["OBSERVATION","ACTIVITY","YEAR"])
   assert.ok(modes.modesFor("cosmos/sun/year").some(x=>x.label===name),name);
 assert.equal(routes.kindForRoute("cosmos/sun/year"),"sky");
 assert.equal(routes.needsSource("cosmos/sun/year","moon"),false);
 assert.equal(routes.needsSource("cosmos/sun/year","celnav"),false);
 assert.equal(routes.needsSource("cosmos/sun/year","planets"),false);
 assert.equal(routes.needsSource("cosmos/sun/year","cycle"),false);
 assert.match(focus,/cosmosModePane\.kind === "annual-solar" \? solarYear/);
 assert.match(focus,/id: solarYear\s*StationCosmosAnnualWheelPane\s*\{/);
 assert.match(focus,/subject: "sun"/);
});

test("Moon phase/position remain intact with a reversible YEAR route",()=>{
 assert.equal(routes.kindForRoute("cosmos/moon/ephemeris"),"sky");
 assert.equal(routes.kindForRoute("cosmos/moon/year"),"sky");
 assert.equal(routes.needsSource("cosmos/moon/year","moon"),false);
 assert.equal(routes.needsSource("cosmos/moon/year","celnav"),false);
 assert.match(moon,/signal routeRequested\(string path\)/);
 assert.match(moon,/objectName: "cosmos-c11-open-moon-year"/);
 assert.match(moon,/onClicked: moonPane\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.match(subject,/cosmosPane\.subjectRoute === "cosmos\/moon\/ephemeris"\s*\? moonCompactComponent/);
 assert.match(subject,/cosmosPane\.subjectRoute === "cosmos\/moon\/year"\s*\? moonYearComponent/);
 assert.match(subject,/id: moonYearComponent\s*StationCosmosAnnualWheelPane\s*\{/);
 assert.match(host,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/ephemeris"\)/);
 assert.match(subject,/id: moonCompactComponent\s*StationCosmosMoonCompactPane[\s\S]*?onRouteRequested: function\(path\)/);
 assert.match(moon,/readonly property int renderedFactCount: 9/);
});

test("Both COSMOS wheels reuse the original MAGICK renderer and JPL actor",()=>{
 assert.match(host,/StationMagickAnnualCalendarPane\s*\{/);
 assert.match(host,/view: annualFocus\.annualView/);
 assert.match(host,/lockedView: annualFocus\.annualView/);
 assert.match(host,/readonly property string annualView:[\s\S]*?moonView === "forecast" \? "forecast" : "moon"/);
 assert.match(host,/objectName: annualFocus\.isMoon[\s\S]*?"cosmos-c11-moon-year-wheel"[\s\S]*?: "cosmos-c11-sun-year-wheel"/);
 assert.match(magick,/property string lockedView: ""/);
 assert.match(magick,/visible: annualPane\.lockedView === ""/);
 assert.match(magick,/height: visible \? 26 : 0/);
 assert.match(magick,/readonly property var calendarSource: annualSource/);
 assert.match(magick,/data\.lunar_events/);
 assert.match(magick,/data\.solar_terms/);
 assert.match(magick,/annualPane\.scopeMode==="month"/);
 assert.match(magick,/annualPane\.zoomAt/);
 assert.match(magick,/annualPane\.panBy/);
 assert.match(magick,/annualPane\.fitWheel/);
 assert.match(magick,/annualPane\.resetView/);
 assert.match(service,/property bool active: false/);
 assert.match(service,/function calculate\(\)/);
 assert.match(service,/Atlas\.validate\(parsed,year,timezoneId\)/);
 assert.doesNotMatch(service,/onCompleted:\s*calculate\(/);
 assert.doesNotMatch(host,/Process\s*\{|XMLHttpRequest|Flickable\s*\{|ScrollView\s*\{|new WebSocket/);
});

test("COSMOS wheel mode is fixed and leaves MAGICK free to choose all three modes",()=>{
 const original=read("widgets/weather/StationMagickLunarSolarPane.qml");
 assert.match(original,/StationMagickAnnualCalendarPane\s*\{/);
 assert.doesNotMatch(original,/lockedView:/);
 assert.match(magick,/model:\s*\[\s*\{id:"moon",label:"LUNAR YEAR"\},[\s\S]*?\{id:"solar",label:"SOLAR YEAR"\},[\s\S]*?\{id:"forecast",label:"FORECAST"\}/);
 assert.match(host,/visible: annualFocus\.isMoon/);
 assert.doesNotMatch(host,/objectName: "cosmos-c17-moon-forecast-tab"/);
 assert.doesNotMatch(host,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/forecast"\)/);
 assert.match(host,/anchors\.leftMargin: annualFocus\.contentInset/);
 assert.match(host,/anchors\.rightMargin: annualFocus\.contentInset/);
 assert.match(host,/anchors\.bottomMargin: annualFocus\.contentInset/);
 assert.match(host,/readonly property int contentInset: isMoon \? 6 : 0/);
 assert.match(host,/objectName: "cosmos-c11-back-to-moon"/);
 assert.match(moon,/readonly property int contentInset: 6/);
});
test("C19 COSMOS year and INDEX forecast offer two full-width main Moon modes",()=>{
 assert.match(host,/objectName: "cosmos-c11-moon-year-mode-rail"/);
 assert.match(host,/height: visible \? 27 : 0/);
 for(const name of ["OVERVIEW","LUNAR YEAR"])
   assert.ok(host.includes('label: "'+name+'"'),name);
 assert.equal((host.match(/height: 27/g)||[]).length,2);
 assert.equal((host.match(/\(lunarModeRail\.width-lunarModeRail\.spacing\)\/2/g)||[]).length,2);
 assert.match(host,/selected: annualFocus\.moonView !== "forecast"/);
 assert.doesNotMatch(host,/selected: annualFocus\.moonView === "forecast"/);
 assert.match(host,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/ephemeris"\)/);
 assert.match(host,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.doesNotMatch(host,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/forecast"\)/);
});

test("C23 MOON year and INDEX forecast reuse the cyan header divider without moving SUN",()=>{
 assert.match(host,/id: moonHeaderDivider[\s\S]*?objectName: "cosmos-c23-moon-year-divider"/);
 assert.match(host,/id: moonHeaderDivider[\s\S]*?visible: annualFocus\.isMoon/);
 assert.match(host,/anchors\.top: lunarModeRail\.bottom/);
 assert.match(host,/anchors\.topMargin: visible \? 2 : 0/);
 assert.match(host,/height: visible \? 2 : 0\s*color: Colors\.cyan/);
 assert.match(host,/anchors\.top: moonHeaderDivider\.bottom/);
 assert.match(host,/anchors\.topMargin: 0/);
 // The original YEAR child began 4px after modeRail. 2px gap +
 // 2px line preserves that exact stage Y coordinate.
 assert.doesNotMatch(host,/anchors\.topMargin: annualFocus\.isMoon \? 4 : 0/);
});
