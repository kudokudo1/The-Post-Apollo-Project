import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M8 // Native 520x300 actual MEDIA OVERVIEW: not a synthetic full NEWS
// page. All provider activation is disabled. Verify compact sticky requests,
// search and topic/time/region with RADIO still using its original half bay.
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
    }
    Timer {
        interval: 180
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks>30) return root.fail("TIMEOUT");
            if (root.phase===3) {
                const full=find(media,"media-m7-reports-pinned-toolbar");
                const fullTopic=find(media,"media-m7-fixed-topic-rail");
                const fullCompact=find(media,"media-m8-overview-fixed-filter-rail");
                const fullNews=find(media,"media-m7-retry-news");
                const fullScroll=find(media,"earth-e2-event-scroll");
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
            const toolbar=find(media,"media-m7-reports-pinned-toolbar");
            const retry=find(media,"media-m7-retry-news");
            const bbc=find(media,"media-m7-request-bbc");
            const aljazeera=find(media,"media-m7-request-aljazeera");
            const search=find(media,"media-m7-fixed-search-rail");
            const source=find(media,"media-m7-source-input");
            const language=find(media,"media-m7-language-input");
            const clearSource=find(media,"media-m7-clear-source");
            const clearLanguage=find(media,"media-m7-clear-language");
            const compact=find(media,"media-m8-overview-fixed-filter-rail");
            const fullTopic=find(media,"media-m7-fixed-topic-rail");
            const fullTime=find(media,"media-m7-fixed-time-rail");
            const fullRegion=find(media,"media-m7-fixed-region-rail");
            const scroll=find(media,"earth-e2-event-scroll");
            const rss=find(media,"media-m6-reports-publisher-feeds");
            const radioTransport=find(media,"media-m1-radio-transport-fixed");
            if (!overview||!news||!radio||!toolbar||!retry||!bbc||!aljazeera
                ||!search||!source||!language||!clearSource||!clearLanguage
                ||!compact||!fullTopic||!fullTime||!fullRegion||!scroll
                ||!rss||!radioTransport) {
                if(root.ticks>8)return root.fail("MISSING_OVERVIEW_STICKY_NODE");
                return;
            }
            if(root.phase===0) {
                const rY=retry.mapToItem(media,0,0).y;
                if(!toolbar.visible||!compact.visible||!search.visible
                    ||fullTopic.visible||fullTime.visible||fullRegion.visible
                    ||!retry.visible||!bbc.visible||!aljazeera.visible
                    ||Math.abs(retry.mapToItem(media,0,0).y
                                -bbc.mapToItem(media,0,0).y)>1
                    ||Math.abs(retry.mapToItem(media,0,0).y
                                -aljazeera.mapToItem(media,0,0).y)>1
                    ||Math.abs(news.height-radio.height)>1
                    ||radio.y+radio.height>overview.height+1
                    ||toolbar.height<55 ||toolbar.height>100
                    ||scroll.y < toolbar.y+toolbar.height
                    ||scroll.height<24
                    ||scroll.y+scroll.height>news.height+1
                    ||!radioTransport.visible
                    ||!rss.pinnedRequests
                    ||rss.stationOpen ||rss.bbcBackend.active ||rss.alJazeeraBackend.active
                    ||count(media,"media-m6-reports-publisher-feeds")!==1)
                    return root.fail("OVERVIEW_COMPACT_LAYOUT // news="
                        +news.height+" radio="+radio.height+" toolbar="
                        +toolbar.height+" scroll="+scroll.height+" y="+scroll.y);
                root.requestY=rY;
                root.searchY=search.mapToItem(media,0,0).y;
                root.filtersY=compact.mapToItem(media,0,0).y;
                root.newsY=news.mapToItem(media,0,0).y;
                root.radioY=radio.mapToItem(media,0,0).y;
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
                    ||retry.mapToItem(media,0,0).y!==root.requestY
                    ||bbc.mapToItem(media,0,0).y!==root.requestY
                    ||aljazeera.mapToItem(media,0,0).y!==root.requestY
                    ||search.mapToItem(media,0,0).y!==root.searchY
                    ||compact.mapToItem(media,0,0).y!==root.filtersY
                    ||news.mapToItem(media,0,0).y!==root.newsY
                    ||radio.mapToItem(media,0,0).y!==root.radioY)
                    return root.fail("OVERVIEW_NEWS_SCROLL_MOVED_FIXED_RAIL");
                media.subjectRoute="media/news/full";
                root.phase=3;
                return;
            }
        }
    }
}
