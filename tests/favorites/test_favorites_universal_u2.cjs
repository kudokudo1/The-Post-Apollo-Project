"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const context={};
vm.runInNewContext(read("services/favorites/FavoritesResourcePolicy.js")
    .replace(/^\.pragma library\s*$/m,""),context);
const projection={};
vm.runInNewContext(read("services/favorites/FavoritesCatalogPolicy.js")
    .replace(/^\.pragma library\s*$/m,""),projection);
const copy=x=>JSON.parse(JSON.stringify(x));
function item(provider,kind,id,capabilities=["favorite"]) {
  const input={provider,kind,resourceId:id,capabilities};
  const normalized=context.normalize(input);
  assert.equal(normalized.ok,true);
  return normalized.record;
}
function group(id,items,state="ready",invalidCount=0) {
  return {id,label:id,items,state,invalidCount};
}

test("U2 catalog merges independent legacy projections without acting on them",()=>{
  const res=projection.build([
    group("time",[item("time","timezone","UTC")]),
    group("places",[item("places","saved-place","7")]),
    group("appcontrol",[item("appcontrol","item","run|private-command")],"unknown")
  ]);
  assert.equal(res.ok,true);
  assert.equal(res.total,3);
  assert.deepEqual(copy(res.groups.map(x=>x.count)),[1,1,1]);
  assert.deepEqual(copy(res.rows.map(x=>x.provider)),["time","places","appcontrol"]);
  assert.equal(res.rows[2].label,"APP CONTROL FAVORITE");
  assert.equal(JSON.stringify(res.rows).includes("private-command"),false);
  assert.equal(JSON.stringify(res.rows).includes("resourceId"),false);
  assert.equal(JSON.stringify(res.rows).includes("fav1:local:"),false);
  assert.equal(res.rows.every(x=>x.availability==="unresolved"),true);
});

test("source states are not liveness claims and unsupported states stay explicit",()=>{
  const res=projection.build([
    group("time",[item("time","timezone","UTC")],"saving"),
    group("places",[],"unsupported"),
    group("appcontrol",[],"unknown")
  ]);
  assert.deepEqual(copy(res.groups.map(x=>x.state)),["saving","unsupported","unknown"]);
  assert.equal(res.rows[0].availability,"unresolved");
  assert.equal(projection.validState("online"),"unknown");
});

test("duplicate identities are counted once and not silently trusted",()=>{
  const same=item("time","timezone","UTC");
  const res=projection.build([group("time",[same,same],"ready")]);
  assert.equal(res.total,1);
  assert.equal(res.duplicateCount,1);
  assert.equal(res.groups[0].duplicateCount,1);
});

test("malformed rows are ignored while unrelated groups remain visible",()=>{
  const res=projection.build([
    group("time",[{},item("time","timezone","UTC")],"ready",2),
    group("places",[item("places","saved-place","4")],"error",1)
  ]);
  assert.equal(res.ok,true);
  assert.equal(res.total,2);
  assert.equal(res.invalidCount,4);
  assert.equal(res.rows.length,2);
  assert.equal(projection.build({}).ok,false);
  assert.equal(projection.build([{id:"time",items:null}]).ok,false);
});

test("display cap is bounded while full per-source totals remain visible",()=>{
  const many=Array.from({length:120},(_,i)=>
    item("time","timezone","Etc/GMT"+i));
  const res=projection.build([group("time",many)]);
  assert.equal(res.total,120);
  assert.equal(res.shown,projection.MAX_ROWS);
  assert.equal(res.groups[0].count,120);
});

