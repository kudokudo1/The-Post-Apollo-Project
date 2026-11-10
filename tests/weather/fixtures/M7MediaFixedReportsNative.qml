import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M7 // Native 520x300 MEDIA/NEWS/REPORTS layout, with exact fixed header.
// GDELT and both manual RSS publishers are deliberately disabled.
// This checks physical pinning and data-owner continuity, not network fetch.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property real requestY: -1
    property real searchY: -1
    property real topicY: -1
    property real scrollY: -1
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const found=find(child,name);
            if(found)return found;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let n=item.objectName===name ? 1 : 0;
        for(const child of (item.children||[]))
            n+=count(child,name);
        return n;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("M7_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationMediaHeader {
            id: header
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            subjectRoute: "media/news/full"
            newsSection: "REPORTS"
        }
        Weather.StationDiscovery {
            id: reports
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            domain: "news"
            newsSubjectRoute: "media/news/full"
            mediaNewsServicesSplit: true
            stationOpen: false
            pinReportsToolbar: true
        }
    }
    Timer {
        running: !root.done
        repeat: true
        interval: 180
        onTriggered: {
            root.ticks++;
            if(root.ticks>28)return root.fail("TIMEOUT");
            const toolbar=find(reports,"media-m7-reports-pinned-toolbar");
            const retry=find(reports,"media-m7-retry-news");
            const bbc=find(reports,"media-m7-request-bbc");
            const aljazeera=find(reports,"media-m7-request-aljazeera");
            const search=find(reports,"media-m7-fixed-search-rail");
            const source=find(reports,"media-m7-source-input");
            const language=find(reports,"media-m7-language-input");
            const clearSource=find(reports,"media-m7-clear-source");
            const clearLanguage=find(reports,"media-m7-clear-language");
            const topic=find(reports,"media-m9-unified-fixed-filter-rail");
            const title=find(reports,"media-m9-pinned-news-title");
            const titleRail=find(reports,"media-m9-pinned-news-header-rail");
            const viewBbc=find(reports,"media-m9-view-bbc");
            const viewAj=find(reports,"media-m9-view-aljazeera");
            const legacyTitle=find(reports,"media-m9-legacy-scrolling-news-header");
            const scroll=find(reports,"earth-e2-event-scroll");
            const rss=find(reports,"media-m6-reports-publisher-feeds");
            if(!toolbar||!retry||!bbc||!aljazeera||!search||!source
                ||!language||!clearSource||!clearLanguage||!topic||!title
                ||!titleRail||!viewBbc||!viewAj||!legacyTitle||!scroll||!rss) {
                if(root.ticks>7)return root.fail("FIXED_REPORTS_CONTROLS_MISSING");
                return;
            }
            if(root.phase===0) {
                const yRetry=retry.mapToItem(reports,0,0).y;
                const yBbc=bbc.mapToItem(reports,0,0).y;
                const yAj=aljazeera.mapToItem(reports,0,0).y;
                if(!toolbar.visible||!scroll.visible
                   ||!retry.visible||!bbc.visible||!aljazeera.visible
                   ||Math.abs(yRetry-yBbc)>1 ||Math.abs(yRetry-yAj)>1
                   ||Math.abs(retry.width-bbc.width)>1
                   ||Math.abs(bbc.width-aljazeera.width)>1
                   ||toolbar.height<100 ||toolbar.height>140
                   ||scroll.y < toolbar.y+toolbar.height
                   ||scroll.height<65 ||scroll.y+scroll.height>reports.height+1
                   ||!search.visible ||!source.visible ||!language.visible
                   ||!topic.visible ||!title.visible ||!titleRail.visible
                   ||!viewBbc.visible ||!viewAj.visible ||legacyTitle.visible
                   ||Math.abs(viewBbc.mapToItem(reports,0,0).y
                               -title.mapToItem(reports,0,0).y)>1
                   ||Math.abs(viewAj.mapToItem(reports,0,0).y
                               -title.mapToItem(reports,0,0).y)>1
                   ||topic.contentWidth<=topic.width
                   ||rss.pinnedRequests!==true ||rss.pinnedViews!==true
                   ||rss.stationOpen
                   ||rss.bbcBackend.active ||rss.alJazeeraBackend.active
                   ||count(reports,"media-m6-reports-publisher-feeds")!==1)
                    return root.fail("HEADER_PINNING_GEOMETRY // panel="
                         +String(reports.height)+" toolbar="+String(toolbar.height)
                         +" scroll="+String(scroll.height)
                         +" y="+String(scroll.y)+" source="+String(source.visible));
                root.requestY=yRetry;
                root.searchY=search.mapToItem(reports,0,0).y;
                root.topicY=topic.mapToItem(reports,0,0).y;
                root.scrollY=scroll.y;
                rss.expandedPublisher="bbc-world";
                reports.newsSourceQuery="BBC";
                reports.newsLanguageQuery="ENGLISH";
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(source.text!=="BBC"||language.text!=="ENGLISH"
                   ||viewBbc.label!=="HIDE BBC" ||viewAj.label!=="VIEW AJ"
                   ||!clearSource.available||!clearLanguage.available)
                    return root.fail("FIXED_SEARCH_FIELDS_NOT_BOUND");
                clearSource.clicked(null);
                clearLanguage.clicked(null);
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(reports.newsSourceQuery!==""||reports.newsLanguageQuery!=="")
                    return root.fail("FIXED_CLEAR_DID_NOT_CHANGE_SOURCE");
                if(scroll.contentHeight<=scroll.height)
                    return root.fail("REPORTS_BODY_NOT_SCROLLABLE");
                scroll.contentY=Math.min(80,scroll.contentHeight-scroll.height);
                root.phase=3;return;
            }
            if(root.phase===3) {
                if(scroll.contentY<=0
                    ||retry.mapToItem(reports,0,0).y!==root.requestY
                    ||bbc.mapToItem(reports,0,0).y!==root.requestY
                    ||aljazeera.mapToItem(reports,0,0).y!==root.requestY
                    ||search.mapToItem(reports,0,0).y!==root.searchY
                    ||topic.mapToItem(reports,0,0).y!==root.topicY
                    ||title.mapToItem(reports,0,0).y!==titleRail.mapToItem(reports,0,0).y
                    ||scroll.y!==root.scrollY)
                    return root.fail("SCROLL_MOVED_PINNED_REPORTS_CONTROLS");
                root.done=true;
                console.log("M7_NATIVE_PASS // NEWS_RETRY_BBC_AJ_AND_SEARCH_FIXED_BODY_SCROLLS");
                Qt.quit();
            }
        }
    }
}
