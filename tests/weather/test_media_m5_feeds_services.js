"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const header=read("widgets/weather/StationMediaHeader.qml");
const services=read("widgets/weather/StationMediaServicesPane.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const discovery=read("widgets/weather/StationDiscovery.qml");
const rss=read("widgets/weather/StationPublisherFeeds.qml");
const radio=read("widgets/weather/StationRadio.qml");
const saved=read("widgets/weather/StationRadioSavedStrips.qml");

test("M6 restores manual BBC/Al Jazeera RSS controls to NEWS REPORTS, not SERVICES",()=>{
    assert.equal((discovery.match(/StationPublisherFeeds\s*\{/g)||[]).length,1);
    assert.ok(discovery.includes('objectName: "media-m6-reports-publisher-feeds"'));
    assert.ok(discovery.includes('visible: stationDiscovery.domain === "news"'));
    assert.ok(discovery.includes('&& stationDiscovery.newsGroupVisible("request")'));
    assert.ok(discovery.includes('stationOpen: stationDiscovery.stationOpen'));
    assert.ok(discovery.includes('stationDiscovery.openRow(row)'));
    assert.ok(!services.includes("StationPublisherFeeds {"));
    assert.ok(!services.includes("media-m5-publisher-feed-loader"));
    assert.ok(!services.includes('viewMode==="feeds"'));
    assert.ok(!header.includes('id:"feeds"'));
    assert.ok(rss.includes('feedId: "bbc-world"'));
    assert.ok(rss.includes('feedId: "al-jazeera-english"'));
    assert.ok(rss.includes('publisherSourceRow.backend.request()'));
    assert.ok(rss.includes('publisherFeeds.headlineSelected(modelData)'));
    assert.ok(rss.includes('active: publisherFeeds.stationOpen && publisherFeeds.visible'));
    assert.equal((news.match(/StationDiscovery\s*\{/g)||[]).length,1);
    assert.ok(discovery.includes('model: stationDiscovery.newsGroupVisible("list")'));
});

test("M6 retains M5 last-observed NEWS runtime and source diagnostics in SERVICES",()=>{
    assert.ok(discovery.includes('property bool mediaNewsServicesSplit: false'));
    assert.ok(news.includes('mediaNewsServicesSplit: true'));
    assert.ok(news.includes('readonly property var newsSourceRows:'));
    assert.ok(news.includes('reportsLoader.item.plannedSources'));
    assert.ok(media.includes('property var lastNewsRuntimeRows: []'));
    assert.ok(media.includes('property var lastNewsSourceRows: []'));
    assert.ok(media.includes('property double lastNewsObservedMs: 0'));
    assert.ok(media.includes('if (!owner || !owner.isReports || !owner.stationOpen)'));
    assert.ok(media.includes('lastNewsRuntimeRows = runtime.map('));
    assert.ok(media.includes('lastNewsSourceRows = sources.map('));
    assert.ok(media.includes('newsObservedMs: mediaPane.lastNewsObservedMs'));
    assert.ok(services.includes('LAST OBSERVED RUNTIME'));
    assert.ok(services.includes('GDELT // SOURCE RACK // LAST OBSERVED'));
    assert.ok(services.includes('NOT MOUNTED ON SERVICES'));
    assert.ok(!services.includes('StationDiscovery {'));
    assert.ok(!services.includes('StationNewsHub {'));
    assert.ok(!services.includes('StationRadio {'));
    assert.ok(header.includes('{id:"sources",label:"SOURCE DIRECTORY"}'));
    assert.ok(header.includes('{id:"runtime",label:"RUNTIME // OWNERS"}'));
    assert.ok(media.includes('mode==="runtime" || mode==="sources"'));
    assert.ok(!media.includes('|| mode==="feeds"'));
    assert.ok(services.includes('media-m5-services-body-scroll'));
});

test("M6 OVERVIEW splits fixed NEWS and RADIO 50/50 with compact RADIO presentation only",()=>{
    assert.ok(media.includes('height: Math.max(0,(mediaOverview.height - 6) / 2)'));
    assert.ok(media.includes('anchors.top: reportsBay.bottom'));
    assert.ok(media.includes('anchors.topMargin: 6'));
    assert.ok(media.includes('anchors.bottom: parent.bottom'));
    assert.ok(!media.includes('id: overviewScroll'));
    assert.ok(media.includes('overviewDocked: true'));
    assert.ok(media.includes('subjectRoute: "media/radio/full"'));
    assert.ok(media.includes('subjectRoute: "media/news/reports"'));
    assert.ok(radio.includes('objectName: "media-m1-radio-directory-scroll"'));
    assert.ok(radio.includes('objectName: "media-m1-radio-transport-fixed"'));
    assert.ok(radio.includes('property bool overviewDocked: false'));
    assert.ok(radio.includes('stationRadio.overviewDocked ? 18 : 30'));
    assert.ok(radio.includes('stationRadio.overviewDocked ? 18 : 29'));
    assert.ok(radio.includes('stationRadio.overviewDocked ? 28 : 88'));
    assert.ok(radio.includes('height: stationRadio.overviewDocked ? 27 : 54'));
    assert.ok(radio.includes('&& !stationRadio.overviewDocked'));
    assert.ok(saved.includes('height: compactDocked ? 28 : 88'));
    assert.ok(saved.includes('visible: strips.compactDocked'));
    assert.ok(radio.includes('radioClient: "weather-radio"'));
    for(const cmd of ['stationRadio.selectHighlighted()','stationRadio.loadSelection()',
        'stationRadio.enterHighlighted()','stationRadio.playbackAction("play")',
        'stationRadio.playbackAction("pause")','stationRadio.playbackAction("stop")',
        'stationRadio.toggleHighlightedFavorite()'])
        assert.ok(radio.includes(cmd),cmd);
});
