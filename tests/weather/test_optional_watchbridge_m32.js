#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const catalogSource=read("widgets/weather/StationNewsCatalogPolicy.js");
const catalog=vm.createContext({});
vm.runInContext(catalogSource.replace(/^\.pragma library\s*$/m,""),catalog);
const hub=read("widgets/weather/StationNewsHub.qml");
const pane=read("widgets/weather/StationMediaSubjectPane.qml");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const nav=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const gate=read("widgets/weather/StationWatchBridgeGate.qml");
const adapter=read("widgets/weather/StationWatchNativeAdapter.qml");

test("only canonical BBC and C-SPAN catalog records carry exact native WATCH v2 tokens",()=>{
  assert.equal(catalog.channels.length,18);
  for(const item of catalog.channels){
    const r=catalog.toViewerRecord(item);
    assert.ok(r,item.id);
    assert.equal(r.watchSourceId,["bbc","cspan"].includes(item.id)?item.id:"",item.id);
  }
  assert.equal(catalog.toViewerRecord({id:"bbc",title:"Fake BBC",
    url:"https://bad.example.invalid/watch"}).watchSourceId,"");
  assert.equal(catalog.toViewerRecord({id:"cspan",title:"Fake C-SPAN",
    url:"https://bad.example.invalid"}).watchSourceId,"");
  assert.equal(catalog.toViewerRecord({id:"user-test",title:"User",url:"https://www.bbc.com/news"}).watchSourceId,"");
  assert.equal(catalog.toViewerRecord(null),null);
  assert.equal(catalog.toViewerRecord({id:"bbc",title:"A",url:"file:///etc/passwd"}),null);
  assert.match(catalogSource,/const canonical = find\(item\.id\)/);
  assert.match(catalogSource,/canonical\.url === item\.url/);
});

test("one active NEWS source follows M31 bounded viewport through MEDIA/INDEX/chassis",()=>{
  assert.match(hub,/readonly property string activeWatchSourceId:/);
  assert.match(hub,/playerViewportRect\.width > 0/);
  assert.match(pane,/readonly property string activeWatchSourceId:/);
  assert.match(pane,/mediaLoader\.item\.activeWatchSourceId/);
  assert.match(pane,/mediaPane\.kind === "radio"/);
  assert.match(pane,/overviewNewsHub\.activeWatchSourceId/);
  assert.match(workspace,/readonly property string activeWatchSourceId:/);
  assert.match(workspace,/mediaWorkspacePane\.activeWatchSourceId/);
  assert.match(nav,/const pane = browser\.indexOpen \? mediaLivePane : workspaceLoader\.item/);
  assert.match(nav,/pane\.activeWatchSourceId/);
  assert.match(station,/readonly property string activeSubjectWatchSourceId:/);
  assert.match(station,/if \(!activeSubjectPlayerViewportValid\)/);
  assert.match(station,/subjectNavigator\.activeWatchSourceId/);
  for(const x of [hub,pane,workspace,nav,station]){
    assert.doesNotMatch(x,/Qt\.openUrlExternally\(/);
    assert.doesNotMatch(x,/\b(?:wl_display_connect|posix_spawn)\s*\(/);
  }
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
});

test("ordinary Weather never imports optional native module or enables browser",()=>{
  assert.match(station,/property bool stageDirectorWatchOptIn: false/);
  assert.match(station,/StationWatchBridgeGate\s*\{/);
  assert.match(station,/optIn: weatherStation\.stageDirectorWatchOptIn/);
  assert.match(station,/viewport: weatherStation\.activeSubjectPlayerViewportRect/);
  assert.match(station,/sourceId: weatherStation\.activeSubjectWatchSourceId/);
  assert.match(station,/!weatherStation\.contextTerminalRequested/);
  assert.match(gate,/property bool optIn: false/);
  assert.match(gate,/active: gate\.optIn && gate\.hostOpen/);
  assert.match(gate,/source: active \? Qt\.resolvedUrl\("StationWatchNativeAdapter\.qml"\) : ""/);
  assert.match(gate,/item\.viewport = Qt\.binding\(function\(\) \{ return gate\.viewport; \}\)/);
  assert.match(gate,/item\.sourceId = Qt\.binding\(function\(\) \{ return gate\.sourceId; \}\)/);
  assert.match(gate,/OPTIONAL_MODULE_UNAVAILABLE/);
  assert.doesNotMatch(station+gate,/\bimport PostApollo\.StageDirector/);
  assert.doesNotMatch(station+gate,/\bWatchBridge\s*\{/);
  assert.match(adapter,/^import PostApollo\.StageDirector 1\.0$/m);
  assert.match(adapter,/WatchBridge\s*\{/);
  assert.match(adapter,/enabled: true/);
  assert.match(adapter,/viewport: adapter\.viewport/);
  assert.match(adapter,/onSourceIdChanged:/);
  assert.match(adapter,/nativeWatch\.close\(\)/);
  assert.match(adapter,/requestSent = nativeWatch\.requestWatch\(sourceId\)/);
  assert.match(adapter,/!nativeWatch\.paired/);
  assert.match(adapter,/sourceId !== "bbc" && sourceId !== "cspan"/);
  assert.doesNotMatch(adapter,/\b(?:QProcess|QtWebEngine|Qt\.openUrlExternally|wl_display_connect)\b/);
});

test("WATCH gate survives a plugin-free boot, then tests explicit fake-only opt-in in isolation",()=>{
  const absent=read("tests/weather/fixtures/M32WatchNoModule.qml");
  const opt=read("tests/weather/fixtures/M32WatchWithStub.qml");
  const mock=read("tests/weather/fixtures/M32StageDirectorStub/WatchBridge.qml");
  const script=read("scripts/weather/verify_optional_watchbridge_m32.sh");
  assert.match(absent,/optIn: false/);
  assert.match(opt,/StationMediaSubjectPane\s*\{/);
  assert.match(opt,/Catalog\.find\("bbc"\)/);
  assert.match(opt,/hub\.closeViewer\(\)/);
  assert.match(opt,/Catalog\.find\("aje"\)/);
  assert.match(opt,/media\.subjectRoute = "media\/radio\/full"/);
  assert.match(script,/case_run absent M32WatchNoModule\.qml/);
  assert.match(script,/case_run mock M32WatchWithStub\.qml/);
  assert.match(script,/M32_NATIVE_OPTIONAL_WATCH/);
  assert.match(mock,/function requestWatch\(sourceId\)/);
  assert.match(mock,/function close\(\)/);
  assert.doesNotMatch(mock,/QProcess|QtWebEngine|Qt\.openUrlExternally/);
});
