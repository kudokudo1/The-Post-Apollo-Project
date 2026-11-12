import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W21 // Disposable native MAGICK Overview, using no live accounts,
// providers, JPL calculation or saved-state writes.
ShellRoot {
    id: root
    property int ticks: 0
    property bool finished: false
    property string lastRoute: ""
    function fail(reason) {
        if(finished)return;
        finished=true;
        console.error("W21_MAGICK_RAIL_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        color: "black"
        visible: true
        Weather.StationMagickSubjectPane {
            id: magick
            anchors.fill: parent
            subjectRoute: "magick/overview"
            runtimeNowMs: 1794397200000
            weatherService: null
            celestialSource: null
            onRouteRequested: function(path) {
                root.lastRoute=path;
            }
        }
    }
    Timer {
        interval: 250
        running: !root.finished
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)
                return root.fail("TIMEOUT");
            const rail=magick.overviewRailItem;
            if(!rail || !rail.visible || rail.height!==49 ||
               rail.buttonRepeater.count!==3)
                return root.fail("MISSING_SHARED_MAGICK_RAIL");
            if(Math.abs(rail.width-(window.width-12))>1)
                return root.fail("MAGICK_RAIL_NOT_FULL_WIDTH");
            if(!rail.titleItem.visible ||
               rail.titleItem.text!=="MAGICK // OVERVIEW"
               || rail.titleItem.height!==18)
                return root.fail("W22_MAGICK_HEADER_MISSING");
            for(let i=0;i<3;i++) {
                const button=rail.buttonRepeater.itemAt(i);
                if(!button || button.width<rail.width/3-7
                   || button.height!==24)
                    return root.fail("MAGICK_LONG_BUTTON_GEOMETRY_"+i);
                if(i>0) {
                    const prev=rail.buttonRepeater.itemAt(i-1);
                    const gap=button.mapToItem(rail,0,0).x
                          - prev.mapToItem(rail,prev.width,0).x;
                    if(gap<7)
                        return root.fail("W22_MAGICK_TAB_GAP_TOO_NARROW_"+i);
                }
            }
            if(root.lastRoute==="") {
                rail.buttonRepeater.itemAt(1).clicked(null);
                if(root.lastRoute!=="magick/astrology/charts")
                    return root.fail("MAGICK_BUTTON_NOT_ROUTED // "+root.lastRoute);
            }
            root.finished=true;
            window.contentItem.grabToImage(function(image) {
                if(image && image.saveToFile(
                      "/tmp/weather-w21-magick-overview.png")) {
                    console.log("W21_MAGICK_PREVIEW_CAPTURED");
                    console.log("W21_MAGICK_RAIL_NATIVE_PASS // FULL_WIDTH_ROUTE_AND_DIVIDER");
                } else {
                    console.error("W21_MAGICK_RAIL_NATIVE_FAIL // SCREENSHOT_MISSING");
                }
                Qt.quit();
            },Qt.size(1040,600));
        }
    }
}
