import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W3 // 520x300 Station with its ordinary 40px HOME deck underneath:
// inspect the actual persistent StationHome renderer and its unfetched views.
// No provider process is started and the operator's desktop is untouched.
ShellRoot {
    id: root
    property bool done: false
    property int ticks: 0
    property int phase: 0
    function find(item,name) {
        if (!item) return null;
        if (item.objectName===name) return item;
        for(const child of (item.children||[])) {
            const found=find(child,name);
            if(found)return found;
        }
        return null;
    }
    function fail(why) {
        if(done)return;
        done=true;
        console.error("W3_NATIVE_FAIL // "+why);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationHome {
            id: home
            x: 0
            y: 0
            width: window.width
            height: window.height-40
            workspaceSection: "history"
        }
    }
    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>28)return root.fail("TIMEOUT");
            const scroll=find(home,"home-w3-content-scroll");
            const content=find(home,"home-w3-content-column");
            const charts=find(home,"home-w3-history-relations");
            const archive=find(home,"home-w3-history-archive");
            const summaries=find(home,"home-w3-history-summary-cards");
            const days=find(home,"home-w3-history-daily-cards");
            const sources=find(home,"home-w3-sources-title");
            const runtime=find(home,"home-w3-sources-runtime");
            const health=find(home,"home-w3-sources-health");
            const services=find(home,"home-w6-services-console");
            if(!scroll||!content||!charts||!archive||!summaries
                ||!days||!sources||!runtime||!health) {
                if(root.ticks>7)return root.fail("HOME_W3_NODES_MISSING");
                return;
            }
            if(root.phase===0) {
                const bottom=days.mapToItem(home,0,days.height).y;
                if(!charts.visible||!archive.visible||!summaries.visible||!days.visible
                    ||sources.visible||runtime.visible||health.visible
                    ||scroll.interactive||scroll.contentHeight>scroll.height+1
                    ||bottom>home.height-2||days.height!==35
                    ||summaries.height!==58||charts.height!==72)
                    return root.fail("HISTORY_OVERFLOW // content="
                        +scroll.contentHeight+" viewport="+scroll.height
                        +" contentImplicit="+content.implicitHeight
                        +" lastBottom="+bottom+" charts="+charts.height);
                home.workspaceSection="sources";
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(!sources.visible||!runtime.visible||!health.visible
                    ||charts.visible||archive.visible||!scroll.interactive)
                    return root.fail("SOURCES_VISIBILITY_OR_OWNER");
                home.workspaceSection="overview";
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(sources.visible||runtime.visible||health.visible
                    ||!scroll.interactive)
                    return root.fail("OVERVIEW_LEAKS_SOURCES");
                // Existing legacy HOME aliases may be selected without a
                // second service. Source-only layout remains the same.
                home.workspaceSection="health";
                root.phase=3;return;
            }
            if(root.phase===3) {
                if(!runtime.visible||!health.visible
                    ||charts.visible||archive.visible)
                    return root.fail("LEGACY_HEALTH_BOOKMARK_NOT_SOURCES");
                root.done=true;
                console.log("W3_NATIVE_PASS // SOURCES_LAST_AND_HISTORY_FITS_520X300");
                Qt.quit();
            }
        }
    }
}
