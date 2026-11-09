"use strict";
// U7b-G regression: simulate the user's real SENSOR 13 workflow with
// duplicate *display names* across different chips, without requiring that
// a QML singleton favorites snapshot is synchronized at click time.
const test=require("node:test"),assert=require("node:assert/strict"),
  fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(file,env){
  vm.runInNewContext(read(file).replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:file});
}
const Resource={},AppFavoriteSelection={Resource},SystemFavoriteSelection={Resource},
  ThermalFavoriteSelection={Resource};
policy("services/favorites/FavoritesResourcePolicy.js",Resource);
policy("services/favorites/FavoritesAppSelectionPolicy.js",AppFavoriteSelection);
policy("services/favorites/FavoritesSystemSelectionPolicy.js",SystemFavoriteSelection);
policy("services/favorites/FavoritesThermalSelectionPolicy.js",ThermalFavoriteSelection);
const app=read("widgets/AppControlW.qml");
const saved=id=>"thermal|"+encodeURIComponent(id);
const live=(id,kind)=>({
  _thermalRecord:true,id,name:id.split(":").slice(-1)[0],
  label:id.split(":").slice(-1)[0],sensorKind:kind,
  chip:id.split(":")[1],source:"/sys/class/hwmon/test-only"
});
function fixture(){
  const trace=[],deferred=[],controller={
    thermalViewMode:0,thermalViewThermal:0,thermalViewFans:1,
    setThermalViewMode(n){this.thermalViewMode=n;}
  };
  const scope={
    appControlWindow:null,menuOpen:false,selectedModeIndex:1,
    appsModeIndex:1,thermalModeIndex:6,systemModeIndex:8,
    pendingFavoriteSelection:null,favoriteNavigationNotice:"",
    favoriteStore:{favoriteKeys:[]},systemRows:[],thermalRows:[],fanRows:[],
    selectedResultIndex:0,hoveredResultIndex:-1,detailFocused:false,
    appSourceNative:0,appSourceMode:0,rememberedAppKey:"",
    DesktopEntries:{applications:{values:[]}},filteredApps:{values:[]},
    thermalResults:{values:[]},systemResults:{values:[]},
    thermalController:controller,searchInput:{text:""},
    AppFavoriteSelection,SystemFavoriteSelection,ThermalFavoriteSelection,
    ListView:{Contain:"Contain"},
    Qt:{callLater(fn){deferred.push(fn);}},
    resultList:{positionViewAtIndex(n,how){trace.push("scroll:"+n+":"+how);}},
    switchMode(mode){scope.selectedModeIndex=mode;trace.push("mode:"+mode);},
    resetDetailActionSelection(){},
  };
  scope.appControlWindow=scope;
  const a=app.indexOf("    function clearFavoriteNavigation() {");
  const b=app.indexOf("    function rememberCurrentAppSelection() {",a);
  assert.ok(a>=0&&b>a);
  vm.runInContext(app.slice(a,b),vm.createContext(scope),
    {filename:"widgets/AppControlW.qml/real-owner-methods"});
  return {scope,controller,trace,deferred};
}
test("same SENSOR 13 name on two chips selects exact saved chip, even when FavoritesStore is stale",()=>{
  const a=live("thermal:k10temp:SENSOR 13","temperature");
  const b=live("thermal:nct6798:SENSOR 13","temperature");
  const x=fixture(),s=x.scope;
  // The user has saved the other row, but owner favorite-store may not
  // have published the latest snapshot. Viewing is not an authorization act.
  s.favoriteStore.favoriteKeys=[];
  s.thermalRows=[a,b];s.thermalResults.values=[a,b];
  assert.equal(s.selectSavedThermal(
    ThermalFavoriteSelection.tokenForSavedKey(saved(b.id))),true);
  assert.equal(s.menuOpen,true);
  assert.equal(s.selectedModeIndex,6);
  assert.equal(s.selectedResultIndex,1);
  assert.equal(s.favoriteNavigationNotice,"");
  assert.equal(x.trace[0],"mode:6");
  assert.equal(ThermalFavoriteSelection.tokenForSavedKey(saved(a.id))===
    ThermalFavoriteSelection.tokenForSavedKey(saved(b.id)),false);
  for(let i=0;i<3 && x.deferred.length;i++)x.deferred.shift()();
  assert.ok(x.trace.includes("scroll:1:Contain"));
});
test("select exact live sensor when stored membership has duplicate or stale records",()=>{
  const r=live("thermal:nct6798:SENSOR 13","temperature");
  const t=fixture(),s=t.scope,raw=saved(r.id);
  s.favoriteStore.favoriteKeys=[raw,raw,"thermal|nonexistent"];
  s.thermalRows=[r];s.thermalResults.values=[r];
  assert.equal(ThermalFavoriteSelection.resolve(
    ThermalFavoriteSelection.tokenForSavedKey(raw),[raw,raw],[r],[]).ok,false,
    "old saved-array gate would reject identical live sensor");
  assert.equal(s.selectSavedThermal(
    ThermalFavoriteSelection.tokenForSavedKey(raw)),true);
  assert.equal(s.selectedResultIndex,0);
  assert.equal(s.favoriteNavigationNotice,"");
});
test("view-only routing rejects malformed sensor identities, wrong family and duplicate LIVE IDs",()=>{
  const r=live("thermal:nct6798:SENSOR 13","temperature"),
    token=ThermalFavoriteSelection.tokenForSavedKey(saved(r.id));
  assert.equal(ThermalFavoriteSelection.resolveVisible("","",[]).ok,false);
  assert.equal(ThermalFavoriteSelection.resolveVisible(token,[],[]).ok,false);
  assert.equal(ThermalFavoriteSelection.resolveVisible(token,[r,r],[]).ok,false);
  assert.equal(ThermalFavoriteSelection.resolveVisible(token,[r],[]).ok,true);
  assert.equal(ThermalFavoriteSelection.resolveVisible(token,[],[r]).ok,false);
  const t=fixture(),s=t.scope;
  s.thermalRows=[r,r];s.thermalResults.values=[r,r];
  assert.equal(s.selectSavedThermal(token),true);
  assert.equal(s.selectedModeIndex,6);
  assert.equal(s.selectedResultIndex,-1);
  assert.match(s.favoriteNavigationNotice,/SAVED SENSOR ID AMBIGUOUS/);
  assert.equal(s.pendingFavoriteSelection.kind,"thermal");
  assert.equal(s.tryResumeFavoriteSelection(),false);
});
test("fan route stays selection-only and never calls device control methods",()=>{
  const r=live("fan:nct6798:FAN 1","fan"),
    other=live("thermal:nct6798:SENSOR 13","temperature"),
    token=ThermalFavoriteSelection.tokenForSavedKey(saved(r.id));
  const t=fixture(),s=t.scope;
  s.fanRows=[r];s.thermalRows=[other];s.thermalResults.values=[r];
  s.favoriteStore.favoriteKeys=[];
  assert.equal(s.selectSavedThermal(token),true);
  assert.equal(s.selectedModeIndex,6);
  assert.equal(t.controller.thermalViewMode,t.controller.thermalViewFans);
  assert.equal(s.selectedResultIndex,0);
  const owner=app.slice(app.indexOf("    function clearFavoriteNavigation() {"),
    app.indexOf("    function rememberCurrentAppSelection() {"));
  for(const prohibited of [
    "writeFanPercent(", "writeControl(", "toggleFanControlUnlocked(",
    "setDesiredFanPercent(", "launchApplication(", "killProcess("
  ]) assert.equal(owner.includes(prohibited),false,prohibited);
});
test("pending exact selection resolves when live telemetry appears, not when store changes",()=>{
  const r=live("thermal:nct6798:SENSOR 13","temperature"),t=fixture(),s=t.scope;
  const token=ThermalFavoriteSelection.tokenForSavedKey(saved(r.id));
  assert.equal(s.selectSavedThermal(token),true);
  assert.equal(s.menuOpen,true);
  assert.match(s.favoriteNavigationNotice,/NOT FOUND IN CURRENT READINGS/);
  assert.equal(s.selectedResultIndex,-1);
  s.thermalRows=[r];s.thermalResults.values=[r];
  assert.equal(s.tryResumeFavoriteSelection(),true);
  assert.equal(s.selectedResultIndex,0);
  assert.equal(s.favoriteNavigationNotice,"");
  assert.equal(s.pendingFavoriteSelection,null);
});
test("QML list<string> saved state is array-like, not a JS Array; owner copies it before APP and SYSTEM checks",()=>{
  function qmlList(values){
    const out={length:values.length};
    for(let i=0;i<values.length;i++)out[i]=values[i];
    return out;
  }
  const appId="org.example.Demo.desktop";
  const qmlApps=qmlList([appId]);
  assert.equal(Array.isArray(qmlApps),false);
  assert.equal(AppFavoriteSelection.ownerAllows(
    appId,qmlApps,[{id:appId,name:"Demo"}]),false,
    "unconverted QML list recreates the user's silent owner refusal");
  const a=fixture(),s=a.scope;
  s.favoriteStore.favoriteKeys=qmlApps;
  s.DesktopEntries.applications.values=[{id:appId,name:"Demo"}];
  s.filteredApps.values=[{id:appId,name:"Demo"}];
  assert.equal(s.selectSavedApplication(appId),true);
  assert.equal(s.menuOpen,true);
  assert.equal(s.selectedModeIndex,s.appsModeIndex);
  assert.equal(s.selectedResultIndex,0);
  assert.equal(s.favoriteNavigationNotice,"");

  const source={id:"system:cpu",name:"CPU",_systemRecord:true};
  const qmlSystem=qmlList(["system|system%3Acpu"]);
  assert.equal(SystemFavoriteSelection.ownerAllows("cpu",qmlSystem,[source]),false);
  const t=fixture(),owner=t.scope;
  owner.favoriteStore.favoriteKeys=qmlSystem;
  owner.systemRows=[source];owner.systemResults.values=[source];
  assert.equal(owner.selectSavedSystemMetric("cpu"),true);
  assert.equal(owner.menuOpen,true);
  assert.equal(owner.selectedModeIndex,owner.systemModeIndex);
  assert.equal(owner.selectedResultIndex,0);
  assert.equal(owner.favoriteNavigationNotice,"");
  assert.equal(Array.isArray(owner.originalFavoriteKeysForSelection()),true);

  // Existing duplicate-favorite safety is not erased by the conversion.
  const d=fixture(),duplicate=d.scope;
  duplicate.favoriteStore.favoriteKeys=qmlList(["system|system%3Acpu","system|system%3Acpu"]);
  duplicate.systemRows=[source];duplicate.systemResults.values=[source];
  assert.equal(duplicate.selectSavedSystemMetric("cpu"),true);
  assert.equal(duplicate.selectedResultIndex,-1);
  assert.match(duplicate.favoriteNavigationNotice,/SYSTEM IS OPEN/);
});
test("source wiring uses live owner resolver for all thermal paths and retains other favorites policies",()=>{
  const p=read("services/favorites/FavoritesThermalSelectionPolicy.js");
  assert.match(p,/function resolveVisible\(token,thermalRows,fanRows\)/);
  const start=app.indexOf("    function tryResumeFavoriteSelection() {");
  const end=app.indexOf("    function rememberCurrentAppSelection() {",start);
  const owner=app.slice(start,end);
  assert.match(owner,/ThermalFavoriteSelection\.resolveVisible\(/);
  assert.equal(owner.includes("ThermalFavoriteSelection.resolve("),false);
  assert.match(app,/function selectSavedApplication\(desktopId\)/);
  assert.match(app,/function selectSavedSystemMetric\(metric\)/);
  assert.match(app,/favoriteNavigationNoticeBar/);
  const native=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  const runner=read("scripts/favorites/verify_cpuplus_hub_fedora_u4.sh");
  assert.match(native,/property list<string> favoriteKeys:/);
  assert.match(native,/U7G_PASS \/\/ QML_TYPED_LIST_AND_EXACT_LIVE_SENSOR/);
  assert.match(runner,/U7G_PASS \/\/ QML_TYPED_LIST_AND_EXACT_LIVE_SENSOR/);
});
