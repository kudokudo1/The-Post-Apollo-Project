"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=p=>{
 const v=vm.createContext({});
 vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),v);
 return v;
};
const modes=policy("widgets/weather/StationCosmosModePolicy.js");
const panels=policy("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const nav=policy("widgets/weather/StationSubjectNavigationPolicy.js");
const focus=read("widgets/weather/StationCosmosModesPane.qml");
const terminal=read("widgets/weather/StationCosmosSunTerminalPane.qml");
const old=read("widgets/weather/StationCosmosSunInstrumentPane.qml");
const viewportMath=policy("widgets/weather/StationSolarImageViewportPolicy.js");

test("C12 primary SUN rail has four composite destinations while old routes still work",()=>{
 const expected=[
   ["OBSERVATION","cosmos/sun/observation","sun-observation"],
   ["ACTIVITY","cosmos/sun/activity","sun-activity"],
   ["YEAR","cosmos/sun/year","annual-solar"]
 ];
 assert.deepEqual(Array.from(modes.MODES.sun,r=>[r.label,r.route,r.kind]),expected);
 for(const [label,route,kind] of expected){
   assert.equal(modes.family(route),"sun");
   assert.equal(modes.kind(route),kind);
   assert.ok(nav.findRoute(route),label);
 }
 for(const path of [
   "cosmos/sun/live","cosmos/sun/position",
   "cosmos/sun/twilight","cosmos/sun/suvi","cosmos/sun/xray",
   "cosmos/sun/flares","cosmos/sun/cycle"
 ]){
   assert.equal(modes.family(path),"sun",path);
   assert.equal(modes.kind(path),path==="cosmos/sun/live" ? "sun-live"
     : path==="cosmos/sun/position" ? "sun-position"
     : path==="cosmos/sun/twilight" ? "light" : "solar-section",path);
   assert.ok(nav.findRoute(path),path);
 }
 assert.equal(modes.canonical("cosmos/sun/photo-light"),"cosmos/sun/twilight");
 assert.equal(modes.canonical("cosmos/sun/activity"),"cosmos/sun/activity");
 assert.equal(modes.usesSky("cosmos/sun/observation"),true);
 assert.equal(modes.usesSky("cosmos/sun/position"),true);
 assert.equal(modes.usesSky("cosmos/sun/live"),false);
 assert.equal(modes.usesSky("cosmos/sun/activity"),false);
 assert.equal(modes.usesSky("cosmos/sun/year"),false);
});

test("C12 source selectors use only existing owners and do not prefetch hidden panels",()=>{
 const cases=[
   ["cosmos/sun/observation",["flares","xray"],["cycle","alerts","kpForecast","aurora"]],
   ["cosmos/sun/live",["flares","xray"],["cycle","alerts","kpForecast","aurora"]],
   ["cosmos/sun/activity",["flares","xray","cycle"],["aurora","alerts","kpForecast"]],
   ["cosmos/sun/year",[],["flares","xray","cycle","aurora","alerts","kpForecast"]]
 ];
 for(const [route,on,off] of cases){
   for(const source of on) assert.equal(panels.needsSource(route,source),true,route+"/"+source);
   for(const source of off) assert.equal(panels.needsSource(route,source),false,route+"/"+source);
 }
 assert.equal(panels.visibleFor("space","cosmos/sun/observation","suvi"),true);
 assert.equal(panels.visibleFor("sky","cosmos/sun/observation","astronomy"),true);
 assert.equal(panels.visibleFor("sky","cosmos/sun/observation","twilight"),true);
 assert.equal(panels.visibleFor("space","cosmos/sun/live","suvi"),true);
 assert.equal(panels.visibleFor("space","cosmos/sun/activity","suvi"),false);
 assert.equal(panels.visibleFor("sky","cosmos/sun/position","twilight"),true);
 assert.equal(panels.visibleFor("sky","cosmos/sun/position","astronomy"),true);
 assert.match(focus,/active: cosmosModePane\.visible && \(cosmosModePane\.kind === "solar-section"/);
 assert.match(focus,/cosmosModePane\.kind === "sun-observation"/);
 assert.match(focus,/cosmosModePane\.kind === "sun-live" \|\| cosmosModePane\.kind === "sun-activity"/);
 assert.match(focus,/id: sunTerminalBoard\s*StationCosmosSunTerminalPane/);
 assert.match(focus,/skyFeed: cosmosModePane\.skyFeed/);
 assert.match(focus,/sourceSpace: cosmosModePane\.spaceFeed/);
 assert.doesNotMatch(terminal,/StationSky\s*\{|StationSpace\s*\{|Process\s*\{|FileView\s*\{|XMLHttpRequest|new WebSocket|Timer\s*\{|ScrollView\s*\{|Flickable\s*\{/);
});

test("C14 OBSERVATION shows interactive SUVI, solar arc, GOES and twilight together",()=>{
 for(const name of ["cosmos-c14-observation-board","cosmos-c14-observation-heroes",
   "cosmos-c14-suvi-hero","cosmos-c14-sun-path-hero",
   "cosmos-c14-live-telemetry","cosmos-c14-position-live-strip",
   "cosmos-c14-twilight-ledger"])
   assert.ok(terminal.includes(name),name);
 assert.match(terminal,/sourceComponent: sunTerminal\.terminalMode==="observation" \? observationBoard/);
 assert.match(focus,/terminalMode: cosmosModePane\.kind === "sun-observation" \? "observation"/);
 assert.equal(nav.findRoute("cosmos/sun/observation").label,
              "OBSERVATION // SUVI + SUN ARC + LIGHT");
 assert.doesNotMatch(terminal,/Flickable\s*\{|ScrollView\s*\{/);
});

test("C12 POSITION keeps sun arc hover controls, eight twilight readings and current sky strip",()=>{
 assert.match(terminal,/objectName: "cosmos-c12-position-board"/);
 assert.match(terminal,/StationCosmosVisualInstruments\s*\{/);
 assert.match(terminal,/compactMode: true/);
 assert.match(terminal,/showMoon: false/);
 assert.match(terminal,/showSun: true/);
 for(const field of [
   "astronomicalDawn","civilDawn","solarNoon","civilDusk",
   "blueMorningStart","blueMorningEnd","goldenMorningStart",
   "goldenMorningEnd","goldenEveningStart","goldenEveningEnd",
   "blueEveningStart","blueEveningEnd",
   "sunrise","sunset","daylightLabel","altitudeDegrees","azimuthDegrees"
 ]) assert.ok(terminal.includes(field),field);
 assert.match(terminal,/objectName: "cosmos-c12-light-ledger"/);
 assert.match(terminal,/objectName: "cosmos-c12-position-live-strip"/);
});

test("C12 LIVE shares complete interactive SUVI imager and displays GOES source context",()=>{
 assert.match(terminal,/objectName: "cosmos-c12-suvi-hero"/);
 assert.match(terminal,/StationCosmosSunInstrumentPane\s*\{/);
 assert.match(terminal,/modeRoute: "cosmos\/sun\/suvi"/);
 assert.match(terminal,/solarImageInfo\.shortLabel/);
 assert.match(terminal,/xray\.fluxLong/);
 assert.match(terminal,/flares\.latest\.classLabel/);
 assert.match(terminal,/objectName: "cosmos-c12-live-source-line"/);
 assert.match(old,/selectSolarImageMode\(modelData\.key\)/);
 assert.match(old,/source: solarFocus\.sourceSpace[\s\S]*?solarImageUrl/);
});

test("C13 ACTIVITY renders xray, flare and cycle in one non-scrolling instrument cluster",()=>{
 for(const name of [
   "cosmos-c12-activity-metrics","cosmos-c13-simultaneous-instruments",
   "cosmos-c13-xray-bay","cosmos-c13-flare-bay","cosmos-c13-cycle-bay",
   "cosmos-c12-xray-trend","cosmos-c12-xray-facts",
   "cosmos-c12-flare-facts","cosmos-c12-cycle-facts"
 ]) assert.ok(terminal.includes(name),name);
 for(const source of ["flareAt","flarePage","cyclePage","xrayPage",
                       "selectedFlareIndex","SolarDetails.flarePage(selectedFlare, 1)"])
   assert.ok(terminal.includes(source),source);
 assert.match(terminal,/cycle\.refresh\(true\)/);
 assert.match(terminal,/flares\.refresh\(\)/);
 assert.match(terminal,/xray\.refresh\(\)/);
 assert.match(terminal,/SOLAR CYCLE \/\/ MONTHLY MODEL \+ RANGES \/\/ NOT LIVE/);
 assert.match(terminal,/OBSERVED FLARES/);
 assert.doesNotMatch(terminal,/id: activityTabs\b|id: activityInstrument\b/);
 assert.doesNotMatch(terminal,/activityFocus===|cycleDetailPage|flareDetailPage|xraySourcePage/);
 assert.match(focus,/id: solarDetails\s*StationCosmosSunInstrumentPane\s*\{/);
 assert.match(focus,/id: solarYear\s*StationCosmosAnnualWheelPane\s*\{/);
});
test("C15 ACTIVITY uses source-backed nonuniform scientific representations",()=>{
 assert.match(terminal,/objectName: "cosmos-c13-xray-graph"/);
 assert.match(terminal,/objectName: "cosmos-c15-cycle-range-chart"/);
 assert.match(terminal,/objectName: "cosmos-c12-flare-facts"/);
 assert.match(terminal,/xray\.trend/);
 assert.match(terminal,/ssnRangeValid/);
 assert.match(terminal,/fluxRangeValid/);
 assert.match(terminal,/predictedSsn/);
 assert.match(terminal,/selectedFlare\.peakUtc/);
 assert.match(terminal,/selectedFlare\.flux/);
 assert.match(terminal,/OBSERVED FLARES/);
 assert.doesNotMatch(terminal,/model: sunTerminal\.cycleFields/);
 assert.doesNotMatch(terminal,/model: sunTerminal\.flareFields/);
 assert.doesNotMatch(terminal,/id: activityTabs\b|id: activityInstrument\b/);
 assert.doesNotMatch(terminal,/Flickable\s*\{|ScrollView\s*\{/);
});


test("C15 OBSERVATION distinguishes live class, source-backed meters, daylight and twilight",()=>{
 for(const name of [
  "cosmos-c14-suvi-hero","cosmos-c14-sun-path-hero",
  "cosmos-c14-live-telemetry","cosmos-c15-space-context-meters",
  "cosmos-c15-daylight-timeline","cosmos-c15-twilight-groups"
 ]) assert.ok(terminal.includes(name),name);
 for(const source of ["kpReady","solarWindReady","magneticFieldReady",
                       "solarWindSpeed","magneticFieldBz"])
   assert.ok(terminal.includes(source),source);
 assert.match(terminal,/contextMeters:/);
 assert.match(terminal,/highlights:/);
 assert.doesNotMatch(terminal,/model: observation\.liveReadings/);
 assert.doesNotMatch(terminal,/Flickable\s*\{|ScrollView\s*\{/);
});

test("C16 twilight is a four-row single-line ledger, not a compact 2x2 grid",()=>{
 assert.match(terminal,/objectName: "cosmos-c15-twilight-groups"/);
 assert.match(terminal,/objectName: "cosmos-c16-twilight-single-row"/);
 assert.match(terminal,/objectName: "cosmos-c16-twilight-one-line-time"/);
 assert.match(terminal,/model: observation\.highlights/);
 for (const label of ["BLUE AM","GOLD AM","GOLD PM","BLUE PM"])
   assert.ok(terminal.includes('name:"'+label+'"'),label);
 assert.match(terminal,/shownRows: twilightRows\.count/);
 assert.match(terminal,/text: modelData\.value/);
 assert.match(terminal,/horizontalAlignment: Text\.AlignRight/);
 const singleLine=terminal.slice(terminal.indexOf('id: twilightGroups'),
    terminal.indexOf('    // ACTIVITY'));
 assert.doesNotMatch(singleLine,/columns: 2/);
 assert.ok((singleLine.match(/wrapMode: Text\.NoWrap/g)||[]).length>=2);
});

test("C16 SUVI zoom is opt-in for OBSERVATION, bounded, panable and resettable",()=>{
 assert.match(terminal,/objectName: "cosmos-c14-suvi-hero"[\s\S]*?imageInteractive: true/);
 assert.doesNotMatch(terminal,/objectName: "cosmos-c12-suvi-hero"[\s\S]*?imageInteractive: true[\s\S]*?objectName: "cosmos-c12-live-telemetry"/);
 for(const token of ["cosmos-c16-suvi-viewport","cosmos-c16-suvi-pan-input",
    "cosmos-c16-suvi-zoom-controls","cosmos-c16-suvi-expand",
    "onWheel: (wheel)","onPositionChanged: (mouse)",
    "function panBy(dx,dy)","function zoomAt(factor,focusX,focusY)",
    "function resetZoom()","source: solarFocus.sourceSpace"])
   assert.ok(old.includes(token),token);
 assert.match(old,/property bool imageInteractive: false/);
 assert.match(old,/visible: solarFocus\.imageInteractive/);
 assert.match(old,/solarFocus\.imageExpanded = !solarFocus\.imageExpanded/);
 assert.match(old,/onSourceChanged: solarFocus\.resetSuviView\(\)/);
 assert.match(old,/width: solarFocus\.imageInteractive && solarFocus\.imageExpanded/);
 assert.match(old,/ImageViewportPolicy\.clampPan/);
 assert.match(old,/ImageViewportPolicy\.zoomAt/);
 assert.doesNotMatch(old,/Process\s*\{|XMLHttpRequest|new WebSocket|Flickable\s*\{|ScrollView\s*\{/);
});

test("C16 image math clamps zoom/pan and keeps the zoom cursor fixed",()=>{
 assert.equal(viewportMath.zoom(-4),1);
 assert.equal(viewportMath.zoom(1),1);
 assert.equal(viewportMath.zoom(99),5);
 const fit=viewportMath.clampPan(1,300,-300,120,120,120,120);
 assert.equal(fit.x,0); assert.equal(fit.y,0);
 const bounded=viewportMath.clampPan(2,300,-300,120,120,120,120);
 assert.equal(bounded.x,60); assert.equal(bounded.y,-60);
 const left=viewportMath.zoomAt(1,2,0,0,30,60,120,120,120,120);
 assert.equal(left.zoom,2); assert.equal(left.x,30); assert.equal(left.y,0);
 const letterbox=viewportMath.clampPan(2,150,150,220,120,120,120);
 assert.equal(letterbox.x,10); assert.equal(letterbox.y,60);
 const out=viewportMath.zoomAt(5,2,0,0,60,60,120,120,120,120);
 assert.equal(out.zoom,5);
});
