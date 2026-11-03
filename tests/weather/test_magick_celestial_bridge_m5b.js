"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const pane=read("widgets/weather/StationMagickSubjectPane.qml");
const service=read("services/weather/CelestialVisualService.qml");
const policy=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const m4=read("scripts/weather/celestial_visual_data.py");
const visual=read("widgets/weather/StationMagickCelestialInstrument.qml");
const context=vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),context);

test("MAGICK calculation routes are explicit, other symbolic routes unchanged",()=>{
  const allowed=[
    "magick/astrology/charts",
    "magick/astrology/zodiac",
    "magick/astrology/aspects",
    "magick/astrology/retrogrades"
  ];
  for(const path of allowed) {
    assert.equal(context.visualForRoute(path),true);
    assert.equal(context.isInterpretationImplemented(path),false);
  }
  for(const path of [
    "magick/overview", "magick/divination/tarot",
    "magick/planetary/hours","magick/grimoire/journal","cosmos/overview"
  ]) assert.equal(context.visualForRoute(path),false);
});

test("Weather Station root is sole calculation owner and SUBJECTS only consumes",()=>{
  assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
  assert.match(station,/id: celestialVisualService/);
  assert.match(station,/MagickPanelPolicy\.visualForRoute\(subjectNavigator\.currentPath\)/);
  assert.match(station,/route: subjectNavigator\.currentPath/);
  assert.match(station,/anchorNowMs: weatherStation\.runtimeNowMs/);
  assert.match(station,/celestialSource: celestialVisualService/);
  assert.equal((navigator.match(/WeatherServices\./g)||[]).length,0);
  assert.match(navigator,/property var celestialSource: null/);
  assert.equal((navigator.match(/celestialSource: browser\.celestialSource/g)||[]).length,2);
  assert.match(surface,/property var celestialSource: null/);
  assert.equal((surface.match(/celestialSource: surface\.celestialSource/g)||[]).length,2);
  assert.match(pane,/property var celestialSource: null/);
  assert.match(pane,/sourceComponent: magickPane\.showCelestial/);
  assert.match(pane,/StationMagickCelestialInstrument\s*\{/);
});

test("on-demand Process uses direct argv and explicit local kernel",()=>{
  assert.match(service,/import Quickshell\.Io/);
  assert.match(service,/Quickshell\.env\("POST_APOLLO_CELESTIAL_KERNEL"\)/);
  assert.match(service,/Quickshell\.env\("POST_APOLLO_CELESTIAL_PYTHON"\)/);
  assert.match(service,/property bool active: false/);
  assert.match(service,/function refresh\(\)/);
  assert.match(service,/if \(!active \|\| !configured \|\| currentKey === ""/);
  assert.match(service,/calculation\.command=\[/);
  assert.match(service,/"--query-json", JSON\.stringify\(spec\)/);
  assert.match(service,/calculation\.running=true/);
  assert.match(service,/onStreamFinished: celestial\.accept\(text\)/);
  assert.match(service,/onExited: function\(exitCode, exitStatus\)/);
  assert.match(service,/onCurrentKeyChanged: clearState\(\)/);
  assert.match(service,/if \(!active\) clearState\(\)/);
  assert.match(service,/text\.length > 524288/);
  assert.match(service,/value\.provenance\.ephemeris_sha256/);
  assert.match(service,/failed=true/);
  assert.match(service,/JPL BACKEND UNAVAILABLE/);
  assert.match(m4,/sources\.add_argument\("--query-json"/);
  assert.match(m4,/len\(args\.query_json\) > 4096/);
  assert.match(m4,/json\.loads\(args\.query_json\)/);
  for(const forbidden of [
    "Timer {","FileView {","StdioWriter {","XMLHttpRequest",
    "swaymsg","curl ","Qt.callLater","onActiveChanged: refresh()",
    "Component.onCompleted: refresh()","QProcess"
  ]) assert.ok(!service.includes(forbidden),"prohibited side effect: "+forbidden);
});

test("only explicit CALCULATE click loads, with clear unavailable state",()=>{
  assert.match(pane,/"CALCULATING" : "CALCULATE"/);
  assert.match(pane,/onClicked: magickPane\.celestialSource\.refresh\(\)/);
  assert.match(pane,/magickPane\.celestialSource\.configured/);
  assert.match(pane,/magickPane\.celestialSource\.ready/);
  assert.match(pane,/visualData: magickPane\.celestialSource/);
  assert.match(service,/SET POST_APOLLO_CELESTIAL_KERNEL/);
  assert.match(service,/READY \/\/ SELECT LOAD CALCULATION/);
  assert.match(visual,/AWAITING|graphModel\.reason|NO CALCULATION SOURCE/);
});

test("no duplication of existing COSMOS or CLASSIC ownership",()=>{
  assert.match(pane,/StationSky\s*\{/);
  assert.match(surface,/StationCosmosSubjectPane\s*\{/);
  assert.match(navigator,/StationWorkspaceSurface\s*\{/);
  assert.match(navigator,/StationMagickSubjectPane\s*\{/);
  for(const part of [pane,policy,surface]) {
    for(const forbidden of ["Process {","FileView {","XMLHttpRequest","swaymsg"])
      assert.equal(part.includes(forbidden),false,"unexpected source in view: "+forbidden);
  }
});
