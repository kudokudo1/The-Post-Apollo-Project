"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const radio=read("widgets/weather/StationRadio.qml");
const saved=read("widgets/weather/StationRadioSavedStrips.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const header=read("widgets/weather/StationMediaHeader.qml");

test("M4 overview has no outer Flickable; NEWS and RADIO bays are both anchored to fixed container",()=>{
    assert.doesNotMatch(media,/id:\s*overviewScroll/);
    assert.doesNotMatch(media,/objectName:\s*"media-m3-overview-scroll"/);
    assert.match(media,/objectName: "media-m3-news-top-bay"/);
    assert.match(media,/objectName: "media-m3-full-radio-bottom-bay"/);
    assert.ok(media.includes("height: Math.max(52,Math.min(110,mediaOverview.height - 158))"));
    assert.ok(media.includes("anchors.top: reportsBay.bottom"));
    assert.ok(media.includes("anchors.bottom: parent.bottom"));
    assert.ok(media.includes('subjectRoute: "media/news/reports"'));
    assert.ok(media.includes("overviewChannelFilters: true"));
    assert.ok(media.includes('section: "REPORTS"'));
    assert.ok(media.includes('subjectRoute: "media/radio/full"'));
    assert.ok(media.includes("overviewDocked: true"));
    assert.ok(media.includes("embeddedHeader: true"));
    assert.equal((media.match(/StationNewsHub\s*\{/g)||[]).length,2);
    assert.equal((media.match(/StationRadio\s*\{/g)||[]).length,2);
});

test("M4 RADIO uses its existing controller, not a second player or alternate source store",()=>{
    assert.ok(radio.includes("property bool overviewDocked: false"));
    assert.ok(radio.includes('objectName: "media-m1-radio-search-fixed"'));
    assert.ok(radio.includes('objectName: "media-m2-radio-fixed-saved"'));
    assert.ok(radio.includes('objectName: "media-m1-radio-directory-scroll"'));
    assert.ok(radio.includes('objectName: "media-m1-radio-transport-fixed"'));
    assert.ok(radio.includes('objectName: "media-m4-fixed-radio-label"'));
    assert.ok(radio.includes("anchors.top: savedStrips.bottom"));
    assert.ok(radio.includes("anchors.bottom: fixedTransport.top"));
    assert.ok(radio.includes("anchors.bottom: parent.bottom"));
    assert.ok(radio.includes("stationRadio.search(queryInput.text, null)"));
    for(const action of ["stationRadio.selectHighlighted()",
                         "stationRadio.loadSelection()",
                         "stationRadio.enterHighlighted()",
                         'stationRadio.playbackAction("play")',
                         'stationRadio.playbackAction("pause")',
                         'stationRadio.playbackAction("stop")',
                         "stationRadio.toggleHighlightedFavorite()"])
        assert.ok(radio.includes(action),action);
    assert.ok(radio.includes('radioClient: "weather-radio"'));
    assert.ok(radio.includes('weather-radio-memory.json'));
    assert.equal((radio.match(/MediaServices\.HeadlessMediaController\s*\{/g)||[]).length,1);
});

test("M4 overview condenses only presentation; stand-alone RADIO retains original normal dimensions",()=>{
    assert.ok(radio.includes("stationRadio.overviewDocked ? 24 : 30"));
    assert.ok(radio.includes("stationRadio.overviewDocked ? 55 : 82"));
    assert.ok(radio.includes("stationRadio.overviewDocked ? 68 : 92"));
    assert.ok(radio.includes("stationRadio.overviewDocked ? 36 : 88"));
    assert.ok(radio.includes("stationRadio.overviewDocked ? 24 : 29"));
    assert.ok(radio.includes("stationRadio.overviewDocked ? 3 : 8"));
    assert.ok(radio.includes("&& !stationRadio.overviewDocked"));
    assert.ok(saved.includes("property bool compactDocked: false"));
    assert.ok(saved.includes("height: compactDocked ? 36 : 88"));
    assert.ok(saved.includes("visible: !strips.compactDocked"));
    assert.ok(saved.includes("visible: strips.compactDocked"));
    assert.ok(saved.includes('objectName: "media-m4-pinned-saved-pair"'));
    assert.ok(saved.includes('objectName: "media-m4-docked-favorites-scroll"'));
    assert.ok(saved.includes('objectName: "media-m4-docked-recents-scroll"'));
    assert.ok(saved.includes('objectName: "media-m4-docked-favorite-tile"'));
    assert.ok(saved.includes('objectName: "media-m4-docked-recent-tile"'));
    assert.ok(saved.includes("height: strips.dockTileWidth"));
    assert.ok(saved.includes("border.color: Colors.magenta"));
    assert.ok(saved.includes("border.color: Colors.orange"));
    assert.ok(saved.includes("flickableDirection: Flickable.HorizontalFlick"));
    assert.ok(saved.includes("onClicked: strips.recallRequested(modelData)"));
    assert.ok(saved.includes("onClicked: strips.removeRequested(modelData)"));
});

test("M4 NEWS stays first with original source filtering and fixed C44 rail",()=>{
    assert.ok(header.includes('activeMode === "news" || activeMode === "overview" ? Catalog.sections'));
    assert.ok(media.includes("loadedNews.selectSection(section)"));
    assert.ok(news.includes("property bool overviewChannelFilters: false"));
    assert.ok(media.includes("const bay = overviewNewsHub.playerViewportRect"));
    assert.ok(media.includes("overviewNewsHub.mapToItem("));
    assert.ok(media.includes('stationOpen: mediaPane.visible && mediaPane.providerActivationAllowed'));
});
