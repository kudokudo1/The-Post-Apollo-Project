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
const Resource={};load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Default={Resource};load("services/favorites/FavoritesDefaultPolicy.js",Default);
const Collections={Resource,Default};
load("services/favorites/FavoritesCollectionsPolicy.js",Collections);
const Adapters={Policy:Resource};
load("services/favorites/FavoritesReadOnlyAdapters.js",Adapters);
const Hub={Resource,Default,Collections,Adapters};
load("services/favorites/FavoritesManagementPolicy.js",Hub);
const plain=v=>JSON.parse(JSON.stringify(v));
const k=(provider,kind,id)=>Resource.identityKey(provider,kind,id);

test("safe current owner entries appear together, with no duplicate writes",()=>{
  const fav=k("finance","instrument","NASDAQ:FOO");
  const out=Hub.list(["UTC","America/New_York"],
    [{id:1,place:{label:"Saved Location"}}],[fav],[fav]);
  assert.equal(out.total,4);
  assert.equal(out.rows.length,4);
  assert.deepEqual(plain(out.rows.map(x=>x.category)),
    ["CLOCK","CLOCK","PLACES","NEW"]);
  assert.equal(out.rows[3].isFavorite,true);
  assert.equal(out.rows[3].isPinned,true);
  assert.equal(out.rows[3].label,"FINANCE // INSTRUMENT");
  assert.equal(out.rows[3].available,"unresolved");
  assert.equal(JSON.stringify(out.rows).includes("latitude"),false);
});

test("bad owners, unsafe identities and corrupted rows never become manager actions",()=>{
  const unsafe=k("appcontrol","item","run|delete-private-home");
  const rawUrl=k("finance","instrument","https://private.example/token");
  const rows=Hub.list(["UTC","Bad Zone",null],
    [{id:-1,place:{label:"bad"}},{id:4,place:{label:"Private Saved Place"}}],
    [unsafe,rawUrl,k("finance","instrument","A")],[]);
  assert.equal(rows.total,3);
  assert.ok(rows.rejected>=4);
  const display=JSON.stringify(rows.rows);
  assert.equal(display.includes("delete-private-home"),false);
  assert.equal(display.includes("https://private.example"),false);
  assert.equal(rows.rows.find(x=>x.category==="NEW").label,"FINANCE // INSTRUMENT");
});

test("the center selector filters without mutating the underlying list",()=>{
  const all=Hub.list(["UTC"],[{id:12,place:{label:"Home"}}],
     [k("finance","instrument","A")],[]);
  const old=plain(all);
  assert.equal(Hub.filterRows(all,"CLOCK").length,1);
  assert.equal(Hub.filterRows(all,"PLACES").length,1);
  assert.equal(Hub.filterRows(all,"NEW").length,1);
  assert.equal(Hub.filterRows(all,"ALL").length,3);
  assert.equal(Hub.filterRows(all,"INVALID").length,3);
  assert.equal(Hub.recordFor(all,k("places","saved-place","12")).provider,"places");
  assert.equal(Hub.recordFor(all,"stale").key,all.rows[0].key);
  assert.deepEqual(plain(all),old);
});

test("new-provider pinned-only identities are selectable and managed separately",()=>{
  const key=k("finance","card","NEWS.01");
  const rec=Hub.list([],[],[],[key]);
  assert.equal(rec.total,1);
  assert.equal(rec.rows[0].isFavorite,false);
  assert.equal(rec.rows[0].isPinned,true);
  assert.equal(rec.rows[0].key,key);
  assert.equal(rec.rows[0].available,"unresolved");
});

