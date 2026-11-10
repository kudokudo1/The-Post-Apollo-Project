import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M8 // Native 520x300 actual MEDIA OVERVIEW layout with providers disabled.
// Mount one independent inactive NEWS/REPORTS probe at the same half-bay
// height so the real compact control deck can be checked without fetching
// GDELT/RSS on CI. Source tests separately verify the OVERVIEW route gate.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property real requestY: -1
    property real searchY: -1
    property real filtersY: -1
    property real newsY: -1
    property real radioY: -1
    function find(item,name) {
        if (!item) return null;
        if (item.objectName===name) return item;
        for (const child of (item.children||[])) {
            const found=find(child,name);
            if (found) return found;
        }
        return null;
    }
    function count(item,name) {
        if (!item) return 0;
        let n=item.objectName===name?1:0;
        for (const child of (item.children||[]))
            n+=count(child,name);
        return n;
    }
    function fail(reason) {
        if (done) return;
        done=true;
        console.error("M8_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationMediaSubjectPane {
            id: media
            anchors.fill: parent
            subjectRoute: "media/overview"
            providerActivationAllowed: false
        }
        Weather.StationDiscovery {
            id: offlineReportsProbe
            x: 600
            y: 0
            width: 520
            height: Math.max(100,(window.height-50)/2)
            visible: true
            domain: "news"
            newsSubjectRoute: "media/news/reports"
            stationOpen: false
            mediaNewsServicesSplit: true
            compactOverviewReportsToolbar: true
        }
    }
    Timer {
        interval: 180
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks>30) return root.fail("TIMEOUT");
            if (root.phase===3) {
                const full=find(offlineReportsProbe,"media-m7-reports-pinned-toolbar");
                const fullTopic=find(offlineReportsProbe,"media-m7-fixed-topic-rail");
                const fullCompact=find(offlineReportsProbe,"media-m8-overview-fixed-filter-rail");
                const fullNews=find(offlineReportsProbe,"media-m7-retry-news");
                const fullScroll=find(offlineReportsProbe,"earth-e2-event-scroll");
                if (!full || !fullNews || !fullTopic || !fullScroll) {
                    if(root.ticks>20)return root.fail("FOCUSED_NEWS_MISSING");
                    return;
                }
                if (!full.visible||!fullTopic.visible||fullCompact.visible
                    ||fullScroll.y<full.y+full.height
                    ||fullScroll.height<55) return root.fail("FOCUSED_NEWS_CHANGED");
                root.done=true;
                console.log("M8_NATIVE_PASS // OVERVIEW_STICKY_REPORTS_AND_RADIO_5050");
                Qt.quit();
                return;
            }
            const overview=find(media,"media-m3-overview");
            const news=find(media,"media-m3-news-top-bay");
            const radio=find(media,"media-m3-full-radio-bottom-bay");
            const toolbar=find(offlineReportsProbe,"media-m7-reports-pinned-toolbar");
            const retry=find(offlineReportsProbe,"media-m7-retry-news");
            const bbc=find(offlineReportsProbe,"media-m7-request-bbc");
            const aljazeera=find(offlineReportsProbe,"media-m7-request-aljazeera");
            const search=find(offlineReportsProbe,"media-m7-fixed-search-rail");
            const source=find(offlineReportsProbe,"media-m7-source-input");
            const language=find(offlineReportsProbe,"media-m7-language-input");
            const clearSource=find(offlineReportsProbe,"media-m7-clear-source");
            const clearLanguage=find(offlineReportsProbe,"media-m7-clear-language");
            const compact=find(offlineReportsProbe,"media-m8-overview-fixed-filter-rail");
            const fullTopic=find(offlineReportsProbe,"media-m7-fixed-topic-rail");
            const fullTime=find(offlineReportsProbe,"media-m7-fixed-time-rail");
            const fullRegion=find(offlineReportsProbe,"media-m7-fixed-region-rail");
            const scroll=find(offlineReportsProbe,"earth-e2-event-scroll");
            const rss=find(offlineReportsProbe,"media-m6-reports-publisher-feeds");
            const radioTransport=find(media,"media-m1-radio-transport-fixed");
            if (!overview||!news||!radio||!toolbar||!retry||!bbc||!aljazeera
                ||!search||!source||!language||!clearSource||!clearLanguage
                ||!compact||!fullTopic||!fullTime||!fullRegion||!scroll
                ||!rss||!radioTransport) {
                if(root.ticks>8)return root.fail("MISSING_OVERVIEW_STICKY_NODE");
                return;
            }
            if(root.phase===0) {
                const rY=retry.mapToItem(offlineReportsProbe,0,0).y;
                if(!toolbar.visible||!compact.visible||!search.visible
                    ||fullTopic.visible||fullTime.visible||fullRegion.visible
                    ||!retry.visible||!bbc.visible||!aljazeera.visible
                    ||Math.abs(retry.mapToItem(offlineReportsProbe,0,0).y
                                -bbc.mapToItem(offlineReportsProbe,0,0).y)>1
                    ||Math.abs(retry.mapToItem(offlineReportsProbe,0,0).y
                                -aljazeera.mapToItem(offlineReportsProbe,0,0).y)>1
                    ||Math.abs(news.height-radio.height)>1
                    ||radio.y+radio.height>overview.height+1
                    ||toolbar.height<55 ||toolbar.height>100
                    ||scroll.y < toolbar.y+toolbar.height
                    ||scroll.height<24
                    ||scroll.y+scroll.height>offlineReportsProbe.height+1
                    ||!radioTransport.visible
                    ||!rss.pinnedRequests
                    ||rss.stationOpen ||rss.bbcBackend.active ||rss.alJazeeraBackend.active
                    ||count(media,"media-m6-reports-publisher-feeds")!==1)
                    return root.fail("OVERVIEW_COMPACT_LAYOUT // news="
                        +news.height+" radio="+radio.height+" toolbar="
                        +toolbar.height+" scroll="+scroll.height+" y="+scroll.y);
                root.requestY=rY;
                root.searchY=search.mapToItem(offlineReportsProbe,0,0).y;
                root.filtersY=compact.mapToItem(offlineReportsProbe,0,0).y;
                root.newsY=news.mapToItem(offlineReportsProbe,0,0).y;
                root.radioY=radio.mapToItem(offlineReportsProbe,0,0).y;
                // Use the existing news hub's active reports owner.
                toolbar.parent.newsSourceQuery="BBC";
                toolbar.parent.newsLanguageQuery="ENGLISH";
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(source.text!=="BBC"||language.text!=="ENGLISH"
                   ||!clearSource.available||!clearLanguage.available)
                    return root.fail("OVERVIEW_SEARCH_NOT_BOUND");
                clearSource.clicked(null);
                clearLanguage.clicked(null);
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(source.text!==""||language.text!=="")
                    return root.fail("OVERVIEW_CLEAR_NOT_WORKING");
                if(scroll.contentHeight<=scroll.height)
                    return root.fail("OVERVIEW_NEWS_BODY_NOT_SCROLLABLE");
                scroll.contentY=Math.min(45,scroll.contentHeight-scroll.height);
                root.phase=4;return;
            }
            if(root.phase===4) {
                if(scroll.contentY<=0
                    ||retry.mapToItem(offlineReportsProbe,0,0).y!==root.requestY
                    ||bbc.mapToItem(offlineReportsProbe,0,0).y!==root.requestY
                    ||aljazeera.mapToItem(offlineReportsProbe,0,0).y!==root.requestY
                    ||search.mapToItem(offlineReportsProbe,0,0).y!==root.searchY
                    ||compact.mapToItem(offlineReportsProbe,0,0).y!==root.filtersY
                    ||news.mapToItem(offlineReportsProbe,0,0).y!==root.newsY
                    ||radio.mapToItem(offlineReportsProbe,0,0).y!==root.radioY)
                    return root.fail("OVERVIEW_NEWS_SCROLL_MOVED_FIXED_RAIL");
                media.subjectRoute="media/news/full";
                offlineReportsProbe.compactOverviewReportsToolbar=false;
                offlineReportsProbe.pinReportsToolbar=true;
                root.phase=3;
                return;
            }
        }
    }
}
