"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const discovery=read("widgets/weather/StationDiscovery.qml");
const publisher=read("widgets/weather/StationPublisherFeeds.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const media=read("widgets/weather/StationMediaSubjectPane.qml");

test("M9 headline title and both VIEW/HIDE actions mount above scroll in full and overview NEWS",()=>{
    const pinnedStart=discovery.indexOf('id: reportsFixedToolbar');
    const scrollStart=discovery.indexOf('id: discoveryScroll',pinnedStart);
    assert.ok(pinnedStart>0&&scrollStart>pinnedStart);
    const pinned=discovery.slice(pinnedStart,scrollStart);
    for(const name of [
        'media-m9-pinned-news-header-rail','media-m9-pinned-news-title',
        'media-m9-view-bbc','media-m9-view-aljazeera',
        'media-m9-pinned-news-source-status',
        'media-m7-retry-news','media-m7-request-bbc','media-m7-request-aljazeera'
    ])assert.ok(pinned.includes('objectName: "'+name+'"'),name);
    assert.ok(pinned.indexOf('id: pinnedNewsTitleRail')<pinned.indexOf('id: reportsRequestRail'));
    assert.ok(pinned.includes('text: stationDiscovery.modeTitle'));
    assert.ok(pinned.includes('color: Colors.cyan'));
    assert.ok(pinned.includes('publisherFeedsContent.togglePublisherView("bbc-world")'));
    assert.ok(pinned.includes('publisherFeedsContent.togglePublisherView("al-jazeera-english")'));
    assert.ok(pinned.includes('publisherFeedsContent.bbcBackend.ready'));
    assert.ok(pinned.includes('publisherFeedsContent.alJazeeraBackend.ready'));
    assert.ok(pinned.includes('publisherFeedsContent.expandedPublisher === "bbc-world"'));
    assert.ok(pinned.includes('HIDE BBC'));
    assert.ok(pinned.includes('VIEW AJ'));
    assert.ok(discovery.includes('objectName: "media-m9-legacy-scrolling-news-header"'));
    assert.ok(discovery.includes('visible: !(stationDiscovery.domain === "news"'));
    assert.ok(discovery.includes('&& stationDiscovery.reportsToolbarActive)'));
    assert.ok(discovery.includes('anchors.top: reportsFixedToolbar.visible'));
    assert.ok(news.includes('compactOverviewReportsToolbar: stationNewsHub.overviewChannelFilters'));
    assert.ok(news.includes('pinReportsToolbar: stationNewsHub.subjectRoute.indexOf("media/news/") === 0'));
});

test("M9 one horizontal TOPIC/TIME/REGION filter rail is pinned in both view sizes",()=>{
    assert.ok(discovery.includes('id: reportsUnifiedFilters'));
    assert.ok(discovery.includes('objectName: "media-m9-unified-fixed-filter-rail"'));
    assert.equal((discovery.match(/id: reportsUnifiedFilters/g)||[]).length,1);
    assert.ok(!discovery.includes('id: reportsTopicRail'));
    assert.ok(!discovery.includes('id: reportsTimeRail'));
    assert.ok(!discovery.includes('id: reportsRegionRail'));
    const a=discovery.indexOf('id: reportsUnifiedFilters');
    const z=discovery.indexOf('id: discoveryScroll',a);
    const rail=discovery.slice(a,z);
    for(const s of ['text: "TOPIC //"','text: "| TIME //"','text: "| REGION //"',
        'model: stationDiscovery.newsTopicOptions',
        'model: stationDiscovery.newsTimeOptions',
        'model: stationDiscovery.newsRegionOptions',
        'stationDiscovery.selectNewsTopic(modelData.id)',
        'stationDiscovery.selectNewsTime(modelData.hours)',
        'stationDiscovery.selectNewsRegion(modelData.id)',
        'flickableDirection: Flickable.HorizontalFlick',
        'visible: stationDiscovery.reportsToolbarActive'])
        assert.ok(rail.includes(s),s);
    assert.ok(rail.includes('stationDiscovery.compactOverviewReportsToolbar ? 18 : 24'));
    assert.ok(!media.includes('id: overviewScroll'));
    assert.ok(media.includes('height: Math.max(0,(mediaOverview.height - 6) / 2)'));
});

test("M9 moves VIEW control surface without duplicating RSS services or article INSPECT",()=>{
    assert.ok(discovery.includes('pinnedViews: stationDiscovery.reportsToolbarActive'));
    assert.ok(discovery.includes('pinnedRequests: stationDiscovery.reportsToolbarActive'));
    assert.equal((discovery.match(/StationPublisherFeeds\s*\{/g)||[]).length,1);
    assert.equal((publisher.match(/WeatherServices\.StationPublisherRssService\s*\{/g)||[]).length,2);
    assert.ok(publisher.includes('property bool pinnedViews: false'));
    assert.ok(publisher.includes('function togglePublisherView(feedId)'));
    assert.ok(publisher.includes('if (!stationOpen || !visible || !backend || !backend.ready)'));
    assert.ok(publisher.includes('expandedPublisher = expandedPublisher === feedId ? "" : feedId'));
    assert.ok(publisher.includes('visible: !publisherFeeds.pinnedViews'));
    assert.ok(publisher.includes('visible: !(publisherFeeds.pinnedRequests && publisherFeeds.pinnedViews)'));
    assert.ok(publisher.includes('publisherFeeds.headlineSelected(modelData)'));
    assert.ok(publisher.includes('feedId: "bbc-world"'));
    assert.ok(publisher.includes('feedId: "al-jazeera-english"'));
    assert.ok(!discovery.slice(discovery.indexOf('id: reportsFixedToolbar'),
         discovery.indexOf('id: discoveryScroll')).includes('Qt.openUrlExternally('));
});
