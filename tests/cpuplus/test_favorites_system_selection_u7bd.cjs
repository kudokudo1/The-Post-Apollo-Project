"use strict";
const test=require("node:test"), assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../.."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
function load(p,env) {
  vm.runInNewContext(read(p).replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:p});
}
const Resource={};
load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Policy={Resource};
load("services/favorites/FavoritesSystemSelectionPolicy.js",Policy);
const plain=x=>JSON.parse(JSON.stringify(x));
const row=metric=>({
  key:Resource.identityKey("appcontrol","item",Policy.savedKey(metric)),
  owner:"appcontrol",provider:"appcontrol",kind:"item",category:"CPU++",
  menu:"SYSTEM",favoriteType:"FAVORITE",readOnly:true,isFavorite:true,
  resolved:true,capabilities:[],available:"unresolved"
});
const live=metric=>({_systemRecord:true,id:Policy.sourceId(metric),name:metric.toUpperCase()});

test("U7b-D admits exactly four fixed SYSTEM metrics without raw favorite keys",()=>{
  assert.deepEqual(plain(Policy.CORE),["cpu","memory","swap","rootfs"]);
  for(const metric of Policy.CORE) {
    assert.equal(Policy.validMetric(metric),true);
    assert.deepEqual(plain(Policy.plan(row(metric))),
      {ok:true,metric,reason:""});
    assert.equal(JSON.stringify(Policy.plan(row(metric))).includes("fav1:"),false);
    assert.equal(JSON.stringify(Policy.plan(row(metric))).includes("system:"),false);
  }
});
test("U7b-D rejects spoofed sources and all file/command/process/device identities",()=>{
  const base=row("cpu");
  const changes=[
    null,[],{}, {...base,readOnly:false}, {...base,resolved:false},
    {...base,isFavorite:false}, {...base,owner:"thermal"},
    {...base,provider:"CPU++"}, {...base,kind:"monitor-watch"},
    {...base,category:"APP CTRL"}, {...base,menu:"THERMAL"},
    {...base,menu:"KILL"}, {...base,menu:"RUN"},
    {...base,favoriteType:"METRIC WATCH"},
    {...base,key:Resource.identityKey("appcontrol","item","thermal|sensor%3Acore")},
    {...base,key:Resource.identityKey("appcontrol","item","system|system%3Adisk%3Anvme0n1")},
    {...base,key:Resource.identityKey("appcontrol","item","system|system%3Anet%3Aeth0")},
    {...base,key:Resource.identityKey("appcontrol","item","system|system%3Agpu%3Asecret")},
    {...base,key:Resource.identityKey("appcontrol","item","run:reboot")},
    {...base,key:Resource.identityKey("appcontrol","item","task|1")},
    {...base,key:base.key+"%20--do-action"},
    {...base,key:undefined},
    {...base,key:base.key.replace(/%/g,"%25")}
  ];
  for(const item of changes) {
    const p=Policy.plan(item);
    assert.equal(p.ok,false,JSON.stringify(item));
    assert.equal(p.metric,"");
  }
  for(const token of ["system:cpu","disk","network","gpu","thermal","cpu:1","CPU",
                      "cpu;exec",1,null,undefined,""]) {
    assert.equal(Policy.validMetric(token),false,String(token));
  }
});
test("original SYSTEM owner must verify one saved identity and exactly one live row",()=>{
  for(const metric of Policy.CORE) {
    const key=Policy.savedKey(metric);
    assert.equal(Policy.ownerAllows(metric,[key],[live(metric)]),true);
    assert.equal(Policy.ownerAllows(metric,[],[live(metric)]),false);
    assert.equal(Policy.ownerAllows(metric,[key,key],[live(metric)]),false);
    assert.equal(Policy.ownerAllows(metric,[key],[]),false);
    assert.equal(Policy.ownerAllows(metric,[key],[live(metric),live(metric)]),false);
    assert.equal(Policy.ownerAllows(metric,[key],[{id:Policy.sourceId(metric)}]),false);
    assert.equal(Policy.ownerAllows(metric,[key],[{...live(metric),_systemRecord:false}]),false);
    assert.equal(Policy.ownerAllows(metric,[key],[{...live(metric),id:"system:other"}]),false);
    assert.equal(Policy.ownerAllows(metric,[key],null),false);
    assert.equal(Policy.selectedIndex(metric,[live("memory"),live(metric)]),
      metric==="memory"?-1:1);
    assert.equal(Policy.selectedIndex(metric,[live(metric),live(metric)]),-1);
    assert.equal(Policy.selectedIndex(metric,[{id:Policy.sourceId(metric)}]),-1);
  }
});
test("CPU++ forwards fixed metric token to shell, preserves APP and Weather",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const shell=read("shell.qml");
  assert.match(pane,/FavoritesSystemSelectionPolicy\.js" as SystemSelection/);
  assert.match(pane,/SystemSelection\.plan\(pane\.selectedResource\)/);
  assert.match(pane,/pane\.systemSelectionRequested\(pane\.systemSelection\.metric\)/);
  assert.match(pane,/pane\.exactNavigationRequested\(target\.owner,target\.route\)/);
  assert.match(pane,/pane\.appSelectionRequested\(pane\.appSelection\.desktopId\)/);
  assert.match(cpu,/signal favoriteSystemSelectionRequested\(string metric\)/);
  assert.match(cpu,/onSystemSelectionRequested: function\(metric\)/);
  assert.match(cpu,/cpuPlusWindow\.favoriteSystemSelectionRequested\(metric\)/);
  const section=shell.split("function openApolloSavedSystemMetric(metric) {")[1]
    .split("function openApolloSavedApp(desktopId) {")[0];
  assert.ok(section);
  assert.match(section,/SystemFavoriteSelection\.validMetric\(metric\)/);
  assert.match(section,/appControlWindow\.selectSavedSystemMetric\(metric\)/);
  assert.match(section,/requestControlKeyboard\("appcontrol","favorites-system-metric"\)/);
  assert.doesNotMatch(section.replace(/\/\/[^\n]*/g,""),
    /\b(?:execDetached|launchApp|runCommand|killProcess|reboot|openUrlExternally)\s*\(/);
  assert.match(shell,/onFavoriteSystemSelectionRequested: function\(metric\)/);
  assert.match(shell,/if\(shellRoot\.openApolloSavedSystemMetric\(metric\)\)\s*cpuPlusWindow\.close\(\)/);
});
test("AppControl uses its existing one-writer favorites and live system monitor without actions",()=>{
  const app=read("widgets/AppControlW.qml");
  const method=app.split("function selectSavedSystemMetric(metric) {")[1]
    .split("function rememberCurrentAppSelection() {")[0];
  assert.ok(method);
  assert.match(method,/SystemFavoriteSelection\.ownerAllows\(/);
  // U7b-G copies QML's list<string> to a JS Array at the owner boundary.
  // Assert both that the resolver uses that copy and the helper still reads
  // the actual FavoritesStore, rather than preserving the obsolete direct gate.
  assert.match(method,/originalFavoriteKeysForSelection\(\)/);
  const helper=app.split("function originalFavoriteKeysForSelection() {")[1]
    .split("function tryResumeFavoriteSelection() {")[0];
  assert.ok(helper);
  assert.match(helper,/favoriteStore\.favoriteKeys/);
  assert.match(helper,/keys\.push\(source\[i\]\)/);
  assert.match(method,/systemRows/);
  assert.match(method,/switchMode\(systemModeIndex,false\)/);
  assert.match(method,/searchInput\.text=""/);
  assert.match(method,/SystemFavoriteSelection\.selectedIndex\(/);
  assert.match(method,/selectedResultIndex=index/);
  assert.match(method,/positionViewAtIndex\(now,ListView\.Contain\)/);
  assert.doesNotMatch(method,/\b(?:execDetached|launch|runCommand|kill|reboot|controlAction|toggleFavorite)\s*\(/);
});
test("native test must click the fixed metric after Weather and AppControl APP selections",()=>{
  const qml=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  const runner=read("scripts/favorites/verify_cpuplus_hub_fedora_u4.sh");
  assert.match(qml,/onSystemSelectionRequested: function\(metric\)/);
  assert.match(qml,/metric!=="cpu"/);
  assert.match(qml,/U7D_PASS \/\/ EXACT_SYSTEM_CORE_SELECTION_NO_ACTIONS/);
  assert.match(runner,/U7C_PASS/);
  assert.match(runner,/U7D_ITEM_READY/);
  assert.match(runner,/U7D_PASS \/\/ EXACT_SYSTEM_CORE_SELECTION_NO_ACTIONS/);
});
