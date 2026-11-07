#!/usr/bin/env node
"use strict";

// M31 verifies the active QML viewport ownership chain and a PURE geometry
// bounds policy. This is not a live compositor/browser acceptance test.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");

const policySource=read("widgets/weather/StationMediaViewportPolicy.js");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const bridge=vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m,""),bridge);

test("pure rectangle guard rejects hidden, malformed, or out-of-host measurements",()=>{
  assert.equal(bridge.FORMAT,"post-apollo.weather.subjects-media-viewport.m31.v1");
  const host=[840,620];
  for(const rect of [
    null, undefined, {}, {x:0,y:0,width:0,height:0},
    {x:-1,y:2,width:20,height:30},
    {x:0,y:-1,width:20,height:30},
    {x:0,y:0,width:-1,height:20},
    {x:0,y:0,width:20,height:0},
    {x:820,y:1,width:21,height:20},
    {x:1,y:601,width:20,height:20},
    {x:Number.NaN,y:0,width:10,height:10},
    {x:0,y:Number.POSITIVE_INFINITY,width:10,height:10},
    {x:0,y:0,width:Number.NaN,height:10},
    {x:1,y:1,width:10,height:Number.NEGATIVE_INFINITY}
  ]) assert.equal(bridge.within(rect,...host),false,JSON.stringify(rect));
  assert.equal(bridge.within({x:0,y:0,width:840,height:620},...host),true);
  assert.equal(bridge.within({x:121.5,y:35.25,width:100,height:90},...host),true);
  assert.equal(bridge.within({x:0,y:0,width:1,height:1},0,620),false);
  assert.equal(bridge.within({x:0,y:0,width:1,height:1},840,NaN),false);
});

test("presentation ownership is singular and never survives terminal takeover or close",()=>{
  for(const indexOpen of [true,false]){
    const expected=indexOpen?"index":"workspace";
    assert.equal(bridge.owner(true,true,false,true,true,indexOpen),expected);
  }
  for(const args of [
    [false,true,false,true,true,false],
    [true,false,false,true,true,false],
    [true,true,true,true,true,false],
    [true,true,false,false,true,false],
    [true,true,false,true,false,false],
    [false,true,false,true,true,true],
    [true,false,false,true,true,true],
    [true,true,true,true,true,true],
    [true,true,false,true,false,true]
  ]) assert.equal(bridge.owner(...args),"none",JSON.stringify(args));
});

test("MEDIA overview reports only nested actual NEWS hub, not a made-up Loader Item property",()=>{
  assert.match(media,/readonly property rect activePlayerViewportRect:/);
  assert.match(media,/mediaPane\.kind === "overview"\s*\?\s*item\.activePlayerViewportRect\s*:\s*item\.playerViewportRect/);
  assert.match(media,/id: overviewNewsHub/);
  assert.match(media,/const bay = overviewNewsHub\.playerViewportRect/);
  assert.match(media,/overviewNewsHub\.mapToItem\(\s*mediaOverview, bay\.x, bay\.y\)/);
  assert.match(media,/item\.mapToItem\(mediaPane, bay\.x, bay\.y\)/);
  assert.match(media,/mediaPane\.kind === "" \|\| mediaPane\.kind === "radio"/);
  assert.match(media,/mediaLoader\.active/);
  assert.match(media,/ViewportPolicy\.within\(mapped, mediaPane\.width, mediaPane\.height\)/);
  assert.equal((media.match(/StationNewsHub\s*\{/g)||[]).length,2,
               "one direct route component plus one nested overview component");
  assert.equal((media.match(/StationRadio\s*\{/g)||[]).length,2);
  assert.match(hub,/readonly property rect playerViewportRect:/);
  assert.match(hub,/if \(!stationOpen \|\| !viewerOpen \|\| !screen\)/);
  assert.match(hub,/onStationOpenChanged: \{ if \(!stationOpen\) closeViewer\(\); \}/);
});

test("ordinary workspace and INDEX cannot publish two overlapping MEDIA players",()=>{
  assert.match(workspace,/property bool subjectWorkspaceActive: true/);
  assert.match(workspace,/id: mediaWorkspacePane/);
  assert.match(workspace,/visible: surface\.activeFamily === "media"\s*&& surface\.subjectWorkspaceActive/);
  assert.match(workspace,/readonly property rect activePlayerViewportRect:/);
  assert.match(workspace,/mediaWorkspacePane\.mapToItem\(surface, bay\.x, bay\.y\)/);
  assert.match(navigator,/subjectWorkspaceActive: !browser\.indexOpen/);
  assert.match(navigator,/id: mediaLivePane/);
  assert.match(navigator,/visible: browser\.visible && browser\.indexOpen\s*&& browser\.liveMediaKind !== ""/);
  assert.match(navigator,/const pane = browser\.indexOpen \? mediaLivePane : workspaceLoader\.item/);
  assert.match(navigator,/pane\.mapToItem\(browser, bay\.x, bay\.y\)/);
  assert.equal((workspace.match(/StationMediaSubjectPane\s*\{/g)||[]).length,1);
  assert.equal((navigator.match(/StationMediaSubjectPane\s*\{/g)||[]).length,1);
});

test("root exports only a bounded chassis-local rect, never native video/input authority",()=>{
  assert.match(station,/readonly property rect activeSubjectPlayerViewportRect:/);
  assert.match(station,/readonly property bool activeSubjectPlayerViewportValid:/);
  assert.match(station,/ViewportPolicy\.owner\(\s*menuOpen, subjectNavigationOpen, contextTerminalRequested,/);
  assert.match(station,/subjectNavigator\.mapToItem\(\s*stationBackground, bay\.x, bay\.y\)/);
  assert.match(station,/ViewportPolicy\.within\(\s*mapped, stationBackground\.width, stationBackground\.height\)/);
  // The viewport remains chassis-local, including after manual resizing.
  assert.match(station,/id: stationBackground\s+width: weatherStation\.frameWidth\s+height: weatherStation\.frameHeight/);
  assert.match(station,/property string chassisLevel: "compact"/);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  for(const source of [media,workspace,navigator,station]) {
    assert.doesNotMatch(source,/^\s*import\s+QtWebEngine\b/m);
    assert.doesNotMatch(source,/\b(?:wl_display_connect|QProcess|posix_spawn)\s*\(/);
    assert.doesNotMatch(source,/Qt\.openUrlExternally\s*\(/);
  }
  assert.ok(!station.includes("newsViewerViewportRect"),
            "retired Classic root geometry must not return");
  assert.ok(!station.includes("weatherContentLoader"));
  assert.ok(!station.includes("WatchBridge {"),
            "native QML plugin deployment remains separately gated");
});
