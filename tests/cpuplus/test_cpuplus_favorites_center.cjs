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
const Radio={Adapters};
load("services/favorites/FavoritesRadioProjection.js",Radio);
const Hospital={Adapters};
load("services/favorites/FavoritesHospitalProjection.js",Hospital);
const CollectionView={CollectionRules:Collections};
load("services/favorites/FavoritesCollectionsViewPolicy.js",CollectionView);
const OwnerNavigation={};
load("services/favorites/FavoritesOwnerNavigationPolicy.js",OwnerNavigation);
const Hub={Resource,Default,Collections,Adapters,WeatherHome,NotificationsProjection:Notifications,RadioProjection:Radio,HospitalProjection:Hospital};
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
  assert.match(src,/selectedModeIndex === 4[\s\S]*?favoritesDetailsPane\.editingText[\s\S]*?favoritesSelectorPane\.editingText/);
  assert.match(src,/selectedModeIndex === 6 && settingsSubMode === "LOCATION"[\s\S]*?settingsLocationPane\.editingText[\s\S]*?settingsLocationOverviewPane\.editingText/);
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
  assert.match(panel,/readonly property var categoryKeys:/);
  assert.match(panel,/"ALL","GROUP","CPU\+\+","APP CTRL","WEATHER","NOTIFS"/);
  assert.match(panel,/"RADIO","HOSPITAL","CLOCK","PLACES","NEW"/);
  assert.match(panel,/id: categoryFilterFlow/);
  assert.match(panel,/readonly property int upperCount: Math\.ceil\(categoryKeys\.length\/2\)/);
  assert.match(panel,/height: 2\*30\+spacing/);
  assert.match(panel,/modelData\.readOnly\?"READ ONLY"/);
  assert.match(panel,/pane\.selectedResource && !pane\.selectedResource\.readOnly/);
  assert.match(panel,/APP CONTROL-OWNED \/\/ READ ONLY/);
  assert.match(panel,/OPEN OWNER/);
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
  // U9g: after the native hide/show pass, "r" is the same full-row click target.
  assert.ok(fixture.includes("16,r.height/2"));
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
  assert.deepEqual(plain(grouped.groups[0].items.map(x=>x.name)),plain(names));
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
     "WEBSITE SOURCE NAME UNAVAILABLE","SOURCE NAME UNAVAILABLE","Weather"]);
  const visible=out.rows.map(row=>row.label).join(" ");
  assert.ok(!visible.includes("person@example.com"));
  assert.ok(!visible.includes("host.example"));
  assert.ok(!visible.includes("App password token"));
  assert.ok(!visible.includes("org.fake.password"));
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
  assert.doesNotMatch(projection,/source\.sourceId|source\.body|source\.message|NotificationsService\.(?:setFavorite|toggleFavorite|notifications|sourcePolicies)/);
});


test("U5c projects original Weather RADIO favorites and recents with stable UUID deduplication",()=>{
  const station=(suffix,title)=>({
    ref:{source:"radio-browser",kind:"station",
         id:"123e4567-e89b-42d3-a456-"+String(suffix).padStart(12,"0")},
    title,artist:"MUST_NOT_COPY",genre:"private,hidden",
    streamHost:"private-stream.invalid",url:"https://private.invalid/audio"
  });
  const favorites=[station(1,"Public News One"),station(2,"Jazz Station")];
  const recents=[station(2,"Jazz Station"),station(3,"World Radio")];
  const snap={state:"ready",favorites,recents};
  const saved=plain(snap);
  const result=Hub.list([],[],[],[],undefined,undefined,undefined,
                        undefined,undefined,snap);
  assert.equal(result.total,3);
  assert.equal(result.rows.length,3);
  const expected=[
    ["FAVORITES","Public News One","FAVORITE STATION",true,false],
    ["FAVORITES","Jazz Station","FAVORITE + RECENT STATION",true,true],
    ["RECENTS","World Radio","RECENT STATION",false,true]
  ];
  for(let i=0;i<expected.length;i++) {
    const row=result.rows[i], [menu,item,type,favorite,recent]=expected[i];
    assert.equal(row.category,"RADIO");
    assert.equal(row.provider,"radio");
    assert.equal(row.owner,"radio");
    assert.equal(row.kind,"station");
    assert.equal(row.menu,menu);
    assert.equal(row.item,item);
    assert.equal(row.label,"RADIO // "+menu+" // "+item);
    assert.equal(row.favoriteType,type);
    assert.equal(row.isFavorite,favorite);
    assert.equal(row.isRecent,recent);
    assert.equal(row.isPinned,false);
    assert.equal(row.readOnly,true);
    assert.equal(row.available,"unresolved");
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
    assert.equal("ref" in row,false);
    assert.equal("url" in row,false);
    assert.equal("streamHost" in row,false);
  }
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const idx=Dossier.build(result);
  assert.equal(idx.total,3);
  assert.deepEqual(plain(idx.groups.map(group=>group.key)),
                   ["RADIO|FAVORITES","RADIO|RECENTS"]);
  assert.deepEqual(plain(idx.groups.map(group=>group.count)),[2,1]);
  assert.deepEqual(plain(idx.groups[0].items.map(item=>item.name)),
                   ["Public News One","Jazz Station"]);
  assert.equal(Hub.filterRows(result,"RADIO").length,3);
  assert.equal(Hub.filterRows(result,"NOTIFS").length,0);
  assert.deepEqual(plain(snap),saved);
  const visible=JSON.stringify(result);
  for(const sensitive of ["MUST_NOT_COPY","private-stream.invalid",
                           "private,hidden","private.invalid"])
    assert.ok(!visible.includes(sensitive),sensitive);
});

test("U5c preserves Radio owner readiness and rejects corrupt station snapshots",()=>{
  const s=(suffix,title)=>({
    ref:{source:"radio-browser",kind:"station",
         id:"123e4567-e89b-42d3-a456-"+String(suffix).padStart(12,"0")},
    title
  });
  assert.equal(Radio.build(null).state,"disconnected");
  for(const state of ["loading","saving","error","load-error","unavailable"]) {
    const result=Radio.build({state,favorites:[s(1,"Station")],recents:[]});
    assert.equal(result.rows.length,0,state);
    assert.equal(result.state,state);
  }
  for(const bad of [
    {state:"ready",favorites:null,recents:[]},
    {state:"ready",favorites:[s(1,"One"),s(1,"Duplicate")],recents:[]},
    {state:"ready",favorites:[s(1,"One")],recents:[s(2,"https://secret.invalid/path")]},
    {state:"ready",favorites:[s(1,"Private token from playback")],recents:[]},
    {state:"ready",favorites:[{ref:{source:"direct-stream",kind:"stream",id:s(1,"").ref.id},title:"Wrong source"}],recents:[]},
    {state:"ready",favorites:[{ref:{source:"radio-browser",kind:"station",id:"not-a-uuid"},title:"Unknown"}],recents:[]},
    {state:"ready",favorites:Array(11).fill(s(1,"One")),recents:[]},
    {state:"ready",favorites:[],recents:Array(9).fill(s(1,"One"))}
  ]) {
    const out=Radio.build(bad);
    assert.equal(out.state,"invalid");
    assert.equal(out.rows.length,0);
    assert.ok(out.invalidCount>0);
  }
  assert.deepEqual(plain(Radio.build({state:"empty",favorites:[],recents:[]}).rows),[]);
});

