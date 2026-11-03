"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const navText = read("widgets/weather/StationSubjectNavigator.qml");
const rootText = read("widgets/weather/WeatherStationW.qml");
const surface = read("widgets/weather/StationWorkspaceSurface.qml");
const earth = read("widgets/weather/StationEarthSubjectPane.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const media = read("widgets/weather/StationMediaSubjectPane.qml");
const news = read("widgets/weather/StationNewsHub.qml");
const mapSource = read("widgets/weather/StationMapProjectionPolicy.js");
const routeSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const MapProjection = vm.createContext({Math,Number,String,Array,Object,isFinite});
const Routes = vm.createContext({Math,Number,String,Array,Object});
vm.runInContext(mapSource.replace(/^\.pragma library\s*$/m,""),MapProjection);
vm.runInContext(routeSource.replace(/^\.pragma library\s*$/m,""),Routes);

const start=navText.indexOf("function showNewsMentionsOnEarth(payload) {");
const end=navText.indexOf("function clearNewsMentions()",start);
assert.ok(start>0&&end>start,"handoff function must exist");

function harness(accept=true) {
  const navigations=[];
  const data={MapProjection,Array,Object,JSON,isFinite,
    newsMentionOverlay:null,
    chooseRoute(p){navigations.push(p);return accept;}
  };
  const env=vm.createContext(data);
  vm.runInContext(navText.slice(start,end),env);
  return {env,navigations};
}
const packet=()=>({
  articleTitle:"SYNTHETIC ARTICLE",articleUrl:"https://example.invalid/test",
  articleSource:"TEST",articleTime:"2026-11-03",
  semantics:"MENTIONED LOCATIONS, NOT VERIFIED EVENT LOCATIONS",
  matchMethod:"GDELT GKG",
  locations:[
    {id:"M28A-NEWS",name:"SYNTHETIC PLACE",latitude:20,longitude:30,
     typeLabel:"LOCATION",mentionCount:2,firstOffset:3,featureId:"TEST"},
    {id:"BAD",latitude:120,longitude:30}
  ]
});

test("MEDIA location handoff admits only plottable geo context and routes to EARTH",()=>{
  assert.equal(Routes.findRoute("media/news/locations").subject,"media");
  assert.equal(Routes.findRoute("earth/maps/overview").subject,"earth");
  const h=harness(),payload=packet();
  assert.equal(h.env.showNewsMentionsOnEarth(payload),true);
  assert.deepEqual(h.navigations,["earth/maps/overview"]);
  const saved=JSON.parse(JSON.stringify(h.env.newsMentionOverlay));
  assert.equal(saved.locations.length,1);
  assert.equal(saved.locations[0].id,"M28A-NEWS");
  assert.equal(saved.articleTitle,"SYNTHETIC ARTICLE");
  assert.equal(saved.semantics,"MENTIONED LOCATIONS, NOT VERIFIED EVENT LOCATIONS");
  saved.locations[0].name="CHANGED";
  assert.equal(payload.locations[0].name,"SYNTHETIC PLACE");
  assert.equal(payload.locations.length,2,"source news data must be immutable");
});

test("invalid/empty/no-view packets do not navigate or replace selection",()=>{
  const h=harness(),badPackets=[null,{}, {locations:[]},
    {locations:[{latitude:200,longitude:0}]},
    {locations:[{latitude:null,longitude:""}]}];
  for(const bad of badPackets)
    assert.equal(h.env.showNewsMentionsOnEarth(bad),false);
  assert.deepEqual(h.navigations,[]);
  assert.equal(h.env.newsMentionOverlay,null);
  const rejected=harness(false);
  assert.equal(rejected.env.showNewsMentionsOnEarth(packet()),false);
  assert.equal(rejected.env.newsMentionOverlay,null);
});

test("two MEDIA entry paths terminate in SUBJECTS EARTH without CLASSIC navigation",()=>{
  assert.match(media,/signal newsMapRequested\(var payload\)/);
  assert.match(media,/mediaPane\.newsMapRequested\(payload\)/);
  assert.match(news,/stationNewsHub\.newsMapRequested\(payload\)/);
  const calls=navText.match(/browser\.showNewsMentionsOnEarth\(payload\)/g)||[];
  assert.equal(calls.length,2,"workspace and legacy index MEDIA call same subject handoff");
  assert.ok(!navText.includes("browser.newsMapRequested(payload)"));
  assert.ok(!navText.includes("signal newsMapRequested(var payload)"));
  const subjectBlock=rootText.split("StationSubjectNavigator {")[1]?.split("StationTerminal {")[0];
  assert.ok(subjectBlock);
  assert.ok(!subjectBlock.includes("onNewsMapRequested"),
    "subject-native MEDIA handoff must never call root CLASSIC MAP");
  assert.ok(!subjectBlock.includes('currentView = "map"'));
  assert.match(navText,/chooseRoute\("earth\/maps\/overview"\)/);
});

test("EARTH receives transient overlay, actual map marker and clear action",()=>{
  assert.match(surface,/newsMentionOverlay: surface\.newsMentionOverlay/);
  assert.match(surface,/onNewsMapClearRequested: surface\.newsMapClearRequested\(\)/);
  assert.match(navText,/newsMentionOverlay: browser\.newsMentionOverlay/g);
  assert.match(earth,/newsMentionOverlay: earthPane\.newsMentionOverlay/);
  assert.match(earth,/onNewsMapClearRequested: earthPane\.newsMapClearRequested\(\)/);
  assert.match(discovery,/model: stationDiscovery\.mapNewsMentionRows/);
  assert.match(discovery,/readonly property var mapNewsMentionRows:[\s\S]*?MapProjection\.plottable\(/);
  const mentionsSection=discovery.split("readonly property var mapNewsMentionRows:")[1]?.split("readonly property var mapEarthquakeRows:")[0]||"";
  assert.ok(!mentionsSection.includes("!stationDiscovery.earthMapOnly"));
  assert.match(discovery,/visible: stationDiscovery\.newsMentionInspectorOpen/);
  assert.match(discovery,/onClicked: stationDiscovery\.newsMapClearRequested\(\)/);
  assert.match(discovery,/onClicked: stationDiscovery\.focusNewsMentions\(\)/);
  assert.match(discovery,/MEDIA → EARTH \/\/ GDELT ARTICLE MENTIONS \/\/ NOT VERIFIED EVENT LOCATIONS/);
  assert.match(discovery,/stationDiscovery\.inspectNewsMention\(modelData\)/);
  assert.match(discovery,/function inspectNewsMention\(row\)/);
  assert.match(discovery,/stationDiscovery\.newsMentionOverlay\.semantics/);
});

test("a news mention cannot be treated as a disaster event or auto dossier save",()=>{
  const sourceSelector=discovery.split("readonly property string selectedContextSourceId:")[1]
    ?.split("readonly property var selectedContextRow:")[0] || "";
  assert.ok(sourceSelector.includes("gdacs")&&sourceSelector.includes("usgs"));
  assert.ok(sourceSelector.includes("eonet")&&sourceSelector.includes("firms"));
  assert.ok(!sourceSelector.includes("news"),"GDELT article mention is not an event source");
  for(const file of [navText,surface,earth,media]) {
    for(const forbidden of ["FileView {","Process {","XMLHttpRequest",
                             "dossierArchiveStore.capture(","archiveEvent("])
      assert.ok(!file.includes(forbidden),"no extra writer/collector: "+forbidden);
  }
  assert.match(discovery,/function focusNewsMentions\(\)/);
  assert.match(discovery,/MapProjection\.fitRows\(mapNewsMentionRows, 1\.35\)/);
});

test("index-only EARTH preview cannot compete with the main workspace map",()=>{
  assert.match(navText,/id: earthLivePane[\s\S]*?visible: browser\.visible && browser\.indexOpen\s*&& browser\.liveEarthKind !== ""/);
  assert.match(navText,/id: workspaceLoader[\s\S]*?visible: browser\.visible && !browser\.indexOpen/);
  assert.equal((earth.match(/StationDiscovery\s*\{/g)||[]).length,1);
});
