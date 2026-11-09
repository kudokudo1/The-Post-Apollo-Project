"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function load(p,env) {
  vm.runInNewContext(read(p).replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:p});
}
const Resource={}; load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Select={Resource};load("services/favorites/FavoritesAppSelectionPolicy.js",Select);
const key=id=>Resource.identityKey("appcontrol","item",id);
const good=id=>({
    key:key(id),owner:"appcontrol",provider:"appcontrol",
    kind:"item",category:"APP CTRL",menu:"APPS",favoriteType:"FAVORITE",
    readOnly:true,resolved:true,isFavorite:true,available:"unresolved",
    capabilities:[]
});
const plain=x=>JSON.parse(JSON.stringify(x));

test("U7b-C emits only the installed-application identity from supported saved APPS rows",()=>{
  for (const id of ["org.example.Editor.desktop","kitty","com.brave.Browser","org.gnome.Terminal-1","App_2"]) {
    const row=good(id),before=plain(row);
    assert.deepEqual(plain(Select.plan(row)),{ok:true,desktopId:id,reason:""});
    assert.deepEqual(plain(row),before);
    assert.equal(JSON.stringify(Select.plan(row)).includes("fav1:"),false);
    assert.equal(JSON.stringify(Select.plan(row)).includes("resourceId"),false);
  }
});
test("U7b-C never promotes RUN, hidden CLI, file, PID or preferred-action keys",()=>{
  const base=good("org.example.Editor.desktop");
  const invalid=[
    null,[],{}, {...base,readOnly:false}, {...base,resolved:false},
    {...base,isFavorite:false}, {...base,owner:"weather-home"},
    {...base,provider:"radio"}, {...base,kind:"preferred-action"},
    {...base,category:"CPU++"}, {...base,menu:"RUN"},
    {...base,favoriteType:"PREFERRED ACTION"},
    {...base,key:key("hidden:btop")},{...base,key:key("run:firefox")},
    {...base,key:key("mode:4:Window")},
    {...base,key:key("task|1234")},{...base,key:key("file:///tmp/secrets")},
    {...base,key:key("bash -c rm -rf /")},
    {...base,key:key("org.example.Editor.desktop\n")},
    {...base,key:"fav1:local:appcontrol:item:%6f%72%67.example.Editor.desktop"},
    {...base,key:"fav1:local:appcontrol:item:%E0%A4%A"},
    {...base,key:key("A".repeat(129))},
    {...base,key:"org.example.Editor.desktop"}
  ];
  for(const row of invalid){
    const out=Select.plan(row);
    assert.equal(out.ok,false,JSON.stringify(row));
    assert.equal(out.desktopId,"");
  }
  for(const id of [""," bad","org.example/File","org.example:run",
                   "org.example;echo","org.example$(id)","org.example%2F",
                   "app name","http://url","app\\name"]) {
    assert.equal(Select.validDesktopId(id),false,id);
  }
});
test("original AppControl owner must confirm exactly one saved and installed application",()=>{
  const id="org.example.Editor.desktop";
  const installed=[{id,name:"Editor",command:["not-invoked"]}];
  assert.equal(Select.ownerAllows(id,[id],installed),true);
  assert.equal(Select.ownerAllows(id,[],installed),false);
  assert.equal(Select.ownerAllows(id,[id,id],installed),false);
  assert.equal(Select.ownerAllows(id,[id],[{id:"another.desktop"}]),false);
  assert.equal(Select.ownerAllows(id,[id],[{id,name:"Editor",_hiddenCommand:true}]),false);
  assert.equal(Select.ownerAllows(id,[id],[...installed,...installed]),false);
  assert.equal(Select.ownerAllows(id,[id],[{name:id}]),false);
  assert.equal(Select.ownerAllows(id,[id],null),false);
  assert.equal(Select.ownerAllows("run:echo",[id],installed),false);
  assert.equal(Select.selectedIndex(id,[{id:"other"},{id}]),1);
  assert.equal(Select.selectedIndex(id,[{id},{id}]),-1);
  assert.equal(Select.selectedIndex(id,[{name:id}]),-1);
  assert.equal(Select.selectedIndex(id,[{id,_hiddenCommand:true}]),-1);
});
test("CPU++ OPEN ITEM is bounded to Weather HOME or read-only AppControl APPS selection",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(pane,/import ".+FavoritesAppSelectionPolicy.js" as AppSelection/);
  assert.match(pane,/AppSelection\.plan\(pane\.selectedResource\)/);
  assert.match(pane,/signal appSelectionRequested\(string desktopId\)/);
  assert.match(pane,/pane\.appSelectionRequested\(pane\.appSelection\.desktopId\)/);
  assert.match(pane,/pane\.exactNavigation\.ok \|\| pane\.appSelection\.ok/);
  assert.match(cpu,/signal favoriteAppSelectionRequested\(string desktopId\)/);
  assert.match(cpu,/onAppSelectionRequested: function\(desktopId\)/);
  assert.match(cpu,/cpuPlusWindow\.favoriteAppSelectionRequested\(desktopId\)/);
});
test("shell validates the scoped app ID and closes CPU++ only if AppControl accepts selection",()=>{
  const shell=read("shell.qml");
  const section=shell.split("function openApolloSavedApp(desktopId) {")[1]
    .split("function openApolloFavoriteItem(owner,route) {")[0];
  assert.ok(section);
  assert.match(section,/AppFavoriteSelection\.validDesktopId\(desktopId\)/);
  assert.match(section,/appControlWindow\.selectSavedApplication\(desktopId\)/);
  assert.match(section,/requestControlKeyboard\("appcontrol","favorites-saved-app"\)/);
  const executable=section.replace(/\/\/[^\n]*/g,"");
  assert.doesNotMatch(executable,/\b(?:execDetached|runCommand|launchApp|killProcess|playStation|openUrlExternally)\s*\(/);
  assert.match(shell,/onFavoriteAppSelectionRequested: function\(desktopId\)/);
  assert.match(shell,/if\(shellRoot\.openApolloSavedApp\(desktopId\)\)\s*cpuPlusWindow\.close\(\)/);
});
test("AppControl rechecks membership, matches installed desktop ID, selects row, never executes",()=>{
  const app=read("widgets/AppControlW.qml");
  const seg=app.split("function selectSavedApplication(desktopId) {")[1]
    .split("function rememberCurrentAppSelection() {")[0];
  assert.ok(seg);
  assert.match(seg,/AppFavoriteSelection\.ownerAllows\(/);
  assert.match(seg,/DesktopEntries\.applications\.values/);
  assert.match(seg,/appSourceMode=appSourceNative/);
  assert.match(seg,/switchMode\(appsModeIndex,false\)/);
  assert.match(seg,/searchInput\.text=""/);
  assert.match(seg,/AppFavoriteSelection\.selectedIndex\(/);
  assert.match(seg,/selectedResultIndex=index/);
  assert.match(seg,/positionViewAtIndex\(now,ListView\.Contain\)/);
  assert.match(seg,/return true/);
  assert.doesNotMatch(seg,/execDetached|Process\s*\{|launchApp|launchCommand|activateResult|killProcess|toggleFavorite|setFavorite\(/);
});
test("existing Weather exact-item path and original AppControl OPEN OWNER remain available",()=>{
  const shell=read("shell.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  assert.match(shell,/function openApolloFavoriteItem\(owner,route\)/);
  assert.match(shell,/function openApolloFavoriteOwner\(owner,view\)/);
  assert.match(pane,/pane\.ownerNavigationRequested\(target\.owner,target\.view\)/);
  assert.match(pane,/pane\.exactNavigationRequested\(target\.owner,target\.route\)/);
  assert.match(pane,/label: pane\.selectedResource && pane\.selectedResource\.readOnly[\s\S]*?"OPEN ITEM"/);
});

test("native fixture covers real mouse click while keeping all original tests",()=>{
  const fixture=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  const runner=read("scripts/favorites/verify_cpuplus_hub_fedora_u4.sh");
  assert.match(fixture,/onAppSelectionRequested: function\(desktopId\)/);
  assert.match(fixture,/desktopId!=="org\.example\.Demo\.desktop"/);
  assert.match(fixture,/detail\.appSelection\.desktopId/);
  assert.match(fixture,/U7C_PASS \/\/ EXACT_DESKTOP_ENTRY_SELECTION_NO_EXECUTION/);
  assert.match(runner,/U7A_PASS/);
  assert.match(runner,/U7B_PASS/);
  assert.match(runner,/U7C_ITEM_READY/);
  assert.match(runner,/U7C_PASS \/\/ EXACT_DESKTOP_ENTRY_SELECTION_NO_EXECUTION/);
  assert.match(runner,/xdotool mousemove --window "\$window" "\$ax" "\$ay" click 1/);
});
