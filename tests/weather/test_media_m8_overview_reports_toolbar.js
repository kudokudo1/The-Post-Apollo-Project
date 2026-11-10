"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const discovery=read("widgets/weather/StationDiscovery.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const publisher=read("widgets/weather/StationPublisherFeeds.qml");

test("M8 fixes the exact MEDIA OVERVIEW route shown on desktop, rather than only focused NEWS",()=>{
    assert.ok(media.includes('subjectRoute: "media/news/reports"'));
    assert.ok(media.includes('overviewChannelFilters: true'));
    assert.ok(hub.includes('compactOverviewReportsToolbar: stationNewsHub.overviewChannelFilters'));
    assert.ok(hub.includes('&& stationNewsHub.subjectRoute === "media/news/reports"'));
    assert.ok(hub.includes('pinReportsToolbar: stationNewsHub.subjectRoute.indexOf("media/news/") === 0'));
    assert.ok(discovery.includes('property bool compactOverviewReportsToolbar: false'));
    assert.ok(discovery.includes('pinReportsToolbar || compactOverviewReportsToolbar'));
    assert.ok(discovery.includes('&& stationDiscovery.reportsToolbarActive'));
    assert.ok(discovery.includes('anchors.top: reportsFixedToolbar.visible'));
    assert.ok(media.includes('height: Math.max(0,(mediaOverview.height - 6) / 2)'));
    assert.ok(media.includes('anchors.top: reportsBay.bottom'));
    assert.ok(media.includes('overviewDocked: true'));
    assert.ok(!media.includes('id: overviewScroll'));
});

test("M8 overview pins request/search plus one horizontal filter strip instead of hiding the news body",()=>{
    const start=discovery.indexOf('id: reportsFixedToolbar');
    const end=discovery.indexOf('id: discoveryScroll',start);
    const fixed=discovery.slice(start,end);
    for(const x of [
        'media-m7-retry-news','media-m7-request-bbc','media-m7-request-aljazeera',
        'media-m7-fixed-search-rail','media-m7-source-input','media-m7-language-input',
        'media-m7-clear-source','media-m7-clear-language',
        'media-m9-unified-fixed-filter-rail'
    ])assert.ok(fixed.includes('objectName: "'+x+'"'),x);
    assert.ok(fixed.includes('visible: stationDiscovery.reportsToolbarActive'));
    assert.ok(fixed.includes('flickableDirection: Flickable.HorizontalFlick'));
    assert.ok(fixed.includes('model: stationDiscovery.newsTopicOptions'));
    assert.ok(fixed.includes('model: stationDiscovery.newsTimeOptions'));
    assert.ok(fixed.includes('model: stationDiscovery.newsRegionOptions'));
    for(const fn of [
       'selectNewsTopic(modelData.id)','selectNewsTime(modelData.hours)',
       'selectNewsRegion(modelData.id)','requestPublisher("bbc-world")',
       'requestPublisher("al-jazeera-english")','source.refresh(true)'
    ])assert.ok(fixed.includes(fn),fn);
    assert.equal((discovery.match(/StationPublisherFeeds\s*\{/g)||[]).length,1);
    assert.ok(discovery.includes('pinnedRequests: stationDiscovery.reportsToolbarActive'));
    assert.ok(publisher.includes('visible: !publisherFeeds.pinnedRequests'));
    assert.ok(discovery.includes('&& !stationDiscovery.reportsToolbarActive'));
    assert.ok(discovery.includes('y: stationDiscovery.reportsToolbarActive ? 4 : 12'));
    assert.ok(!fixed.includes('Qt.openUrlExternally('));
});

test("M9 uses one pinned topic/time/region rail for both full NEWS and OVERVIEW",()=>{
    assert.ok(discovery.includes('id: reportsUnifiedFilters'));
    assert.ok(discovery.includes('objectName: "media-m9-unified-fixed-filter-rail"'));
    assert.equal((discovery.match(/id: reportsUnifiedFilters/g)||[]).length,1);
    assert.ok(discovery.includes('visible: stationDiscovery.reportsToolbarActive'));
    assert.ok(discovery.includes('contentWidth: unifiedFilterChoices.implicitWidth'));
    assert.ok(discovery.includes('height: visible ? (stationDiscovery.compactOverviewReportsToolbar ? 18 : 24) : 0'));
    assert.ok(!discovery.includes('id: reportsTopicRail'));
    assert.ok(!discovery.includes('id: reportsTimeRail'));
    assert.ok(!discovery.includes('id: reportsRegionRail'));
    assert.ok(discovery.includes('property bool pinReportsToolbar: false'));
    assert.ok(publisher.includes('feedId: "bbc-world"'));
    assert.ok(publisher.includes('feedId: "al-jazeera-english"'));
    assert.equal((publisher.match(/WeatherServices\.StationPublisherRssService\s*\{/g)||[]).length,2);
    assert.ok(publisher.includes('function requestPublisher(feedId)'));
});
