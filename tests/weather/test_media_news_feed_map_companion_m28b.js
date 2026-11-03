"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const base=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(base,p),"utf8");
const mediaText=read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const mapText=read("widgets/weather/StationMapCompanionPolicy.js");
const qml=read("widgets/weather/StationDiscovery.qml");
const mediaPane=read("widgets/weather/StationMediaSubjectPane.qml");
const earthPane=read("widgets/weather/StationEarthSubjectPane.qml");
const nav=read("widgets/weather/StationSubjectNavigator.qml");
const newsHub=read("widgets/weather/StationNewsHub.qml");
const media=vm.createContext({Array,Object,Number,String,Math,isFinite});
const map=vm.createContext({Array,Object,Number,String,Math,isFinite});
vm.runInContext(mediaText.replace(/^\.pragma library\s*$/m,""),media);
vm.runInContext(mapText.replace(/^\.pragma library\s*$/m,""),map);
const plain=x=>JSON.parse(JSON.stringify(x));
const fixture=()=>[
 {id:"alpha",latitude:20,longitude:30,title:"EARTH EVENT ALPHA"},
 {id:"beta",latitude:25,longitude:40,title:"EARTH EVENT BETA"},
 {id:"gamma",latitude:-45,longitude:60,title:"EARTH EVENT GAMMA"},
 {id:"delta",latitude:-30,longitude:-55,title:"EARTH EVENT DELTA"},
 {id:"epsilon",latitude:34,longitude:15,title:"EARTH EVENT EPSILON"},
 {id:"invalid",latitude:100,longitude:999,title:"INVALID"}
];

test("MEDIA headline list is primary; analytics are dedicated sibling destinations",()=>{
  for(const route of ["media/news/reports","media/news/filters",
                      "media/news/locations","media/news/viewer"])
    assert.equal(media.newsGroupVisible(route,"list"),true,route);
  for(const route of ["media/news/trends","media/news/stories"])
    assert.equal(media.newsGroupVisible(route,"list"),false,route);
  assert.equal(media.newsGroupVisible("media/news/reports","trend"),false);
  assert.equal(media.newsGroupVisible("media/news/reports","stories"),false);
  assert.equal(media.newsGroupVisible("media/news/trends","trend"),true);
  assert.equal(media.newsGroupVisible("media/news/stories","stories"),true);
  assert.equal(media.newsGroupVisible("","trend"),true,"CLASSIC unchanged during migration");
  assert.equal(media.newsGroupVisible("","stories"),true,"CLASSIC unchanged during migration");
  assert.equal(media.newsGroupVisible("weather/overview","list"),false);
  const feedAt=qml.indexOf('title: "NEWS HEADLINES // CURRENT FILTERED BATCH');
  const analyticsAt=qml.indexOf('title: "REPORTING TREND // CURRENT FILTERED BATCH"');
  const storiesAt=qml.indexOf('title: "STORY FAMILIES // CONSERVATIVE TITLE TOKENS"');
  assert.ok(feedAt>0&&analyticsAt>feedAt&&storiesAt>analyticsAt,
            "headlines must render above analysis");
  assert.match(qml,/REQUEST HELD \/\/ PROVIDER COOLDOWN \/\/ ARTICLES NOT LOADED/);
});

