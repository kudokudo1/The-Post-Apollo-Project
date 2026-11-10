import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationWorkspaceNavigationPolicy.js" as Workspace

// M3 // Real OVERVIEW pane, real NEWS + RADIO components; provider
// activation suppressed for isolated native geometry and route verification.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property real radioTopBefore: -1
    property real newsTopBefore: -1
    property real searchYBefore: -1
    property real footerYBefore: -1
    function find(item,name) {
        if (!item) return null;
        if (item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const result=find(child,name);
            if(result)return result;
        }
        return null;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("M3_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id:window
        width:520
        height:300
        visible:true
        color:"black"
        Weather.StationMediaSubjectPane {
            id: media
            anchors.fill: parent
            subjectRoute:"media/overview"
            providerActivationAllowed:false
        }
    }
    Timer {
        interval:180
        repeat:true
        running:!root.done
        onTriggered:{
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            // Switching to SERVICES deliberately unmounts the OVERVIEW
            // Loader. Verify the destination before looking for old nodes.
            if(root.phase===3) {
                const services=find(media,"media-m1-services");
                if(!services ||media.kind!=="services") {
                    if(root.ticks>12)
                        return root.fail("SERVICES_BOTTOM_ROUTE_NOT_RESOLVED");
                    return;
                }
                root.done=true;
                console.log("M3_NATIVE_PASS // NEWS_TOP_FULL_RADIO_BOTTOM_SERVICES_TAB");
                Qt.quit();
                return;
            }
            const overview=find(media,"media-m3-overview");
            const overviewScroll=find(media,"media-m3-overview-scroll");
            const news=find(media,"media-m3-news-top-bay");
            const radioBay=find(media,"media-m3-full-radio-bottom-bay");
            const radio=find(media,"media-m3-overview-full-radio");
            const fixedSearch=find(media,"media-m1-radio-search-fixed");
            const saved=find(media,"media-m2-radio-fixed-saved");
            const directory=find(media,"media-m1-radio-directory-scroll");
            const transport=find(media,"media-m1-radio-transport-fixed");
            const header=find(media,"media-m1-global-fixed-header");
            if(!overview||!news||!radioBay||!radio
                ||!fixedSearch||!saved||!directory||!transport||!header) {
                if(root.ticks>=8) {
                    const nodes=[
                        ["overview",overview],
                        ["news",news],["radioBay",radioBay],
                        ["radio",radio],["search",fixedSearch],
                        ["saved",saved],["directory",directory],
                        ["transport",transport],["header",header]];
                    const missing=nodes.filter(function(pair){return !pair[1];})
                        .map(function(pair){return pair[0];}).join(",");
                    return root.fail("MISSING_NODES // "+missing
                        +" // childCount="+String(media.children.length)
                        +" // paneKind="+String(media.kind));
                }
                return;
            }
            if(root.phase===0) {
                const modes=Workspace.tabsFor("media/overview");
                const live=find(header,"media-m2-mode-live");
                const reports=find(header,"media-m2-mode-reports");
                if(modes.length!==6
                    ||modes[5].path!=="media/services/health"
                    ||Workspace.selectedGroup("media/services/health")!=="services"
                    ||!live||!reports
                    ||!media.loadedNews
                    ||media.loadedNews.section!=="REPORTS"
                    ||radio.subjectRoute!=="media/radio/full"
                    ||radio.compactOverview ||!radio.embeddedHeader
                    ||!radio.overviewDocked ||overviewScroll
                    ||news.y!==0
                    ||Math.abs(news.height-radioBay.height)>1
                    ||radioBay.y<news.y+news.height
                    ||radioBay.y+radioBay.height>overview.height+1
                    ||radioBay.height<95
                    ||!fixedSearch.visible ||!saved.visible ||!transport.visible
                    ||directory.height<15 ||directory.y<saved.y+saved.height
                    ||directory.y+directory.height>transport.y+1)
                    return root.fail("NEWS_FIRST_FULL_RADIO_BOUNDS // height="
                       +String(overview.height)+" radio="+String(radio.height)
                       +" dir="+String(directory.height));
                root.radioTopBefore=radio.mapToItem(media,0,0).y;
                root.newsTopBefore=news.mapToItem(media,0,0).y;
                root.searchYBefore=fixedSearch.y;
                root.footerYBefore=transport.y;
                live.clicked(null);
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(!media.loadedNews ||media.loadedNews.section!=="LIVE"
                    ||media.subjectRoute!=="media/overview")
                    return root.fail("OVERVIEW_NEWS_FILTER_LEFT_SCREEN");
                // Force scrollable synthetic directory content; the
                // real provider is deliberately disabled in this fixture.
                directory.contentHeight=directory.height+160;
                directory.contentY=75;
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(directory.contentY<=0
                    ||Math.abs(transport.y+transport.height-radio.height+3)>1
                    ||radio.mapToItem(media,0,0).y!==root.radioTopBefore
                    ||news.mapToItem(media,0,0).y!==root.newsTopBefore
                    ||fixedSearch.y!==root.searchYBefore
                    ||transport.y!==root.footerYBefore
                    ||!saved.visible||!fixedSearch.visible)
                    return root.fail("DIRECTORY_SCROLL_MOVED_STATIONARY_INSTRUMENT");
                media.subjectRoute="media/services/health";
                root.phase=3;return;
            }

        }
    }
}
