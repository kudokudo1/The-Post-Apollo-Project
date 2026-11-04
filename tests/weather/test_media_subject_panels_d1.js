"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = x => fs.readFileSync(path.join(root,x),"utf8");
const navSrc = read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySrc = read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const pane = read("widgets/weather/StationMediaSubjectPane.qml");
const hub = read("widgets/weather/StationNewsHub.qml");
const radio = read("widgets/weather/StationRadio.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const browser = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const catalog = read("widgets/weather/StationNewsCatalogPolicy.js");
const nav = vm.createContext({});
const policy = vm.createContext({});
vm.runInContext(navSrc.replace(/^\.pragma library\s*$/m,""),nav);
vm.runInContext(policySrc.replace(/^\.pragma library\s*$/m,""),policy);
const asArray = x => JSON.parse(JSON.stringify(x));

test("17 original MEDIA destinations plus two exact CLASSIC full-page routes are canonical", () => {
  assert.equal(policy.FORMAT,"post-apollo.weather.media-panels.d1.v1");
  const rows=Object.keys(policy.ROUTES);
  assert.equal(rows.length,19);
  assert.equal(new Set(rows).size,19);
  assert.equal(rows.filter(x=>x!=="media/news/full" && x!=="media/radio/full").length,17);
  const kinds={overview:0,news:0,catalog:0,radio:0};
  for(const route of rows) {
    const found=nav.findRoute(route);
    assert.ok(found,route);
    assert.equal(found.subject,"media",route);
    const kind=policy.kindForRoute(route);
    assert.ok(kind in kinds,route+" "+kind);
    kinds[kind]++;
  }
  assert.deepEqual(kinds,{overview:1,news:7,catalog:7,radio:4});
  for(const p of ["media","media/news","media/radio","media/watch","media/creators",
                    "weather/overview","cosmos/overview","earth/overview","magick/astrology/charts"])
    assert.equal(policy.kindForRoute(p),"",p);
});

test("NEWS routes share GDELT, one report loader, local filters, trend and story analysis", () => {
  for(const part of ["reports","filters","trends","stories","locations","viewer"]) {
    const route="media/news/"+part;
    assert.equal(policy.kindForRoute(route),"news");
    assert.equal(policy.catalogSectionFor(route),"REPORTS");
    assert.equal(policy.newsGroupVisible(route,"header"),true);
    assert.equal(policy.newsGroupVisible(route,"request"),true);
    assert.equal(policy.newsGroupVisible(route,"filters"),true);
    assert.equal(policy.newsGroupVisible(route,"list"),
      ["reports","filters","locations","viewer"].includes(part));
  }
  assert.equal(policy.newsGroupVisible("media/news/reports","trend"),false);
  assert.equal(policy.newsGroupVisible("media/news/reports","stories"),false);
  assert.equal(policy.newsGroupVisible("media/news/trends","trend"),true);
  assert.equal(policy.newsGroupVisible("media/news/trends","stories"),false);
  assert.equal(policy.newsGroupVisible("media/news/stories","stories"),true);
  assert.equal(policy.newsGroupVisible("media/news/stories","trend"),false);
  assert.equal(policy.newsGroupVisible("media/news/locations","inspector-hint"),true);
  assert.match(policy.hintFor("media/news/locations"),/MENTIONS, NOT VERIFIED EVENT SITES/);
  assert.equal(policy.newsGroupVisible("weather/conditions/current","list"),false);
  assert.match(hub,/MediaPanelPolicy\.kindForRoute\(subjectRoute\) === "news"/);
  assert.match(hub,/section === "REPORTS"/);
  assert.match(hub,/StationDiscovery\s*\{/);
  assert.match(hub,/newsSubjectRoute: stationNewsHub\.subjectRoute/);
  assert.match(discovery,/property string newsSubjectRoute: ""/);
  assert.match(discovery,/newsGroupVisible\("filters"\)/);
  assert.match(discovery,/newsGroupVisible\("trend"\)/);
  assert.match(discovery,/newsGroupVisible\("stories"\)/);
  assert.match(discovery,/newsGroupVisible\("inspector-hint"\)/);
  assert.match(discovery,/title: "REPORTING TREND \/\/ CURRENT FILTERED BATCH"/);
  assert.match(discovery,/STORY FAMILIES \/\/ CONSERVATIVE TITLE TOKENS/);
  assert.match(discovery,/id: newsTimeRail/);
  assert.match(discovery,/id: newsRegionRail/);
  assert.match(discovery,/StationViewerPolicy|ViewerPolicy/);
});

test("WATCH catalog sections preserve real access notes and in-station attempted viewer", () => {
  const map={
    "media/watch/live":"LIVE","media/watch/congress":"CONGRESS",
    "media/watch/reports":"REPORTS","media/watch/compare":"COMPARE",
    "media/watch/satire":"SATIRE"
  };
  for(const [route,section] of Object.entries(map)) {
    assert.equal(policy.kindForRoute(route),"catalog");
    assert.equal(policy.catalogSectionFor(route),section);
  }
  assert.match(hub,/Catalog\.itemsFor\(effectiveSection\)/);
  assert.match(hub,/onClicked: stationNewsHub\.chooseItem\(modelData\)/);
  assert.match(hub,/StationChannelScreen\s*\{/);
  assert.match(hub,/label: "WATCH IN STATION"/);
  assert.match(hub,/label: "MUTE: ON"/);
  assert.match(hub,/available: false/);
  assert.match(hub,/VIDEO ENGINE TEMPORARILY DISABLED/);
  assert.match(catalog,/EMBED UNVERIFIED/);
  assert.match(catalog,/SUBSCRIPTION \/ TV LOGIN/);
  assert.equal(policy.kindForRoute("media/watch/not-real"),"");
});

test("CREATORS routes reuse one saved channel store and explicit upload request", () => {
  for(const p of ["media/creators/saved","media/creators/uploads"]) {
    assert.equal(policy.kindForRoute(p),"catalog");
    assert.equal(policy.catalogSectionFor(p),"CREATORS");
  }
  assert.match(policy.hintFor("media/creators/uploads"),/EXPLICIT REQUEST/);
  assert.match(hub,/weather-news-creators\.json/);
  assert.match(hub,/onClicked: stationNewsHub\.saveCreator\(\)/);
  assert.match(hub,/onClicked: stationNewsHub\.checkUploads\(modelData\)/);
  assert.match(hub,/creatorFeedProcess\.running = true/);
  assert.match(hub,/station_youtube_feed\.py/);
  assert.match(hub,/creatorFeedRows/);
});

test("RADIO presents directory, favorites and transport without a duplicate MPD owner", () => {
  for(const part of ["directory","saved","transport"])
    assert.equal(policy.kindForRoute("media/radio/"+part),"radio");
  assert.equal(policy.radioGroupVisible("media/radio/directory","directory"),true);
  assert.equal(policy.radioGroupVisible("media/radio/directory","saved"),false);
  assert.equal(policy.radioGroupVisible("media/radio/saved","saved"),true);
  assert.equal(policy.radioGroupVisible("media/radio/saved","directory"),false);
  assert.equal(policy.radioGroupVisible("media/radio/transport","transport"),true);
  assert.equal(policy.radioGroupVisible("media/radio/transport","saved"),true);
  assert.equal(policy.radioGroupVisible("media/radio/transport","directory"),false);
  assert.equal(policy.radioGroupVisible("media/watch/live","transport"),false);
  assert.match(radio,/MediaServices\.HeadlessMediaController\s*\{/);
  assert.match(radio,/radioClient: "weather-radio"/);
  assert.match(radio,/weather-radio-memory\.json/);
  assert.match(radio,/property string subjectRoute: ""/);
  assert.match(radio,/function sectionVisible\(group\)/);
  assert.equal((radio.match(/stationRadio\.sectionVisible\("([^"]+)"\)/g)||[]).length,21);
  assert.match(radio,/sectionVisible\("directory"\)/);
  assert.match(radio,/label: "PLAY"/);
  assert.match(radio,/label: "PAUSE"/);
  assert.match(radio,/label: "STOP"/);
  assert.match(radio,/NO AUTOPLAY/);
  assert.equal(policy.radioGroupVisible("","search"),true,"CLASSIC");
});

test("MEDIA overview has one NEWS and one RADIO bay while WATCH remains nearby", () => {
  assert.equal(policy.kindForRoute("media/overview"),"overview");
  assert.match(pane,/id: reportsBay/);
  assert.match(pane,/height: Math\.max\(0,\(mediaOverview\.height - 8\) \/ 2\)/);
  assert.match(pane,/anchors\.top: reportsBay\.bottom/);
  assert.equal((pane.match(/StationNewsHub\s*\{/g)||[]).length,2);
  assert.equal((pane.match(/StationRadio\s*\{/g)||[]).length,2);
  assert.match(pane,/subjectRoute: "media\/news\/reports"/);
  assert.match(pane,/subjectRoute: "media\/overview"/);
  assert.match(pane,/active: mediaPane\.visible && mediaPane\.kind !== ""/);
  assert.match(pane,/mediaPane\.kind === "radio"/);
  assert.match(pane,/onNewsMapRequested: function\(payload\)/);
});

test("CLASSIC MEDIA behavior and NEWS-to-MAP handoff remain available", () => {
  assert.equal(policy.newsGroupVisible("","trend"),true);
  assert.equal(policy.newsGroupVisible("","stories"),true);
  assert.equal(policy.newsGroupVisible("","filters"),true);
  assert.equal(policy.radioGroupVisible("","saved"),true);
  assert.match(hub,/property string section: "LIVE"/);
  assert.match(hub,/subjectRoute === "" \|\| MediaPanelPolicy\.isFullNews\(subjectRoute\)/);
  assert.match(hub,/usesOriginalChannelTabs\s*\? section/);
  assert.match(hub,/stationNewsHub\.usesOriginalChannelTabs \? 33 : 0/);
  assert.match(hub,/path: Quickshell\.dataDir \+ "\/weather-news-creators\.json"/);
  assert.match(radio,/property bool stationOpen: true/);
  assert.match(browser,/StationWeatherSubjectPane\s*\{/);
  assert.match(browser,/StationCosmosSubjectPane\s*\{/);
  assert.match(browser,/StationEarthSubjectPane\s*\{/);
  assert.match(browser,/StationMediaSubjectPane\s*\{/);
  assert.match(browser,/visible: browser\.visible && browser\.liveMediaKind !== ""/);
  assert.ok(!station.includes("weatherContentLoader"));
  assert.match(browser,/function showNewsMentionsOnEarth\(payload\)/);
  assert.match(browser,/newsMentionOverlay = incoming/);
  assert.match(browser,/chooseRoute\("earth\/maps\/overview"\)/);
  assert.ok(!station.includes("switchToClassic"));
  assert.ok(!station.includes("openLegacyFromSubject"));
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(station,/subjectNavigator\.indexOpen/);
});

test("MEDIA routing never claims a new feed, media server or durable store", () => {
  for(const token of ["FileView {","Process {","XMLHttpRequest",
    "WeatherServices.","MediaServices.","writeAdapter()","saveCreator()",
    "openUrl(","curl ","swaymsg"])
    assert.ok(!pane.includes(token),"unexpected side effect in MEDIA pane "+token);
  for(const token of ["FileView {","Process {","XMLHttpRequest","MediaServices.",
    "writeAdapter()","fetch(","curl ","swaymsg"])
    assert.ok(!policySrc.includes(token),"unexpected side effect in route policy "+token);
  assert.match(hub,/onStationOpenChanged: \{ if \(!stationOpen\) closeViewer\(\); \}/);
});