test("NEWS retains original full filtered article rows and click-to-inspect",()=>{
  assert.match(qml,/id: discoveryRecordCard/);
  assert.equal((qml.match(/id: discoveryRecordCard/g)||[]).length,1);
  const feedBlock=qml.split("NEWS HEADLINES // CURRENT FILTERED BATCH")[1]
                    ?.split("REPORTING TREND // CURRENT FILTERED BATCH")[0]||"";
  assert.match(feedBlock,/model: source.ready \? stationDiscovery.visibleRows : \[\]/);
  assert.match(feedBlock,/delegate: discoveryRecordCard/);
  assert.match(qml,/onClicked: stationDiscovery.openRow\(modelData\)/);
  assert.match(qml,/function openRow\(row\)/);
  assert.match(qml,/selectedNews = next;/);
  assert.match(newsHub,/domain: "news"/);
  assert.match(mediaPane,/StationNewsHub\s*\{/);
  assert.match(qml,/DiscoveryPolicy\.filterNewsRows\(/);
  assert.match(qml,/newsGroupVisible\("filters"\)/);
});

test("compact EARTH event tray selects in-view EONET records, prioritizing a selected event",()=>{
  assert.equal(map.FORMAT,"post-apollo.weather.earth-map-companion.m28b.v1");
  const rows=fixture();
  const bounds={valid:true,west:10,east:50,south:10,north:40};
  const preview=plain(map.previewEonet(rows,null,bounds,4));
  assert.deepEqual(preview.map(x=>x.id),["alpha","beta","epsilon"]);
  const selected=plain(map.previewEonet(rows,rows[3],bounds,2));
  assert.deepEqual(selected.map(x=>x.id),["delta","alpha"]);
  assert.deepEqual(plain(map.previewEonet(rows,null,{valid:false},2))
                     .map(x=>x.id),["alpha","beta"]);
  assert.equal(map.validPoint({id:"bad",latitude:95,longitude:3}),false);
  assert.deepEqual(plain(map.previewEonet(rows,null,bounds,0)).map(x=>x.id),["alpha"]);
  assert.deepEqual(plain(map.previewEonet([],null,bounds,4)),[]);
  assert.equal(rows.length,6,"source data must never be mutated");
});

test("EARTH MAPS is compact, EONET source route retains full event list",()=>{
  assert.match(qml,/import "StationMapCompanionPolicy.js" as MapCompanion/);
  assert.match(qml,/earthMapRoute === "earth\/events\/eonet"\s*\? visibleRows/);
  assert.match(qml,/MapCompanion\.previewEonet\(\s*mapPointRows, selectedMapEvent, mapVisibleBounds, 4/);
  assert.match(qml,/model: stationDiscovery.earthLayerEnabled\("eonet"\)\s*&& source.ready\s*\? stationDiscovery.mapCompanionEonetRows/);
  assert.match(qml,/EARTH MAP CONTEXT \/\/ EONET EVENTS IN VIEW/);
  assert.match(qml,/NASA EONET \/\/ FULL EVENT LIST/);
  assert.match(qml,/COMPLETE LIST UNDER EARTH → EVENTS → EONET/);
  assert.match(earthPane,/domain: "map"/);
  assert.match(qml,/StationEventContextCard\s*\{/);
  const replay=qml.match(/delegate: discoveryRecordCard/g)||[];
  assert.equal(replay.length,3,"NEWS, EARTH and CLASSIC share one row renderer");
  const mapStart=qml.indexOf("id: mapCanvasSection");
  const places=qml.indexOf("MAP COMPANION // ARTICLE MENTIONED PLACES");
  const eventList=qml.indexOf("EARTH MAP CONTEXT // EONET EVENTS IN VIEW");
  const retry=qml.indexOf('label: "RETRY NEWS"');
  assert.ok(mapStart < places && places < eventList && eventList < retry,
            "EARTH companion must follow the map and precede unrelated sections");
});

test("EARTH news companion is the selected MEDIA article's known places, not another feed",()=>{
  assert.match(nav,/function showNewsMentionsOnEarth\(payload\)/);
  assert.match(nav,/chooseRoute\("earth\/maps\/overview"\)/);
  assert.match(earthPane,/newsMentionOverlay: earthPane\.newsMentionOverlay/);
  assert.match(qml,/MAP COMPANION \/\/ ARTICLE MENTIONED PLACES/);
  assert.match(qml,/model: stationDiscovery.mapNewsMentionRows\.slice\(0, 5\)/);
  assert.match(qml,/stationDiscovery\.inspectNewsMention\(modelData\)/);
  assert.match(qml,/ARTICLE MENTIONS ONLY \/\/ NOT VERIFIED EVENT LOCATIONS/);
  const selector=qml.split("readonly property string selectedContextSourceId:")[1]
                    ?.split("readonly property var selectedContextRow:")[0]||"";
  assert.ok(!selector.includes("news"),"article mention is not a provider-native event");
  const companion=qml.split("MAP COMPANION // ARTICLE MENTIONED PLACES")[1]
                   ?.split("delegate: discoveryRecordCard")[0]||"";
  for(const forbidden of ["StationDiscoveryService {","GdeltArticleLocationService {",
                          "FileView {","dossierArchiveStore.capture("])
    assert.ok(!companion.includes(forbidden),"no duplicate provider or saver");
});
test.todo("operator Fedora/Sway visual acceptance of NEWS feed-first scroll and EARTH companions");
