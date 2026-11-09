"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const header=read("widgets/weather/StationMediaHeader.qml");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const radio=read("widgets/weather/StationRadio.qml");
const saved=read("widgets/weather/StationRadioSavedStrips.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const services=read("widgets/weather/StationMediaServicesPane.qml");

test("M2 RADIO contextual rail delegates exact preset search to the one mounted controller",()=>{
    assert.match(header,/activeMode === "radio" \? radioPresets/);
    assert.match(header,/mediaHeader\.radioPresetRequested\(index\)/);
    assert.match(header,/NEWS FIRST/);
    assert.match(header,/property bool radioCanOperate: false/);
    assert.match(media,/radioPresets: mediaPane\.loadedRadio \? mediaPane\.loadedRadio\.presets : \[\]/);
    assert.match(media,/onRadioPresetRequested: function\(index\)/);
    assert.match(media,/loadedRadio\.searchPreset\(index\)/);
    assert.match(radio,/queryInput\.text = presets\[index\]\.query;/);
    assert.match(radio,/search\(queryInput\.text, null\)/);
    assert.match(radio,/embeddedHeader: false/);
    assert.match(radio,/!stationRadio\.embeddedHeader/);
    assert.match(radio,/onClicked: stationRadio\.searchPreset\(index\)/);
    assert.match(header,/objectName: "media-m1-c44-divider"/);
    assert.match(header,/anchors\.top: modeRail\.bottom/);
});

test("M2 NEWS contextual section buttons live in C44; internal channel rail is suppressed only when embedded",()=>{
    assert.match(header,/activeMode === "news" \? Catalog\.sections/);
    assert.match(header,/mediaHeader\.newsSectionRequested\(modelData\)/);
    assert.match(media,/loadedNews\.selectSection\(section\)/);
    assert.match(media,/mediaPane\.routeRequested\("media\/news\/full"\)/);
    assert.match(news,/function selectSection\(nextSection\)/);
    assert.match(news,/Catalog\.sections\.indexOf\(nextSection\)/);
    assert.match(news,/stationNewsHub\.section = nextSection/);
    assert.match(news,/height: stationNewsHub\.usesOriginalChannelTabs && !stationNewsHub\.embeddedHeader \? 33 : 0/);
    assert.match(news,/visible: stationNewsHub\.usesOriginalChannelTabs\s*&& !stationNewsHub\.embeddedHeader/);
    assert.match(news,/StationDiscovery\s*\{/);
    assert.match(news,/domain: "news"/);
});

test("M2 MEDIA overview/watch/creators keep global nav; SERVICES uses its own header modes",()=>{
    assert.match(header,/subjectRoute\.indexOf\("media\/creators\/"\) === 0 \? "creators"/);
    assert.match(header,/activeMode === "services" \? servicesSections/);
    assert.match(header,/mediaHeader\.servicesModeRequested\(modelData\.id\)/);
    assert.match(media,/loadedServices\.viewMode=mode/);
    assert.match(media,/StationMediaServicesPane \{ embeddedHeader: true \}/);
    assert.match(services,/property bool embeddedHeader: false/);
    assert.match(services,/visible: !services\.embeddedHeader/);
    for(const x of ["OVERVIEW","NEWS","WATCH","RADIO","CREATORS","SERVICES"])
        assert.ok(header.includes('label:"'+x+'"'));
    assert.match(media,/onRouteRequested: function\(path\)/);
});

test("M2 favorite and recent rows are fixed under search, ten squares across and independently horizontally scrollable",()=>{
    assert.match(radio,/StationRadioSavedStrips\s*\{/);
    assert.match(radio,/anchors\.top: fixedSearch\.bottom/);
    assert.match(radio,/anchors\.top: savedStrips\.bottom/);
    assert.match(radio,/anchors\.bottom: fixedTransport\.top/);
    assert.match(radio,/favoriteItems: stationRadio\.favoriteItems/);
    assert.match(radio,/recentItems: stationRadio\.recentItems/);
    assert.match(radio,/stationRadio\.recallSaved\(item\)/);
    assert.match(radio,/stationRadio\.removeFavorite\(item\)/);
    assert.doesNotMatch(radio,/SAVED \/\/ FAVORITES \+ RECENTLY LOADED/);
    assert.match(saved,/objectName: "media-m2-radio-saved-strips"/);
    assert.match(saved,/\(width - 9\*gap\)\/10/);
    assert.match(saved,/model: strips\.favoriteItems/);
    assert.match(saved,/model: strips\.recentItems/);
    assert.match(saved,/flickableDirection: Flickable\.HorizontalFlick/g);
    assert.match(saved,/contentWidth: Math\.max\(width,/g);
    assert.match(saved,/border\.color: Colors\.magenta/);
    assert.match(saved,/border\.color: Colors\.orange/);
    assert.match(saved,/onClicked: strips\.recallRequested\(modelData\)/);
    assert.match(saved,/onClicked: strips\.removeRequested\(modelData\)/);
    assert.doesNotMatch(saved,/HeadlessMediaController|FileView|XMLHttpRequest|Process\s*\{/);
});

test("M2 preserves bounded RADIO footer, station directory scroll and existing MPD ownership",()=>{
    assert.match(radio,/objectName: "media-m1-radio-directory-scroll"/);
    assert.match(radio,/objectName: "media-m1-radio-transport-fixed"/);
    for(const s of ['"SELECT"','"LOAD"','"ENTER"','"PLAY"','"PAUSE"','"STOP"'])
        assert.ok(radio.includes('label: '+s));
    assert.match(radio,/controller\.ownsPlayback/);
    assert.match(radio,/radioClient: "weather-radio"/);
    assert.match(radio,/path: Quickshell\.dataDir \+ "\/weather-radio-memory\.json"/);
    assert.match(radio,/onClicked: stationRadio\.toggleHighlightedFavorite\(\)/);
});
