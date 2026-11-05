import QtQuick
import Quickshell
import "widgets/weather"

// Native QtQuick behavior proof with no WebEngine, internet, Kitty or Sway.
// Uses the actual StationMediaSubjectPane and nested StationNewsHub Loader.
ShellRoot {
    id: root
    property string phase: "directEmpty"
    property int ticks: 0
    property bool finished: false

    FloatingWindow {
        id: win
        title: "M31-WEATHER-MEDIA-VIEWPORT"
        visible: true
        implicitWidth: 950
        implicitHeight: 750
        StationMediaSubjectPane {
            id: media
            x: 20
            y: 20
            width: 840
            height: 620
            subjectRoute: "media/watch/live"
        }
    }

    function hubIn(item) {
        if (!item)
            return null;
        if (item.viewerOpen !== undefined
                && item.playerViewportRect !== undefined
                && item.closeViewer !== undefined)
            return item;
        if (!item.children)
            return null;
        for (let i = 0; i < item.children.length; i++) {
            const result = hubIn(item.children[i]);
            if (result) return result;
        }
        return null;
    }
    function empty(rect) {
        return !rect || rect.x === 0 && rect.y === 0
            && rect.width === 0 && rect.height === 0;
    }
    function within(rect) {
        return rect && isFinite(rect.x) && isFinite(rect.y)
            && rect.x >= 0 && rect.y >= 0
            && rect.width > 0 && rect.height > 0
            && rect.x + rect.width <= media.width
            && rect.y + rect.height <= media.height;
    }
    function show(hub) {
        if (!hub) return false;
        hub.chosenRecord = {
            id: "m31-offline-synthetic",
            title: "M31 OFFLINE VIEWPORT TEST",
            url: "https://www.bbc.com/"
        };
        hub.viewerOpen = true;
        return true;
    }
    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("M31_FAIL // " + reason + " phase=" + phase);
    }
    function pass() {
        finished = true;
        console.log("M31_PASS // NATIVE_MEDIA_VIEWPORT direct=1 hide=1 "
                    + "overview_nested=1 radio_zero=1 route_clear=1 "
                    + "hidden_pane_zero=1 no_browser=1 no_kitty=1");
    }

    Timer {
        interval: 65
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            const hub = root.hubIn(media);
            const rect = media.activePlayerViewportRect;
            if (root.phase === "directEmpty") {
                if (!hub || !root.empty(rect)) return;
                root.show(hub);
                root.phase = "directOpen";
            } else if (root.phase === "directOpen") {
                if (!root.within(rect)) return;
                hub.closeViewer();
                root.phase = "directClosed";
            } else if (root.phase === "directClosed") {
                if (!root.empty(rect)) return;
                media.subjectRoute = "media/overview";
                root.phase = "overviewEmpty";
            } else if (root.phase === "overviewEmpty") {
                if (!hub || !root.empty(rect)) return;
                root.show(hub);
                root.phase = "overviewOpen";
            } else if (root.phase === "overviewOpen") {
                if (!root.within(rect)) return;
                // This viewport is within the reports BAY, not radio's bay.
                if (rect.y + rect.height > media.height / 2 + 1) {
                    root.fail("OVERVIEW_NEWS_OUTSIDE_REPORTS_BAY");
                    return;
                }
                media.subjectRoute = "media/radio/full";
                root.phase = "radioZero";
            } else if (root.phase === "radioZero") {
                if (!root.empty(rect)) return;
                media.subjectRoute = "media/watch/live";
                root.phase = "routeCleared";
            } else if (root.phase === "routeCleared") {
                if (!hub || !root.empty(rect)) return;
                root.show(hub);
                root.phase = "hiddenOpen";
            } else if (root.phase === "hiddenOpen") {
                if (!root.within(rect)) return;
                media.visible = false;
                root.phase = "hiddenZero";
            } else if (root.phase === "hiddenZero") {
                if (!root.empty(rect)) return;
                media.visible = true;
                root.phase = "returnedZero";
            } else if (root.phase === "returnedZero") {
                if (!root.empty(rect)) return;
                root.pass();
            }
        }
    }
    Timer {
        interval: 14000
        repeat: false
        running: !root.finished
        onTriggered: root.fail("TIMEOUT_OR_NO_REACTIVE_VIEWPORT")
    }
    Timer {
        interval: 175
        repeat: false
        running: root.finished
        onTriggered: Qt.quit()
    }
}
