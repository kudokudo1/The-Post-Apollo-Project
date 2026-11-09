"use strict";
// U7b-F: execute the real AppControl owner JavaScript navigation functions
// with synthetic model data. The earlier native Favorites fixture only
// verified CPU++ emitted its signal; this tests the owner opening logic too.
const test=require("node:test"), assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function loadPolicy(file,env) {
  vm.runInNewContext(read(file).replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:file});
}
const Resource={};loadPolicy("services/favorites/FavoritesResourcePolicy.js",Resource);
const AppFavoriteSelection={Resource},SystemFavoriteSelection={Resource},ThermalFavoriteSelection={Resource};
loadPolicy("services/favorites/FavoritesAppSelectionPolicy.js",AppFavoriteSelection);
loadPolicy("services/favorites/FavoritesSystemSelectionPolicy.js",SystemFavoriteSelection);
loadPolicy("services/favorites/FavoritesThermalSelectionPolicy.js",ThermalFavoriteSelection);
const app=read("widgets/AppControlW.qml");
const shell=read("shell.qml");

function ownerFixture() {
  const trace=[],callbacks=[],controller={
    thermalViewMode:0,thermalViewThermal:0,thermalViewFans:1,
    setThermalViewMode(mode){this.thermalViewMode=mode;trace.push("thermal-submode:"+mode);}
  };
  const scope={
    appControlWindow:null,menuOpen:false,selectedModeIndex:0,
    appsModeIndex:1,systemModeIndex:8,thermalModeIndex:6,
    appSourceNative:0,appSourceMode:-1,rememberedAppKey:"",
    selectedResultIndex:5,hoveredResultIndex:3,detailFocused:true,
    favoriteNavigationNotice:"",pendingFavoriteSelection:null,
    favoriteStore:{favoriteKeys:[]},systemRows:[],thermalRows:[],fanRows:[],
    DesktopEntries:{applications:{values:[]}},
    filteredApps:{values:[]},systemResults:{values:[]},thermalResults:{values:[]},
    searchInput:{text:"old search"},
    thermalController:controller,
    AppFavoriteSelection,SystemFavoriteSelection,ThermalFavoriteSelection,
    ListView:{Contain:"Contain"},
    Qt:{callLater(fn){callbacks.push(fn);}},
    resultList:{positionViewAtIndex(index,method){trace.push("position:"+index+":"+method);}},
    trace,
    switchMode(index,preserve){trace.push("open-mode:"+index);this.selectedModeIndex=index;},
    resetDetailActionSelection(){trace.push("reset-detail");}
  };
  scope.appControlWindow=scope;
  const context=vm.createContext(scope);
  const start=app.indexOf("    function clearFavoriteNavigation() {");
  const end=app.indexOf("    function rememberCurrentAppSelection() {",start);
  assert.ok(start>0 && end>start,"Owner navigation function segment exists");
  vm.runInContext(app.slice(start,end),context,{filename:"widgets/AppControlW.qml/U7b-F"});
  return {scope,trace,callbacks,controller};
}
function flushLater(fixture) {
  for(let i=0;i<20 && fixture.callbacks.length;i++)
    fixture.callbacks.shift()();
}
test("APP opening happens before installed/saved checks; stale item is explained INSIDE APPS",()=>{
  const t=ownerFixture(),s=t.scope;
  assert.equal(s.selectSavedApplication("org.example.Demo.desktop"),true);
  assert.equal(s.menuOpen,true);
  assert.equal(s.selectedModeIndex,s.appsModeIndex);
  assert.equal(s.appSourceMode,s.appSourceNative);
  assert.equal(s.searchInput.text,"");
  assert.equal(s.selectedResultIndex,-1);
  assert.match(s.favoriteNavigationNotice,/APPS IS OPEN/);
  assert.equal(s.pendingFavoriteSelection.kind,"app");
  assert.deepEqual(t.trace.slice(0,1),["open-mode:1"]);
  // Install and save it after navigation, then simulate model publication.
  s.favoriteStore.favoriteKeys=["org.example.Demo.desktop"];
  s.DesktopEntries.applications.values=[{id:"org.example.Demo.desktop",name:"Demo"}];
  s.filteredApps.values=[{id:"org.example.Other.desktop"},{id:"org.example.Demo.desktop"}];
  assert.equal(s.tryResumeFavoriteSelection(),true);
  assert.equal(s.selectedResultIndex,1);
  assert.equal(s.favoriteNavigationNotice,"");
  assert.equal(s.pendingFavoriteSelection,null);
  flushLater(t);
  assert.ok(t.trace.includes("position:1:Contain"));
});
test("SYSTEM opens immediately with no telemetry, selects only when saved core reading appears",()=>{
  const t=ownerFixture(),s=t.scope;
  assert.equal(s.selectSavedSystemMetric("cpu"),true);
  assert.equal(s.menuOpen,true);
  assert.equal(s.selectedModeIndex,s.systemModeIndex);
  assert.match(s.favoriteNavigationNotice,/SYSTEM IS OPEN/);
  assert.equal(s.selectedResultIndex,-1);
  assert.equal(s.tryResumeFavoriteSelection(),false);
  const metric={id:"system:cpu",name:"CPU",_systemRecord:true};
  s.favoriteStore.favoriteKeys=["system|system%3Acpu"];
  s.systemRows=[metric];
  s.systemResults.values=[metric];
  assert.equal(s.tryResumeFavoriteSelection(),true);
  assert.equal(s.selectedResultIndex,0);
  assert.equal(s.favoriteNavigationNotice,"");
  flushLater(t);
  assert.ok(t.trace.includes("position:0:Contain"));
});
test("THERMAL/FANS opens before sensor data, never calls PWM or control methods",()=>{
  for(const sourceId of ["thermal:k10temp:Tctl","fan:nct6775:CPU Fan"]) {
    const t=ownerFixture(),s=t.scope;
    const raw="thermal|"+encodeURIComponent(sourceId);
    const token=ThermalFavoriteSelection.tokenForSavedKey(raw);
    assert.equal(s.selectSavedThermal(token),true);
    assert.equal(s.menuOpen,true);
    assert.equal(s.selectedModeIndex,s.thermalModeIndex);
    assert.equal(t.controller.thermalViewMode,sourceId.startsWith("fan:")?1:0);
    assert.match(s.favoriteNavigationNotice,/THERMAL IS OPEN/);
    assert.equal(s.selectedResultIndex,-1);
    const row={
      id:sourceId,sensorKind:sourceId.startsWith("fan:")?"fan":"temperature",
      _thermalRecord:true,name:"live"
    };
    s.favoriteStore.favoriteKeys=[raw];
    if(row.sensorKind==="fan") s.fanRows=[row];
    else s.thermalRows=[row];
    s.thermalResults.values=[row];
    assert.equal(s.tryResumeFavoriteSelection(),true);
    assert.equal(s.selectedResultIndex,0);
    assert.equal(s.favoriteNavigationNotice,"");
    flushLater(t);
    assert.ok(t.trace.includes("position:0:Contain"));
  }
});
test("invalid route tokens are rejected before opening, and stale duplicates never select another row",()=>{
  let t=ownerFixture(),s=t.scope;
  assert.equal(s.selectSavedApplication("rm -rf /"),false);
  assert.equal(s.selectSavedSystemMetric("network-control"),false);
  assert.equal(s.selectSavedThermal("fan:raw/path"),false);
  assert.equal(s.menuOpen,false);
  assert.equal(t.trace.length,0);
  t=ownerFixture();s=t.scope;
  assert.equal(s.selectSavedSystemMetric("cpu"),true);
  s.favoriteStore.favoriteKeys=["system|system%3Acpu","system|system%3Acpu"];
  s.systemRows=[{id:"system:cpu",_systemRecord:true}];
  s.systemResults.values=s.systemRows.slice();
  assert.equal(s.tryResumeFavoriteSelection(),false);
  assert.equal(s.selectedResultIndex,-1);
  assert.match(s.favoriteNavigationNotice,/SYSTEM IS OPEN/);
});
test("shell closes CPU++ for successful local navigation, not for unsupported routes",()=>{
  for(const [handler,owner] of [
    ["openApolloSavedApp","selectSavedApplication"],
    ["openApolloSavedSystemMetric","selectSavedSystemMetric"],
    ["openApolloSavedThermal","selectSavedThermal"]
  ]) {
    const start=shell.indexOf("function "+handler+"(");
    assert.ok(start>=0);
    const body=shell.slice(start,start+540);
    assert.match(body,new RegExp("appControlWindow\\."+owner+"\\("));
    assert.match(body,/requestControlKeyboard\("appcontrol"/);
    assert.match(body,/return true;/);
  }
  assert.match(shell,/if\(shellRoot\.openApolloSavedApp\(desktopId\)\)\s*cpuPlusWindow\.close\(\)/);
  assert.match(shell,/if\(shellRoot\.openApolloSavedSystemMetric\(metric\)\)\s*cpuPlusWindow\.close\(\)/);
  assert.match(shell,/if\(shellRoot\.openApolloSavedThermal\(token\)\)\s*cpuPlusWindow\.close\(\)/);
});
test("UI notice is visible, nonblocking; telemetry refresh retries rather than selecting arbitrary row 0",()=>{
  assert.match(app,/property string favoriteNavigationNotice: ""/);
  assert.match(app,/visible: appControlWindow\.menuOpen\s*&& appControlWindow\.favoriteNavigationNotice\.length>0/);
  assert.match(app,/SAVED SENSOR NOT FOUND IN CURRENT READINGS \/\/ THERMAL IS OPEN/);
  const refreshed=app.slice(app.indexOf("target: appControlWindow.systemTelemetry"),
    app.indexOf("// This controller is intentionally per-view"));
  assert.match(refreshed,/pendingFavoriteSelection/);
  assert.match(refreshed,/tryResumeFavoriteSelection\(\)/);
  assert.match(refreshed,/return;\s*const count/);
  assert.match(app,/if\(!menuOpen\) clearFavoriteNavigation\(\)/);
  assert.match(app,/selectedModeIndex!==pendingFavoriteSelection\.mode/);
  const start=app.indexOf("function clearFavoriteNavigation() {");
  const end=app.indexOf("function rememberCurrentAppSelection() {",start);
  const methods=app.slice(start,end).replace(/\/\/[^\n]*/g,"");
  assert.doesNotMatch(methods,
    /\b(?:launchApplication|execDetached|runCommand|killProcess|writeFanPercent|writeControl|toggleFanControlUnlocked)\s*\(/);
});
