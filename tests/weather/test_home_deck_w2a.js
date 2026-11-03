"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const policyText = read("widgets/weather/StationHomeDeckPolicy.js");
const nav = read("widgets/weather/StationSubjectNavigator.qml");
const surface = read("widgets/weather/StationWorkspaceSurface.qml");
const workspace = read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const stationHome = read("widgets/weather/StationHome.qml");
const weatherStation = read("widgets/weather/WeatherStationW.qml");
const env = vm.createContext({Math,Number,String,Array,Object,isFinite});
vm.runInContext(policyText.replace(/^\.pragma library\s*$/m,""),env);
const native = value => JSON.parse(JSON.stringify(value));

test("W2a rotates only the six existing operational HOME panel routes",()=>{
  const routes=native(env.ROTATABLE);
  assert.deepEqual(routes,[
    "home/auto","home/quick","home/snapshot",
    "home/history","home/runtime","home/health"
  ]);
  assert.equal(new Set(routes).size,6);
  for(const r of routes) {
    assert.equal(env.isRotatable(r),true);
    assert.match(workspace,new RegExp(r.replace("/","\\/")));
  }
  for(const p of ["home/overview","home/magick","weather/overview",
                   "earth/overview","home/bad",""]) {
    assert.equal(env.isRotatable(p),false,p);
  }
});

test("favorites use stable source-independent panel routes, not display indices",()=>{
  const dirty=["home/auto","home/auto","earth/overview","home/runtime",null,7];
  assert.deepEqual(native(env.normalizedFavorites(dirty)),["home/auto","home/runtime"]);
  const pinned=native(env.toggleFavorite(dirty,"home/quick"));
  assert.deepEqual(pinned,["home/auto","home/runtime","home/quick"]);
  assert.equal(env.favorite(pinned,"home/quick"),true);
  assert.deepEqual(native(env.toggleFavorite(pinned,"home/auto")),
                   ["home/runtime","home/quick"]);
  assert.deepEqual(native(env.toggleFavorite(pinned,"home/magick")),pinned);
});

test("AUTO is random, MIXED weights favorites, PINNED never escapes its pins",()=>{
  assert.deepEqual(native(env.MODES),["mixed","auto","pinned"]);
  assert.equal(env.nextMode("mixed"),"auto");
  assert.equal(env.nextMode("auto"),"pinned");
  assert.equal(env.nextMode("pinned"),"mixed");
  assert.equal(env.normalizedMode("bad"),"mixed");
  assert.equal(env.nextRoute("home/auto",[],"auto",0),"home/quick");
  assert.equal(env.nextRoute("home/auto",[],"auto",0.999999),"home/health");
  const favorites=["home/history","home/health"];
  assert.equal(env.nextRoute("home/auto",favorites,"mixed",0.30),"home/history");
  assert.equal(env.nextRoute("home/auto",favorites,"pinned",0),"home/history");
  assert.equal(env.nextRoute("home/auto",favorites,"pinned",0.999),"home/health");
  assert.equal(env.nextRoute("home/history",["home/history"],"pinned",0.2),"");
  assert.equal(env.nextRoute("home/auto",[],"pinned",0.8),"");
  for (const sample of [0,0.2,0.6,0.9999,1,NaN,-1]) {
    assert.notEqual(env.nextRoute("home/auto",favorites,"mixed",sample),"home/auto");
    assert.ok(env.isRotatable(env.nextRoute("home/auto",favorites,"mixed",sample)));
  }
});

test("rotation cannot navigate from another subject, a hidden/index view or HOLD",()=>{
  assert.equal(env.mayRotate("home",true,true,false,false),true);
  for(const args of [
    ["weather",true,true,false,false],
    ["home",false,true,false,false],
    ["home",true,false,false,false],
    ["home",true,true,true,false],
    ["home",true,true,false,true],
  ]) assert.equal(env.mayRotate(...args),false,JSON.stringify(args));
});

test("W2a is an opt-in HOME-only control rail with manual NEXT and reading hold",()=>{
  assert.match(surface,/import "StationHomeDeckPolicy.js" as HomeDeck/);
  assert.match(surface,/id: homeDeckBar/);
  assert.match(surface,/visible: surface\.activeFamily === "home"/);
  assert.match(surface,/label: surface\.deckEnabled \? "ROTATE \/\/ ON" : "ROTATE \/\/ OFF"/);
  assert.match(surface,/label: "MODE \/\/ " \+ surface\.deckMode\.toUpperCase\(\)/);
  assert.match(surface,/label: surface\.deckHeld \? "RESUME" : "HOLD"/);
  assert.match(surface,/HomeDeck\.toggleFavorite\(/);
  assert.match(surface,/onClicked: surface\.advanceDeck\(\)/);
  assert.match(surface,/id: deckTimer[\s\S]*?interval: 30000/);
  assert.match(surface,/running: HomeDeck\.mayRotate\(/);
  assert.match(surface,/onTriggered: surface\.advanceDeck\(\)/);
  assert.match(surface,/onCurrentPathChanged:[\s\S]*?deckTimer\.restart\(\)/);
  assert.match(surface,/HomeDeck\.nextRoute\([\s\S]*?Math\.random\(\)/);
  // No hidden duplicate StationHome, no change to the eight existing tabs.
  assert.equal((surface.match(/StationHome\s*\{/g)||[]).length,1);
  assert.match(surface,/model: surface\.activeTabs/);
  assert.match(surface,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
  assert.match(stationHome,/StationHomePolicy\.rankRelevant\(/);
  assert.match(stationHome,/interval: 60000/);
});

test("navigator retains session choices across subject tabs without new disk owners",()=>{
  for(const key of ["homeDeckEnabled","homeDeckHeld","homeDeckMode","homeDeckFavorites"])
    assert.match(nav,new RegExp("property (?:bool|string|var) "+key+":"));
  for(const wiring of [
    "deckEnabled: browser.homeDeckEnabled",
    "deckHeld: browser.homeDeckHeld",
    "deckMode: browser.homeDeckMode",
    "deckFavorites: browser.homeDeckFavorites",
    "deckIndexOpen: browser.indexOpen",
    "browser.homeDeckFavorites = paths",
    "browser.homeDeckEnabled = enabled"
  ]) assert.ok(nav.includes(wiring),wiring);
  assert.match(nav,/active: browser\.visible/);
  assert.match(stationHome,/property string workspaceSection: ""/);
  assert.match(weatherStation,/StationSubjectNavigator\s*\{/);
  for(const source of [surface,nav,policyText]) {
    for(const unsafe of ["FileView {","Process {","XMLHttpRequest",
                         "WeatherServices.","Qt.createQmlObject","swaymsg",
                         "archiveEvent(","dossierArchiveStore.capture("])
      assert.ok(!source.includes(unsafe),"no new owner: "+unsafe);
  }
});

test.todo("persist favorite routes across full Quickshell restarts after storage owner approval");
test.todo("native Fedora/Sway mouse geometry and timer acceptance on the operator host");