test("U5c Radio remains the sole Weather radio memory writer and playback owner",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const policy=read("services/favorites/FavoritesRadioProjection.js");
  const manager=read("services/favorites/FavoritesManagementPolicy.js");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const dossier=read("services/favorites/FavoritesDossierIndexPolicy.js");
  const radio=read("widgets/weather/StationRadio.qml");
  const memory=read("widgets/weather/StationRadioMemoryPolicy.js");
  assert.match(radio,/FileView\s*\{/);
  assert.match(radio,/weather-radio-memory\.json/);
  assert.match(radio,/RadioMemory\.decodeList\(radioMemoryAdapter\.favoriteEntries, 10\)/);
  assert.match(radio,/RadioMemory\.decodeList\(radioMemoryAdapter\.recentEntries, 8\)/);
  assert.match(memory,/function decodeList\(/);
  assert.match(cpu,/property var radioFavoritesSource: null/);
  assert.match(cpu,/cpuPlusWindow\.radioFavoritesSnapshot/);
  assert.match(manager,/RadioProjection\.build\(radioSnapshot\)/);
  assert.match(pane,/"RADIO"/);
  assert.match(pane,/SOURCE \/\/ WEATHER STATION RADIO/);
  assert.match(dossier,/"RADIO\|FAVORITES","RADIO\|RECENTS"/);
  assert.doesNotMatch(policy+cpu+manager,
      /FileView\s*\{|JsonAdapter\s*\{|Process\s*\{|loadMedia\(|playMedia\(|toggleFavorite\(|setFavorite\(/);
  assert.doesNotMatch(policy,/streamHost|\.genre|\.artist|\.codec|\.bitrate|\.url/);
  assert.doesNotMatch(cpu,/StationRadio\s*\{/);
});


test("U5a and U5c Weather favorites pass only loaded owner snapshots through shell",()=>{
  const shell=read("shell.qml");
  const weather=read("widgets/weather/WeatherStationW.qml");
  const station=read("widgets/weather/StationSubjectNavigator.qml");
  const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
  const media=read("widgets/weather/StationMediaSubjectPane.qml");
  const radio=read("widgets/weather/StationRadio.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const home=read("services/weather/WeatherHomeFavoritesStore.qml");

  // The actual shell wiring is not just a synthetic projection or a second
  // store. Both references point into the existing WeatherStationW instance.
  assert.match(shell,/weatherHomeFavoritesSource:\s*weatherStationWindow\.homeFavoritesReadOnlySnapshot/);
  assert.match(shell,/radioFavoritesSource:\s*weatherStationWindow\.radioFavoritesReadOnlySnapshot/);
  assert.match(weather,/readonly property var homeFavoritesReadOnlySnapshot:/);
  assert.match(weather,/storageState:homeFavoritesStore\.storageState/);
  assert.match(weather,/homeFavoritesStore\.panelRoutes\.slice\(\)/);
  assert.match(weather,/homeFavoritesStore\.cardKeys\.slice\(\)/);
  assert.match(weather,/readonly property var radioFavoritesReadOnlySnapshot:\s*subjectNavigator\.radioFavoritesSnapshot/);
  assert.match(home,/readonly property var panelRoutes: document\.panelRoutes/);
  assert.match(home,/readonly property var cardKeys: document\.cardKeys/);
  assert.match(cpu,/cpuPlusWindow\.weatherHomeFavoritesSnapshot/);
  assert.match(cpu,/cpuPlusWindow\.radioFavoritesSnapshot/);

  // The route chain includes both workspace and INDEX.MEDIA paths.
  assert.match(station,/readonly property var radioFavoritesSnapshot:/);
  assert.match(station,/browser\.indexOpen \? mediaLivePane : workspaceLoader\.item/);
  assert.match(station,/if \(!browser\.visible \|\| browser\.liveMediaKind===""\) return null;/);
  assert.match(workspace,/mediaWorkspacePane\.radioFavoritesSnapshot/);
  assert.match(media,/readonly property var radioFavoritesSnapshot:/);
  assert.match(media,/mediaLoader\.active && mediaLoader\.item/);
  assert.match(media,/mediaLoader\.item\.favoritesBridgeSnapshot/);
  assert.match(media,/readonly property var favoritesBridgeSnapshot:\s*overviewRadio\.favoritesBridgeSnapshot/);
  assert.match(media,/id: overviewRadio/);

  // A FileView load/success/failure sets source truth, not CPU++.
  assert.match(radio,/property string radioMemoryState: "loading"/);
  assert.match(radio,/onLoaded: stationRadio\.radioMemoryState="ready"/);
  assert.match(radio,/onLoadFailed: function\(error\)/);
  assert.match(radio,/stationRadio\.radioMemoryState="unavailable"/);
  assert.match(radio,/onSaved: stationRadio\.radioMemoryState="ready"/);
  assert.match(radio,/onSaveFailed: function\(error\)/);
  assert.match(radio,/radioMemoryState="loading";\s*reload\(\);/);
  assert.match(radio,/if \(state!=="ready"\) return \(\{state:state,favorites:\[\],recents:\[\]\}\);/);
  assert.match(radio,/favorites:copy\(stationRadio\.favoriteItems\)/);
  assert.match(radio,/recents:copy\(stationRadio\.recentItems\)/);

  // Keep original owner files and playback exactly where they were.
  assert.equal((radio.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((home.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((shell.match(/\bWeatherStationW\s*\{/g)||[]).length,1);
  assert.doesNotMatch(shell+cpu,/\bStationRadio\s*\{|\bWeatherHomeFavoritesStore\s*\{|\bFileView\s*\{/);
  assert.doesNotMatch(media+station+workspace,/writeAdapter\(|loadMedia\(|transport\(|execDetached/);
});


test("U5d Hospital pinned activities have readable source/type/time but no archive text",()=>{
  const record=(source,kind,date,ordinal,privateFields={})=>({
    ref:"pinned|"+source+"|"+kind+"|"+date+"|"+ordinal,
    source,kind,recordedAt:date,...privateFields
  });
  const sample={
    state:"hydrated",
    pins:[
      record("reports","report","2026-11-08T18:12:05.000Z",1,
             {title:"PRIVATE PERSON // ROOM B",detail:"PRIVATE_REPORT_BODY",
              context:{room:"PRIVATE_ROOM"},route:"reports",
              key:"PRIVATE_ACTIVITY_KEY"}),
      record("rounds","room","2026-11-08T18:13:08.000Z",1,
             {title:"PRIVATE_TEAM_DO_NOT_SHOW",body:"PRIVATE_TRANSCRIPT"}),
      record("intercom","intercom","2026-11-08T18:14:09.000Z",1,
             {message:"PRIVATE_CONVERSATION"})
    ]
  };
  const untouched=plain(sample);
  const result=Hub.list([],[],[],[],undefined,undefined,undefined,
                        undefined,undefined,undefined,sample);
  assert.equal(result.total,3);
  assert.equal(result.rows.length,3);
  assert.deepEqual(plain(result.rows.map(r=>r.label)),[
    "HOSPITAL // REPORTS // REPORT // 2026-11-08 18:12:05 UTC",
    "HOSPITAL // ROUNDS // ROOM // 2026-11-08 18:13:08 UTC",
    "HOSPITAL // INTERCOM // INTERCOM // 2026-11-08 18:14:09 UTC"
  ]);
  for(const row of result.rows) {
    assert.equal(row.owner,"hospital");
    assert.equal(row.provider,"hospital");
    assert.equal(row.category,"HOSPITAL");
    assert.equal(row.kind,"activity");
    assert.equal(row.favoriteType,"PINNED ACTIVITY");
    assert.equal(row.readOnly,true);
    assert.equal(row.isPinned,true);
    assert.equal(row.isFavorite,true);
    assert.equal(row.available,"unresolved");
    assert.deepEqual(plain(row.capabilities),[]);
    assert.equal("resourceId" in row,false);
    assert.equal("title" in row,false);
    assert.equal("context" in row,false);
    assert.equal("body" in row,false);
    assert.equal("route" in row,false);
  }
  assert.equal(Hub.filterRows(result,"HOSPITAL").length,3);
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const grouped=Dossier.build(result);
  assert.deepEqual(plain(grouped.groups.map(g=>g.key)),
                   ["HOSPITAL|ROUNDS","HOSPITAL|REPORTS","HOSPITAL|INTERCOM"]);
  assert.equal(grouped.total,3);
  for(const word of ["PRIVATE PERSON","PRIVATE_REPORT_BODY","PRIVATE_ROOM",
                     "PRIVATE_ACTIVITY_KEY","PRIVATE_TEAM_DO_NOT_SHOW",
                     "PRIVATE_TRANSCRIPT","PRIVATE_CONVERSATION"]) {
    assert.equal(JSON.stringify(grouped).includes(word),false,word);
    assert.equal(JSON.stringify(result).includes(word),false,word);
  }
  assert.deepEqual(plain(sample),untouched);
});

test("U5d Hospital projection declines unhydrated, malformed and raw sensitive identities",()=>{
  assert.equal(Hospital.build(null).state,"disconnected");
  for(const state of ["loading","failed","error","unsupported"]) {
    const got=Hospital.build({state,pins:[]});
    assert.equal(got.rows.length,0);
    assert.equal(got.state,state);
  }
  const goodAt="2026-11-08T18:22:30.000Z";
  const good={ref:"pinned|reports|report|"+goodAt+"|1",
    source:"reports",kind:"report",recordedAt:goodAt};
  for(const bad of [
    {state:"hydrated",pins:null},
    {state:"hydrated",pins:Array(6).fill(good)},
    {state:"hydrated",pins:[good,good]},
    {state:"hydrated",pins:[{...good,ref:"reports::PRIVATE_CLIENT_NAME"}]},
    {state:"hydrated",pins:[{...good,source:"PRIVATE_CLIENT_NAME"}]},
    {state:"hydrated",pins:[{...good,kind:"report//PRIVATE_REPORT"}]},
    {state:"hydrated",pins:[{...good,recordedAt:"../../private"}]},
    {state:"hydrated",pins:[{...good,ref:"pinned|reports|report|"+goodAt+"|7"}]}
  ]) {
    const out=Hospital.build(bad);
    assert.equal(out.state,"invalid");
    assert.equal(out.rows.length,0);
    assert.ok(out.invalidCount>0);
  }
  const unknown=Hospital.build({state:"hydrated",pins:[{
    ref:"pinned|activity|activity|undated|1",
    source:"activity",kind:"activity",recordedAt:""
  }]});
  assert.equal(unknown.rows.length,1);
  assert.equal(unknown.rows[0].item,"ACTIVITY // DATE UNAVAILABLE");
  assert.equal(unknown.rows[0].resolved,true);
  assert.ok(!JSON.stringify(unknown).includes("PRIVATE"));
});

test("U5d Hospital owner emits sanitized refs and shell routes only metadata to CPU++",()=>{
  const w=read("widgets/HospitalW.qml");
  const sh=read("shell.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const manager=read("services/favorites/FavoritesManagementPolicy.js");
  const adapter=read("services/favorites/FavoritesReadOnlyAdapters.js");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const index=read("services/favorites/FavoritesDossierIndexPolicy.js");
  const projection=read("services/favorites/FavoritesHospitalProjection.js");
  const owner=read("services/hospital/HospitalReceptionistService.qml");

  assert.match(w,/readonly property var receptionPinnedReadOnlySnapshot:/);
  assert.match(w,/receptionistService\.pinnedKeys/);
  assert.match(w,/receptionistService\.activityEvents/);
  assert.match(w,/Object\.prototype\.hasOwnProperty\.call\(byKey,privateKey\)/);
  assert.match(w,/ref:"pinned\|"\+base\+"\|"\+serial/);
  assert.match(w,/source:source,kind:kind,recordedAt:at/);
  assert.doesNotMatch(w.slice(w.indexOf("readonly property var receptionPinnedReadOnlySnapshot:"),
                               w.indexOf("HospitalContextService {")),/event\.title|event\.detail|event\.context|event\.route/);
  assert.match(sh,/hospitalPinnedFavoritesSource:\s*hospitalWindow\.receptionPinnedReadOnlySnapshot/);
  assert.match(cpu,/property var hospitalPinnedFavoritesSource: null/);
  assert.match(cpu,/cpuPlusWindow\.hospitalPinnedFavoritesSnapshot/);
  assert.match(manager,/HospitalProjection\.build\(hospitalSnapshot\)/);
  assert.match(adapter,/function hospital\(pinnedKeys\)/);
  assert.match(pane,/"HOSPITAL"/);
  assert.match(pane,/SOURCE \/\/ HOSPITAL RECEPTION/);
  assert.match(index,/"HOSPITAL\|ROUNDS"/);
  assert.match(owner,/path: Quickshell\.dataPath\("hospital-reception\.json"\)/);
  assert.match(owner,/function setPinned\(event, pinnedValue\)/);
  assert.doesNotMatch(projection+cpu,
       /FileView\s*\{|JsonAdapter\s*\{|Process\s*\{|setPinned\(|togglePinned\(|exportArchive\(/);
  assert.doesNotMatch(projection,/\.title|\.detail|\.context|\.route|\.message|\.body/);
});


test("U6b collections join matching owner candidates in saved member order without exposing keys",()=>{
  const keys=[
    k("weather-home","panel","home/auto"),
    k("radio","station","123e4567-e89b-42d3-a456-000000000001"),
    k("weather-home","panel","home/history")
  ];
  let doc=Collections.change(Collections.empty(),{type:"create",name:"Daily Operations"}).document;
  for(const key of keys)
    doc=Collections.change(doc,{type:"set-member",
      collectionId:"c1",key,enabled:true}).document;
  const original=plain(doc);
  const candidates={rows:[
    {key:keys[1],label:"RADIO // FAVORITES // Jazz Station",item:"Jazz Station",
     resolved:true,category:"RADIO",owner:"radio",readOnly:true},
    {key:keys[0],label:"WEATHER // HOME // AUTO",item:"AUTO",
     resolved:true,category:"WEATHER",owner:"weather-home",readOnly:true},
    {key:k("appcontrol","item","run:kitty:private"),label:"PRIVATE COMMAND",
     resolved:false,category:"APP CTRL",owner:"appcontrol",readOnly:true}
  ]};
  const view=CollectionView.build(doc.collections,candidates,"ready");
  assert.equal(view.state,"ready");
  assert.equal(view.count,1);
  assert.equal(view.memberCount,3);
  assert.equal(view.missingCount,1);
  const group=CollectionView.section(view,"c1");
  assert.equal(group.name,"Daily Operations");
  assert.equal(group.count,3);
  assert.equal(group.available,2);
  assert.equal(group.missing,1);
  assert.deepEqual(plain(group.items.map(x=>x.name)),[
    "AUTO","Jazz Station","SAVED MEMBER UNAVAILABLE"
  ]);
  assert.equal(group.items[2].key,"");
  assert.equal(group.items[2].missing,true);
  assert.deepEqual(plain(CollectionView.rowsFor(view,"c1").map(x=>x.key)),
                   keys.slice(0,2));
  assert.equal(CollectionView.rowsFor(view,"c9").length,0);
  assert.equal(JSON.stringify(view).includes("PRIVATE COMMAND"),false);
  assert.equal(JSON.stringify(group.items).includes("home%2Fhistory"),false);
  assert.deepEqual(plain(doc),original);
  const updated=CollectionView.build(doc.collections,
    {rows:candidates.rows.concat([{
      key:keys[2],item:"HISTORY",label:"WEATHER // HOME // HISTORY",
      category:"WEATHER",owner:"weather-home",resolved:true
    }])},"saving");
  assert.equal(updated.groups[0].available,3);
  assert.equal(updated.missingCount,0);
  assert.equal(updated.groups[0].items[2].name,"HISTORY");
  assert.equal(JSON.stringify(updated).includes("PRIVATE COMMAND"),false);
});

test("U6b collections fail closed on bad storage state and invalid metadata",()=>{
  const key=k("weather-home","panel","home/auto");
  const good={id:"c1",name:"Daily Operations",members:[key]};
  const snapshot={rows:[{key,label:"WEATHER // HOME // AUTO",
    item:"AUTO",category:"WEATHER",resolved:true}]};
  for(const state of ["loading","error","unsupported","disconnected"]) {
    const view=CollectionView.build([good],snapshot,state);
    assert.equal(view.count,0);
    assert.equal(view.state,state);
  }
  for(const groups of [
    null,Array(25).fill(good),[good,good],
    [{...good,members:[key,key]}],
    [{...good,id:"../../private"}],
    [{...good,name:"Bad\nName"}],
    [{...good,members:[k("appcontrol","item","run:secret")]}],
    [{...good,members:Array(81).fill(key)}]
  ]) {
    const view=CollectionView.build(groups,snapshot,"ready");
    assert.equal(view.state,"invalid");
    assert.equal(view.count,0);
  }
  assert.equal(CollectionView.section(null,"c1"),null);
  assert.equal(CollectionView.rowsFor(null,"c1").length,0);
});

test("U6b CPU++ index routes a collection across all three bays, without owner actions",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const projection=read("services/favorites/FavoritesCollectionsViewPolicy.js");
  const store=read("services/favorites/FavoritesCollectionsStore.qml");
  assert.match(cpu,/property string selectedFavoriteCollectionId: ""/);
  assert.equal((cpu.match(/selectedCollectionId: cpuPlusWindow\.selectedFavoriteCollectionId/g)||[]).length,3);
  assert.match(cpu,/onCollectionRequested: function\(collectionId\)/);
  assert.match(cpu,/onCollectionMemberRequested: function\(collectionId,key\)/);
  assert.match(cpu,/favoritesSelectorPane\.filterMode="GROUP"/);
  assert.match(pane,/import "\.\.\/\.\.\/services\/favorites\/FavoritesCollectionsViewPolicy\.js" as CollectionView/);
  assert.match(pane,/signal collectionRequested\(string collectionId\)/);
  assert.match(pane,/signal collectionMemberRequested\(string collectionId, string key\)/);
  assert.match(pane,/pane\.filterMode==="GROUP"/);
  assert.match(pane,/CollectionView\.rowsFor\(pane\.collectionView,pane\.selectedCollectionId\)/);
  assert.match(projection,/SAVED MEMBER UNAVAILABLE/);
  assert.match(pane,/pane\.collectionView\.groups/);
  assert.match(store,/favorites-collections-v1\.json/);
  // The existing right-side pane intentionally still owns the pre-U6b
  // Clock/NEW controls. Test the new projection and navigation seam, not
  // unrelated original owner actions already present in the component.
  assert.doesNotMatch(projection,
    /FileView\s*\{|Process\s*\{|JsonAdapter\s*\{|setFavorite\(|togglePinned\(|loadMedia\(/);
  assert.doesNotMatch(pane,
    /FileView\s*\{|Process\s*\{|JsonAdapter\s*\{/);
  const navigation=pane.slice(pane.indexOf("// U6b: collections"),
    pane.indexOf("id: dossierScroll"));
  assert.doesNotMatch(navigation,
    /setFavorite\(|togglePinned\(|loadMedia\(/);
});


test("U6c right collection names navigate to shared GROUP filter without activating owners",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const panel=read("components/FavoritesCollectionPanel.qml");
  const toggle=read("components/FavoritesCollectionToggleButton.qml");
  const store=read("services/favorites/FavoritesCollectionsStore.qml");
  const policy=read("services/favorites/FavoritesCollectionsPolicy.js");
  assert.match(cpu,/function openFavoriteCollection\(collectionId,memberKey\)/);
  assert.match(cpu,/if\(key && !section\.rows\.some\(function\(row\)/);
  assert.match(cpu,/selectedFavoriteCollectionId=collectionId/);
  assert.match(cpu,/favoritesSelectorPane\.filterMode="GROUP"/);
  assert.match(cpu,/selectedFavoriteKey=key \|\| \(section\.rows\.length/);
  assert.match(cpu,/cpuPlusWindow\.openFavoriteCollection\(collectionId,""\)/);
  assert.match(cpu,/cpuPlusWindow\.openFavoriteCollection\(collectionId,key\)/);
  assert.match(pane,/onCollectionRequested: function\(collectionId\)/);
  assert.match(pane,/onCreateAccepted: function\(collectionId\)/);
  assert.match(pane,/pane\.collectionRequested\(collectionId\)/);
  assert.match(pane,/Qt\.callLater\(function\(\) \{/);
  assert.match(panel,/signal collectionRequested\(string collectionId\)/);
  assert.match(panel,/Accessible\.name: "Open collection "\+modelData\.name/);
  assert.match(panel,/onClicked: panel\.collectionRequested\(modelData\.id\)/);
  assert.match(panel,/groupRow\.saveRename\(\)/);
  assert.match(toggle,/label: inCollection \? "UNLINK" : "ADD"/);
  assert.match(store,/function renameCollection\(id,name\)/);
  assert.match(policy,/action\.type==="rename"/);
  assert.equal((cpu.match(/selectedCollectionId: cpuPlusWindow\.selectedFavoriteCollectionId/g)||[]).length,3);
  for(const src of [cpu.slice(cpu.indexOf("function openFavoriteCollection"),
          cpu.indexOf("function openFavoriteCollection")+1100),panel]) {
    assert.doesNotMatch(src,/FileView\s*\{|Process\s*\{|JsonAdapter\s*\{|setFavorite\(|togglePinned\(|loadMedia\(/);
  }
});


test("U7a owner navigation emits fixed views for existing read-only sources only",()=>{
  const row=(owner,category,menu)=>({
    owner,category,menu,readOnly:true,
    key:"fav1:local:"+owner+":item:PRIVATE_KEY",
    resourceId:"PRIVATE_RESOURCE",
    item:"PRIVATE_ITEM",label:"PRIVATE_LABEL",
    sourceName:"PRIVATE_SOURCE",capabilities:[]
  });
  const good=[
    ["appcontrol","APP CTRL","APPS","appcontrol","APPS"],
    ["appcontrol","APP CTRL","RUN","appcontrol","RUN"],
    ["appcontrol","APP CTRL","FILES","appcontrol","FILES"],
    ["appcontrol","APP CTRL","KILL","appcontrol","KILL"],
    ["appcontrol","APP CTRL","SYSTEM","appcontrol","SYSTEM"],
    ["appcontrol","CPU++","KILL","appcontrol","KILL"],
    ["appcontrol","CPU++","THERMAL","appcontrol","THERMAL"],
    ["appcontrol","CPU++","SYSTEM","appcontrol","SYSTEM"],
    ["appcontrol","APP CTRL","OTHER","appcontrol","FAVORITES"],
    ["weather-home","WEATHER","HOME","weather","home"],
    ["weather-home","WEATHER","CARD","weather","home"],
    ["radio","RADIO","FAVORITES","weather","radio"],
    ["radio","RADIO","RECENTS","weather","radio"],
    ["notifications","NOTIFS","SOURCES","notifications","favorites"],
    ["hospital","HOSPITAL","ROUNDS","hospital","reception"],
    ["hospital","HOSPITAL","REPORTS","hospital","reception"]
  ];
  for(const [owner,category,menu,destination,view] of good) {
    const source=row(owner,category,menu);
    const before=plain(source);
    const target=OwnerNavigation.plan(source);
    assert.deepEqual(plain(target),{ok:true,owner:destination,view});
    const output=JSON.stringify(target);
    for(const privateValue of ["PRIVATE_KEY","PRIVATE_RESOURCE",
                               "PRIVATE_ITEM","PRIVATE_LABEL","PRIVATE_SOURCE"])
      assert.equal(output.includes(privateValue),false,privateValue);
    assert.deepEqual(plain(source),before);
  }
});

test("U7a owner navigation refuses unsupported, mutable or forged destinations",()=>{
  const good={key:"fav1:local:radio:station:PRIVATE",
    owner:"radio",category:"RADIO",menu:"FAVORITES",readOnly:true};
  for(const altered of [
    null,[],{}, {...good,key:""}, {...good,readOnly:false},
    {...good,owner:"radio",category:"APP CTRL"},
    {...good,category:"RADIO",menu:"STREAM"},
    {...good,owner:"weather-home",category:"WEATHER",menu:"TERMINAL"},
    {...good,owner:"hospital",category:"HOSPITAL",menu:"PRIVATE_REPORT"},
    {...good,owner:"notifications",category:"NOTIFS",menu:"WEBSITE"},
    {...good,owner:"appcontrol",category:"APP CTRL",menu:"EXECUTE"},
    {...good,owner:"appcontrol",category:"CPU++",menu:"APPS"},
    {...good,owner:"appcontrol",category:"CPU++",menu:"RUN"},
    {...good,owner:"appcontrol",category:"CPU++",menu:"FILES"},
    {...good,owner:"appcontrol",category:"CPU++",menu:"EXECUTE"},
    {...good,owner:"shell",category:"RADIO",menu:"FAVORITES"},
    {...good,owner:"../../private",category:"RADIO",menu:"FAVORITES"}
  ]) {
    assert.deepEqual(plain(OwnerNavigation.plan(altered)),
                     {ok:false,owner:"",view:""});
  }
});

test("U7a OPEN OWNER uses shell's existing windows and never forwards selected IDs",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const shell=read("shell.qml");
  const policy=read("services/favorites/FavoritesOwnerNavigationPolicy.js");
  assert.match(pane,/import "\.\.\/\.\.\/services\/favorites\/FavoritesOwnerNavigationPolicy\.js" as OwnerNavigation/);
  assert.match(pane,/signal ownerNavigationRequested\(string owner, string view\)/);
  assert.match(pane,/OwnerNavigation\.plan\(pane\.selectedResource\)/);
  assert.match(pane,/label: pane\.selectedResource && pane\.selectedResource\.readOnly\s*\? "OPEN OWNER"/);
  assert.match(pane,/if\(item\.readOnly\) return pane\.ownerNavigation\.ok/);
  assert.match(pane,/pane\.ownerNavigationRequested\(target\.owner,target\.view\)/);
  assert.match(cpu,/signal favoriteOwnerNavigationRequested\(string owner,string view\)/);
  assert.match(cpu,/onOwnerNavigationRequested: function\(owner,view\)/);
  assert.match(cpu,/cpuPlusWindow\.favoriteOwnerNavigationRequested\(owner,view\)/);
  assert.match(shell,/function openApolloFavoriteOwner\(owner,view\)/);
  assert.match(shell,/onFavoriteOwnerNavigationRequested: function\(owner,view\)/);
  assert.match(shell,/if\(shellRoot\.openApolloFavoriteOwner\(owner,view\)\)\s*cpuPlusWindow\.close\(\)/);
  const route=shell.slice(shell.indexOf("function openApolloFavoriteOwner("),
                          shell.indexOf("function swapControlKeyboardOwner()"));
  assert.match(route,/appControlWindow\.switchMode\(modes\[view\],false\)/);
  assert.match(route,/weatherStationWindow\.openNotificationView\(view\)/);
  assert.match(route,/notificationsHubWindow\.activeFilter="favorites"/);
  assert.match(route,/hospitalWindow\.openReception\(\)/);
  assert.match(route,/requestControlKeyboard\("appcontrol","favorites-owner"\)/);
  assert.match(route,/requestControlKeyboard\("weather","favorites-owner"\)/);
  assert.match(route,/requestControlKeyboard\("notifications","favorites-owner"\)/);
  assert.match(route,/requestControlKeyboard\("hospital","favorites-owner"\)/);
  for(const code of [policy,route]) {
    assert.doesNotMatch(code,/FileView\s*\{|Process\s*\{|JsonAdapter\s*\{|execDetached|setFavorite\(|togglePinned\(|loadMedia\(|runCommand\(/);
    assert.doesNotMatch(code,/\.resourceId|\.command|\.streamUrl|\.url|\.hospitalRecord/);
  }
  assert.match(shell,/function openApolloNotificationRoute\(destination\)/);
});


test("U8a secondary source/menu filters use only canonical dossier metadata",()=>{
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  const rows=[
    {category:"APP CTRL",menu:"RUN",key:"safe1"},
    {category:"APP CTRL",menu:"APPS",key:"safe2"},
    {category:"APP CTRL",menu:"FILES",key:"safe3"},
    {category:"APP CTRL",menu:"RUN",key:"safe4"},
    {category:"CPU++",menu:"SYSTEM",key:"safe5"},
    {category:"CPU++",menu:"KILL",key:"safe6"},
    {category:"WEATHER",menu:"HOME",key:"safe7"},
    {category:"APP CTRL",menu:"DELETE PRIVATE COMMAND",key:"unsafe"}
  ];
  const candidates={rows},before=plain(candidates);
  assert.deepEqual(plain(Dossier.menusFor(candidates,"APP CTRL",[])),
    ["ALL","APPS","FILES","RUN"]);
  assert.deepEqual(plain(Dossier.menusFor(candidates,"CPU++",[])),
    ["ALL","KILL","SYSTEM"]);
  assert.deepEqual(plain(Dossier.menusFor(candidates,"WEATHER",[])),
    ["ALL","HOME"]);
  assert.deepEqual(plain(Dossier.menusFor(candidates,"GROUP",
    [rows[4],rows[1]])),["ALL","APPS","SYSTEM"]);
  assert.deepEqual(plain(Dossier.menusFor(null,"APP CTRL",null)),["ALL"]);
  assert.ok(!JSON.stringify(Dossier.menusFor(candidates,"ALL",[]))
    .includes("DELETE PRIVATE COMMAND"));
  assert.deepEqual(plain(candidates),before);
});
test("U8a main category icons reflect source module glyphs",()=>{
  const Dossier={};
  load("services/favorites/FavoritesDossierIndexPolicy.js",Dossier);
  for(const [category,component,glyph] of [
    ["CPU++","modules/Cpu.qml","🖥"],
    ["APP CTRL","modules/Applauncher.qml","♱"],
    ["NOTIFS","modules/NotificationsHub.qml","🗒"],
    ["HOSPITAL","modules/Hospital.qml","⚚"],
    ["CLOCK","modules/Clock.qml","🕰"]
  ]) {
    assert.equal(Dossier.mainIcon(category),glyph);
    assert.ok(read(component).includes(glyph),category);
  }
  for(const category of ["ALL","GROUP","WEATHER","RADIO","PLACES","NEW"])
    assert.notEqual(Dossier.mainIcon(category),"",category);
  assert.equal(Dossier.mainIcon("PRIVATE_MODE"),"");
});
test("U8a left dossier can collapse every group and keeps per-group toggle",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  assert.match(pane,/property alias collapseAllControl: collapseAllButton/);
  assert.match(pane,/function allIndexGroupsCollapsed\(\)/);
  assert.match(pane,/function toggleAllIndexGroups\(\)/);
  assert.match(pane,/for\(const group of pane\.dossier\.groups\)/);
  assert.match(pane,/collapsedIndexGroups=next/);
  assert.match(pane,/pane\.toggleIndexGroup\(\s*dossierGroup\.section\.key\)/);
  assert.match(pane,/label: pane\.allIndexGroupsCollapsed\(\) \? "EXPAND ALL" : "COLLAPSE ALL"/);
});
test("U8a bottom subfilters are scoped to the main category and are view-only",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(pane,/property string menuFilter: "ALL"/);
  assert.match(pane,/Dossier\.menusFor\(pane\.candidates,pane\.filterMode,pane\.menuSourceRows\)/);
  assert.match(pane,/row\.category===pane\.filterMode/);
  assert.match(pane,/row\.menu===pane\.menuFilter/);
  assert.match(pane,/id: subfilterScroll/);
  assert.match(pane,/id: subfilterButtons/);
  assert.match(pane,/id: menuFilterPrev/);
  assert.match(pane,/id: menuFilterNext/);
  assert.match(pane,/subfilterScroll\.contentX-140/);
  assert.match(pane,/subfilterScroll\.contentX\+140/);
  assert.match(pane,/onLeftClicked: pane\.menuFilter=modelData/);
  assert.match(cpu,/favoritesSelectorPane\.menuFilter = "ALL"/);
  assert.match(cpu,/favoritesSelectorPane\.menuFilter="ALL"/);
  const section=pane.slice(pane.indexOf("id: subfilterScroll"),
    pane.indexOf('id: details\n'));
  assert.doesNotMatch(section,/setFavorite|deleteCollection|Process\s*\{|execDetached|ownerNavigationRequested/);
});
test("U8a red left-side collection delete uses two clicks and the original writer",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const store=read("services/favorites/FavoritesCollectionsStore.qml");
  const native=read("components/FavoritesCollectionPanel.qml");
  const start=pane.indexOf("id: leftCollectionDelete");
  const end=pane.indexOf('id: dossierScroll',start);
  assert.ok(start>=0 && end>start);
  const section=pane.slice(start,end);
  assert.match(section,/label: collectionGroup\.confirmDelete \? "SURE\?" : "✕"/);
  assert.match(section,/accentColor: Colors\.red/);
  assert.match(section,/destructive: true/);
  assert.match(section,/if \(!collectionGroup\.confirmDelete\)/);
  assert.match(section,/pane\.collectionsOwner\.deleteCollection\(id\)/);
  assert.match(section,/pane\.collectionDeleteAccepted\(id\)/);
  assert.match(store,/function deleteCollection\(id\)/);
  assert.match(native,/id: deleteButton[\s\S]*?accentColor: Colors\.red/);
  assert.match(cpu,/function favoriteCollectionDeleted\(id\)/);
  assert.match(cpu,/selectedFavoriteCollectionId=""/);
  assert.match(cpu,/onCollectionDeleteAccepted: function\(collectionId\)/);
});
test("U8a CPU++ red X closes through the established lifecycle while glow probe code remains",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(cpu,/id: cpuPlusCloseButton/);
  const close=cpu.slice(cpu.indexOf("id: cpuPlusCloseButton"),
    cpu.indexOf("id: modeRailHeaderLine"));
  assert.match(close,/text: "×"/);
  assert.match(close,/font\.pixelSize: 27/);
  assert.match(close,/color: Colors\.black/);
  assert.match(close,/border\.color:[\s\S]*?Colors\.red/);
  assert.match(close,/color: Colors\.red/);
  assert.match(close,/onClicked: cpuPlusWindow\.close\(\)/);
  assert.match(cpu,/\/\*\s*\/\/ Temporary test controls/);
  assert.match(cpu,/id: sampledGlowTestControls/);
  assert.match(cpu,/id: sampledGlowTestControls[\s\S]*?modeGlowExperiment = modelData\.value[\s\S]*?\*\//);
  assert.match(cpu,/readonly property string glowStartupChoice:/);
  assert.match(cpu,/property int modeGlowExperiment:/);
  assert.match(cpu,/primaryGlowEnabled:/);
  assert.match(cpu,/labelGlowEnabled:/);
});


test("U8a collapse-all transitions execute on the actual index functions",()=>{
  const source=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const first=source.indexOf("    function toggleIndexGroup(key) {");
  const last=source.indexOf("    function revealSelectedInSelector() {",first);
  assert.ok(first>=0&&last>first);
  const scope={pane:{dossier:{groups:[
    {key:"APP CTRL|RUN"},{key:"CPU++|SYSTEM"},{key:"WEATHER|HOME"}
  ]},collapsedIndexGroups:{}},dossierScroll:{contentY:84}};
  Object.defineProperty(scope,"collapsedIndexGroups",{
    get(){return scope.pane.collapsedIndexGroups;},
    set(value){scope.pane.collapsedIndexGroups=value;}
  });
  const ctx=vm.createContext(scope);
  vm.runInContext(source.slice(first,last),ctx);
  assert.equal(scope.allIndexGroupsCollapsed(),false);
  scope.toggleAllIndexGroups();
  assert.equal(scope.allIndexGroupsCollapsed(),true);
  assert.equal(scope.dossierScroll.contentY,0);
  assert.deepEqual(plain(scope.pane.collapsedIndexGroups),{
    "APP CTRL|RUN":true,"CPU++|SYSTEM":true,"WEATHER|HOME":true
  });
  scope.toggleIndexGroup("CPU++|SYSTEM");
  assert.equal(scope.allIndexGroupsCollapsed(),false);
  assert.equal(scope.pane.collapsedIndexGroups["CPU++|SYSTEM"],false);
  scope.toggleAllIndexGroups();
  assert.equal(scope.allIndexGroupsCollapsed(),true);
  scope.toggleAllIndexGroups();
  assert.deepEqual(plain(scope.pane.collapsedIndexGroups),{});
  assert.equal(scope.allIndexGroupsCollapsed(),false);
});
test("U8a two-click red left collection delete invokes store only on confirmation",()=>{
  const source=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const start=source.indexOf("id: leftCollectionDelete");
  const after=source.slice(start);
  const marker="onLeftClicked: {";
  const a=after.indexOf(marker),b=after.indexOf("\n                                    }\n                                }\n",a);
  assert.ok(start>=0 && a>=0 && b>a);
  const action=after.slice(a+marker.length,b);
  const calls=[];
  const scope={
    collectionGroup:{confirmDelete:false,section:{id:"c7"}},
    pane:{
      collectionsOwner:{deleteCollection(id){calls.push("delete:"+id);return true;}},
      collectionDeleteAccepted(id){calls.push("accepted:"+id);}
    }
  };
  const context=vm.createContext(scope);
  vm.runInContext("function click() {"+action+"\n}",context);
  scope.click();
  assert.equal(scope.collectionGroup.confirmDelete,true);
  assert.deepEqual(calls,[]);
  scope.click();
  assert.deepEqual(calls,["delete:c7","accepted:c7"]);
  const policy=read("services/favorites/FavoritesCollectionsPolicy.js");
  assert.match(policy,/action\.type==="delete"/);
  // Collection deletion is only a grouping writer, not the original owner.
  assert.doesNotMatch(action,/setFavorite|execDetached|deleteFile|killProcess/);
});


test("U8d compact Favorites icon rail keeps each row centered and icons readable",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const begin=pane.indexOf("id: categoryFilterFlow");
  const end=pane.indexOf("id: subfilterScroll");
  assert.ok(begin>=0 && end>begin);
  const main=pane.slice(begin,end);
  assert.match(main,/Math\.min\(40,Math\.max\(30,\(width-\(upperCount-1\)\*4\)\/upperCount\)\)/);
  assert.match(main,/spacing: 4\s+width: rowKeys\.length\*categoryFilterFlow\.tileWidth/);
  assert.match(main,/anchors\.horizontalCenter: parent\.horizontalCenter/);
  assert.match(main,/categoryFilterFlow\.categoryKeys\.slice\(/);
  assert.match(main,/label: Dossier\.mainIcon\(modelData\)/);
  assert.match(main,/modelData==="WEATHER" \|\| modelData==="PLACES"/);
  assert.match(main,/\? 23 : 18/);
  assert.match(main,/Accessible\.name: modelData\+" favorites filter"/);
  assert.match(main,/onLeftClicked: pane\.filterMode=modelData/);
  const width=260,spacing=4,upperCount=6;
  const tile=Math.min(40,Math.max(30,(width-(upperCount-1)*spacing)/upperCount));
  assert.equal(tile,40);
  for(const count of [6,5]) {
    const used=count*tile+(count-1)*spacing;
    assert.ok(used<=width);
    assert.equal((width-used)/2>=0,true);
    if(count===6)assert.equal(used,width);
  }
  assert.match(pane,/selector\.height-categoryFilterFlow\.height-favoritesSearchBar\.height-129/);
  assert.match(pane,/id: subfilterButtons[\s\S]*?label: modelData/);
});

test("U8d inactive filters remain black; only the opened filter is yellow with magenta icon and glow",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const main=pane.slice(pane.indexOf("id: categoryFilterFlow"),
                        pane.indexOf("id: menuFilterPrev"));
  function propertyExpr(name,next) {
    const re=new RegExp("readonly property (?:bool|color) "+name+":([\\s\\S]*?)"+
                       "(?=\\n\\s*readonly property (?:bool|color) "+next+":)");
    const m=main.match(re);
    assert.ok(m,name+" is a QML property");
    return m[1].trim();
  }
  const whiteExpr=propertyExpr("whiteGlyph","iconInk");
  const iconExpr=propertyExpr("iconInk","frameInk");
  const frameExpr=propertyExpr("frameInk","iconGlowInk");
  const glowExpr=main.split("readonly property color iconGlowInk:")[1]
     .split("\n\n                            width:")[0].trim();
  const colors={white:"#DCF3FA",cyan:"#55CFCA",magenta:"#C74EC7",
    orange:"#ED981A",yellow:"#F2BE4E"};
  for(const [category,icon,border,glow] of [
    ["ALL","magenta","magenta","magenta"],
    ["GROUP","cyan","cyan","cyan"],
    ["CPU++","white","cyan","cyan"],
    ["APP CTRL","cyan","cyan","cyan"],
    ["WEATHER","orange","orange","orange"],
    ["NOTIFS","white","white","white"],
    ["RADIO","magenta","cyan","magenta"],
    ["HOSPITAL","white","magenta","magenta"],
    ["CLOCK","white","white","white"],
    ["PLACES","yellow","yellow","yellow"],
    ["NEW","cyan","cyan","cyan"]
  ]) {
    const ctx=vm.createContext({modelData:category,Colors:colors});
    ctx.whiteGlyph=vm.runInContext(whiteExpr,ctx);
    ctx.iconInk=vm.runInContext(iconExpr,ctx);
    ctx.frameInk=vm.runInContext(frameExpr,ctx);
    ctx.iconGlowInk=vm.runInContext(glowExpr,ctx);
    assert.equal(ctx.iconInk,colors[icon],category+" normal icon");
    assert.equal(ctx.frameInk,colors[border],category+" normal frame");
    assert.equal(ctx.iconGlowInk,colors[glow],category+" normal glow");
  }
  assert.match(main,/idleBorderColor: frameInk/);
  for(const state of ["hover","pressed","keyboardSelected"])
    assert.match(main,new RegExp(state+
      "BorderColor:\\s*filterOpen \\? Colors\\.magenta : frameInk"));
  assert.match(main,/selectedBorderColor: Colors\.magenta/);
  assert.match(main,/selected: filterOpen/);
  assert.match(main,/readonly property bool filterOpen:\s*pane\.filterMode===modelData/);
  assert.match(main,/idleFillColor: Colors\.black/);
  for(const state of ["hover","pressed","keyboardSelected"])
    assert.match(main,new RegExp(state+
      "FillColor:\\s*filterOpen \\? Colors\\.yellow : Colors\\.black"));
  assert.match(main,/selectedFillColor: Colors\.yellow/);
  assert.match(main,/selectedForegroundColor: Colors\.magenta/);
  assert.match(main,/selectedContentGlowColor: Colors\.magenta/);
  assert.match(main,/selectedSoftGlowColor: Colors\.magenta/);
  assert.match(main,/hoverForegroundColor:\s*filterOpen \? Colors\.magenta : iconInk/);
  assert.match(main,/keyboardSelectedForegroundColor:\s*filterOpen \? Colors\.magenta : iconInk/);
  assert.match(main,/contentGlowPressedOpacity: 0\.68/);
  assert.match(main,/softGlowSelectedOpacity: 0\.72/);
});

test("U8d network indicator distinguishes live HTTPS evidence, failure, no link and unknown",()=>{
  const Policy={};
  load("services/favorites/FavoritesInternetStatusPolicy.js",Policy);
  const now=1000000;
  const base={localLinkAvailable:true,linkKnownDown:false,
    lastSampleMs:now-120000,reachability:"reachable"};
  assert.deepEqual(plain(Policy.plan(base,now)),{code:"online",label:"ONLINE"});
  assert.deepEqual(plain(Policy.plan({...base,reachability:"impaired"},now)),
    {code:"limited",label:"LIMITED"});
  assert.deepEqual(plain(Policy.plan({
    ...base,localLinkAvailable:false,linkKnownDown:true
  },now)),{code:"offline",label:"NO LINK"});
  assert.deepEqual(plain(Policy.plan({
    ...base,localLinkAvailable:false,linkKnownDown:false
  },now)),{code:"checking",label:"CHECKING"});
  assert.deepEqual(plain(Policy.plan({...base,lastSampleMs:now-420001},now)),
    {code:"checking",label:"CHECKING"});
  assert.deepEqual(plain(Policy.plan({...base,lastSampleMs:now+10},now)),
    {code:"checking",label:"CHECKING"});
  assert.deepEqual(plain(Policy.plan({...base,lastSampleMs:0},now)),
    {code:"checking",label:"CHECKING"});
  assert.deepEqual(plain(Policy.plan({...base,reachability:""},now)),
    {code:"checking",label:"CHECKING"});
  assert.deepEqual(plain(Policy.plan(null,now)),
    {code:"checking",label:"CHECKING"});
});

test("U8d network badge reuses the existing Network dock; header red X stays clear of divider",()=>{
  const net=read("modules/Network.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  const shell=read("shell.qml");
  const producer=read("services/notifications/NetworkInternetHealthNotificationProducer.qml");
  assert.match(net,/readonly property var internetHealthSnapshot:/);
  assert.match(net,/networkInternetHealthProducer\.localLinkAvailable/);
  assert.match(net,/networkInternetHealthProducer\.reachabilityState/);
  assert.match(net,/networkLinkProducer\.linkState/);
  assert.match(shell,/internetHealthObservation: sharedNetworkDock\.internetHealthSnapshot/);
  assert.match(cpu,/InternetStatusPolicy\.plan\(internetHealthObservation,internetStatusClockMs\)/);
  assert.match(cpu,/interval: 60000\s+repeat: true\s+running: cpuPlusWindow\.menuOpen/);
  assert.match(cpu,/if \(menuOpen\)\s*internetStatusClockMs=Date\.now\(\)/);
  assert.match(cpu,/id: cpuPlusInternetIndicator/);
  assert.match(cpu,/text: "LIVE \/\/ NET \/\/ "\+cpuPlusWindow\.internetStatus\.label/);
  assert.match(cpu,/internetStatus\.code==="online" \? Colors\.omnitrix/);
  assert.match(cpu,/internetStatus\.code==="offline" \? Colors\.red/);
  assert.match(cpu,/internetStatus\.code==="limited" \? Colors\.orange : Colors\.cyan/);
  assert.match(cpu,/id: cpuPlusCloseButton[\s\S]*?text: "×"/);
  assert.match(cpu,/id: cpuPlusCloseButton[\s\S]*?color: Colors\.black/);
  assert.match(cpu,/id: cpuPlusCloseMouse[\s\S]*?onClicked: cpuPlusWindow\.close\(\)/);
  const header=cpu.slice(cpu.indexOf("id: cpuPlusCloseButton"),
                         cpu.indexOf("id: modeButtonRow"));
  assert.match(header,/anchors\.top: cpuPlusCloseButton\.bottom/);
  assert.match(header,/anchors\.topMargin: 3[\s\S]*?height: 2[\s\S]*?color: Colors\.cyan/);
  assert.match(header,/anchors\.verticalCenter: cpuPlusCloseButton\.verticalCenter/);
  assert.match(header,/height: 22[\s\S]*?color: Colors\.black/);
  const dock=net.slice(net.indexOf("readonly property var internetHealthSnapshot"),
    net.indexOf("contentGlowEnabled: false"));
  assert.doesNotMatch(dock,/Process\s*\{|command:|nmcli|https?:\/\//);
  assert.match(producer,/interval: 120000/);
});


test("U9a / U9b LOCATION separates Explore, pinned search/saved, and Home editing",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const left=cpu.split("id: sharedInstrumentPane")[1].split("id: targetPane")[0];
  const middle=cpu.split("id: targetPane")[1].split("id: actuatorPane")[0];
  const right=cpu.split("id: actuatorPane")[1];
  assert.match(left,/id: settingsLocationOverviewPane/);
  assert.match(left,/CpuPlusSettingsLocationOverviewPane \{/);
  assert.match(left,/settingsSubMode === "LOCATION"/);
  assert.match(left,/settingsSubMode === "LOCATION"\)\)\s*&& cpuPlusWindow.selectedModeIndex !== 5/);
  assert.match(middle,/id: settingsLocationSelectionPane/);
  assert.match(middle,/CpuPlusSettingsLocationSelectionPane \{/);
  assert.match(middle,/durationKey: settingsLocationOverviewPane\.durationKey/);
  assert.match(middle,/onHomeCandidateRequested: function\(candidate\)/);
  assert.match(middle,/settingsLocationPane\.fillHomeCandidate\(candidate\)/);
  assert.match(middle,/onExploreCandidateRequested: function\(candidate\)/);
  assert.match(middle,/settingsLocationOverviewPane\.fillExploreCandidate\(candidate\)/);
  assert.match(middle,/anchors\.top: targetSubModeStrip\.bottom/);
  assert.doesNotMatch(middle,/id: settingsCategorySummary/);
  assert.match(right,/id: settingsLocationPane/);
  assert.match(right,/LOCATION \/\/ EDIT HOME/);
  const overview=read("widgets/cpuplus/CpuPlusSettingsLocationOverviewPane.qml");
  const selection=read("widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml");
  const editor=read("widgets/cpuplus/CpuPlusSettingsLocationPane.qml");
  assert.doesNotMatch(overview,/CpuPlusPlaceSearchPanel \{/);
  assert.match(overview,/CpuPlusExploreLocationPanel \{/);
  assert.match(overview,/function fillExploreCandidate\(candidate\)/);
  assert.match(overview,/property alias durationKey: explorePanel\.durationKey/);
  assert.match(overview,/explorePanel\.fillDestination\(candidate\)/);
  assert.match(cpu,/SHARED CONTEXT \/\/ /);
  assert.match(cpu,/PlaceRegistry\.contextKind/);
  assert.match(cpu,/PlaceRegistry\.effectivePlace\.label/);
  assert.match(cpu,/LOCATION \/\/ EXPLORE/);
  assert.match(selection,/CpuPlusPlaceSearchPanel \{/);
  assert.match(selection,/compactPinned: true/);
  assert.match(selection,/onUseForHome: function\(candidate\)/);
  assert.match(selection,/onUseForExplore: function\(candidate\)/);
  assert.match(selection,/CpuPlusSavedPlacesPanel \{/);
  assert.match(selection,/durationKey: locationSelection\.durationKey/);
  assert.match(selection,/registry: locationSelection\.registry/);
  assert.match(editor,/function fillHomeCandidate\(candidate\)/);
  assert.match(editor,/registry\.saveHome\(/);
  assert.doesNotMatch(editor,/CpuPlusPlaceSearchPanel|CpuPlusExploreLocationPanel|CpuPlusSavedPlacesPanel/);
  assert.equal((overview.match(/CpuPlusExploreLocationPanel \{/g)||[]).length,1);
  assert.equal((selection.match(/CpuPlusPlaceSearchPanel \{/g)||[]).length,1);
  assert.equal((selection.match(/CpuPlusSavedPlacesPanel \{/g)||[]).length,1);
  assert.equal((editor.match(/saveHome\(/g)||[]).length,1);
  assert.match(cpu,/settingsLocationOverviewPane\.editingText/);
  assert.match(cpu,/settingsLocationSelectionPane\.editingText/);
  assert.match(cpu,/settingsLocationPane\.editingText/);
});

test("U9a original Home edit fields accept search selection without invoking PlaceRegistry",()=>{
  const editor=read("widgets/cpuplus/CpuPlusSettingsLocationPane.qml");
  const start=editor.indexOf("    function fillHomeCandidate(candidate) {");
  const end=editor.indexOf("    function readableError(code) {",start);
  assert.ok(start>=0 && end>start);
  const calls=[];
  const inputs={
    homeLabelInput:{text:"",mapToItem(){return {y:230};}},
    homeLatitudeInput:{text:""},
    homeLongitudeInput:{text:""}
  };
  const loc={feedback:"",registry:{saveHome(){calls.push("save");return true;}}};
  const scroll={contentHeight:900,height:310,contentY:0};
  const ctx=vm.createContext({...inputs,locationPane:loc,body:{},
    locationScroll:scroll,Qt:{callLater(fn){fn();}}});
  vm.runInContext(editor.slice(start,end),ctx);
  assert.equal(ctx.fillHomeCandidate({label:"Search place",latitude:38.8,
    longitude:-76.8}),true);
  assert.equal(inputs.homeLabelInput.text,"Search place");
  assert.equal(inputs.homeLatitudeInput.text,"38.8");
  assert.equal(inputs.homeLongitudeInput.text,"-76.8");
  assert.match(loc.feedback,/REVIEW THEN SAVE HOME/);
  assert.equal(scroll.contentY,185);
  assert.deepEqual(calls,[]);
  assert.equal(ctx.fillHomeCandidate(null),false);
  assert.deepEqual(calls,[]);
  const overview=read("widgets/cpuplus/CpuPlusSettingsLocationOverviewPane.qml");
  const selection=read("widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml");
  assert.doesNotMatch(overview,/\.saveHome\(|\.removeSavedPlace\(|\.startExplore\(/);
  assert.doesNotMatch(selection,/\.saveHome\(|\.removeSavedPlace\(|\.startExplore\(/);
});

test("U9a close reuses Hospital's exact U+00D7 glyph, frame and red glow on black",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const hospital=read("widgets/HospitalW.qml");
  const git=read("widgets/GitW.qml");
  const close=cpu.slice(cpu.indexOf("id: cpuPlusCloseButton"),
    cpu.indexOf("id: cpuPlusInternetIndicator"));
  assert.match(close,/width: 36\s+height: 30/);
  assert.match(close,/color: Colors\.black/);
  assert.match(close,/border\.width: 1/);
  assert.match(close,/border\.color: cpuPlusCloseMouse\.pressed/);
  assert.match(close,/text: "×"/);
  assert.match(close,/font\.pixelSize: 27/);
  assert.match(close,/color: Colors\.red/);
  assert.match(close,/id: cpuPlusCloseMouse/);
  assert.match(close,/onClicked: cpuPlusWindow\.close\(\)/);
  assert.doesNotMatch(close,/Colors\.yellow|hoverFillColor|pressedFillColor|label: "✕"/);
  assert.match(hospital,/text: "×"/);
  assert.match(git,/text: "×"/);
  assert.match(hospital,/id: hospitalCloseButton[\s\S]*?width: 40[\s\S]*?height: 34/);
  assert.match(cpu,/anchors\.top: cpuPlusCloseButton\.bottom/);
  assert.match(cpu,/anchors\.topMargin: 3[\s\S]*?height: 2[\s\S]*?color: Colors\.cyan/);
  assert.match(cpu,/text: "LIVE \/\/ NET \/\/ "\+cpuPlusWindow\.internetStatus\.label/);
});


test("U9b sticky middle place search scrolls matches but never scrolls its query controls",()=>{
  const middle=read("widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml");
  const search=read("widgets/cpuplus/CpuPlusPlaceSearchPanel.qml");
  assert.match(middle,/id: placeSearchPanel/);
  assert.match(middle,/compactPinned: true/);
  assert.match(middle,/resultsViewportLimit: Math\.max\(50,Math\.min\(108,/);
  assert.match(middle,/height: implicitHeight/);
  assert.match(middle,/anchors\.top: placeSearchPanel\.bottom/);
  assert.match(middle,/id: selectedPlacesScroll/);
  // Stage 1 uses the shared viewport-host geometry rather than duplicate
  // y/height overrides. The saved-places track starts below FIND PLACE.
  assert.match(middle,/geometryHost: selectedPlacesScroll/);
  assert.match(middle,/mountingParent: locationSelection/);
  assert.match(middle,/onUseForHome: function\(candidate\)/);
  assert.match(middle,/onUseForExplore: function\(candidate\)/);
  assert.match(search,/property bool compactPinned: false/);
  assert.match(search,/property int resultsViewportLimit: 108/);
  const parent=search.indexOf("id: searchContent");
  const buttons=search.indexOf("id: runSearchButton",parent);
  const matches=search.indexOf("id: matchesScroll",parent);
  assert.ok(parent>=0 && buttons>parent && matches>buttons);
  assert.match(search,/contentHeight: matchesBody\.implicitHeight/);
  assert.match(search,/searchPanel\.compactPinned[\s\S]*?matchesBody\.implicitHeight/);
  assert.match(search,/visible: searchPanel\.compactPinned && scrollable/);
  assert.match(search,/searchPanel\.useForHome\(resultCard\.modelData\)/);
  assert.match(search,/searchPanel\.useForExplore\(resultCard\.modelData\)/);
  assert.doesNotMatch(search,/registry\.saveHome|registry\.exploreHere|registry\.returnHome/);
  // Both selection signals still only prepare the existing editors.
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(cpu,/onHomeCandidateRequested: function\(candidate\) \{\s*settingsLocationPane\.fillHomeCandidate\(candidate\)/);
  assert.match(cpu,/onExploreCandidateRequested: function\(candidate\) \{\s*settingsLocationOverviewPane\.fillExploreCandidate\(candidate\)/);
});

test("U9b shared context is above Explore, with active location directly below its actions",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const overview=read("widgets/cpuplus/CpuPlusSettingsLocationOverviewPane.qml");
  const explore=read("widgets/cpuplus/CpuPlusExploreLocationPanel.qml");
  const parentHeader=cpu.indexOf('id: sharedInstrumentHeader');
  const shared=cpu.indexOf('"SHARED CONTEXT // "',parentHeader);
  const exploreHeading=cpu.indexOf('"LOCATION // EXPLORE"',shared);
  assert.ok(parentHeader>=0 && shared>parentHeader && exploreHeading>shared);
  assert.match(cpu,/PlaceRegistry\.effectivePlace\.label/);
  assert.match(cpu,/PlaceRegistry\.effectivePlace\.latitude/);
  assert.match(cpu,/PlaceRegistry\.effectivePlace\.longitude/);
  assert.doesNotMatch(overview,/CpuPlusPlaceSearchPanel \{/);
  assert.doesNotMatch(overview,/height: 109/);
  assert.match(overview,/CpuPlusExploreLocationPanel \{/);
  const inputs=explore.indexOf('"DESTINATION NAME"');
  const duration=explore.indexOf('"EXPLORATION DURATION"');
  const exploreAction=explore.indexOf('id: startExploreButton');
  const returnAction=explore.indexOf('id: returnHomeButton');
  const active=explore.indexOf('"ACTIVE // "');
  const feedback=explore.indexOf('text: explorePanel.feedback');
  assert.ok(inputs>=0 && duration>inputs && exploreAction>duration
    && returnAction>exploreAction && active>returnAction && feedback>active);
  assert.match(explore,/explorePanel\.registry\.exploreHere\(/);
  assert.match(explore,/explorePanel\.registry\.returnHome\(\)/);
  assert.match(cpu,/settingsLocationSelectionPane\.editingText/);
});

test("U9b smaller canonical CPU++ close preserves red-on-black and divider clearance",()=>{
  const cpu=read("widgets/CpuPlusW.qml");
  const close=cpu.slice(cpu.indexOf('id: cpuPlusCloseButton'),
    cpu.indexOf('id: cpuPlusInternetIndicator'));
  assert.match(close,/width: 36\s+height: 30/);
  assert.match(close,/text: "×"/);
  assert.match(close,/font\.pixelSize: 27/);
  assert.match(close,/color: Colors\.black/);
  assert.match(close,/border\.color: cpuPlusCloseMouse\.pressed/);
  assert.match(close,/color: Colors\.red/);
  assert.match(close,/onClicked: cpuPlusWindow\.close\(\)/);
  assert.match(cpu,/anchors\.top: cpuPlusCloseButton\.bottom/);
  assert.match(cpu,/text: "LIVE \/\/ NET \/\/ "\+cpuPlusWindow\.internetStatus\.label/);
});


test("U9c search matches safe source names and types with unordered partial tokens",()=>{
  const Search={};
  load("services/favorites/FavoritesSearchPolicy.js",Search);
  const sensor={
    key:"fav1:secret:monitor-watch:private-sensor-secret",
    resourceId:"hidden-device-id",
    category:"CPU++",menu:"THERMAL",
    item:"SENSOR 13",label:"THERMAL // SENSOR 13",
    favoriteType:"METRIC WATCH",provider:"appcontrol",
    kind:"monitor-watch",owner:"appcontrol"
  };
  for(const q of ["thermal sensor","sensor thermal","SENSOR 1",
     "1", "sensor 13 thermal", "THeRm sEnS 1", "monitor thermal 13",
     "watch thermal sensor","cpu thermal sensor"]) {
    assert.equal(Search.matches(sensor,q),true,q);
  }
  for(const q of ["Maryland","sensor 99","cpu disk","unknown label"]) {
    assert.equal(Search.matches(sensor,q),false,q);
  }
  const app={key:"SECRET_ONE",category:"APP CTRL",menu:"APPS",
    label:"App control // Proton Mail",item:"Proton Mail",
    favoriteType:"FAVORITE",owner:"appcontrol"};
  for(const q of ["app CTRL","CTRL app","app, ctrl","control app",
                  "appcontrol mail","mail proton app"]) {
    assert.equal(Search.matches(app,q),true,q);
  }
  assert.equal(Search.matches(app,"one"),false,"private key excluded");
  assert.equal(Search.matches({...app,label:"",item:"",menu:""}, "secret"),false);
  assert.equal(Search.matches(sensor,"private-sensor-secret"),false);
  assert.equal(Search.matches(sensor,"hidden-device-id"),false);
  assert.equal(Search.matches(sensor,""),true);
  assert.equal(Search.matches(sensor,"  "),true);
});

test("U9c search treats Maryland/MD and United States/USA as equivalent place terms",()=>{
  const Search={};
  load("services/favorites/FavoritesSearchPolicy.js",Search);
  const spelled={category:"PLACES",menu:"PLACES",provider:"places",
    label:"Baltimore, Maryland, United States",item:""};
  const abbreviated={category:"PLACES",menu:"PLACES",provider:"places",
    label:"Baltimore, MD, USA",item:""};
  for(const row of [spelled,abbreviated]) {
    for(const q of ["maryland united states","usa md","MD USA",
                     "USA Maryland","United States MD",
                     "states baltimore maryland","md baltimore USA",
                     "balt  usa  md", "USA, MD"]) {
      assert.equal(Search.matches(row,q),true,JSON.stringify([row.label,q]));
    }
    assert.equal(Search.matches(row,"virginia"),false);
  }
  const app={category:"APP CTRL",menu:"APPS",item:"Markdown Editor"};
  assert.equal(Search.matches(app,"maryland"),false,
    "embedded md in another word must not expand to Maryland");
  assert.equal(Search.matches(app,"MD"),false,
    "an abbreviation must not match unrelated words");
  assert.equal(Search.matches({...app,label:"MD Reader"},"MD"),true,
    "a visible exact abbreviation remains searchable");
});

test("U9c filters share yellow fill, magenta border, icon and glow in EVERY selected state",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const top=pane.slice(pane.indexOf("id: categoryFilterFlow"),
     pane.indexOf("id: favoritesSearchBar"));
  const menu=pane.slice(pane.indexOf("id: subfilterButtons"),
     pane.indexOf("id: menuFilterNext"));
  assert.match(top,/selected: filterOpen/);
  assert.match(menu,/selected: filterOpen/);
  for(const region of [top,menu]) {
    assert.match(region,/selectedFillColor: Colors\.yellow/);
    assert.match(region,/selectedBorderColor: Colors\.magenta/);
    assert.match(region,/selectedForegroundColor: Colors\.magenta/);
    assert.match(region,/selectedContentGlowColor: Colors\.magenta/);
    assert.match(region,/selectedSoftGlowColor: Colors\.magenta/);
    assert.match(region,/idleFillColor: Colors\.black/);
    for(const state of ["hover","pressed","keyboardSelected"]) {
      assert.match(region,new RegExp(state+
        "FillColor:\\s*filterOpen \\? Colors\\.yellow : Colors\\.black"));
      assert.match(region,new RegExp(state+
        "BorderColor:\\s*filterOpen \\? Colors\\.magenta : "));
      assert.match(region,new RegExp(state+
        "ForegroundColor:\\s*filterOpen \\? Colors\\.magenta : "));
      assert.match(region,new RegExp(state+
        "ContentGlowColor:\\s*filterOpen \\? Colors\\.magenta : "));
      assert.match(region,new RegExp(state+
        "SoftGlowColor:\\s*filterOpen \\? Colors\\.magenta : "));
    }
  }
  // Inactive main glyphs still preserve module-specific identities.
  assert.match(top,/idleBorderColor: frameInk/);
  assert.match(top,/idleForegroundColor: iconInk/);
  assert.match(top,/idleContentGlowColor: iconGlowInk/);
  assert.match(top,/idleSoftGlowColor: frameInk/);
  assert.match(menu,/onLeftClicked: pane\.menuFilter=modelData/);
  assert.match(top,/onLeftClicked: pane\.filterMode=modelData/);
});

test("U9c middle search is live, source-only and suppresses CPU++ hotkeys when focused",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const cpu=read("widgets/CpuPlusW.qml");
  assert.match(pane,/FavoritesSearchPolicy\.js" as Search/);
  assert.match(pane,/property alias searchQuery: favoritesSearchInput\.text/);
  assert.match(pane,/Search\.matches\(row,pane\.searchQuery\)/);
  assert.match(pane,/id: favoritesSearchBar/);
  assert.match(pane,/id: favoritesSearchInput/);
  assert.match(pane,/maximumLength: 120/);
  assert.match(pane,/SEARCH \/\/ NAME, MENU, PLACE/);
  assert.match(pane,/pane\.filterMode="ALL"/);
  assert.match(pane,/pane\.menuFilter="ALL"/);
  assert.match(pane,/listScroll\.contentY=0/);
  assert.match(pane,/onLeftClicked: favoritesSearchInput\.text=""/);
  assert.match(pane,/area==="selector" && favoritesSearchInput\.activeFocus/);
  assert.match(cpu,/favoritesSelectorPane\.editingText/);
  const searchUI=pane.slice(pane.indexOf("id: favoritesSearchBar"),
    pane.indexOf("id: listScroll"));
  for(const unsafe of ["Process {","execDetached(","setFavorite(",
    "saveHome(","deleteCollection(","openUrl(","resourceId","row.key"])
    assert.equal(searchUI.includes(unsafe),false,unsafe);
  const policy=read("services/favorites/FavoritesSearchPolicy.js");
  assert.match(policy,/var FIELDS=\[/);
  for(const unsafe of ['"key"','"resourceId"','"command"','"url"'])
    assert.equal(policy.includes(unsafe),false,unsafe);
});


test("U9d fuzzy search tolerates spelling and transposition errors but keeps digits exact",()=>{
  const Search={};
  load("services/favorites/FavoritesSearchPolicy.js",Search);
  const sensor={key:"secret-raw-identity-00001",resourceId:"private-calibration",
    category:"CPU++",menu:"THERMAL",label:"Sensor 13",
    item:"Sensor 13",favoriteType:"METRIC WATCH",
    kind:"monitor-watch",sourceName:"APP CONTROL"};
  for(const q of [
    "theraml sensor","snesor thermal","sensro thermal",
    "threm sensro","therml sensor","sensor theraml",
    "wathc sensor", "THERMAL 1", "threm sensr 13"
  ]) {
    assert.equal(Search.matches(sensor,q),true,"misspelling: "+q);
  }
  for(const q of [
    "sensor 12","sensor 99","thermal 2","secret-raw-identity",
    "private-calibration", "wholly unrelated","sensor 14"
  ]) {
    assert.equal(Search.matches(sensor,q),false,"must not match: "+q);
  }
  for(const q of ["1","13","senso","thermal","thermal sensor"])
    assert.equal(Search.matches(sensor,q),true,"original substring: "+q);
  assert.equal(Search.typoBudget("1"),0);
  assert.equal(Search.typoBudget("13"),0);
  assert.equal(Search.typoBudget("MD"),0);
  assert.equal(Search.typoBudget("usa"),0);
  assert.equal(Search.typoBudget("sens"),1);
  assert.equal(Search.typoBudget("thermal"),2);
  assert.equal(Search.typoBudget("sensor13"),0);
  assert.equal(Search.withinEdits("sensro","sensor",1),true);
  assert.equal(Search.withinEdits("sensor","screen",1),false);
  assert.equal(Search.withinEdits("zzzzzzzz","thermal",2),false);
});

test("U9d fuzzy place and AppControl queries preserve aliases and safe display boundaries",()=>{
  const Search={};
  load("services/favorites/FavoritesSearchPolicy.js",Search);
  const place={category:"PLACES",menu:"PLACES",
    label:"Baltimore, Maryland, United States",key:"HIDDENSECRET42",
    provider:"places"};
  const short={category:"PLACES",menu:"PLACES",
    label:"Baltimore, MD, USA",key:"PRIVATE_ID_4",provider:"places"};
  for(const row of [place,short]) {
    for(const q of ["Baltimroe MD USA","Marland United Stats",
                    "maryalnd usa","USA balti", "md state",
                    "USA MD", "United States Maryland"])
      assert.equal(Search.matches(row,q),true,JSON.stringify([row.label,q]));
    for(const q of ["secret42","PRIVATE_ID","Virginia"])
      assert.equal(Search.matches(row,q),false,q);
  }
  const app={category:"APP CTRL",menu:"APPS",
    label:"Proton Mail",item:"Proton Mail",owner:"appcontrol",
    key:"HIDDENSECRET"}
  for(const q of ["app ctrl", "app control", "ctrl app",
                  "appconrtol mail", "protn mail", "mial proton"])
    assert.equal(Search.matches(app,q),true,q);
  assert.equal(Search.matches(app,"hiddensecret"),false);
});

test("U9e Favorites search is left-aligned, vertically centered, magenta with orange caret and red X",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const section=pane.slice(pane.indexOf("id: favoritesSearchBar"),
    pane.indexOf('text: pane.filterMode==="GROUP"',pane.indexOf("id: favoritesSearchBar")));
  const input=section.slice(section.indexOf("TextInput {"),
    section.indexOf("ActionButton {"));
  const clear=section.slice(section.indexOf("id: favoritesSearchClear"));
  assert.match(section,/anchors\.left: favoritesSearchInput\.left/);
  assert.match(section,/anchors\.verticalCenter: parent\.verticalCenter/);
  assert.match(section,/horizontalAlignment: Text\.AlignLeft/);
  assert.match(input,/horizontalAlignment: TextInput\.AlignLeft/);
  assert.match(input,/verticalAlignment: TextInput\.AlignVCenter/);
  assert.match(input,/anchors\.verticalCenter: parent\.verticalCenter/);
  assert.match(input,/height: 22/);
  assert.match(input,/color: Colors\.magenta/);
  assert.match(input,/cursorDelegate: Rectangle \{/);
  assert.match(input,/height: favoritesSearchInput\.font\.pixelSize\+4/);
  assert.match(input,/color: Colors\.orange/);
  assert.match(clear,/label: "×"/);
  assert.match(clear,/accentColor: Colors\.red/);
  assert.match(clear,/destructive: true/);
  for(const state of ["idle","hover","pressed","selected","keyboardSelected"]) {
    assert.match(clear,new RegExp(state+"FillColor: Colors\\.black"));
    assert.match(clear,new RegExp(state+"ForegroundColor: Colors\\.red"));
    assert.match(clear,new RegExp(state+"BorderColor: Colors\\.red"));
    assert.match(clear,new RegExp(state+"ContentGlowColor: Colors\\.red"));
    assert.match(clear,new RegExp(state+"SoftGlowColor: Colors\\.red"));
  }
  assert.match(clear,/onLeftClicked: favoritesSearchInput\.text=""/);
  // This remains a local display search; no new owner capability or process.
  for(const unsafe of ["Process {","execDetached(","saveHome(",
                       "deleteCollection(","openUrl(","resourceId"])
    assert.equal(section.includes(unsafe),false,unsafe);
});


test("U9f middle Favorites rows use selected-over-hover full-row palette and glows",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const from=pane.indexOf("id: favoriteRow");
  const to=pane.indexOf("// One full-row selection target.",from);
  assert.ok(from>=0 && to>from);
  const row=pane.slice(from,to);
  assert.match(row,/readonly property bool isOpen:/);
  assert.match(row,/pane\.selectedResource\.key===modelData\.key/);
  assert.match(row,/readonly property bool isHovered:\s*!isOpen && \(rowHit\.containsMouse \|\| rowHit\.activeFocus\)/);
  assert.match(row,/color: isOpen \|\| isHovered \? Colors\.yellow : Colors\.black/);
  assert.match(row,/border\.color: rowAccent/);
  assert.match(row,/readonly property color rowAccent:\s*isOpen \? Colors\.magenta\s*: isHovered \? Colors\.orange : Colors\.cyan/);
  const colorTokens={magenta:"#C74EC7",orange:"#ED981A",cyan:"#55CFCA",yellow:"#F2BE4E",black:"#1B0623"};
  function evaluate(isSelected,hovered,focused) {
    const o={Colors:colorTokens,modelData:{key:"a"},
      pane:{selectedResource:isSelected?{key:"a"}:{key:"b"}},
      rowHit:{containsMouse:hovered,activeFocus:focused}};
    const extract=(first,last)=>row.split(first)[1].split(last)[0].trim();
    o.isOpen=vm.runInNewContext(extract("readonly property bool isOpen:",
      "readonly property bool isHovered:"),o);
    o.isHovered=vm.runInNewContext(extract("readonly property bool isHovered:",
      "readonly property color rowAccent:"),o);
    o.rowAccent=vm.runInNewContext(extract("readonly property color rowAccent:",
      "\n\n                        color:"),o);
    const fill=vm.runInNewContext(extract("\n                        color:",
      "\n                        border.width:"),o);
    return {isOpen:o.isOpen,isHovered:o.isHovered,accent:o.rowAccent,fill};
  }
  assert.deepEqual(evaluate(false,false,false),
    {isOpen:false,isHovered:false,accent:colorTokens.cyan,fill:colorTokens.black});
  assert.deepEqual(evaluate(false,true,false),
    {isOpen:false,isHovered:true,accent:colorTokens.orange,fill:colorTokens.yellow});
  assert.deepEqual(evaluate(false,false,true),
    {isOpen:false,isHovered:true,accent:colorTokens.orange,fill:colorTokens.yellow});
  assert.deepEqual(evaluate(true,true,true),
    {isOpen:true,isHovered:false,accent:colorTokens.magenta,fill:colorTokens.yellow});
  assert.deepEqual(evaluate(true,false,false),
    {isOpen:true,isHovered:false,accent:colorTokens.magenta,fill:colorTokens.yellow});
  // Both glyph lines receive the selected magenta and hover orange treatment.
  assert.match(row,/color: favoriteRow\.isOpen \? Colors\.magenta\s*: favoriteRow\.isHovered \? Colors\.orange : Colors\.white/);
  assert.match(row,/color: favoriteRow\.isOpen \? Colors\.magenta : Colors\.orange/);
  assert.doesNotMatch(row,/^\s*RectangularShadow \{/m);
  assert.match(row,/color: "transparent"/);
  assert.match(row,/border\.color: favoriteRow\.rowAccent/);
  assert.match(row,/visible: favoriteRow\.isOpen \|\| favoriteRow\.isHovered/);
  assert.equal((row.match(/SafeDropShadow \{/g)||[]).length,2);
  for(const id of ["rowTitle","rowStatus"]) {
    assert.match(row,new RegExp("safeSource: "+id));
  }
  assert.equal((row.match(/requestedVisible: favoriteRow\.isOpen \|\| favoriteRow\.isHovered/g)||[]).length,2);
  assert.match(row,/color: favoriteRow\.rowAccent/);
});

test("U9f middle Favorites row stays selection-only with keyboard and whole-row input",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const row=pane.slice(pane.indexOf("id: favoriteRow"),
                       pane.indexOf("NO SUPPORTED SAVED ITEMS IN THIS FILTER"));
  assert.match(row,/id: rowHit/);
  assert.match(row,/anchors\.fill: parent/);
  assert.match(row,/onClicked: pane\.selectionRequested\(modelData\.key\)/);
  assert.match(row,/Accessible\.onPressAction: pane\.selectionRequested\(modelData\.key\)/);
  assert.match(row,/event\.key===Qt\.Key_Return/);
  assert.match(row,/event\.key===Qt\.Key_Enter/);
  assert.match(row,/event\.key===Qt\.Key_Space/);
  assert.match(row,/onWheel: function\(wheel\) \{ wheel\.accepted=false; \}/);
  assert.doesNotMatch(row,/execDetached|Process \{|setFavorite\(|killProcess\(|deleteCollection\(|saveHome\(/);
});


test("U9g Favorites++ uses Angel-repaired opaque open-only faces, not tinted broad shadows",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const angel=read("widgets/AngelActionButton.qml");
  const top=pane.slice(pane.indexOf("id: categoryFilterFlow"),
                      pane.indexOf("id: favoritesSearchBar"));
  const bottom=pane.slice(pane.indexOf("id: subfilterButtons"),
                         pane.indexOf("id: menuFilterNext",pane.indexOf("id: subfilterButtons")));
  for(const [name,region] of [["top",top],["bottom",bottom]]) {
    assert.match(region,/selected: filterOpen/);
    assert.match(region,/color: filterOpen \? Colors\.yellow : Colors\.black/);
    assert.match(region,/idleFillColor: Colors\.black/);
    assert.match(region,/selectedFillColor: Colors\.yellow/);
    assert.match(region,/softGlowEnabled: false/);
    assert.match(region,/wideGlowEnabled: false/);
    assert.match(region,/contentGlowEnabled: true/);
    assert.match(region,/color: "transparent"/);
    assert.match(region,/border\.color: Colors\.magenta/);
    assert.match(region,/visible: filterOpen/);
    assert.doesNotMatch(region,/softGlowEnabled: true|wideGlowEnabled: true/);
  }
  // The original Angels repair is the explicit precedent, not a new
  // interpretation of the generalized ActionButton state dispatcher.
  assert.match(angel,/color: highlightWhenSelected && selected \? activeFillColor : defaultFillColor/);
  assert.match(angel,/softGlowEnabled: false/);
  assert.match(angel,/wideGlowEnabled: false/);
  assert.match(angel,/contentGlowEnabled: true/);
});

test("U9g middle rows keep hover/open semantics without a broad filled glow",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const row=pane.slice(pane.indexOf("id: favoriteRow"),
                       pane.indexOf("// One full-row selection target."));
  assert.match(row,/readonly property bool isOpen:/);
  assert.match(row,/readonly property bool isHovered:\s*!isOpen &&/);
  assert.match(row,/color: isOpen \|\| isHovered \? Colors\.yellow : Colors\.black/);
  assert.match(row,/border\.color: rowAccent/);
  assert.match(row,/Rectangle \{/);
  assert.match(row,/anchors\.margins: -2/);
  assert.match(row,/color: "transparent"/);
  assert.doesNotMatch(row,/^\s*RectangularShadow \{/m);
  assert.equal((row.match(/SafeDropShadow \{/g)||[]).length,2);
  assert.match(row,/safeSource: rowTitle/);
  assert.match(row,/safeSource: rowStatus/);
  assert.match(row,/requestedVisible: favoriteRow\.isOpen \|\| favoriteRow\.isHovered/);
});

test("U9g native fixture actively hides and reopens the selector before pointer test",()=>{
  const fixture=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  assert.match(pane,/property alias categoryRowRepeater: categoryRowsRepeater/);
  assert.match(pane,/id: categoryRowsRepeater/);
  assert.match(pane,/property alias categoryButtons: categoryIconRepeater/);
  assert.match(pane,/id: categoryIconRepeater/);
  assert.match(fixture,/selector\.visible=false;/);
  assert.match(fixture,/id: paintReopenTimer/);
  assert.match(fixture,/selector\.visible=true;/);
  assert.match(fixture,/idle\.filterOpen \|\| !open\.filterOpen/);
  assert.match(fixture,/idle\.softGlowEnabled \|\| open\.softGlowEnabled/);
  assert.match(fixture,/U9G_REOPEN_PAINT_CHANGED/);
  assert.match(fixture,/U9G_PASS \/\/ REOPEN_IDLE_BLACK_OPEN_YELLOW_NO_FILLED_GLOW/);
  assert.match(fixture,/root\.ready=true/);
  // No event/writer privilege is added by the visual test seam.
  assert.doesNotMatch(pane,/execDetached\(|onClicked:\s*.+deleteCollection/);
});


test("CPU++ stage-1 Favorites++ scroll indicators cover both left lists and middle saved items",()=>{
  const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const filters=[
    ["collectionScroll","collectionScrollTrack","collectionViewportHost","overview"],
    ["dossierScroll","dossierScrollTrack","dossierViewportHost","overview"],
    ["listScroll","listScrollTrack","listViewportHost","selector"]
  ];
  assert.match(pane,/property alias collectionScrollArea: collectionScroll/);
  assert.match(pane,/property alias dossierScrollArea: dossierScroll/);
  assert.match(pane,/property alias listScrollArea: listScroll/);
  assert.match(pane,/property alias collectionScrollIndicator: collectionScrollTrack/);
  assert.match(pane,/property alias dossierScrollIndicator: dossierScrollTrack/);
  assert.match(pane,/property alias listScrollIndicator: listScrollTrack/);
  for(const [viewport,indicator,wrapper,area] of filters) {
    const wrapperStart=pane.indexOf("id: "+wrapper);
    const viewportStart=pane.indexOf("id: "+viewport,wrapperStart);
    const barStart=pane.indexOf("id: "+indicator,viewportStart);
    assert.ok(wrapperStart>=0 && viewportStart>wrapperStart && barStart>viewportStart,
      "the scroll area and rail share a stable Item wrapper: "+viewport);
    assert.match(pane.slice(wrapperStart-42,wrapperStart),/Item \{/);
    const section=pane.slice(barStart,barStart+370);
    assert.match(section,new RegExp("flickable: "+viewport));
    assert.match(section,new RegExp("mountingParent: "+wrapper));
    assert.match(section,new RegExp("geometryHost: "+viewport));
    assert.match(section,/handleStyle: "bar"/);
    assert.match(section,/maximumBarHandleHeight: 42/);
    assert.match(section,new RegExp('pane\\.area==="'+area+'"'));
    assert.match(section,/scrollable/);
  }
  for(const [name,viewport] of [
    ["collectionRows","collectionScroll"],
    ["dossierRows","dossierScroll"],
    ["listRows","listScroll"]
  ]) {
    const section=pane.slice(pane.indexOf("id: "+name),
                             pane.indexOf("id: "+name)+145);
    assert.match(section,new RegExp(
      "width: Math\\.max\\(0,"+viewport+"\\.width-24\\)"));
  }
  assert.equal((pane.match(/NeonScrollBar \{/g)||[]).length,3);
  assert.match(pane,/onClicked: pane\.selectionRequested\(modelData\.key\)/);
  const native=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
  assert.match(native,/CPU_SCROLL_STAGE1_PASS \/\/ 3_BOUNDED_FAVORITES_RAILS/);
  assert.match(native,/bar\.parent!==v\.parent/);
});

test("CPU++ stage-1 Location panes use viewport-bound rounded bars and clear gutters",()=>{
  const panes=[
    ["widgets/cpuplus/CpuPlusSettingsLocationOverviewPane.qml",
     "overviewScroll","locationOverview","locationBody"],
    ["widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml",
     "selectedPlacesScroll","locationSelection","locationBody"],
    ["widgets/cpuplus/CpuPlusSettingsLocationPane.qml",
     "locationScroll","locationPane","body"],
    ["widgets/cpuplus/CpuPlusPlaceSearchPanel.qml",
     "matchesScroll","matchesViewport","resultCard"]
  ];
  for(const [file,scroll,host,body] of panes) {
    const src=read(file);
    const pos=src.indexOf("NeonScrollBar {");
    assert.ok(pos>=0,file);
    const bar=src.slice(pos,src.indexOf("}",pos)+1);
    assert.match(bar,new RegExp("flickable: "+scroll));
    assert.match(bar,new RegExp("mountingParent: "+host));
    assert.match(bar,new RegExp("geometryHost: "+scroll));
    assert.match(bar,/handleStyle: "bar"/);
    assert.match(bar,/maximumBarHandleHeight: 42/);
    assert.match(bar,/visible: .*scrollable/);
    assert.doesNotMatch(bar,/^\s*(?:x:|y:|height:)/m,
      "use shared box geometry rather than manual full-height track: "+file);
    if(file.endsWith("CpuPlusPlaceSearchPanel.qml")) {
      assert.match(src,/width: Math\.max\(0,matchesBody\.width-\(searchPanel\.compactPinned \? 24 : 0\)\)/);
    } else {
      const section=src.slice(src.indexOf("id: "+body),
                              src.indexOf("id: "+body)+200);
      assert.match(section,/-\s*24/);
    }
  }
  const selection=read("widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml");
  assert.match(selection,/anchors\.top: placeSearchPanel\.bottom/);
  assert.match(selection,/id: selectedPlacesScroll/);
  assert.match(selection,/onUseForHome: function\(candidate\)/);
  assert.match(selection,/onUseForExplore: function\(candidate\)/);
  const right=read("widgets/cpuplus/CpuPlusSettingsLocationPane.qml");
  assert.match(right,/registry\.saveHome\(/);
});

test("CPU++ rounded scrollbar cap is opt-in and star migration remains a separate stage",()=>{
  const code=read("components/NeonScrollBar.qml");
  assert.match(code,/property int maximumBarHandleHeight: 0/);
  assert.match(code,/maximumBarHandleHeight > 0/);
  assert.match(code,/Math\.min\(normal, Math\.max\(minimumHandleHeight, maximumBarHandleHeight\)\)/);
  assert.match(code,/function activeHandleExtent\(\)/);
  assert.match(code,/starStyle \? starHandleSize : normalHandleHeight\(\)/);
  const users=[
    "widgets/cpuplus/CpuPlusFavoritesHubPane.qml",
    "widgets/cpuplus/CpuPlusSettingsLocationOverviewPane.qml",
    "widgets/cpuplus/CpuPlusSettingsLocationSelectionPane.qml",
    "widgets/cpuplus/CpuPlusSettingsLocationPane.qml",
    "widgets/cpuplus/CpuPlusPlaceSearchPanel.qml"
  ];
  for(const file of users) {
    const source=read(file);
    assert.match(source,/maximumBarHandleHeight: 42/);
    const segments=source.split("NeonScrollBar {").slice(1);
    for(const segment of segments)
      assert.match(segment.split("}")[0],/handleStyle: "bar"/);
    assert.doesNotMatch(source,/handleStyle: "star"/,
      "no CPU++ shape migration until operator visually approves stage 1");
  }
  const runtime=read("tests/components/test_neon_scrollbar_qt_runtime.py");
  assert.match(runtime,/bounded rounded thumb/);
  assert.match(runtime,/legacy proportional thumb is opt-out/);
});
