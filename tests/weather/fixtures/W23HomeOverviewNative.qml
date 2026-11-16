import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W23 // Disposable original HOME route test. No providers or disk writer.
ShellRoot {
    id: root
    property int ticks: 0
    property bool finished: false
    property string lastRoute: ""
    function fail(reason) {
        if(finished) return;
        finished=true;
        console.error("W23_HOME_RAIL_NATIVE_FAIL // "+reason);
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
        interval: 250
        running: !root.finished
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)return root.fail("TIMEOUT");
            if(!home.homeOverviewWorkspace)
                return root.fail("HOME_OVERVIEW_MODE_MISSING");
            const rail=home.homeOverviewRailItem;
            if(!rail || !rail.visible || rail.height!==56
               || rail.buttonRepeater.count!==3)
                return root.fail("HOME_SHARED_RAIL_NOT_VISIBLE");
            if(!rail.titleItem.visible ||
               rail.titleItem.text!=="HOME // OVERVIEW" ||
               rail.titleItem.height!==18)
                return root.fail("HOME_C44_HEADER_MISSING");
            if(rail.width<window.width-13)
                return root.fail("HOME_RAIL_NOT_FULL_WIDTH");
            for(let i=0;i<3;i++) {
                const button=rail.buttonRepeater.itemAt(i);
                if(!button || button.height!==27
                    || button.width<rail.width/3-8)
                    return root.fail("HOME_BUTTON_GEOMETRY_"+i);
                const dividerGap=rail.dividerItem.y
                    - button.mapToItem(rail,0,button.height).y;
                if(Math.abs(dividerGap-5)>0.1)
                    return root.fail("HOME_DIVIDER_GAP_"+dividerGap);
                if(i>0) {
                    const previous=rail.buttonRepeater.itemAt(i-1);
                    const gap=button.mapToItem(rail,0,0).x
                        - previous.mapToItem(rail,previous.width,0).x;
                    if(gap<7)
                        return root.fail("HOME_BUTTON_HORIZONTAL_GAP_"+gap);
                }
            }
            if(root.lastRoute==="") {
                rail.buttonRepeater.itemAt(0).clicked(null);
                if(root.lastRoute!=="home/auto")
                    return root.fail("HOME_BUTTON_NOT_ROUTED_"+root.lastRoute);
            }
            root.finished=true;
            window.contentItem.grabToImage(function(image) {
                if(image && image.saveToFile(
                    "/tmp/weather-w23-home-overview.png")) {
                    console.log("W23_HOME_PREVIEW_CAPTURED");
                    console.log("W23_HOME_RAIL_NATIVE_PASS // C44_FIVE_PIXEL_GAP_AND_ROUTE");
                } else console.error("W23_HOME_RAIL_NATIVE_FAIL // SCREENSHOT_MISSING");
                Qt.quit();
            },Qt.size(1040,600));
        }
    }
}
