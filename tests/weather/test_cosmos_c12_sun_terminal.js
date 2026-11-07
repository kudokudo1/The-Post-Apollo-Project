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

test("C12 primary SUN rail has four composite destinations while old routes still work",()=>{
 const expected=[
   ["LIVE","cosmos/sun/live","sun-live"],
   ["POSITION + LIGHT","cosmos/sun/position","sun-position"],
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
   "cosmos/sun/twilight","cosmos/sun/suvi","cosmos/sun/xray",
   "cosmos/sun/flares","cosmos/sun/cycle"
 ]){
   assert.equal(modes.family(path),"sun",path);
   assert.equal(modes.kind(path),path==="cosmos/sun/twilight"
     ? "light" : "solar-section",path);
   assert.ok(nav.findRoute(path),path);
 }
 assert.equal(modes.canonical("cosmos/sun/photo-light"),"cosmos/sun/twilight");
 assert.equal(modes.canonical("cosmos/sun/activity"),"cosmos/sun/activity");
 assert.equal(modes.usesSky("cosmos/sun/position"),true);
 assert.equal(modes.usesSky("cosmos/sun/live"),false);
 assert.equal(modes.usesSky("cosmos/sun/activity"),false);
 assert.equal(modes.usesSky("cosmos/sun/year"),false);
});

test("C12 source selectors use only existing owners and do not prefetch hidden panels",()=>{
 const cases=[
   ["cosmos/sun/live",["flares","xray"],["cycle","alerts","kpForecast","aurora"]],
   ["cosmos/sun/activity",["flares","xray","cycle"],["aurora","alerts","kpForecast"]],
   ["cosmos/sun/year",[],["flares","xray","cycle","aurora","alerts","kpForecast"]]
 ];
 for(const [route,on,off] of cases){
   for(const source of on) assert.equal(panels.needsSource(route,source),true,route+"/"+source);
   for(const source of off) assert.equal(panels.needsSource(route,source),false,route+"/"+source);
 }
 assert.equal(panels.visibleFor("space","cosmos/sun/live","suvi"),true);
 assert.equal(panels.visibleFor("space","cosmos/sun/activity","suvi"),false);
 assert.equal(panels.visibleFor("sky","cosmos/sun/position","twilight"),true);
 assert.equal(panels.visibleFor("sky","cosmos/sun/position","astronomy"),true);
 assert.match(focus,/active: cosmosModePane\.visible && \(cosmosModePane\.kind === "solar-section"/);
 assert.match(focus,/cosmosModePane\.kind === "sun-live" \|\| cosmosModePane\.kind === "sun-activity"/);
 assert.match(focus,/id: sunTerminalBoard\s*StationCosmosSunTerminalPane/);
 assert.match(focus,/skyFeed: cosmosModePane\.skyFeed/);
 assert.match(focus,/sourceSpace: cosmosModePane\.spaceFeed/);
 assert.doesNotMatch(terminal,/StationSky\s*\{|StationSpace\s*\{|Process\s*\{|FileView\s*\{|XMLHttpRequest|new WebSocket|Timer\s*\{|ScrollView\s*\{|Flickable\s*\{/);
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

test("C12 ACTIVITY keeps xray history/source, flare event paging and cycle three-page model",()=>{
 for(const name of [
   "cosmos-c12-activity-metrics","cosmos-c12-activity-inner-modes",
   "cosmos-c12-xray-trend","cosmos-c12-xray-facts",
   "cosmos-c12-flare-facts","cosmos-c12-cycle-facts"
 ]) assert.ok(terminal.includes(name),name);
 for(const key of [
   "flareCount","flareAt","flarePage","cyclePage","xrayPage",
   "selectedFlareIndex","flareDetailPage","cycleDetailPage","xraySourcePage"
 ]) assert.ok(terminal.includes(key),key);
 assert.match(terminal,/cycle\.refresh\(true\)/);
 assert.match(terminal,/flares\.refresh\(\)/);
 assert.match(terminal,/xray\.refresh\(\)/);
 assert.match(terminal,/NOAA SOLAR CYCLE \/\/ MONTHLY PREDICTION, NOT LIVE FLUX/);
 assert.match(terminal,/OBSERVED EVENT PEAKS, NOT ALERTS/);
 assert.match(focus,/id: solarDetails\s*StationCosmosSunInstrumentPane\s*\{/);
 assert.match(focus,/id: solarYear\s*StationCosmosAnnualWheelPane\s*\{/);
});
