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
            if(!rail || !rail.visible || rail.height!==31 ||
               rail.buttonRepeater.count!==3)
                return root.fail("MISSING_SHARED_MAGICK_RAIL");
            if(Math.abs(rail.width-(window.width-12))>1)
                return root.fail("MAGICK_RAIL_NOT_FULL_WIDTH");
            for(let i=0;i<3;i++) {
                const button=rail.buttonRepeater.itemAt(i);
                if(!button || button.width<rail.width/3-6
                   || button.height!==25)
                    return root.fail("MAGICK_LONG_BUTTON_GEOMETRY_"+i);
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
