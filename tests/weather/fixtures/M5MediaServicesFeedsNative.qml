import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M5 // Actual MEDIA surface in 520x300 disposable headless Qt.
// Provider activation is off: inspecting SERVICES never triggers RSS/GDELT.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
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
        let result=item.objectName===name?1:0;
        for(const child of (item.children||[]))
            result+=count(child,name);
        return result;
    }
    function fail(msg) {
        if(done)return;
        done=true;
        console.error("M5_NATIVE_FAIL // "+msg);
        Qt.quit();
    }
    Window {
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationMediaSubjectPane {
            id:media
            anchors.fill:parent
            subjectRoute:"media/services/health"
            providerActivationAllowed:false
        }
    }
    Timer {
        running:!root.done
        interval:180
        repeat:true
        onTriggered: {
            root.ticks++;
            if(root.ticks>30)return root.fail("TIMEOUT");
            const services=find(media,"media-m1-services");
            const runtime=find(media,"media-m5-runtime-content");
            const sources=find(media,"media-m5-source-content");
            const feedLoader=find(media,"media-m5-publisher-feed-loader");
            const header=find(media,"media-m1-global-fixed-header");
            if(!services||!runtime||!sources||!feedLoader||!header) {
                if(root.ticks>8) {
                    const missing=[
                        ["services",services],["runtime",runtime],
                        ["sources",sources],["feedLoader",feedLoader],
                        ["header",header]].filter(function(x){return !x[1];})
                           .map(function(x){return x[0];}).join(",");
                    return root.fail("MISSING_NODES // "+missing
                        +" // mediaKind="+String(media.kind)
                        +" // loaded="+String(media.loadedServices)
                        +" // children="+String(media.children.length));
                }
                return;
            }
            if(root.phase===0) {
                const feedsButton=find(header,"media-m2-mode-feeds");
                if(!feedsButton ||services.viewMode!=="runtime"
                    ||services.stationOpen ||feedLoader.active
                    ||count(media,"media-m5-publisher-rss-owner")!==0)
                    return root.fail("SERVICES_INITIAL_MODE_OR_RSS_MOUNT");
                media.lastNewsObservedMs=1234567890;
                media.lastNewsFeedBadge="NEWS RECEIVED // 3";
                media.lastNewsRuntimeRows=[{name:"GDELT",state:"RECEIVED 3"}];
                media.lastNewsSourceRows=[{name:"GDELT DOC",state:"CONNECTED"}];
                feedsButton.clicked(null);
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(services.viewMode!=="feeds"||!feedLoader.active
                    ||count(media,"media-m5-publisher-rss-owner")!==1
                    ||!find(media,"media-m5-services-body-scroll")
                    ||services.stationOpen
                    ||services.newsFeedBadge!=="NEWS RECEIVED // 3")
                    return root.fail("FEEDS_MOUNT_OR_SNAPSHOT_BOUNDARY");
                const runtimeButton=find(header,"media-m2-mode-runtime");
                if(!runtimeButton)return root.fail("MISSING_RUNTIME_BUTTON");
                runtimeButton.clicked(null);
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(services.viewMode!=="runtime"||feedLoader.active
                    ||count(media,"media-m5-publisher-rss-owner")!==0
                    ||!runtime.visible ||services.newsRuntimeRows.length!==1)
                    return root.fail("RUNTIME_NOT_RESTORED");
                const sourcesButton=find(header,"media-m2-mode-sources");
                if(!sourcesButton)return root.fail("MISSING_SOURCES_BUTTON");
                sourcesButton.clicked(null);
                root.phase=3;return;
            }
            if(root.phase===3) {
                if(services.viewMode!=="sources" ||!sources.visible
                    ||services.newsSourceRows.length!==1
                    ||count(media,"media-m5-publisher-rss-owner")!==0)
                    return root.fail("SOURCE_SNAPSHOT_OR_LAZY_RSS");
                media.subjectRoute="media/overview";
                root.phase=4;return;
            }
            if(root.phase===4) {
                const news=find(media,"media-m3-news-top-bay");
                const radio=find(media,"media-m3-full-radio-bottom-bay");
                const feed=find(media,"media-m5-publisher-rss-owner");
                if(!news||!radio||feed ||news.height<60
                    ||radio.y+radio.height>media.height+1
                    ||media.loadedNews===null)
                    return root.fail("OVERVIEW_HEIGHT_OR_NEWS_OWNER");
                root.done=true;
                console.log("M5_NATIVE_PASS // SERVICES_RSS_ONLY_NEWS_PLUS8_FIXED_RADIO");
                Qt.quit();
            }
        }
    }
}
