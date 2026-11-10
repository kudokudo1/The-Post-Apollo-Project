"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const discovery=read("widgets/weather/StationDiscovery.qml");
const publisher=read("widgets/weather/StationPublisherFeeds.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const services=read("widgets/weather/StationMediaServicesPane.qml");
const media=read("widgets/weather/StationMediaSubjectPane.qml");

test("M7 focuses sticky controls in NEWS full, not OVERVIEW or CLASSIC",()=>{
    assert.ok(discovery.includes("property bool pinReportsToolbar: false"));
    assert.ok(hub.includes('pinReportsToolbar: stationNewsHub.subjectRoute.indexOf("media/news/") === 0'));
    assert.ok(hub.includes('&& !stationNewsHub.overviewChannelFilters'));
    assert.ok(media.includes('overviewChannelFilters: true'));
    assert.ok(discovery.includes('id: reportsFixedToolbar'));
    assert.ok(discovery.includes('objectName: "media-m7-reports-pinned-toolbar"'));
    assert.ok(discovery.includes('visible: stationDiscovery.domain === "news"'));
    assert.ok(discovery.includes('&& stationDiscovery.pinReportsToolbar'));
    assert.ok(discovery.includes('id: discoveryScroll'));
    assert.ok(discovery.includes('anchors.top: reportsFixedToolbar.visible'));
    assert.ok(discovery.includes('? reportsFixedToolbar.bottom'));
    assert.ok(discovery.includes('anchors.topMargin: reportsFixedToolbar.visible ? 3'));
    assert.ok(discovery.includes('id: content'));
    assert.ok(discovery.includes('y: stationDiscovery.pinReportsToolbar ? 4 : 12'));
    assert.ok(discovery.includes('visible: !stationDiscovery.viewerOpen'));
    assert.ok(!media.includes('id: overviewScroll'));
});

test("M7 pins RETRY NEWS, BBC and AL JAZEERA request controls on one action row",()=>{
    const start=discovery.indexOf('id: reportsRequestRail');
    const end=discovery.indexOf('id: reportsSearchRail',start);
    assert.ok(start>0 && end>start);
    const group=discovery.slice(start,end);
    for(const name of ['media-m7-retry-news','media-m7-request-bbc',
                        'media-m7-request-aljazeera'])
        assert.ok(group.includes('objectName: "'+name+'"'),name);
    assert.equal((group.match(/ActionButton\s*\{/g)||[]).length,3);
    assert.ok(group.includes('onClicked: source.refresh(true)'));
    assert.ok(group.includes('publisherFeedsContent.requestPublisher("bbc-world")'));
    assert.ok(group.includes('publisherFeedsContent.requestPublisher("al-jazeera-english")'));
    assert.ok(group.includes('publisherFeedsContent.bbcBackend.canRequest'));
    assert.ok(group.includes('publisherFeedsContent.alJazeeraBackend.canRequest'));
    assert.ok(group.includes('REFRESH BBC'));
    assert.ok(group.includes('LOAD AL JAZEERA'));
    assert.equal((discovery.match(/StationPublisherFeeds\s*\{/g)||[]).length,1);
    assert.ok(discovery.includes('id: publisherFeedsContent'));
    assert.ok(discovery.includes('pinnedRequests: stationDiscovery.pinReportsToolbar'));
});

test("M7 pinned source and language search, clear actions and all topic/time/region buttons",()=>{
    for(const x of [
        'media-m7-fixed-search-rail','media-m7-fixed-source-search',
        'media-m7-fixed-language-search','media-m7-source-input',
        'media-m7-language-input','media-m7-clear-source',
        'media-m7-clear-language','media-m7-fixed-topic-rail',
        'media-m7-fixed-time-rail','media-m7-fixed-region-rail'
    ])assert.ok(discovery.includes('objectName: "'+x+'"'),x);
    for(const x of [
        'onTextEdited: stationDiscovery.newsSourceQuery = text',
        'onTextEdited: stationDiscovery.newsLanguageQuery = text',
        'onClicked: stationDiscovery.newsSourceQuery = ""',
        'onClicked: stationDiscovery.newsLanguageQuery = ""',
        'onTriggered: stationDiscovery.selectNewsTopic(modelData.id)',
        'onTriggered: stationDiscovery.selectNewsTime(modelData.hours)',
        'onTriggered: stationDiscovery.selectNewsRegion(modelData.id)'
    ]) assert.ok(discovery.includes(x),x);
    assert.equal((discovery.match(/flickableDirection: Flickable.HorizontalFlick/g)||[]).length>=3,true);
    const legacy=discovery.slice(discovery.indexOf('id: newsTopicRail'),
        discovery.indexOf('// M28-B: MEDIA owns the full article feed.'));
    assert.equal((legacy.match(/&& !stationDiscovery.pinReportsToolbar/g)||[]).length,5);
    assert.ok(discovery.includes('&& !stationDiscovery.pinReportsToolbar\n                spacing: 12'));
});

test("M7 only exposes existing manual publisher RSS requests; expanded rows remain scrollable",()=>{
    assert.ok(publisher.includes('property bool pinnedRequests: false'));
    assert.ok(publisher.includes('readonly property var bbcBackend: bbc'));
    assert.ok(publisher.includes('readonly property var alJazeeraBackend: alJazeera'));
    assert.ok(publisher.includes('function requestPublisher(feedId)'));
    assert.ok(publisher.includes('if (!stationOpen || !visible || !backend || !backend.canRequest)'));
    assert.ok(publisher.includes('return backend.request()'));
    assert.ok(publisher.includes('visible: !publisherFeeds.pinnedRequests'));
    assert.ok(publisher.includes('publisherFeeds.expandedPublisher'));
    assert.ok(publisher.includes('publisherFeeds.headlineSelected(modelData)'));
    assert.ok(publisher.includes('feedId: "bbc-world"'));
    assert.ok(publisher.includes('feedId: "al-jazeera-english"'));
    assert.equal((publisher.match(/WeatherServices\.StationPublisherRssService\s*\{/g)||[]).length,2);
    assert.ok(!services.includes('StationPublisherFeeds {'));
    // StationDiscovery has pre-existing, unrelated browser paths. The new
    // fixed REPORTS controls and the RSS owner must never open one.
    const fixedDeck=discovery.slice(discovery.indexOf('id: reportsFixedToolbar'),
                                  discovery.indexOf('id: discoveryScroll'));
    assert.ok(!fixedDeck.includes('Qt.openUrlExternally('));
    assert.ok(!publisher.includes('Qt.openUrlExternally('));
});
