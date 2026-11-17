import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W24 // Disposable HOME layout and click-switch regression.
// 520×300 + 440×275, synthetic/offline sources, no durable state writes.
ShellRoot {
    id: root
    property int ticks: 0
    property int phase: 0
    property bool capturing: false
    property bool finished: false
    property string lastRoute: ""
    readonly property var modeOrder: ["live","auto","quick","snapshot","live"]
    function fail(reason) {
        if(finished) return;
        finished=true;
        console.error("W24_HOME_INLINE_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        color: "black"
        visible: true
        Weather.StationHome {
            id: home
            anchors.fill: parent
            subjectRoute: ""
            workspaceSection: "overview"
            runtimeNowMs: 1794397200000
            weatherService: null
            spaceService: null
            nwsAlertSource: null
            historyService: null
            liveHistoryStore: null
            homeFavoritesStore: null
            onRouteRequested: function(path) { root.lastRoute=path; }
        }
    }
    Timer {
        interval: 200
        running: !root.finished
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>90)return root.fail("TIMEOUT");
            if(root.capturing)return;
            const rail=home.homeOverviewRailItem;
            const scroll=home.overviewViewportItem;
            const column=home.overviewContentItem;
            const live=home.overviewSnapshotItem;
            const autoRow=home.overviewRelevantItem;
            const quick=home.homeQuickItem;
            const mode=root.modeOrder[root.phase % 5];
            if(!home.homeOverviewWorkspace ||
               home.homeInlineMode!==mode || !rail || !scroll || !column)
                return root.fail("HOME_LOCAL_MODE_LOST_"+root.phase);
            if(!rail.visible || rail.height!==56 ||
                rail.buttonRepeater.count!==4 ||
                !rail.titleItem.visible ||
                rail.titleItem.text!=="HOME // OVERVIEW")
                return root.fail("HOME_SHARED_HEADER_MISSING");
            if(rail.width<window.width-13)
                return root.fail("HOME_LONG_BUTTON_WIDTH");
            for(let i=0;i<4;i++) {
                const button=rail.buttonRepeater.itemAt(i);
                if(!button || button.height!==27 ||
                   button.width<rail.width/4-8)
                    return root.fail("HOME_BUTTON_GEOMETRY_"+i);
                const gap=rail.dividerItem.y
                    - button.mapToItem(rail,0,button.height).y;
                if(Math.abs(gap-5)>0.1)
                    return root.fail("HOME_DIVIDER_GAP_"+gap);
                if(i>0) {
                    const prev=rail.buttonRepeater.itemAt(i-1);
                    const horizontal=button.mapToItem(rail,0,0).x
                        -prev.mapToItem(rail,prev.width,0).x;
                    if(horizontal<7)
                        return root.fail("HOME_HORIZONTAL_GAP_"+i);
                }
            }
            if(scroll.interactive || Math.abs(scroll.contentHeight-scroll.height)>1
               || scroll.contentY>0.5
               || column.y+column.implicitHeight>scroll.height+1)
                return root.fail("HOME_SHOULD_NOT_SCROLL_OR_CLIP_"+
                    mode+"_"+column.implicitHeight+"/"+scroll.height);
            if(root.lastRoute!=="")
                return root.fail("HOME_BUTTON_REDIRECTED_TO_"+root.lastRoute);
            if(mode==="live") {
                if(!live.visible || !autoRow.visible || quick.visible ||
                   live.y+live.height>=autoRow.y)
                    return root.fail("LIVE_TOP_AUTO_BOTTOM_LOST");
            } else if(mode==="auto") {
                if(live.visible || quick.visible || !autoRow.visible)
                    return root.fail("AUTO_NOT_SOLO");
            } else if(mode==="quick") {
                if(live.visible || !quick.visible || autoRow.visible)
                    return root.fail("QUICK_NOT_SOLO");
            } else {
                if(!live.visible || quick.visible || autoRow.visible)
                    return root.fail("SNAPSHOT_NOT_SOLO");
            }
            root.capturing=true;
            const name="/tmp/weather-w24-home-"+
                (root.phase>=5 ? "compact-" : "wide-")+mode+".png";
            window.contentItem.grabToImage(function(image) {
                if(!image || !image.saveToFile(name))
                    return root.fail("SCREENSHOT_MISSING_"+name);
                console.log("W24_HOME_CAPTURED // "+name);
                root.phase++;
                root.capturing=false;
                if(root.phase>=10) {
                    root.finished=true;
                    console.log("W24_HOME_INLINE_NATIVE_PASS // FIVE_MODES_520_440_NO_SCROLL");
                    Qt.quit();
                    return;
                }
                if(root.phase===5) {
                    window.width=440;
                    window.height=275;
                    return;
                }
                const next=root.modeOrder[root.phase%5];
                const index=next==="live" ? 0 : next==="auto" ? 1
                    : next==="quick" ? 2 : 3;
                rail.buttonRepeater.itemAt(index).clicked(null);
            },Qt.size(window.width*2,window.height*2));
        }
    }
}
