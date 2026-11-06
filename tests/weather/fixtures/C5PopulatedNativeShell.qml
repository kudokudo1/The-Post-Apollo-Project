import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// Synthetic DATA ONLY for an offscreen source→renderer smoke. No external
// provider response is fabricated in production; existing QML is unmodified.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property string route: "cosmos/planets-stars/planet-clock"

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
        visible: true
        width: 520
        height: 340
        color: "black"
        Weather.StationCosmosModesPane {
            id: focused
            anchors.fill: parent
            subjectRoute: root.route
            weatherService: fakeWeather
            spaceService: null
            runtimeNowMs: Date.UTC(2026, 10, 5, 13, 0)
        }
    }

    function findNamed(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        const children = item.children || [];
        for (let i=0;i<children.length;i++) {
            const hit = findNamed(children[i], name);
            if (hit) return hit;
        }
        return null;
    }

    function countNamed(item, name) {
        if (!item) return 0;
        let count = item.objectName === name ? 1 : 0;
        const children = item.children || [];
        for (let i=0;i<children.length;i++)
            count += countNamed(children[i], name);
        return count;
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("C5_POPULATED_FAIL // " + reason
            + " // route=" + focused.subjectRoute
            + " kind=" + focused.kind
            + " clock=" + focused.visibleClockLaneCount
            + " cards=" + (focused.cards ? focused.cards.length : "null"));
        Qt.quit();
    }

    function succeed() {
        if (done) return;
        done = true;
        console.log("C5_POPULATED_PASS // SUN_ARC PLANET_EVENTS ISS_TIMES ACTIVE_METEORS");
        Qt.quit();
    }

    Timer {
        interval: 110
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks > 45) return root.fail("TIMEOUT");
            if (root.phase === 0) {
                if (!focused.planetSource || !focused.planetSource.configured)
                    return root.fail("MISSING_USNO_PROVIDER_CONFIGURATION");
                // Stop the network collector; supply a dated sample through
                // its real read-only presentation interface.
                focused.planetSource.active = false;
                focused.planetSource.loadedKey = focused.planetSource.currentKey;
                focused.planetSource.rows = [{
                    name:"MERCURY", date:focused.civilDate, status:"NORMAL",
                    rise:"06:15", transit:"12:00", set:"18:20"
                }];
                focused.planetSource.ready = true;
                root.phase = 1;
            } else if (root.phase === 1) {
                if (focused.planetRows[0].events.length !== 3)
                    return root.fail("USNO_RECORDS_NOT_MAPPED_TO_EVENT_CLOCK");
                if (countNamed(focused.instrumentLoader.item,
                        "cosmos-c5-planet-event-marker") !== 3)
                    return root.fail("USNO_EVENT_MARKERS_NOT_RENDERED");
                root.phase = 2;
                root.route = "cosmos/events/iss";
            } else if (root.phase === 2) {
                if (!focused.issSource || !focused.issSource.configured)
                    return root.fail("ISS_LOCATION_NOT_CONFIGURED");
                focused.issSource.active = false;
                focused.issSource.passes = [{
                    rise:{timeUtc:"2026-11-05 12:00Z"},
                    culminate:{degrees:42.3,timeUtc:"2026-11-05 12:04Z"}
                }];
                focused.issSource.ready = true;
                root.phase = 3;
            } else if (root.phase === 3) {
                if (!focused.cards || focused.cards.length !== 1
                        || focused.cards[0].detail.indexOf("12:04Z") < 0
                        || focused.cards[0].detail.indexOf("undefined") >= 0)
                    return root.fail("ISS_RECORD_FIELDS_NOT_RENDERED");
                if (countNamed(focused.instrumentLoader.item,
                        "cosmos-c5-source-card") !== 1)
                    return root.fail("ISS_CARD_NOT_IN_VISUAL_TREE");
                root.phase = 4;
                root.route = "cosmos/events/meteors";
            } else if (root.phase === 4) {
                if (!focused.meteorSource || !focused.meteorSource.configured)
                    return root.fail("IAU_LOCATION_NOT_CONFIGURED");
                focused.meteorSource.active = false;
                focused.meteorSource.activeShowers = [{
                    name:"SAMPLE ACTIVE",peakUtc:"2026-11-05 23:00Z",
                    code:"TEST-A"
                }];
                focused.meteorSource.upcomingShowers = [{
                    name:"SAMPLE FUTURE",peakUtc:"2026-11-12 23:00Z",
                    code:"TEST-B"
                }];
                focused.meteorSource.ready = true;
                root.phase = 5;
            } else if (root.phase === 5) {
                if (!focused.cards || focused.cards.length !== 2
                        || focused.cards[0].info !== "ACTIVE NOW"
                        || focused.cards[1].info !== "UPCOMING")
                    return root.fail("ACTIVE_IAU_RECORDS_MISSING");
                if (countNamed(focused.instrumentLoader.item,
                        "cosmos-c5-meteor-card") !== 2)
                    return root.fail("IAU_CARDS_NOT_RENDERED");
                root.phase = 6;
                root.route = "cosmos/sun/position";
            } else if (root.phase === 6) {
                const sun = findNamed(focused.instrumentLoader.item,
                    "cosmos-c5-sun-path");
                if (!sun || !sun.solarData || !sun.solarData.ready
                        || sun.solarData.rows.length < 60)
                    return root.fail("SOURCE_BACKED_SOLAR_ARC_NOT_RENDERED");
                if (!focused.skyFeed || focused.skyFeed.focusedLocalMinute < 0)
                    return root.fail("VERIFIED_LOCAL_MINUTE_MISSING");
                root.succeed();
            }
        }
    }
}
