"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root,name),"utf8");

const modePane = read("widgets/weather/StationCosmosModesPane.qml");
const solarPane = read("widgets/weather/StationCosmosSunInstrumentPane.qml");
const space = read("widgets/weather/StationSpace.qml");
const cosmosSource = read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const cosmos = vm.createContext({});
vm.runInContext(cosmosSource.replace(/^\.pragma library\s*$/m,""),cosmos);

test("C5c uses the single original NOAA collector and does not create an independent one",()=>{
  for(const [route,section,source] of [
    ["cosmos/sun/suvi","suvi",null],
    ["cosmos/sun/xray","xray","xray"],
    ["cosmos/sun/flares","flares","flares"],
    ["cosmos/sun/cycle","cycle","cycle"]
  ]) {
    assert.equal(cosmos.kindForRoute(route),"space");
    assert.equal(cosmos.visibleFor("space",route,section),true);
    if(source) assert.equal(cosmos.needsSource(route,source),true);
  }
  assert.match(space,/property bool sourceOnly: false/);
  assert.match(space,/readonly property var xrayObservation: xrayService/);
  assert.match(space,/readonly property var flareObservation: flareService/);
  assert.match(space,/readonly property var cycleObservation: solarCycleService/);
  assert.match(space,/id: spaceScroll\s*visible: !space\.sourceOnly/);
  assert.match(space,/source: space\.sourceOnly \? "" : space\.solarImageUrl/);
  assert.match(modePane,/id: spaceSourceLoader/);
  assert.match(modePane,/active: cosmosModePane\.visible && cosmosModePane\.kind === "solar-section"/);
  assert.match(modePane,/sourceOnly: true/);
  assert.match(modePane,/id: solarDetails\s*StationCosmosSunInstrumentPane\s*\{/);
  assert.match(modePane,/sourceSpace: cosmosModePane\.spaceFeed/);
  assert.doesNotMatch(modePane,/id: solarDetails\s*StationSpace\s*\{/);
  for(const src of [modePane,solarPane]) {
    for(const unsafe of ["WeatherServices.","Process {","FileView {",
      "XMLHttpRequest","new WebSocket","Timer {","curl","swaymsg"]) {
      assert.equal(src.includes(unsafe),false,unsafe);
    }
    assert.doesNotMatch(src,/\bid:\s*console\b/);
  }
});

test("C5c SUN presents exactly one fixed, readable source-backed instrument",()=>{
  for(const component of ["suviMode","xrayMode","flareMode","cycleMode"]) {
    assert.ok(solarPane.includes("id: "+component),component);
  }
  for(const sourceField of [
    "solarImageUrl","selectSolarImageMode","refreshSolarImage",
    "solarImageLastLoadedMs","solarImageError","fluxLong","fluxShort",
    "classEquivalent.label","sampleUtc","sampleFresh","trend",
    "count24h","cPlus24h","events","predictedSsn","predictedFlux","peakMonth"
  ]) {
    assert.ok(solarPane.includes(sourceField),sourceField);
  }
  assert.match(solarPane,/source: solarFocus\.sourceSpace/);
  assert.match(solarPane,/cache: false/);
  assert.match(solarPane,/asynchronous: true/);
  assert.match(solarPane,/fillMode: Image\.PreserveAspectFit/);
  assert.match(solarPane,/NOAA PREDICTION \/\/ NOT LIVE SOLAR FLUX/);
  assert.match(solarPane,/EVENT PEAKS, NOT ALERTS/);
  assert.doesNotMatch(solarPane,/Flickable\s*\{|ScrollView\s*\{/);
  assert.doesNotMatch(solarPane,/StationSpace\s*\{/);
  assert.match(solarPane,/anchors\.fill: parent/);
  assert.ok(solarPane.includes("width:Math.max(1,(cycleGrid.width-7)/2)"));
});
