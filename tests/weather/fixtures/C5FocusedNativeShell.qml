import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// Disposable offscreen native QML smoke. No real service or network, no
// desktop compositor, no user files, and no real Weather Station activation.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false

    // Fake coordinates and the already supported source offset only.
    // No fake USNO or NOAA observations: we test source activation, not
    // fabricate successful provider responses.
    QtObject {
        id: fakeWeather
        property real latitude: 38.9
        property real longitude: -76.75
        property var dailyForecast: []
        property int airQualityUtcOffsetMinutes: -300
        property bool ready: false
        property bool loading: false
        property string localObservationDateTime: ""
        property real localObservationAnchorMs: 0
    }

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
            weatherService: fakeWeather
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
        console.log("C5_NATIVE_PASS // ROUTED_HIDDEN_SOURCES_ACTIVE");
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
                if (focused.displayedPlanetRows.length !== 5
                        || focused.visibleClockLaneCount !== 5)
                    return root.fail("EMPTY_PLANET_CLOCK_LANES // rowdata="
                        + focused.displayedPlanetRows.length
                        + " rendered=" + focused.visibleClockLaneCount
                        + " mounted=" + focused.instrumentMounted
                        + " state=" + focused.instrumentLoadState
                        + " mode=" + focused.kind);
                if (focused.sourceStatus === "")
                    return root.fail("NO_MISSING_SOURCE_STATUS");
                if (!focused.planetSource || !focused.planetSource.configured
                    || !focused.planetSource.active)
                    return root.fail("PLANET_PROVIDER_NOT_ACTIVE_OR_CONFIGURED");
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
                if (!focused.meteorSource || !focused.meteorSource.configured)
                    return root.fail("METEOR_PROVIDER_NOT_CONFIGURED");
                // Simulate the visual source being hidden offscreen. The
                // selected route is still active, so acquisition must remain.
                focused.skyFeed.visible = false;
                if (!focused.meteorSource.active)
                    return root.fail("HIDDEN_SOURCE_LOST_ACTIVE_ROUTE");
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
