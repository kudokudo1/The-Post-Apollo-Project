"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const nav=read("widgets/weather/StationSubjectNavigationPolicy.js");
const preview=read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const mediaPolicy=read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const catalogPolicy=read("widgets/weather/StationNewsCatalogPolicy.js");
const pane=read("widgets/weather/StationMediaSubjectPane.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const viewer=read("widgets/weather/StationChannelScreen.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const env=vm.createContext({}),media=vm.createContext({}),catalog=vm.createContext({});
vm.runInContext(nav.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(mediaPolicy.replace(/^\.pragma library\s*$/m,""),media);
vm.runInContext(catalogPolicy.replace(/^\.pragma library\s*$/m,""),catalog);
const plain=x=>JSON.parse(JSON.stringify(x));

const reviewed=[
  ["news-live","media/watch/live","LIVE"],
  ["news-congress","media/watch/congress","CONGRESS"],
  ["news-reports-catalog","media/watch/reports","REPORTS"],
  ["news-compare","media/watch/compare","COMPARE"],
  ["news-satire","media/watch/satire","SATIRE"],
  ["news-creators","media/creators/saved","CREATORS"],
  ["news-uploads","media/creators/uploads","CREATORS"]
];

test("exact M28-J original WATCH catalogue and CREATORS controls have real MEDIA routes",()=>{
  const ids=Object.keys(env.WIRED_IN_SUBJECTS)
    .filter(id=>env.WIRED_IN_SUBJECTS[id]==="M28-J").sort();
  assert.deepEqual(ids,reviewed.map(row=>row[0]).sort());
  assert.equal(reviewed.length,7);
  for(const [id,route,section] of reviewed){
    assert.equal(env.PANELS[id],route,id+" original semantic owner");
    const leaf=env.findRoute(route);
    assert.ok(leaf && leaf.subject==="media" && !leaf.group,id+" actual leaf");
    assert.equal(media.kindForRoute(route),"catalog");
    assert.equal(media.catalogSectionFor(route),section,id+" original section");
    assert.ok(catalog.sections.includes(section),section);
  }
  assert.equal(Object.keys(env.PANELS).length,103);
  assert.equal(Object.values(env.WIRED_IN_SUBJECTS).filter(m=>m==="M28-J").length,7,
    "M28-J seven native media controls remain exact");
  assert.ok(Object.keys(env.WIRED_IN_SUBJECTS).length>=96,
    "later independently reviewed HOME controls may increase the total");
  assert.deepEqual(plain(env.remainingSourcePagesForPath("media",env.PANELS)),[]);
  assert.deepEqual(plain(env.sourcePagesForPath("media/watch",env.PANELS).map(x=>x.id)),["news"],
    "original M1 SOURCE lineage remains intact");
  assert.deepEqual(plain(env.nativeDestinationsForPath("media/watch",env.PANELS).map(x=>x.path)),
    ["media/watch/compare","media/watch/congress","media/watch/live",
     "media/watch/reports","media/watch/satire"]);
  assert.deepEqual(plain(env.nativeDestinationsForPath("media/creators",env.PANELS).map(x=>x.path)),
    ["media/creators/saved","media/creators/uploads"]);
});

test("five WATCH sections are real publisher catalogue destinations with access notes",()=>{
  for(const section of ["LIVE","CONGRESS","REPORTS","COMPARE","SATIRE"]){
    const rows=plain(catalog.itemsFor(section));
    assert.ok(rows.length>0,section+" populated");
    for(const item of rows){
      assert.ok(item.title && item.access && item.detail && /^https:\/\//.test(item.url));
      assert.ok(catalog.toViewerRecord(item),item.id);
    }
  }
  assert.ok(catalog.itemsFor("LIVE").some(item=>item.id==="aje"));
  assert.ok(catalog.itemsFor("CONGRESS").some(item=>item.id==="cspan"));
  assert.ok(catalog.itemsFor("COMPARE").some(item=>item.id==="allsides"));
  assert.ok(catalog.itemsFor("SATIRE").some(item=>item.id==="theonion"));
  assert.match(hub,/Catalog\.itemsFor\(effectiveSection\)/);
  assert.match(hub,/onClicked: stationNewsHub\.chooseItem\(modelData\)/);
  assert.match(hub,/label: "WATCH IN STATION"/);
  assert.match(hub,/text: "CATALOG DESTINATIONS \/\/ VIDEO SAFE MODE"/);
  assert.match(hub,/VIDEO ENGINE TEMPORARILY DISABLED/);
  assert.match(pane,/StationNewsHub\s*\{/);
  assert.match(pane,/subjectRoute: mediaPane\.subjectRoute/);
});

test("saved CREATORS and explicit recent uploads use the original one active NEWS hub",()=>{
  assert.match(hub,/weather-news-creators\.json/);
  for(const fn of ["saveCreator","removeCreator","checkUploads"])
    assert.ok(hub.includes("function "+fn+"("),fn);
  assert.match(hub,/onClicked: stationNewsHub\.saveCreator\(\)/);
  assert.match(hub,/onClicked: stationNewsHub\.removeCreator\(modelData\.channelId\)/);
  assert.match(hub,/onClicked: stationNewsHub\.checkUploads\(modelData\)/);
  assert.match(hub,/stationNewsHub\.creatorFeedRows = result\.rows\.slice\(0, 15\)/);
  assert.match(hub,/station_youtube_feed\.py/);
  assert.match(hub,/stationNewsHub\.inflightCreatorId/);
  assert.match(hub,/REQUESTING UPLOADS \/\/ NO AUTOPLAY/);
  assert.match(pane,/active: mediaPane\.visible && mediaPane\.kind !== ""/);
  assert.match(pane,/mediaPane\.kind === "radio"/);
  assert.match(hub,/FileView\s*\{/);
  assert.equal(media.kindForRoute("media/creators/uploads"),"catalog");
  assert.equal(media.catalogSectionFor("media/creators/uploads"),"CREATORS");
  assert.match(media.hintFor("media/creators/uploads"),/EXPLICIT REQUEST/);
  assert.equal(catalog.safeChannelId("https://www.youtube.com/watch?v=invalid"),"");
});

test("same safe in-station viewer opens and closes, but embedded video playback remains explicitly blocked",()=>{
  assert.match(hub,/function chooseItem\(item\)/);
  assert.match(hub,/chosenRecord = Catalog\.toViewerRecord\(item\)/);
  assert.match(hub,/viewerOpen = true/);
  assert.match(hub,/function closeViewer\(\)/);
  assert.match(hub,/viewerOpen = false/);
  assert.match(hub,/StationChannelScreen\s*\{/);
  assert.match(viewer,/readonly property bool playbackAvailable: false/);
  assert.match(viewer,/WEBENGINE DISABLED \/\/ QUICKSHELL CRASH PROTECTION/);
  assert.match(viewer,/DESTINATION REGISTERED \/\/ EXTERNAL VIEWER NOT CONNECTED/);
  assert.match(viewer,/BLOCKED_VIEWPORT_UNAVAILABLE/);
  assert.match(viewer,/NO WebEngine object or dynamic Loader/);
  assert.match(viewer,/onClicked: channelScreen\.closeRequested\(\)/);
  assert.match(viewer,/available: channelScreen\.playbackAvailable/);
  assert.doesNotMatch(viewer,/^\s*import\s+QtWebEngine\b/m,
    "no in-process WebEngine import");
  assert.match(media.hintFor("media/watch/live"),/EMBEDDING ARE NOT CERTIFIED/);
});

test("catalogue transfer does not create duplicate NEWS writer, web renderer or terminal owner",()=>{
  assert.match(pane,/sourceComponent: mediaPane\.kind === "overview"/);
  assert.match(pane,/sourceComponent: mediaPane\.kind === "overview"[\s\S]*?mediaPane\.kind === "radio"/);
  assert.match(pane,/subjectRoute: mediaPane\.subjectRoute/);
  assert.equal((pane.match(/StationNewsHub\s*\{/g)||[]).length,2,
    "one active route hub, plus separate overview definition");
  assert.equal((pane.match(/StationRadio\s*\{/g)||[]).length,2);
  for(const forbidden of ["FileView {","Process {","XMLHttpRequest","StationTerminal {"])
    assert.ok(!pane.includes(forbidden),"no source/controller duplication "+forbidden);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.match(navigator,/onClicked: browser\.chooseRoute\(modelData\.path\)/);
  assert.match(navigator,/model: browser\.classicSources/);
});

test("M28-J seven catalog controls remain exact after HOME is separately reviewed",()=>{
  assert.equal(Object.values(env.WIRED_IN_SUBJECTS)
    .filter(milestone=>milestone==="M28-J").length,7,
    "M28-J retains all five WATCH and two creator controls");
  const expected=["ground-source","map-source-rack","station-source-badge"];
  const pending=Object.keys(env.PANELS).filter(id=>!env.WIRED_IN_SUBJECTS[id]).sort();
  assert.deepEqual(pending,expected.sort());
  assert.ok(env.remainingSourcePagesForPath("tools/sources/health",env.PANELS).length>0);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("weather",env.PANELS)),[],
    "M28-K original HOME controls belong to the native HOME workspace");
  assert.deepEqual(plain(env.nativeDestinationsForPath("../media",env.PANELS)),[]);
});
