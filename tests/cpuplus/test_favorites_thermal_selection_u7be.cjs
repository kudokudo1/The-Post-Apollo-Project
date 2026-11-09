"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../.."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
function load(file,env){
  vm.runInNewContext(read(file).replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:file});
}
const Resource={};load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Thermal={Resource};load("services/favorites/FavoritesThermalSelectionPolicy.js",Thermal);
const plain=x=>JSON.parse(JSON.stringify(x));
const save=id=>"thermal|"+encodeURIComponent(id);
const key=id=>Resource.identityKey("appcontrol","item",save(id));
const row=id=>({
  key:key(id),owner:"appcontrol",provider:"appcontrol",kind:"item",
  category:"CPU++",menu:"THERMAL",favoriteType:"FAVORITE",
  resolved:true,readOnly:true,isFavorite:true,available:"unresolved",capabilities:[]
});
const hot="thermal:k10temp:Tctl",fan="fan:nct6775:CPU Fan";
const sensor=id=>({
  _thermalRecord:true,sensorKind:id.startsWith("fan:")?"fan":"temperature",
  id,name:id.split(":").slice(-1)[0],chip:"demo"
});
test("U7b-E provides an opaque short selection token for exact saved telemetry IDs",()=>{
  for(const id of [hot,fan,"thermal:amdgpu:edge","thermal:coretemp:Package id 0",
                   "fan:nct6799:Chassis Fan 1"]){
    const p=Thermal.plan(row(id)),r=Thermal.parseResourceKey(key(id));
    assert.equal(p.ok,true,id);
    assert.match(p.token,/^[tf]-[a-f0-9]{16}$/);
    assert.equal(p.token[0],id.startsWith("fan:")?"f":"t");
    assert.equal(p.token.includes(id),false);
    assert.equal(JSON.stringify(p).includes("thermal|"),false);
    assert.equal(r.sourceId,id);
    assert.equal(r.raw,save(id));
    assert.equal(Thermal.tokenForSavedKey(save(id)),p.token);
    assert.equal(Thermal.validToken(p.token),true);
    assert.deepEqual(plain(row(id)),plain(row(id)));
  }
  assert.notEqual(Thermal.plan(row(hot)).token,Thermal.plan(row(fan)).token);
});
test("rejects wrong family, forged encoding, commands, paths, and monitor/watch actions",()=>{
  const x=row(hot);
  for(const altered of [
    null,[],{}, {...x,owner:"weather"}, {...x,provider:"CPU++"},
    {...x,kind:"monitor-watch"}, {...x,menu:"RUN"},
    {...x,menu:"SYSTEM"}, {...x,category:"APP CTRL"},
    {...x,favoriteType:"METRIC WATCH"}, {...x,resolved:false},
    {...x,readOnly:false},{...x,isFavorite:false},
    {...x,key:key("fan:/sys/devices/pwm:Fan 1")},
    {...x,key:key("thermal:nct6775:./secrets")},
    {...x,key:key("thermal:nct6775:bad\nname")},
    {...x,key:key("thermal:nct6775:$HOME")},
    {...x,key:Resource.identityKey("appcontrol","item","run:kitty:top")},
    {...x,key:Resource.identityKey("appcontrol","item","task|1234")},
    {...x,key:Resource.identityKey("appcontrol","monitor-watch",save(hot))},
    {...x,key:key(hot).replace("thermal%257C","thermal%7C")},
    {...x,key:"fav1:local:appcontrol:item:%E0%A4%A"},
    {...x,key:"fav1:local:appcontrol:item:"}
  ]) {
    const p=Thermal.plan(altered);
    assert.equal(p.ok,false,JSON.stringify(altered));
    assert.equal(p.token,"");
  }
  for(const token of ["","t-1234","f-xyz","t-0123456789abcdef0",
                       "T-0123456789abcdef","t-0123456789abcdeg",null,1]) {
    assert.equal(Thermal.validToken(token),false,String(token));
  }
});
test("source owner revalidates exact saved membership and unique live sensor for both submodes",()=>{
  for(const id of [hot,fan]) {
    const token=Thermal.plan(row(id)).token,raw=save(id);
    const therm=id===hot?[sensor(id)]:[],fans=id===fan?[sensor(id)]:[];
    const valid=Thermal.resolve(token,[raw],therm,fans);
    assert.equal(valid.ok,true,id);
    assert.equal(valid.sourceId,id);
    assert.equal(valid.kind,id.startsWith("fan:")?"fan":"temperature");
    assert.equal(Thermal.resolve(token,[],therm,fans).ok,false);
    assert.equal(Thermal.resolve(token,[raw,raw],therm,fans).ok,false);
    assert.equal(Thermal.resolve(token,[raw],[],[]).ok,false);
    assert.equal(Thermal.resolve(token,[raw,null],therm,fans).ok,true);
    assert.equal(Thermal.resolve(token,[raw],
      id===hot?[sensor(id),sensor(id)]:[],id===fan?[sensor(id),sensor(id)]:[]).ok,false);
    const spoof={...sensor(id),sensorKind:"not-a-sensor"};
    assert.equal(Thermal.resolve(token,[raw],id===hot?[spoof]:[],id===fan?[spoof]:[]).ok,false);
    const missingKind={id,_thermalRecord:true};
    assert.equal(Thermal.resolve(token,[raw],id===hot?[missingKind]:[],
      id===fan?[missingKind]:[]).ok,false);
    assert.equal(Thermal.resolve(token,[raw],null,fans).ok,false);
    assert.equal(Thermal.resolve(token,[raw],therm,null).ok,false);
    assert.equal(Thermal.selectedIndex(token,id,[sensor("thermal:test:other"),sensor(id)],
      valid.kind),1);
    assert.equal(Thermal.selectedIndex(token,id,[sensor(id),sensor(id)],valid.kind),-1);
    assert.equal(Thermal.selectedIndex(token,id,[{id}],valid.kind),-1);
  }
});
test("CPU++ shell and AppControl select a saved sensor, never activate fan control",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml"),
        cpu=read("widgets/CpuPlusW.qml"),
        shell=read("shell.qml"),
        app=read("widgets/AppControlW.qml");
  assert.match(pane,/ThermalSelection\.plan\(pane\.selectedResource\)/);
  assert.match(pane,/signal thermalSelectionRequested\(string token\)/);
  assert.match(pane,/pane\.thermalSelectionRequested\(pane\.thermalSelection\.token\)/);
  assert.match(pane,/pane\.systemSelectionRequested\(pane\.systemSelection\.metric\)/);
  assert.match(cpu,/signal favoriteThermalSelectionRequested\(string token\)/);
  assert.match(cpu,/cpuPlusWindow\.favoriteThermalSelectionRequested\(token\)/);
  const route=shell.split("function openApolloSavedThermal(token) {")[1]
    .split("function openApolloSavedSystemMetric(metric) {")[0];
  assert.ok(route);
  assert.match(route,/ThermalFavoriteSelection\.validToken\(token\)/);
  assert.match(route,/appControlWindow\.selectSavedThermal\(token\)/);
  assert.match(route,/requestControlKeyboard\("appcontrol","favorites-thermal-reading"\)/);
  assert.match(shell,/onFavoriteThermalSelectionRequested: function\(token\)/);
  assert.match(shell,/if\(shellRoot\.openApolloSavedThermal\(token\)\)\s*cpuPlusWindow\.close\(\)/);
  const owner=app.split("function selectSavedThermal(token) {")[1]
    .split("function rememberCurrentAppSelection() {")[0];
  assert.ok(owner);
  assert.match(owner,/ThermalFavoriteSelection\.resolve\(/);
  assert.match(owner,/favoriteStore\.favoriteKeys/);
  assert.match(owner,/thermalRows,fanRows/);
  assert.match(owner,/switchMode\(thermalModeIndex,false\)/);
  assert.match(owner,/thermalController\.setThermalViewMode\(/);
  assert.match(owner,/ThermalFavoriteSelection\.selectedIndex\(/);
  assert.match(owner,/selectedResultIndex=index/);
  assert.match(owner,/positionViewAtIndex\(now,ListView\.Contain\)/);
  for(const source of [route,owner]) {
    const executable=source.replace(/\/\/[^\n]*/g,"");
    assert.doesNotMatch(executable,
      /\b(?:writeControl|writeFanPercent|toggleFanControlUnlocked|setDesiredFanPercent|execDetached|runCommand|killProcess|launchApp)\s*\(/);
  }
  assert.match(app,/function selectSavedSystemMetric\(metric\)/);
  assert.match(app,/function selectSavedApplication\(desktopId\)/);
});
test("native original U7 click tests are retained and temperature + fan clicks are added",()=>{
  const qml=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  const runner=read("scripts/favorites/verify_cpuplus_hub_fedora_u4.sh");
  assert.match(qml,/onThermalSelectionRequested: function\(token\)/);
  assert.match(qml,/U7E_TEMP_READY/);
  assert.match(qml,/U7E_FAN_READY/);
  assert.match(qml,/U7E_PASS \/\/ EXACT_THERMAL_AND_FAN_SELECTION_NO_ACTIONS/);
  assert.match(runner,/U7A_PASS/);
  assert.match(runner,/U7B_PASS/);
  assert.match(runner,/U7C_PASS/);
  assert.match(runner,/U7D_PASS/);
  assert.match(runner,/U7E_PASS \/\/ EXACT_THERMAL_AND_FAN_SELECTION_NO_ACTIONS/);
});
