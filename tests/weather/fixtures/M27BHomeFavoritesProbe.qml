import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather"

// W2b disposable native card-pin and FileView lifecycle fixture.
// Test data is synthetic and never imported from real user preferences.
ShellRoot {
    id: root
    readonly property string phase: Quickshell.env("W2B_PHASE")
    property bool done: false
    property int ticks: 0
    property bool pinAnnounced: false

    WeatherHomeFavoritesStore { id: favorites }

    FloatingWindow {
        id: testWindow
        title: "W2B-HOME-FAVORITES"
        visible: true
        implicitWidth: 490
        implicitHeight: 250

        StationHomeMetricCard {
            id: card
            anchors.centerIn: parent
            width: 420
            height: 124
            title: "SYNTHETIC SKY WATCH"
            valueText: "NO LIVE SAMPLE"
            detailText: "TEST ONLY"
            provenanceText: "FRESHNESS UNVERIFIED"
            pinEnabled: true
            pinned: favorites.cardKeys.indexOf("sky|next-hours") >= 0
            pinAvailable: favorites.writable
            onPinRequested: {
                if (root.phase !== "save") {
                    root.fail("NON_SAVE_PHASE_CLICK");
                    return;
                }
                if (!favorites.toggleCardFavorite("sky","next-hours"))
                    root.fail("PIN_ACTION_REJECTED");
                else
                    console.log("W2B_PIN_CLICK_ACCEPTED");
            }
        }
    }

    function find(item, wanted) {
        if (!item) return null;
        if (item.label !== undefined && item.label === wanted &&
            item.available !== undefined) return item;
        if (!item.children) return null;
        for (let i=0;i<item.children.length;i++) {
            const result=find(item.children[i],wanted);
            if(result) return result;
        }
        return null;
    }
    function fail(reason) {
        if(done) return;
        done=true;
        console.error("W2B_FAIL // " + reason + " // phase=" + phase
            + " state=" + favorites.storageState
            + " revision=" + favorites.revision);
    }
    Connections {
        target: favorites
        function onFavoritesSaved(revision) {
            if (root.phase !== "save") {
                root.fail("UNEXPECTED_WRITE");
                return;
            }
            if (revision === 1) {
                if (favorites.cardKeys.length !== 1
                    || favorites.cardKeys[0] !== "sky|next-hours"
                    || !favorites.replacePanelFavorites(
                        ["home/auto","home/runtime"]))
                    root.fail("PANEL_SAVE_REJECTED");
            } else if (revision === 2) {
                if (favorites.panelRoutes.join(",") !== "home/auto,home/runtime"
                    || favorites.cardKeys.join(",") !== "sky|next-hours")
                    root.fail("FINAL_SAVE_IDENTITY_WRONG");
                else {
                    root.done=true;
                    console.log("W2B_PASS // NATIVE_PIN_AND_PANEL_FILEVIEW_SAVED");
                }
            } else root.fail("UNEXPECTED_REVISION");
        }
    }
    Component.onCompleted:
        console.log("W2B_BOOT // phase=" + phase)

    Timer {
        interval: 60
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks === 1 || root.ticks % 70 === 0)
                console.log("W2B_HEARTBEAT // phase=" + root.phase
                    + " state=" + favorites.storageState
                    + " revision=" + favorites.revision);

            if (root.phase === "save") {
                if (favorites.storageState !== "empty" || root.pinAnnounced)
                    return;
                const pin=root.find(card,"☆");
                if (!pin || !pin.available) return;
                const point=pin.mapToItem(testWindow.contentItem,
                                          pin.width/2,pin.height/2);
                if (point.x <= 0 || point.x >= testWindow.width ||
                    point.y <= 0 || point.y >= testWindow.height) {
                    root.fail("PIN_NOT_WITHIN_WINDOW");
                    return;
                }
                root.pinAnnounced=true;
                console.log("W2B_PIN_READY // x=" + Math.round(point.x)
                            + " y=" + Math.round(point.y));
            } else if (root.phase === "read") {
                if (favorites.storageState !== "ready")return;
                if (favorites.revision !== 2
                    || favorites.panelRoutes.join(",") !== "home/auto,home/runtime"
                    || favorites.cardKeys.join(",") !== "sky|next-hours"
                    || !card.pinned) root.fail("RESTART_READBACK_WRONG");
                else {
                    root.done=true;
                    console.log("W2B_PASS // RESTART_READBACK_IDS_ONLY");
                }
            } else if (root.phase === "corrupt"
                       || root.phase === "unsupported") {
                const expected=root.phase === "corrupt" ? "error" : "unsupported";
                if (favorites.storageState !== expected) return;
                if (favorites.writable || card.pinAvailable
                    || favorites.toggleCardFavorite("sky","next-hours"))
                    root.fail("CORRUPT_STORE_ACCEPTED_WRITE");
                else {
                    root.done=true;
                    console.log("W2B_PASS // " + root.phase.toUpperCase()
                                + "_PRESERVED_AND_REFUSED");
                }
            } else root.fail("UNKNOWN_PHASE");
        }
    }

    Timer {
        interval: 14000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 250
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
