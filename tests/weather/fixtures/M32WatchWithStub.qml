import QtQuick
import Quickshell
import "widgets/weather"
import "widgets/weather/StationNewsCatalogPolicy.js" as Catalog

// Actual MEDIA Loader and opt-in gate, fake Qt WATCH ONLY in disposable CI.
// The production module import is resolved from the CI-only stub qmldir.
ShellRoot {
    id: root
    property string phase: "idle"
    property bool done: false
    property int ticks: 0

    FloatingWindow {
        id: window
        title: "M32-WATCH-OPTIN-FAKE"
        visible: true
        implicitWidth: 900
        implicitHeight: 740
        StationMediaSubjectPane {
            id: media
            x: 12
            y: 12
            width: 840
            height: 620
            subjectRoute: "media/watch/reports"
        }
        StationWatchBridgeGate {
            id: gate
            optIn: true
            hostOpen: true
            viewport: media.activePlayerViewportRect
            sourceId: media.activeWatchSourceId
        }
    }

    function findHub(obj) {
        if (!obj) return null;
        if (obj.chooseItem !== undefined && obj.viewerOpen !== undefined
                && obj.activeWatchSourceId !== undefined)
            return obj;
        if (!obj.children) return null;
        for (let i = 0; i < obj.children.length; i++) {
            const h = findHub(obj.children[i]);
            if (h) return h;
        }
        return null;
    }
    function fail(message) {
        if (done) return;
        done = true;
        console.error("M32_FAIL // " + message + " phase=" + phase
                      + " gate=" + gate.bridgeStatus);
    }
    function pass() {
        done = true;
        console.log("M32_PASS // REAL_QML_GATE_AND_MEDIA optional_load=1 "
                    + "bbc_catalog_source=1 watch_candidate=1 viewer_close=1 "
                    + "other_source_denied=1 radio_zero=1 no_browser=1");
    }

    Timer {
        interval: 60
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            const hub = root.findHub(media);
            if (root.phase === "idle") {
                if (!hub || gate.bridgeStatus !== "WATCH_V2_AVAILABLE")
                    return;
                hub.chooseItem(Catalog.find("bbc"));
                root.phase = "watch";
            } else if (root.phase === "watch") {
                if (media.activeWatchSourceId !== "bbc"
                        || media.activePlayerViewportRect.width <= 0
                        || gate.bridgeStatus !== "WATCH_CANDIDATE_ONLY")
                    return;
                hub.closeViewer();
                root.phase = "closed";
            } else if (root.phase === "closed") {
                if (media.activeWatchSourceId !== ""
                        || media.activePlayerViewportRect.width !== 0
                        || gate.bridgeStatus !== "CLOSED"
                        || gate.connected)
                    return;
                hub.chooseItem(Catalog.find("aje"));
                root.phase = "other";
            } else if (root.phase === "other") {
                if (!hub.viewerOpen || media.activePlayerViewportRect.width <= 0
                        || media.activeWatchSourceId !== ""
                        || gate.bridgeStatus !== "CLOSED")
                    return;
                media.subjectRoute = "media/radio/full";
                root.phase = "radio";
            } else if (root.phase === "radio") {
                if (media.activeWatchSourceId !== ""
                        || media.activePlayerViewportRect.width !== 0)
                    return;
                root.pass();
            }
        }
    }
    Timer {
        interval: 13000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 150
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
