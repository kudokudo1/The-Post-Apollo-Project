import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M6 // Disposable 520x300 real MEDIA Quickshell UI, providers disabled.
// Verify the return of NEWS/REPORTS publisher controls and equal dock bays.
// Do not request GDELT, RSS, RadioBrowser or MPD in this fixture.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property real newsBefore: -1
    property real radioBefore: -1
    property real searchBefore: -1
    property real footerBefore: -1
    function find(item,name) {
        if(!item) return null;
        if(item.objectName===name) return item;
        for(const child of (item.children||[])) {
            const found=find(child,name);
            if(found) return found;
        }
        return null;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("M6_NATIVE_FAIL // "+reason);
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
            subjectRoute: "media/services/health"
            providerActivationAllowed: false
        }
        // Inspect an actual REPORTS component without activating any
        // provider. The NEWS hub is gated inactive by design in test mode.
        Weather.StationDiscovery {
            id: reportsProbe
            x: 600
            y: 0
            width: 520
            height: 300
            visible: false
            stationOpen: false
            domain: "news"
            newsSubjectRoute: "media/news/reports"
            mediaNewsServicesSplit: true
        }
    }
    Timer {
        interval: 180
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            const rss=find(reportsProbe,"media-m6-reports-publisher-feeds");
            if(!rss) {
                if(root.ticks>8)return root.fail("REPORTS_RSS_NOT_MOUNTED");
                return;
            }
            if(rss.stationOpen) return root.fail("RSS_UNEXPECTEDLY_ACTIVE");
            // OVERVIEW deliberately unloads SERVICES; check the new route
            // before dereferencing any former SERVICES children.
            if(root.phase===3 || root.phase===4) {
                const overview=find(media,"media-m3-overview");
                const news=find(media,"media-m3-news-top-bay");
                const radio=find(media,"media-m3-full-radio-bottom-bay");
                const search=find(media,"media-m1-radio-search-fixed");
                const saved=find(media,"media-m2-radio-fixed-saved");
                const directory=find(media,"media-m1-radio-directory-scroll");
                const footer=find(media,"media-m1-radio-transport-fixed");
                if(!overview||!news||!radio||!search||!saved||!directory||!footer) {
                    if(root.ticks>18) return root.fail("OVERVIEW_MISSING_CONTROL");
                    return;
                }
                if(Math.abs(news.height-radio.height)>1
                    ||Math.abs(news.height-(overview.height-6)/2)>1
                    ||radio.y < news.y+news.height
                    ||radio.y+radio.height>overview.height+1
                    ||!search.visible||!saved.visible||!footer.visible
                    ||saved.height!==28 ||directory.height<15
                    ||directory.y < saved.y+saved.height
                    ||directory.y+directory.height>footer.y+1) {
                    return root.fail("SPLIT_OR_CLIPPED_RADIO // overview="
                        +String(overview.height)+" news="+String(news.height)
                        +" radio="+String(radio.height)
                        +" search="+String(search.height)
                        +" saved="+String(saved.height)
                        +" dir="+String(directory.height)
                        +" footer="+String(footer.height));
                }
                if(root.phase===3) {
                    root.newsBefore=news.mapToItem(media,0,0).y;
                    root.radioBefore=radio.mapToItem(media,0,0).y;
                    root.searchBefore=search.y;
                    root.footerBefore=footer.y;
                    directory.contentHeight=directory.height+160;
                    directory.contentY=60;
                    root.phase=4;return;
                }
                if(directory.contentY<=0
                    ||news.mapToItem(media,0,0).y!==root.newsBefore
                    ||radio.mapToItem(media,0,0).y!==root.radioBefore
                    ||search.y!==root.searchBefore
                    ||footer.y!==root.footerBefore)
                    return root.fail("NESTED_SCROLL_MOVED_FIXED_INSTRUMENT");
                root.done=true;
                console.log("M6_NATIVE_PASS // RSS_REPORTS_DIAGNOSTIC_SERVICES_EQUAL_BAYS");
                Qt.quit();
                return;
            }

            const services=find(media,"media-m1-services");
            const header=find(media,"media-m1-global-fixed-header");
            if(!services||!header){
                if(root.ticks>8)return root.fail("SERVICES_NOT_LOADED");
                return;
            }
            if(find(media,"media-m5-publisher-rss-owner")
                ||find(header,"media-m2-mode-feeds"))
                return root.fail("RSS_STILL_IN_SERVICES");
            if(root.phase===0) {
                if(!find(header,"media-m2-mode-runtime")
                    ||!find(header,"media-m2-mode-sources")
                    ||services.viewMode!=="runtime")
                    return root.fail("SERVICES_TWO_MODES");
                media.lastNewsObservedMs=1234567890;
                media.lastNewsFeedBadge="NEWS RECEIVED // 3";
                media.lastNewsRuntimeRows=[{name:"GDELT",state:"RECEIVED 3"}];
                media.lastNewsSourceRows=[{name:"GDELT DOC",state:"CONNECTED"}];
                find(header,"media-m2-mode-sources").clicked(null);
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(services.viewMode!=="sources"||services.newsSourceRows.length!==1)
                    return root.fail("SERVICES_SOURCE_SNAPSHOT");
                find(header,"media-m2-mode-runtime").clicked(null);
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(services.viewMode!=="runtime"
                    ||services.newsRuntimeRows.length!==1
                    ||services.newsFeedBadge!=="NEWS RECEIVED // 3")
                    return root.fail("SERVICES_RUNTIME_SNAPSHOT");
                media.subjectRoute="media/overview";
                root.phase=3;
                return;
            }
        }
    }
}