test("the real CPU++ mode order is exactly the requested suffix",()=>{
  const src=read("widgets/CpuPlusW.qml");
  const segment=src.split("readonly property var modes: [")[1].split("function open()")[0];
  const names=[...segment.matchAll(/name: "([^"]+)"/g)].map(x=>x[1]);
  assert.deepEqual(names,["OVERVIEW","PROCESS","THERMAL","SYSTEM",
                          "FAVORITES","ID MANAGEMENT","SETTINGS"]);
  assert.match(src,/selectedModeIndex === 4 && favoritesDetailsPane\.editingText/);
  assert.match(src,/selectedModeIndex === 6 && settingsLocationPane\.editingText/);
  assert.match(src,/cpuPlusWindow\.selectMode\(index\)/);
  assert.match(src,/selectedModeIndex === 2 \|\| selectedModeIndex === 3/);
  assert.match(src,/if \(index === 0\)/);
});

test("the existing three CPU++ bays host one manager view each",()=>{
  const src=read("widgets/CpuPlusW.qml");
  const left=src.split("id: sharedInstrumentPane")[1].split("id: targetPane")[0];
  const middle=src.split("id: targetPane")[1].split("id: actuatorPane")[0];
  const right=src.split("id: actuatorPane")[1];
  for(const [part,id,area] of [
    [left,"favoritesOverviewPane","overview"],
    [middle,"favoritesSelectorPane","selector"],
    [right,"favoritesDetailsPane","details"]]) {
    assert.match(part,/CpuPlusFavoritesHubPane \{/);
    assert.ok(part.includes("id: "+id));
    assert.ok(part.includes('area: "'+area+'"'));
    assert.ok(part.includes("visible: cpuPlusWindow.selectedModeIndex === 4"));
  }
  assert.equal((src.match(/CpuPlusFavoritesHubPane \{/g)||[]).length,3);
  for(const owner of ["TimeSettings","PlaceRegistry","FavoritesDefaultStore",
      "FavoritesCollectionsStore"]) {
    assert.ok(src.includes(owner));
  }
});

test("manager actions are always routed to owning stores with no new writer",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  assert.match(pane,/TimeSettings|pane\.timeOwner/);
  assert.match(pane,/pane\.timeOwner\.toggleWorldFavorite\(/);
  assert.match(pane,/pane\.placesOwner\.removeSavedPlace\(/);
  assert.match(pane,/pane\.defaultOwner\.setFavorite\(/);
  assert.match(pane,/pane\.defaultOwner\.togglePinned\(/);
  assert.match(pane,/collectionStore: pane\.collectionsOwner/);
  assert.match(pane,/pane\.removeArmed/);
  assert.match(pane,/FavoritesUnifiedPreview \{/);
  assert.match(pane,/FavoritesCollectionPanel \{/);
  assert.doesNotMatch(pane,/FileView\s*\{|Process\s*\{|execDetached|Qt\.openUrlExternally/);
  assert.doesNotMatch(pane,/AppControlW|FavoritesService\.toggle/);
});

test("no original provider data is copied into a CPU++ runtime writer",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const policy=read("services/favorites/FavoritesManagementPolicy.js");
  for(const item of [cpu,policy]) {
    assert.doesNotMatch(item,/FileView\s*\{|JsonAdapter\s*\{|Process\s*\{/);
  }
  const original=read("services/favorites/FavoritesStore.qml");
  assert.match(original,/appcontrol-favorites\.json/);
  const clock=read("services/time/TimeSettings.qml");
  assert.match(clock,/time-world-favorites-v1\.json/);
  const places=read("services/location/PlaceRegistry.qml");
  assert.match(places,/places-v1\.json/);
  const collection=read("services/favorites/FavoritesCollectionsStore.qml");
  assert.match(collection,/favorites-collections-v1\.json/);
});


test("AppControl favorites now appear in the CPU++ middle selector",()=>{
  const app={
    favoriteKeys:[
      "task|process-secret",
      "thermal|sensor-private",
      "system|cpu-memory-private",
      "app|some-private-application",
      "run|hidden-command",
      "mode:8:PRIVATE_WINDOW"
    ],
    favoriteDetailActionKeys:["app|private|command"],
    favoriteMonitorBoxKeys:[
      "watchbox|thermal|private-sensor|core-temp",
      "watchbox|system|private-sensor|cpu"
    ],
    favoriteTaskMetricKeys:["taskmetric|private-process|cpu"]
  };
  const result=Hub.list(["UTC"],[],[],[],app);
  assert.equal(result.total,11);
  const cpu=Hub.filterRows(result,"CPU++");
  const other=Hub.filterRows(result,"APP CTRL");
  assert.equal(cpu.length,6);
  assert.equal(other.length,4);
  assert.deepEqual(plain(cpu.map(x=>x.label)),[
    "PROCESS FAVORITE #1","THERMAL FAVORITE #1","SYSTEM FAVORITE #1",
    "THERMAL METRIC WATCH #1","SYSTEM METRIC WATCH #1","PROCESS METRIC WATCH #1"
  ]);
  assert.deepEqual(plain(other.map(x=>x.label)),[
    "APP CONTROL FAVORITE #1","APP CONTROL FAVORITE #2",
    "APP CONTROL FAVORITE #3","PREFERRED ACTION #1"
  ]);
  assert.ok(cpu.every(x=>x.owner==="appcontrol" && x.readOnly));
  assert.ok(other.every(x=>x.owner==="appcontrol" && x.readOnly));
  assert.ok(cpu.every(x=>x.available==="unresolved"));
  for (const record of cpu.concat(other)) {
    assert.equal(Object.prototype.hasOwnProperty.call(record,"resourceId"),false);
    assert.deepEqual(plain(record.capabilities),[]);
    for(const text of ["private","hidden-command","PRIVATE_WINDOW"])
      assert.equal(record.label.includes(text),false);
  }
});

test("AppControl membership is source-owned and cannot enter a generic collection or action",()=>{
  const donor={favoriteKeys:["task|critical-process"],favoriteDetailActionKeys:[],
    favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]};
  const items=Hub.list([],[],[],[],donor);
  assert.equal(items.total,1);
  const record=items.rows[0];
  assert.equal(record.category,"CPU++");
  assert.equal(record.readOnly,true);
  assert.equal(record.provider,"appcontrol");
  assert.equal(Collections.checkMemberKey(record.key).ok,false);
  assert.equal(Hub.filterRows(items,"CPU++").length,1);
  assert.equal(Hub.filterRows(items,"APP CTRL").length,0);
});

test("malformed AppControl snapshots are bounded and don't become actions",()=>{
  const bad={
    favoriteKeys:["",null,"task|valid","run|secret\u0001control",
      "a".repeat(2300)],
    favoriteDetailActionKeys:[],
    favoriteMonitorBoxKeys:[],
    favoriteTaskMetricKeys:[]
  };
  const out=Hub.list([],[],[],[],bad);
  assert.equal(out.total,1);
  assert.equal(out.rows[0].label,"PROCESS FAVORITE #1");
  assert.ok(out.rejected>=4);
  const missing=Hub.list([],[],[],[],{favoriteKeys:["task|ok"]});
  assert.equal(missing.total,0);
  assert.ok(missing.rejected>=3);
  assert.equal(
    Hub.list([],[],[],[],{
      favoriteKeys:Array.from({length:530},(_,i)=>"task|pid"+i),
      favoriteDetailActionKeys:[],
      favoriteMonitorBoxKeys:[],
      favoriteTaskMetricKeys:[]
    }).shown,
    Math.min(Hub.MAX_ROWS,Hub.MAX_APP_PER_FAMILY)
  );
});

test("CPU++ imports all AppControl owner lists, with two-row filters and read-only details",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const panel=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  for(const field of [
    "FavoritesStore.favoriteKeys",
    "FavoritesStore.favoriteDetailActionKeys",
    "FavoritesStore.favoriteMonitorBoxKeys",
    "FavoritesStore.favoriteTaskMetricKeys"
  ]) assert.ok(cpu.includes(field),field);
  assert.match(cpu,/FavoritesManagement\.list\(/);
  assert.match(panel,/model: \["ALL","CPU\+\+","APP CTRL","CLOCK","PLACES","NEW"\]/);
  assert.match(panel,/height: 59/);
  assert.match(panel,/modelData\.readOnly\?"READ ONLY"/);
  assert.match(panel,/pane\.selectedResource && !pane\.selectedResource\.readOnly/);
  assert.match(panel,/APP CONTROL-OWNED \/\/ READ ONLY/);
  assert.match(panel,/OWNER CONTROL/);
  assert.doesNotMatch(panel,/pane\.appControlOwner|FavoritesStore\.favoriteKeys\s*=/);
});


test("owner-provided labels are display-only and safely validated",()=>{
  const donor={favoriteKeys:["task|alpha","task|beta","run|private-command"],
    favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
    favoriteTaskMetricKeys:[]};
  const baseline=Hub.list([],[],[],[],donor);
  const [first,second,third]=baseline.rows.map(x=>x.key);
  const labels=Object.create(null);
  labels[first]="Firefox Worker";
  labels[second]="/home/private/secret";
  labels[third]="token://private";
  const withLabels=Hub.list([],[],[],[],donor,labels);
  assert.equal(withLabels.rows[0].label,"Firefox Worker");
  assert.equal(withLabels.rows[1].label,"PROCESS FAVORITE #2");
  assert.equal(withLabels.rows[2].label,"APP CONTROL FAVORITE #1");
  for(const row of withLabels.rows) {
    assert.equal(row.readOnly,true);
    assert.equal(row.owner,"appcontrol");
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
  }
  assert.equal(Hub.list([],[],[],[],donor).rows[0].label,"PROCESS FAVORITE #1");
  assert.ok(withLabels.rows.every(row=>!row.label.includes("private-command")));
});

test("display label ingress remains volatile and owned by AppControl",()=>{
  const store=read("services/favorites/FavoritesStore.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(store,/property var favoriteDisplayLabels: \(\{\}\)/);
  assert.match(cpu,/FavoritesStore\.favoriteDisplayLabels/);
  const persisted=store.split("JsonAdapter {")[1];
  assert.doesNotMatch(persisted,/favoriteDisplayLabels/);
});


test("AppControl original models resolve actual menu, exact item and type",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={
    favoriteKeys:[
      "org.mozilla.firefox.desktop","thermal|sensor-a",
      "system|memory","task|firefox","run:private%20command"
    ],
    favoriteDetailActionKeys:["app|org.mozilla.firefox.desktop|launch"],
    favoriteMonitorBoxKeys:["watchbox|thermal|sensor-a|temp"],
    favoriteTaskMetricKeys:["taskmetric|firefox|cpu"]
  };
  const model={
    apps:[{id:"org.mozilla.firefox.desktop",name:"Firefox",actions:[]}],
    thermalRows:[{id:"sensor-a",name:"CPU Temperature"}],
    fanRows:[],
    systemRows:[{id:"memory",name:"Memory Usage"}],
    taskRows:[{comm:"firefox",name:"Firefox",pid:4321,args:"private arg"}]
  };
  const descriptions=Display.build(saved,model);
  const all=Hub.list([],[],[],[],saved,{},descriptions);
  assert.equal(all.total,8);
  const get=(kind,raw)=>all.rows.find(row=>
      row.key===Resource.identityKey("appcontrol",kind,raw));
  for (const [kind,raw,menu,item,type] of [
    ["item","org.mozilla.firefox.desktop","APPS","Firefox","FAVORITE"],
    ["item","thermal|sensor-a","THERMAL","CPU Temperature","FAVORITE"],
    ["item","system|memory","SYSTEM","Memory Usage","FAVORITE"],
    ["item","task|firefox","KILL","firefox","PROCESS FAVORITE"],
    ["preferred-action","app|org.mozilla.firefox.desktop|launch",
      "APPS","Firefox - Launch","PREFERRED ACTION"],
    ["monitor-watch","watchbox|thermal|sensor-a|temp",
      "THERMAL","CPU Temperature - TEMP","METRIC WATCH"],
    ["task-watch","taskmetric|firefox|cpu",
      "KILL","firefox - CPU","METRIC WATCH"]
  ]) {
    const row=get(kind,raw);
    assert.ok(row,kind+" "+raw);
    assert.equal(row.menu,menu);
    assert.equal(row.item,item);
    assert.equal(row.favoriteType,type);
    assert.equal(row.resolved,true);
    assert.equal(row.label,menu+" // "+item);
    assert.equal(row.readOnly,true);
    assert.deepEqual(plain(row.capabilities),[]);
  }
  const command=get("item","run:private%20command");
  assert.equal(command.resolved,false);
  assert.equal(command.menu,"RUN");
  assert.equal(command.item,"NAME UNAVAILABLE");
  assert.ok(!all.rows.some(row=>row.label.includes("private command")));
  assert.ok(!all.rows.some(row=>row.label.includes("4321")));
  assert.ok(!all.rows.some(row=>row.label.includes("private arg")));
});

test("AppControl owner labels update with source availability without executing",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={favoriteKeys:["org.test.desktop","task|absent-app",
    "thermal|sensor-secret"],favoriteDetailActionKeys:[],
    favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]};
  const empty=Hub.list([],[],[],[],saved,{},Display.build(saved,{}));
  assert.equal(empty.rows[0].resolved,false);
  assert.equal(empty.rows[0].menu,"OTHER");
  const ready=Hub.list([],[],[],[],saved,{},Display.build(saved,{
    apps:[{id:"org.test.desktop",name:"Test Application"}],
    taskRows:[],thermalRows:[],systemRows:[]
  }));
  assert.equal(ready.rows[0].item,"Test Application");
  assert.equal(ready.rows[0].menu,"APPS");
  assert.equal(ready.rows[1].item,"absent-app"); // AppControl's offline comm rule
  assert.equal(ready.rows[2].resolved,false);
  // A label-looking command or private path must never be accepted.
  const bad=Display.build({
    favoriteKeys:["task|private-name"],favoriteDetailActionKeys:[],
    favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]
  },{taskRows:[{comm:"private-name",name:"/home/private/secret"}]});
  assert.equal(Hub.list([],[],[],[],{
    favoriteKeys:["task|private-name"],favoriteDetailActionKeys:[],
    favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]
  },{},bad).rows[0].item,"private-name");
});

test("CPU++ source renders real AppControl metadata without crossing authority",()=>{
  const qml=read("widgets/appcontrol/AppControlFavoriteDisplaySource.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const policy=read("services/favorites/FavoritesAppControlDisplayPolicy.js");
  assert.match(qml,/DesktopEntries\.applications\.values/);
  for(const token of ["appControlOwner.thermalRows","appControlOwner.fanRows",
    "appControlOwner.systemRows","appControlOwner.taskRows"])
    assert.ok(qml.includes(token),token);
  assert.match(cpu,/AppControlFavoriteDisplaySource \{/);
  assert.match(cpu,/cpuAppFavoriteDescriptions\.records/);
  for(const token of ["SOURCE // APP CONTROL","MENU // ","ITEM // ",
    "TYPE // ","STATUS // READ ONLY"])
    assert.ok(pane.includes(token),token);
  assert.match(pane,/modelData\.favoriteType/);
  assert.match(pane,/modelData\.menu/);
  assert.match(pane,/modelData\.item/);
  assert.doesNotMatch(qml+policy,/FileView\s*\{|execDetached|Process\s*\{/);
  assert.doesNotMatch(pane,/AppControlW\.execute|appControlWindow\.kill/);
});
