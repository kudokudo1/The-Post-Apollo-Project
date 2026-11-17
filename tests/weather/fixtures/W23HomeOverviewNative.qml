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
    // Native synthetic history uses the same existing alignment/graph code.
    property var aqiSamples: []
    property var weatherSamples: []
    Component.onCompleted: {
        const start=1794397200000-8*600000;
        for(let i=0;i<8;i++) {
            const ms=start+i*600000;
            aqiSamples.push({
                observedAtMs:ms, receivedAtMs:ms,
                payload:{aqi:32+i*4}
            });
            weatherSamples.push({
                observedAtMs:ms, receivedAtMs:ms,
                payload:{humidity:41+i*2,windMph:5+(i%3)*3}
            });
        }
    }
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
            // No network call: only the coordinates needed to scope the
            // existing historical samples and two fake ready=false flags.
            weatherService: ({
                latitude:38.9, longitude:-77.03, ready:false,
                aqiReady:false, hourlyForecast:[]
            })
            spaceService: null
            nwsAlertSource: null
            historyService: null
            liveHistoryStore: ({
                revision:1,
                count:function(source,scope,now) { return 8; },
                samples:function(source,scope,now) {
                    return source==="air-quality"
                        ? root.aqiSamples : root.weatherSamples;
                }
            })
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
            const charts=home.homeOverviewGraphItem;
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
                if(!charts || !charts.visible || charts.height!==72
                    || !live.visible || !autoRow.visible || quick.visible
                    || charts.y+charts.height>=live.y
                    || live.y+live.height>=autoRow.y)
                    return root.fail("W25_GRAPHS_TOP_LIVE_MIDDLE_AUTO_BOTTOM");
                if(Math.abs(live.height-46)>0.1 ||
                   Math.abs(autoRow.height-46)>0.1)
                    return root.fail("W25_CARD_ROWS_NOT_COMPACT");
                if(charts.children.length<2
                   || !charts.children[0].chartReady
                   || !charts.children[1].chartReady)
                    return root.fail("W25_ORIGINAL_GRAPHS_NO_ALIGNED_LINES");
                if(autoRow.mapToItem(home,0,autoRow.height).y
                    <scroll.height-5)
                    return root.fail("W25_AUTO_NOT_BOTTOM_ANCHORED");
            } else if(mode==="auto") {
                if(live.visible || quick.visible || !autoRow.visible
                   || charts.visible)
                    return root.fail("AUTO_NOT_SOLO");
            } else if(mode==="quick") {
                if(live.visible || !quick.visible || autoRow.visible
                   || charts.visible)
                    return root.fail("QUICK_NOT_SOLO");
            } else {
                if(!live.visible || quick.visible || autoRow.visible
                   || charts.visible)
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
                    console.log("W25_HOME_GRAPHS_NATIVE_PASS // TWO_ORIGINAL_LINE_CHARTS_TOP_COMPACT_LIVE_AUTO_BOTTOM");
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
