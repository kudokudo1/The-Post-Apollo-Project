import QtQuick
import QtQuick.Window
import Quickshell
import "../../../widgets/weather" as Weather

// Disposable offscreen native QML smoke. No real service or network, no
// desktop compositor, no user files, and no real Weather Station activation.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false

    Window {
        id: testWindow
        visible: true
        width: 520
        height: 340
        color: "black"
        Weather.StationCosmosModesPane {
            id: focused
            anchors.fill: parent
            subjectRoute: "cosmos/planets-stars/planet-clock"
            weatherService: null
            spaceService: null
            runtimeNowMs: Date.UTC(2026,10,5,13,0)
            onRouteRequested: function(path) {
                root.requestedPath = path;
            }
        }
    }
    property string requestedPath: ""

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("C5_NATIVE_FAIL // " + reason);
        Qt.quit();
    }
    function succeed() {
        if (done) return;
        done = true;
        console.log("C5_NATIVE_PASS // MODES_LOAD_WITHOUT_SOURCES");
        Qt.quit();
    }

    Timer {
        interval: 160
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks > 25) { root.fail("TIMEOUT"); return; }
            if (root.phase === 0) {
                if (focused.family !== "astronomy"
                        || focused.kind !== "planet-clock")
                    return root.fail("WRONG_CLOCK_ROUTE");
                if (focused.displayedPlanetRows.length !== 5)
                    return root.fail("EMPTY_PLANET_CLOCK_LANES");
                if (focused.sourceStatus === "")
                    return root.fail("NO_MISSING_SOURCE_STATUS");
                focused.routeRequested("cosmos/planets-stars/celestial-fix");
                if (root.requestedPath !== "cosmos/planets-stars/celestial-fix")
                    return root.fail("ROUTE_SIGNAL_FAILED");
                root.phase = 1;
                focused.subjectRoute = "cosmos/events/meteors";
            } else if (root.phase === 1) {
                if (focused.kind !== "meteors" || focused.family !== "events")
                    return root.fail("WRONG_METEOR_ROUTE");
                if (focused.sourceStatus === "")
                    return root.fail("EMPTY_METEOR_STATUS");
                root.phase = 2;
                focused.subjectRoute = "cosmos/sun/position";
            } else if (root.phase === 2) {
                if (focused.kind !== "solar-path" || focused.family !== "sun")
                    return root.fail("WRONG_SUN_ROUTE");
                if (focused.sourceStatus === "")
                    return root.fail("EMPTY_SOLAR_STATUS");
                root.succeed();
            }
        }
    }
}