test("AppControl process/monitor/preferred actions cannot reveal identifiers",()=>{
  const rows=[
    item("appcontrol","item","file:/sensitive/path"),
    item("appcontrol","task-watch","taskmetric|secret|mem",["watch"]),
    item("appcontrol","monitor-watch","watchbox|thermal|a",["watch"]),
    item("appcontrol","preferred-action","app|sensitive|launch",
      ["preferred-action"])
  ];
  const res=projection.build([group("appcontrol",rows,"unknown")]);
  assert.deepEqual(copy(res.rows.map(x=>x.label)),[
    "APP CONTROL FAVORITE","TASK METRIC WATCH",
    "MONITOR WATCH","PREFERRED ACTION"
  ]);
  const rendered=JSON.stringify(res.rows);
  for(const sensitive of ["sensitive","secret","launch","/path","file:"])
    assert.equal(rendered.includes(sensitive),false);
});

test("U2 provider object must be injected, never creates a second writer",()=>{
  const source=read("services/favorites/FavoritesUnifiedCatalog.qml");
  assert.match(source,/property var appControlSource: null/);
  assert.match(source,/property var worldSource: null/);
  assert.match(source,/property var placesSource: null/);
  assert.match(source,/Adapters\.appControl\(/);
  assert.match(source,/Adapters\.worldClock\(/);
  assert.match(source,/Adapters\.places\(/);
  assert.match(source,/CatalogPolicy\.build\(groups\)/);
  assert.doesNotMatch(source,/FileView\s*\{|writeAdapter|setText|execDetached|Process\s*\{/);
  assert.match(read("services/favorites/qmldir"),
               /FavoritesUnifiedCatalog 1\.0 FavoritesUnifiedCatalog\.qml/);
});

test("Clock UI pilot is opt-in read-only and preserves owner star semantics",()=>{
  const clock=read("widgets/TimeW.qml");
  assert.match(clock,/import qs\.services\.favorites/);
  assert.match(clock,/import qs\.services\.location/);
  assert.match(clock,/appControlSource: FavoritesStore/);
  assert.match(clock,/worldSource: TimeSettings/);
  assert.match(clock,/placesSource: PlaceRegistry/);
  assert.match(clock,/id: unifiedFavoritesButton/);
  assert.match(clock,/label: timew\.universalFavoritesOpen[\s\S]*?"CLOSE ALL" : "ALL FAVS"/);
  assert.match(clock,/FavoritesUnifiedPreview\s*\{/);
  assert.match(clock,/snapshot: unifiedFavoritesCatalog\.snapshot/);
  assert.match(clock,/onLeftClicked: TimeSettings\.toggleWorldFavorite\(/);
  assert.match(clock,/model: TimeSettings\.worldFavoriteZones/);
  assert.match(clock,/universalFavoritesOpen = false/);
  const preview=read("components/FavoritesUnifiedPreview.qml");
  assert.match(preview,/FAVORITES\+\+ \/\/ READ ONLY/);
  assert.match(preview,/SAVED IDENTITY ≠ LIVE RESOURCE \/\/ NO ACTIONS/);
  assert.doesNotMatch(preview,/onClicked: .*exec|toggleFavorite|setFavorite|Process\s*\{/);
  assert.match(read("components/qmldir"),
               /FavoritesUnifiedPreview 1\.0 FavoritesUnifiedPreview\.qml/);
});

test("legacy disk writers remain separate and no global store is introduced",()=>{
  const all=["services/favorites/FavoritesCatalogPolicy.js",
             "services/favorites/FavoritesUnifiedCatalog.qml",
             "components/FavoritesUnifiedPreview.qml"].map(read).join("\n");
  assert.doesNotMatch(all,/appcontrol-favorites\.json|weather-home-favorites-v1\.json|time-world-favorites-v1\.json|places-v1\.json/);
  assert.doesNotMatch(all,/writeAdapter\(|onSaved:|execDetached|sendSignal|kill -TERM/);
  assert.match(read("services/favorites/FavoritesStore.qml"),
               /appcontrol-favorites\.json/);
  assert.match(read("services/time/TimeSettings.qml"),
               /time-world-favorites-v1\.json/);
  assert.match(read("services/location/PlaceRegistry.qml"),
               /places-v1\.json/);
});
