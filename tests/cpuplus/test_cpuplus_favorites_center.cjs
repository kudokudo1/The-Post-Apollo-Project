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
const WeatherRules={};
load("services/weather/WeatherHomeFavoritesPolicy.js",WeatherRules);
const WeatherHome={WeatherRules,Adapters};
load("services/favorites/FavoritesWeatherHomeProjection.js",WeatherHome);
const Notifications={Adapters};
load("services/favorites/FavoritesNotificationsProjection.js",Notifications);
const Hub={Resource,Default,Collections,Adapters,WeatherHome,NotificationsProjection:Notifications};
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
  assert.match(pane,/Dossier\.build\(pane\.candidates\)/);
  assert.doesNotMatch(pane,/FavoritesUnifiedPreview \{/);
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
    "KILL // SAVED PROCESS #1","THERMAL // SAVED SENSOR #1","SYSTEM // SAVED METRIC #1",
    "THERMAL // METRIC WATCH #1","SYSTEM // METRIC WATCH #1","KILL // METRIC WATCH #1"
  ]);
  assert.deepEqual(plain(other.map(x=>x.label)),[
    "APP CONTROL FAVORITE #1","RUN // SAVED COMMAND #1",
    "SYSTEM // SAVED METRIC #1","APPS // PREFERRED ACTION #1"
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
  assert.equal(out.rows[0].label,"KILL // SAVED PROCESS #1");
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

test("CPU++ imports all AppControl owner lists, with seven source filters and read-only details",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const panel=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  for(const field of [
    "FavoritesStore.favoriteKeys",
    "FavoritesStore.favoriteDetailActionKeys",
    "FavoritesStore.favoriteMonitorBoxKeys",
    "FavoritesStore.favoriteTaskMetricKeys"
  ]) assert.ok(cpu.includes(field),field);
  assert.match(cpu,/FavoritesManagement\.list\(/);
  assert.match(panel,/model: \["ALL","CPU\+\+","APP CTRL","WEATHER","NOTIFS","CLOCK","PLACES","NEW"\]/);
  assert.match(panel,/height: 90/);
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
  assert.equal(withLabels.rows[1].label,"KILL // SAVED PROCESS #2");
  assert.equal(withLabels.rows[2].label,"RUN // SAVED COMMAND #1");
  for(const row of withLabels.rows) {
    assert.equal(row.readOnly,true);
    assert.equal(row.owner,"appcontrol");
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
  }
  assert.equal(Hub.list([],[],[],[],donor).rows[0].label,"KILL // SAVED PROCESS #1");
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
  // Without a live DesktopEntry, the saved APPS ID can still provide its
  // safe program token. A real installed name supersedes that fallback.
  assert.equal(empty.rows[0].resolved,true);
  assert.equal(empty.rows[0].menu,"APPS");
  assert.equal(empty.rows[0].item,"test [SAVED APP ID]");
  assert.equal(empty.rows[0].available,"unresolved");
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

test("CPU++ Favorites entries select from their entire row with // breadcrumb separators",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const fixture=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  for (const required of [
    "id: favoriteRow",
    "MouseArea {",
    "id: rowHit",
    "anchors.fill: parent",
    "onClicked: pane.selectionRequested(modelData.key)",
    "Accessible.role: Accessible.Button",
    "Keys.onPressed:",
    "function favoriteRowLabel(item)",
    'return "APP CTRL // "+menu+" // "+text',
    "text: pane.favoriteRowLabel(modelData)"
  ]) assert.ok(pane.includes(required),required);
  assert.doesNotMatch(pane,/label:\s*"VIEW"/);
  assert.ok(fixture.includes("16,row.height/2"));
  assert.ok(!fixture.includes("row.width-33"));
});


test("RUN, hidden CLI, windows and preferred RUN favorites expose distinguishable safe menu/items",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={
    favoriteKeys:[
      "run:kitty:zellij%20--session%20private-value",
      "run:firefox",
      "run:toolbox:mpv%20--fullscreen",
      "hidden:btop",
      "mode:4:Work Window",
      "mode:1:App Settings",
      "mode:2:%2Fhome%2Fprivate%2Fnotes.txt",
      "run:private%20command",
      "run:%2Fhome%2Fprivate%2Fscript%20--token%20never-show",
      "mode:4:Confidential Document"
    ],
    favoriteDetailActionKeys:["run|run%3Akitty%3Azellij%2520--session%2520private-value|kitty"],
    favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]
  };
  const source=Display.build(saved,{
    apps:[],taskRows:[],thermalRows:[],fanRows:[],systemRows:[],
    swayWindows:[{name:"Work Window"},{name:"Confidential Document"}],
    appTabs:[]
  });
  const hub=Hub.list([],[],[],[],saved,{},source);
  const row=(kind,raw)=>hub.rows.find(x=>
    x.key===Resource.identityKey("appcontrol",kind,raw));
  const expected=[
    ["item","run:kitty:zellij%20--session%20private-value",
        "RUN","zellij [KITTY] [OPTIONS HIDDEN]","FAVORITE"],
    ["item","run:firefox","RUN","firefox","FAVORITE"],
    ["item","run:toolbox:mpv%20--fullscreen",
        "RUN","mpv [TOOLBOX] [OPTIONS HIDDEN]","FAVORITE"],
    ["item","hidden:btop","APPS","btop [CLI]","FAVORITE"],
    ["item","mode:4:Work Window","WINDOWS","Work Window","FAVORITE"],
    ["item","mode:1:App Settings","APPS","App Settings","FAVORITE"],
    ["preferred-action","run|run%3Akitty%3Azellij%2520--session%2520private-value|kitty",
        "RUN","zellij [KITTY] [OPTIONS HIDDEN] - Run in Kitty","PREFERRED ACTION"]
  ];
  for(const [kind,raw,menu,item,type] of expected) {
    const entry=row(kind,raw);
    assert.ok(entry,raw);
    assert.equal(entry.resolved,true,raw);
    assert.equal(entry.menu,menu);
    assert.equal(entry.item,item);
    assert.equal(entry.label,menu+" // "+item);
    assert.equal(entry.favoriteType,type);
    assert.equal(entry.readOnly,true);
    assert.deepEqual(plain(entry.capabilities),[]);
    assert.equal("resourceId" in entry,false);
  }
  const denied=[
    ["mode:2:%2Fhome%2Fprivate%2Fnotes.txt","FILES"],
    ["run:private%20command","RUN"],
    ["run:%2Fhome%2Fprivate%2Fscript%20--token%20never-show","RUN"],
    ["mode:4:Confidential Document","WINDOWS"]
  ];
  for(const [raw,menu] of denied) {
    const entry=row("item",raw);
    assert.equal(entry.resolved,false,raw);
    assert.equal(entry.menu,menu);
    assert.equal(entry.item,"NAME UNAVAILABLE");
    assert.ok(entry.label.startsWith(menu+" // SAVED "));
  }
  const visible=hub.rows.map(x=>x.label).join(" | ");
  for(const secret of ["private-value","never-show","notes.txt",
                       "Confidential Document","%2Fhome"])
    assert.ok(!visible.includes(secret),secret);
});

test("AppControl saved-mode fallbacks provide actual source family without guessing names",()=>{
  const donor={favoriteKeys:[
    "mode:4:private document","mode:5:remote secret",
    "mode:2:private file","mode:7:private process",
    "hidden:secret-token",
    "run:token%3Dabc%20--hidden"
  ],favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
  favoriteTaskMetricKeys:[]};
  const descriptions=Object.create(null);
  const result=Hub.list([],[],[],[],donor,{},descriptions);
  assert.deepEqual(plain(result.rows.map(x=>x.menu)),
      ["WINDOWS","REMOTE","FILES","KILL","APPS","RUN"]);
  for(const entry of result.rows) {
    assert.equal(entry.resolved,false);
    assert.equal(entry.item,"NAME UNAVAILABLE");
    assert.equal(entry.readOnly,true);
    assert.equal(entry.capabilities.length,0);
    assert.ok(!entry.label.includes("private"));
    assert.ok(!entry.label.includes("secret"));
  }
});

test("AppControl display source reads original window and tab models without new authority",()=>{
  const qml=read("widgets/appcontrol/AppControlFavoriteDisplaySource.qml");
  const policy=read("services/favorites/FavoritesAppControlDisplayPolicy.js");
  for(const prop of [
    "appControlOwner.swayWindows","appControlOwner.appTabs",
    "appControlOwner.thermalRows","appControlOwner.systemRows"
  ]) assert.ok(qml.includes(prop),prop);
  for(const term of ["safeRunDisplay","modeIdentity","stableOwnerWindowName",
    "preferredRunAction"]) assert.ok(policy.includes(term),term);
  assert.doesNotMatch(qml+policy,/FileView\s*\{|execDetached|Process\s*\{|Qt\.openUrlExternally/);
  const panel=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  assert.match(panel,/onClicked: pane\.selectionRequested\(modelData\.key\)/);
  assert.match(panel,/pane\.favoriteRowLabel\(modelData\)/);
});


test("saved freedesktop identifiers remain recognizable without installed app models",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={favoriteKeys:[
      "org.example.Galaxy.desktop",
      "com.example.secret-vault.desktop",
      "com.example.SecureApp.desktop",
      "Brave Web Browser", "kitty"
    ],
    favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
    favoriteTaskMetricKeys:[]
  };
  const desc=Display.build(saved,{apps:[]});
  const list=Hub.list([],[],[],[],saved,{},desc);
  assert.equal(list.rows.length,5);
  assert.equal(list.rows[0].menu,"APPS");
  assert.equal(list.rows[0].item,"Galaxy [SAVED APP ID]");
  assert.equal(list.rows[0].label,"APPS // Galaxy [SAVED APP ID]");
  assert.equal(list.rows[0].available,"unresolved");
  assert.equal(list.rows[1].resolved,false);
  assert.equal(list.rows[1].item,"NAME UNAVAILABLE");
  assert.equal(list.rows[1].menu,"APPS");
  assert.equal(list.rows[1].label,"APPS // SAVED APPLICATION #2");
  assert.equal(list.rows[2].item,"SecureApp [SAVED APP ID]");
  assert.equal(list.rows[3].item,"Brave Web Browser [SAVED APP ID]");
  assert.equal(list.rows[4].item,"kitty [SAVED APP ID]");
  for(const row of list.rows) {
    assert.equal(row.readOnly,true);
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
    assert.ok(!row.label.includes("org.example."));
  }
});


test("FILES favorites recover original filenames and file kinds without filesystem access",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={favoriteKeys:[
    "mode:2:◇  quarterly review (2026).pdf",
    "mode:2:⌯🗁๋࣭⭑  Agreements/",
    "mode:2:↗  latest-contract.pdf",
    "mode:2:◇  résumé — signed.pdf",
    "mode:2:◇  inbox@company.eml",
    "mode:2:report-v3.txt",
    "mode:2:◇  #3",
    "mode:2:◇  report.txt",
    "mode:2:⌯🗁๋࣭⭑  report.txt/"
  ],favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
  favoriteTaskMetricKeys:[]};
  const projected=Hub.list([],[],[],[],saved,{},Display.build(saved,{}));
  assert.equal(projected.rows.length,saved.favoriteKeys.length);
  const expected=[
    ["quarterly review (2026).pdf","FILE FAVORITE"],
    ["Agreements","DIRECTORY FAVORITE"],
    ["latest-contract.pdf","SYMLINK FAVORITE"],
    ["résumé — signed.pdf","FILE FAVORITE"],
    ["inbox@company.eml","FILE FAVORITE"],
    ["report-v3.txt","FAVORITE"],
    ["#3","FILE FAVORITE"],
    ["report.txt","FILE FAVORITE"],
    ["report.txt","DIRECTORY FAVORITE"]
  ];
  for(let i=0;i<expected.length;i++){
    const row=projected.rows[i];
    assert.equal(row.provider,"appcontrol");
    assert.equal(row.menu,"FILES");
    assert.equal(row.item,expected[i][0]);
    assert.equal(row.label,"FILES // "+expected[i][0]);
    assert.equal(row.favoriteType,expected[i][1]);
    assert.equal(row.resolved,true);
    assert.equal(row.available,"unresolved");
    assert.equal(row.readOnly,true);
    assert.equal(row.capabilities.length,0);
    assert.equal("resourceId" in row,false);
  }
  assert.notEqual(projected.rows[7].key,projected.rows[8].key);
});

test("file name recovery rejects navigation, paths and encoded path escapes",()=>{
  const Display={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",Display);
  const saved={favoriteKeys:[
    "mode:2:⌯🗁๋࣭⭑  ..",
    "mode:2:◇  ../notes.txt",
    "mode:2:◇  /home/secret/file.txt",
    "mode:2:◇  notes%2Fprivate.txt",
    "mode:2:file:/home/secret.txt",
    "mode:2:◇  report|command.txt",
    "mode:2:◇  report\nhidden.txt",
    "mode:2:◇  "
  ],favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
  favoriteTaskMetricKeys:[]};
  const out=Hub.list([],[],[],[],saved,{},Display.build(saved,{}));
  assert.equal(out.rows.length,6); // control/newline and trailing-whitespace keys rejected by U0
  for(const row of out.rows) {
    assert.equal(row.menu,"FILES");
    assert.equal(row.resolved,false);
    assert.equal(row.item,"NAME UNAVAILABLE");
    assert.ok(row.label.startsWith("FILES // SAVED FILE #"));
    assert.equal(row.readOnly,true);
    assert.equal(row.capabilities.length,0);
  }
  const visible=out.rows.map(x=>x.label).join(" ");
  for(const value of ["notes.txt","secret.txt","file.txt","private.txt",
                      "command.txt","hidden.txt"])
    assert.equal(visible.includes(value),false);
});

test("FILES view labels retain actual names and original owner without executable actions",()=>{
  const source=read("services/favorites/FavoritesAppControlDisplayPolicy.js");
  const manager=read("services/favorites/FavoritesManagementPolicy.js");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const fixture=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  assert.match(source,/function savedFileDescription\(/);
  assert.match(source,/safeSavedFileName/);
  assert.match(source,/DIRECTORY FAVORITE/);
  assert.match(source,/SYMLINK FAVORITE/);
  assert.match(manager,/"FILES".*"RUN"|"RUN".*"FILES"/);
  assert.match(pane,/pane.favoriteRowLabel\(modelData\)/);
  assert.ok(fixture.includes("mode:2:◇  budget-2026.xlsx"));
  assert.ok(fixture.includes("mode:2:⌯🗁๋࣭⭑  Properties/"));
  assert.ok(fixture.includes("mode:2:↗  Active Contract.pdf"));
  assert.doesNotMatch(source+manager,/execDetached|Qt\.openUrlExternally|FileView\s*\{|Process\s*\{/);
});


test("left dossier lists every original saved resource exactly once, grouped by source and menu",()=>{
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const saved={favoriteKeys:[
      "mode:2:◇  budget-2026.xlsx",
      "mode:2:⌯🗁๋࣭⭑  Properties/",
      "mode:2:↗  Active Contract.pdf",
      "run:firefox",
      "task|kitty"
    ],favoriteDetailActionKeys:[],favoriteMonitorBoxKeys:[],
    favoriteTaskMetricKeys:[]};
  const owner={Resource};
  load("services/favorites/FavoritesAppControlDisplayPolicy.js",owner);
  const records=Hub.list(["UTC"],[{id:4,place:{label:"House"}}],
    [k("finance","instrument","EXAMPLE")],[],saved,{},
    owner.build(saved,{taskRows:[{comm:"kitty"}]}));
  const index=Dossier.build(records);
  assert.equal(index.total,records.rows.length);
  assert.equal(index.groups.reduce((n,g)=>n+g.count,0),records.rows.length);
  const file=index.groups.find(g=>g.key==="APP CTRL|FILES");
  assert.equal(file.count,3);
  assert.deepEqual(plain(file.items.map(x=>x.name)),
    ["budget-2026.xlsx","Properties","Active Contract.pdf"]);
  assert.deepEqual(plain(file.items.map(x=>x.type)),
    ["FILE FAVORITE","DIRECTORY FAVORITE","SYMLINK FAVORITE"]);
  assert.ok(index.groups.some(g=>g.key==="CPU++|KILL"));
  assert.ok(index.groups.some(g=>g.key==="CLOCK|CLOCK"));
  assert.ok(index.groups.some(g=>g.key==="PLACES|PLACES"));
  assert.ok(index.groups.some(g=>g.key==="NEW|NEW"));
  const every=index.groups.flatMap(g=>g.items);
  assert.equal(new Set(every.map(x=>x.key)).size,every.length);
  assert.ok(every.every(x=>!Object.prototype.hasOwnProperty.call(x,"resourceId")));
  assert.ok(every.every(x=>!Object.prototype.hasOwnProperty.call(x,"capabilities")));
});

test("dossier selection is a navigation request, never a second provider mutation",()=>{
  const src=read("widgets/CpuPlusW.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const policy=read("services/favorites/FavoritesDossierIndexPolicy.js");
  assert.match(src,/onIndexSelectionRequested: function\(key, category\)/);
  assert.match(src,/favoritesSelectorPane\.filterMode = category;/);
  assert.match(src,/cpuPlusWindow\.selectedFavoriteKey = key;/);
  assert.match(pane,/signal indexSelectionRequested\(string key, string category\)/);
  assert.match(pane,/pane\.indexSelectionRequested\(/);
  assert.match(pane,/function toggleIndexGroup\(key\)/);
  assert.match(pane,/dossierGroup\.section\.count/);
  assert.match(pane,/pane\.revealSelectedInSelector/);
  assert.doesNotMatch(policy,/execDetached|Process\s*\{|FileView\s*\{|JsonAdapter\s*\{|setFavorite\(/);
  assert.doesNotMatch(pane,/FavoritesUnifiedPreview\s*\{/);
});

test("dossier uses only supplied labels and never decodes raw identities",()=>{
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const keys=["opaque-a","opaque-b","opaque-c"];
  const result=Dossier.build({rows:[
    {key:keys[0],category:"APP CTRL",owner:"appcontrol",
     menu:"RUN",label:"RUN // SAVED COMMAND #1",resolved:false,
     favoriteType:"FAVORITE",readOnly:true},
    {key:keys[1],category:"APP CTRL",owner:"appcontrol",
     menu:"FILES",label:"FILES // report.pdf",resolved:true,
     item:"report.pdf",favoriteType:"FILE FAVORITE",readOnly:true},
    {key:keys[2],category:"CPU++",owner:"appcontrol",
     menu:"KILL",label:"KILL // kitty",resolved:true,item:"kitty",
     favoriteType:"PROCESS FAVORITE",readOnly:true}
  ]});
  assert.equal(result.total,3);
  assert.deepEqual(plain(result.groups.map(g=>g.title)),
    ["APP CTRL // FILES","APP CTRL // RUN","CPU++ // KILL"]);
  assert.equal(result.groups[1].unresolved,1);
  assert.equal(result.groups[1].items[0].name,"SAVED COMMAND #1");
  assert.equal(result.groups[0].items[0].name,"report.pdf");
  assert.equal(result.groups[2].items[0].name,"kitty");
  assert.ok(!JSON.stringify(result).includes("private-command"));
  assert.ok(!JSON.stringify(result).includes("resourceId"));
});


test("U5a Weather HOME panels and cards join the same read-only CPU++ candidate list",()=>{
  const wx={storageState:"ready",panelRoutes:["home/auto","home/history"],
            cardKeys:["sky|next-hours","space|geomagnetic"]};
  const original=plain(wx);
  const result=Hub.list([],[],[],[],undefined,undefined,undefined,wx);
  assert.equal(result.total,4);
  assert.equal(result.rows.length,4);
  const expected=[
    ["panel","HOME","AUTO","HOME PANEL FAVORITE"],
    ["panel","HOME","HISTORY","HOME PANEL FAVORITE"],
    ["card","CARD","SKY // NEXT HOURS","HOME CARD FAVORITE"],
    ["card","CARD","SPACE // GEOMAGNETIC","HOME CARD FAVORITE"]
  ];
  for(let i=0;i<expected.length;i++) {
    const row=result.rows[i], [kind,menu,item,type]=expected[i];
    assert.equal(row.kind,kind);
    assert.equal(row.menu,menu);
    assert.equal(row.item,item);
    assert.equal(row.label,"WEATHER // "+menu+" // "+item);
    assert.equal(row.favoriteType,type);
    assert.equal(row.category,"WEATHER");
    assert.equal(row.provider,"weather-home");
    assert.equal(row.owner,"weather-home");
    assert.equal(row.readOnly,true);
    assert.equal(row.available,"unresolved");
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
    assert.equal("action" in row,false);
  }
  assert.deepEqual(plain(wx),original);
  assert.equal(Hub.filterRows(result,"WEATHER").length,4);
  assert.equal(Hub.filterRows(result,"APP CTRL").length,0);
  assert.equal(Hub.filterRows(result,"ALL").length,4);
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const index=Dossier.build(result);
  assert.equal(index.total,4);
  assert.deepEqual(plain(index.groups.map(g=>g.title)),
                   ["WEATHER // HOME","WEATHER // CARD"]);
  assert.deepEqual(plain(index.groups[1].items.map(x=>x.name)),
                   ["SKY // NEXT HOURS","SPACE // GEOMAGNETIC"]);
});

test("U5a weather source fails closed for unavailable or invalid owner snapshots",()=>{
  assert.equal(WeatherHome.build(null).state,"disconnected");
  for(const state of ["loading","saving","error","unsupported","load-error"]) {
    const result=Hub.list([],[],[],[],undefined,undefined,undefined,
      {storageState:state,panelRoutes:["home/auto"],
       cardKeys:["sky|next-hours"]});
    assert.equal(result.total,0,state);
    assert.equal(result.rows.length,0,state);
  }
  for(const input of [
    {storageState:"ready",panelRoutes:["home/not-a-panel"],cardKeys:[]},
    {storageState:"ready",panelRoutes:["home/auto","home/auto"],cardKeys:[]},
    {storageState:"ready",panelRoutes:["home/auto"],
      cardKeys:["sky|next-hours","sky|next-hours"]},
    {storageState:"ready",panelRoutes:["home/auto"],
      cardKeys:["weather|private/script"]},
    {storageState:"ready",panelRoutes:["home/auto"],
      cardKeys:["sky|foo\nsecret"]},
    {storageState:"ready",panelRoutes:[],
      cardKeys:Array(33).fill("sky|next-hours")},
    {storageState:"ready",panelRoutes:null,cardKeys:[]}
  ]) {
    const invalid=WeatherHome.build(input);
    assert.equal(invalid.rows.length,0);
    assert.equal(invalid.state,"invalid");
    assert.ok(invalid.invalidCount>0);
  }
  const safe=WeatherHome.build({
    storageState:"empty",panelRoutes:[],cardKeys:[]});
  assert.equal(safe.state,"empty");
  assert.equal(safe.rows.length,0);
});

test("U5a Weather source is optional and cannot instantiate a duplicate writer",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const manager=read("services/favorites/FavoritesManagementPolicy.js");
  const projection=read("services/favorites/FavoritesWeatherHomeProjection.js");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const dossier=read("services/favorites/FavoritesDossierIndexPolicy.js");
  assert.match(cpu,/property var weatherHomeFavoritesSource: null/);
  assert.match(cpu,/cpuPlusWindow\.weatherHomeFavoritesSnapshot/);
  assert.match(manager,/WeatherHome\.build\(weatherHomeSnapshot\)/);
  assert.match(pane,/"WEATHER"/);
  assert.match(pane,/SOURCE \/\/ WEATHER STATION/);
  assert.match(dossier,/"WEATHER\|HOME","WEATHER\|CARD"/);
  assert.doesNotMatch(cpu+manager+projection,
    /FileView\s*\{|JsonAdapter\s*\{|Process\s*\{|execDetached|setText\(/);
  // The existing W2b owner is still instantiated only inside WeatherStationW.
  const station=read("widgets/weather/WeatherStationW.qml");
  assert.match(station,/WeatherServices\.WeatherHomeFavoritesStore \{/);
  const shell=read("shell.qml");
  assert.doesNotMatch(shell,/WeatherHomeFavoritesStore\s*\{/);
  assert.doesNotMatch(cpu,/WeatherHomeFavoritesStore\s*\{/);
});


test("U5b notification source favorites appear as read-only named candidates",()=>{
  const snap={
    ready:true,status:"ready",revision:7,
    sources:[
      {appKey:"org.mozilla.firefox",source:"Firefox",sourceId:"PRIVATE_ID_SHOULD_NOT_APPEAR"},
      {appKey:"github",source:"GitHub",message:"PRIVATE_MESSAGE_BODY"},
      {appKey:"proton-mail",source:"Proton Mail",url:"https://private.example"}
    ]
  };
  const original=plain(snap);
  const projected=Notifications.build(snap);
  assert.equal(projected.state,"ready");
  assert.equal(projected.invalidCount,0);
  assert.equal(projected.rows.length,3);
  const all=Hub.list([],[],[],[],undefined,undefined,undefined,undefined,snap);
  assert.equal(all.total,3);
  const names=all.rows.map(x=>x.item);
  assert.deepEqual(plain(names),["Firefox","GitHub","Proton Mail"]);
  for(const row of all.rows) {
    assert.equal(row.category,"NOTIFS");
    assert.equal(row.menu,"SOURCES");
    assert.equal(row.owner,"notifications");
    assert.equal(row.provider,"notifications");
    assert.equal(row.favoriteType,"SOURCE FAVORITE");
    assert.equal(row.readOnly,true);
    assert.equal(row.available,"unresolved");
    assert.equal(row.isFavorite,true);
    assert.equal(row.isPinned,false);
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("sourceId" in row,false);
    assert.equal("resourceId" in row,false);
    assert.equal("body" in row,false);
    assert.equal("url" in row,false);
    assert.equal(row.label,"NOTIFICATIONS // SOURCES // "+row.item);
  }
  assert.equal(Hub.filterRows(all,"NOTIFS").length,3);
  assert.equal(Hub.filterRows(all,"WEATHER").length,0);
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const grouped=Dossier.build(all);
  assert.equal(grouped.total,3);
  assert.equal(grouped.groups.length,1);
  assert.equal(grouped.groups[0].key,"NOTIFS|SOURCES");
  assert.equal(grouped.groups[0].title,"NOTIFICATIONS // SOURCES");
  assert.deepEqual(plain(grouped.groups[0].items.map(x=>x.name)),names);
  const rendered=all.rows.map(row=>row.label).join(" ");
  for(const hidden of ["PRIVATE_ID_SHOULD_NOT_APPEAR","PRIVATE_MESSAGE_BODY","private.example"])
    assert.ok(!rendered.includes(hidden),hidden);
  assert.deepEqual(plain(snap),original);
});

test("U5b notifications refuse bad storage state and private-looking names",()=>{
  const noData=Notifications.build(null);
  assert.equal(noData.state,"disconnected");
  assert.equal(noData.rows.length,0);
  for(const status of ["loading","saving","parse-error","load-error","save-error","new"]) {
    const out=Notifications.build({
      ready:true,status:status,sources:[{appKey:"github",source:"GitHub"}]});
    assert.equal(out.rows.length,0,status);
    assert.equal(out.state,status);
  }
  assert.equal(Notifications.build({
    ready:false,status:"ready",sources:[{appKey:"github",source:"GitHub"}]
  }).rows.length,0);
  const snap={ready:true,status:"saved",sources:[
    {appKey:"github",source:"GitHub"},
    {appKey:"github",source:"duplicate"},
    {appKey:"com.example.notify",source:"person@example.com"},
    {appKey:"website:encoded::host.example",source:""},
    {appKey:"",source:"INVALID"},
    {appKey:"https://private.example",source:"unsafe"},
    {appKey:"org.fake.password",source:"App password token"},
    {appKey:"weather",source:"Weather"}
  ]};
  const out=Notifications.build(snap);
  assert.ok(out.invalidCount>=3);
  assert.deepEqual(plain(out.rows.map(row=>row.item)),
    ["GitHub","com.example.notify",
     "WEBSITE SOURCE NAME UNAVAILABLE","org.fake.password","Weather"]);
  const visible=out.rows.map(row=>row.label).join(" ");
  assert.ok(!visible.includes("person@example.com"));
  assert.ok(!visible.includes("host.example"));
  assert.ok(!visible.includes("App password token"));
  assert.ok(!visible.includes("https://private.example"));
  assert.equal(out.rows.every(row=>row.readOnly&&row.capabilities.length===0),true);
  assert.equal(Notifications.build({
    ready:true,status:"ready",sources:Array(129).fill({appKey:"same",source:"Same"})
  }).state,"invalid");
});

test("U5b consumes the existing Notifications singleton without duplicating its writer",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const projection=read("services/favorites/FavoritesNotificationsProjection.js");
  const manager=read("services/favorites/FavoritesManagementPolicy.js");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const index=read("services/favorites/FavoritesDossierIndexPolicy.js");
  const owner=read("services/notifications/NotificationsService.qml");
  assert.match(owner,/pragma Singleton/);
  assert.match(owner,/property ListModel favoriteSources: ListModel \{\}/);
  assert.match(owner,/property int favoritesRevision: 0/);
  assert.match(cpu,/import qs.services.notifications/);
  assert.match(cpu,/NotificationsService\.favoritesRevision/);
  assert.match(cpu,/NotificationsService\.favoriteSources/);
  assert.match(cpu,/NotificationsService\.favoritesStatus/);
  assert.match(cpu,/cpuPlusWindow\.notificationFavoritesSnapshot/);
  assert.match(manager,/NotificationsProjection\.build\(notificationsSnapshot\)/);
  assert.match(pane,/"NOTIFS"/);
  assert.match(pane,/SOURCE \/\/ NOTIFICATIONS/);
  assert.match(index,/"NOTIFS\|SOURCES"/);
  assert.doesNotMatch(projection+manager+cpu,
    /FileView\s*\{|JsonAdapter\s*\{|Process\s*\{|setFavorite\(|toggleFavorite\(/);
  assert.doesNotMatch(cpu,/NotificationsService\s*\{/);
  assert.doesNotMatch(projection,/source\.sourceId|source\.body|source\.message|NotificationsService\./);
});
