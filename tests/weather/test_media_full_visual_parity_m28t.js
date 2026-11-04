"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policySrc=read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const navSrc=read("widgets/weather/StationSubjectNavigationPolicy.js");
const tabsSrc=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const pane=read("widgets/weather/StationMediaSubjectPane.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const radio=read("widgets/weather/StationRadio.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const catalogSrc=read("widgets/weather/StationNewsCatalogPolicy.js");
const mapTest=read("tests/weather/test_map_full_visual_parity_m28s.js");
function parse(s) {const o=vm.createContext({});vm.runInContext(s.replace(/^\.pragma library\s*$/m,""),o);return o;}
const policy=parse(policySrc),nav=parse(navSrc),tabs=parse(tabsSrc),catalog=parse(catalogSrc);
const FULL_NEWS="media/news/full", FULL_RADIO="media/radio/full";
const originalNewsGroups=["header","request","status","filters","list","trend","stories","inspector-hint"];
const originalRadioGroups=["header","source","search","directory","saved","transport","status"];

test("M28-T adds exactly two complete native routes without losing the 17 original MEDIA destinations",()=>{
  const names=Object.keys(policy.ROUTES);
  assert.equal(names.length,19);
  assert.equal(names.filter(x=>x!==FULL_NEWS && x!==FULL_RADIO).length,17);
  assert.equal(new Set(names).size,19);
  for(const [route,kind,group] of [
    [FULL_NEWS,"news","NEWS // ALL ORIGINAL TABS AND REPORTS"],
    [FULL_RADIO,"radio","RADIO // ALL ORIGINAL CONTROLS"]
  ]){
    assert.equal(policy.kindForRoute(route),kind);
    const node=nav.findRoute(route);
    assert.ok(node && node.subject==="media" && !node.group);
    assert.equal(node.label,group);
  }
  assert.equal(policy.isFullNews(FULL_NEWS),true);
  assert.equal(policy.isFullRadio(FULL_RADIO),true);
  for(const x of ["media/news/reports","media/watch/live","media/creators/saved","media/overview",
                  "media/radio/directory",null,"media/news/fake",{}]){
    assert.equal(policy.isFullNews(x),false);
    assert.equal(policy.isFullRadio(x),false);
  }
  assert.equal(Object.keys(nav.PANELS).length,103);
  assert.equal(nav.PANELS["news-story-families"],"media/news/stories");
  assert.equal(nav.PANELS["radio-favorites-recent"],"media/radio/saved");
});

test("MEDIA bottom NEWS // ALL and RADIO // ALL are actual clickable modes, old five families unchanged",()=>{
  const modes=JSON.parse(JSON.stringify(tabs.tabsFor("media/overview")));
  assert.equal(modes.length,5);
  assert.deepEqual(modes.map(x=>x.key),["overview","news","watch","radio","creators"]);
  const n=modes.find(x=>x.key==="news"),r=modes.find(x=>x.key==="radio");
  assert.deepEqual(n,{label:"NEWS // ALL",path:FULL_NEWS,key:"news"});
  assert.deepEqual(r,{label:"RADIO // ALL",path:FULL_RADIO,key:"radio"});
  assert.equal(tabs.selectedGroup(FULL_NEWS),"news");
  assert.equal(tabs.selectedGroup(FULL_RADIO),"radio");
  assert.equal(tabs.familyFor(FULL_NEWS),"media");
  assert.equal(tabs.familyFor(FULL_RADIO),"media");
  assert.equal(nav.findRoute("media/news/reports").group,false);
  assert.equal(nav.findRoute("media/radio/directory").group,false);
});

test("NEWS // ALL exposes all original six channel tabs and the entire GDELT report/inspector visualization",()=>{
  assert.deepEqual(JSON.parse(JSON.stringify(catalog.sections)),
    ["LIVE","CONGRESS","REPORTS","COMPARE","CREATORS","SATIRE"]);
  for(const group of originalNewsGroups){
    assert.equal(policy.newsGroupVisible(FULL_NEWS,group),true,
      "original full report section: "+group);
    assert.equal(policy.newsGroupVisible("",group),true,"CLASSIC baseline "+group);
  }
  assert.equal(policy.newsGroupVisible("media/news/reports","trend"),false,
    "focused NEWS routes remain selective");
  assert.equal(policy.newsGroupVisible("media/news/stories","stories"),true);
  assert.equal(policy.newsGroupVisible("media/watch/live","list"),false);
  assert.equal(policy.newsGroupVisible("media/news/not-valid","list"),false);
  assert.match(news,/readonly property bool usesOriginalChannelTabs:/);
  assert.match(news,/subjectRoute === "" \|\| MediaPanelPolicy\.isFullNews\(subjectRoute\)/);
  assert.match(news,/readonly property string effectiveSection: usesOriginalChannelTabs\s*\? section/);
  assert.match(news,/readonly property bool isReports: usesOriginalChannelTabs\s*\? section === "REPORTS"/);
  assert.match(news,/height: stationNewsHub\.usesOriginalChannelTabs \? 33 : 0/);
  assert.match(news,/visible: stationNewsHub\.usesOriginalChannelTabs\s*&& !stationNewsHub\.viewerOpen/);
  assert.match(news,/model: Catalog\.sections/);
  assert.match(news,/stationNewsHub\.section = modelData;/);
  assert.match(news,/StationDiscovery\s*\{/);
  assert.match(news,/newsSubjectRoute: stationNewsHub\.subjectRoute/);
  for(const g of ["filters","list","trend","stories","inspector-hint"])
    assert.ok(discovery.includes('stationDiscovery.newsGroupVisible("'+g+'")'),
      "original report graphic/inspector group "+g);
  for(const token of ["REPORTING TREND // CURRENT FILTERED BATCH",
                      "STORY FAMILIES // CONSERVATIVE TITLE TOKENS",
                      "id: newsTopicRail","id: newsTimeRail","id: newsRegionRail"])
    assert.ok(discovery.includes(token),"report visualization missing: "+token);
});

test("RADIO // ALL restores all seven original sections, search, saved stations, recent history and transport",()=>{
  for(const g of originalRadioGroups){
    assert.equal(policy.radioGroupVisible(FULL_RADIO,g),true,
      "original RADIO section "+g);
    assert.equal(policy.radioGroupVisible("",g),true,
      "CLASSIC original section "+g);
  }
  assert.equal(policy.radioGroupVisible("media/radio/directory","saved"),false);
  assert.equal(policy.radioGroupVisible("media/radio/saved","directory"),false);
  assert.equal(policy.radioGroupVisible("media/radio/transport","transport"),true);
  assert.equal(policy.radioGroupVisible("media/watch/live","transport"),false);
  assert.equal(policy.radioGroupVisible("media/radio/unknown","search"),false);
  for(const g of originalRadioGroups)
    assert.ok(radio.includes('stationRadio.sectionVisible("'+g+'")'),
      "original RADIO view missing "+g);
  for(const x of ["favoriteItems","recentItems","weather-radio-memory.json",
                  'radioClient: "weather-radio"',"MediaServices.HeadlessMediaController {",
                  "onClicked: stationRadio.loadSelection()",
                  'onClicked: stationRadio.playbackAction("play")',
                  'onClicked: stationRadio.playbackAction("pause")',
                  'onClicked: stationRadio.playbackAction("stop")',
                  "NeonScrollBar {","id: radioScroll","NO AUTOPLAY"])
    assert.ok(radio.includes(x),"original RADIO source/control "+x);
  assert.match(radio,/running: stationRadio\.stationOpen\s*&& stationRadio\.visible && !stationRadio\.initialSearchSent\s*&& stationRadio\.sectionVisible\("directory"\)/);
});

test("native MEDIA uses same original NEWS/RADIO components and preserves safe-mode video",()=>{
  assert.equal((pane.match(/StationNewsHub\s*\{/g)||[]).length,2,
    "one direct original NEWS + one existing overview bay");
  assert.equal((pane.match(/StationRadio\s*\{/g)||[]).length,2,
    "one direct original RADIO + one existing overview bay");
  assert.match(pane,/sourceComponent: mediaPane\.kind === "overview"/);
  assert.match(pane,/\? radioComponent\s*:\s*newsComponent/);
  assert.match(pane,/active: mediaPane\.visible && mediaPane\.kind !== ""/);
  assert.match(pane,/subjectRoute: mediaPane\.subjectRoute/);
  assert.match(pane,/onNewsMapRequested: function\(payload\)/);
  assert.match(news,/onNewsMapRequested: function\(payload\)/);
  assert.match(news,/StationChannelScreen\s*\{/);
  assert.match(news,/VIDEO ENGINE TEMPORARILY DISABLED/);
  assert.match(news,/available: false/);
  for(const src of [policySrc,tabsSrc]){
    for(const x of ["Process {","FileView {","MediaServices.","WeatherServices.",
                    "XMLHttpRequest","swaymsg","curl ","writeAdapter()"])
      assert.equal(src.includes(x),false,"unexpected source owner in navigation metadata: "+x);
  }
  assert.match(mapTest,/EARTH bottom MAP/,"M28-S full MAP regression carried forward in this milestone");
});
