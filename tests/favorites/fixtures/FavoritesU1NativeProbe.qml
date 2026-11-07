import QtQuick
import Quickshell
import "components"
import "services/favorites" as FavoriteServices

// Disposable native U1 lifecycle fixture. No real operator data or live widgets.
ShellRoot {
    id: root
    readonly property string phase: Quickshell.env("U1_PHASE")
    readonly property string resourceKey: "fav1:local:demo-u1:tile:test-value"
    readonly property var resourceDescriptor: ({
        provider:"demo-u1", kind:"tile", resourceId:"test-value",
        label:"Synthetic Resource", capabilities:["favorite","pin"]
    })
    readonly property var store: FavoriteServices.FavoritesDefaultStore
    property bool done: false
    property bool announced: false
    property int ticks: 0

    FloatingWindow {
        id: win
        title: "U1-FAVORITES-DEFAULT"
        visible: true
        implicitWidth: 390
        implicitHeight: 180

        Row {
            anchors.centerIn: parent
            spacing: 20
            FavoritesToggleButton {
                id: star
                resource: root.resourceDescriptor
                feature: "favorite"
                onChangeAccepted: console.log("U1_CLICK_ACCEPTED // favorite")
            }
            FavoritesToggleButton {
                id: pin
                resource: root.resourceDescriptor
                feature: "pin"
            }
        }
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("U1_FAIL // " + reason + " // " + root.phase
            + " state=" + store.storageState
            + " rev=" + store.revision
            + " saved=" + store.savedRevision
            + " last=" + store.lastResultCode);
    }

    Connections {
        target: root.store
        function onFavoritesSaved(revision) {
            if (root.phase !== "save") {
                root.fail("UNEXPECTED_WRITE");
                return;
            }
            const k = root.resourceKey;
            if (revision === 1) {
                if (!store.isFavorite(k) || store.isPinned(k)
                        || !store.setPinned(k,true)
                        || !store.toggleFavorite(k)
                        || !store.toggleFavorite(k)
                        || !store.togglePinned(k)
                        || !store.togglePinned(k)
                        || store.lastResultCode !== "QUEUED"
                        || store.revision !== 6) {
                    root.fail("RAPID_QUEUE_LOST");
                }
            } else if (revision === 2) {
                if (!store.busy || store.revision !== 6
                        || !store.isPinned(k) || !store.isFavorite(k))
                    root.fail("QUEUED_WRITE_NOT_VISIBLE");
            } else if (revision === 6) {
                if (store.busy || store.savedRevision !== 6
                        || !store.isPinned(k) || !store.isFavorite(k)
                        || !star.selected || !pin.selected)
                    root.fail("FINAL_SAVE_STATE_WRONG");
                else {
                    root.done = true;
                    console.log("U1_PASS // CLICK_RAPID_QUEUE_AND_FILEVIEW_SAVED");
                }
            } else root.fail("UNEXPECTED_REVISION_" + revision);
        }

        function onFavoritesSaveFailed(reason) {
            root.fail("WRITE_FAILED_" + reason);
        }
    }

    Timer {
        interval: 80
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks % 35 === 0)
                console.log("U1_HEARTBEAT // phase=" + phase
                    + " state=" + store.storageState
                    + " rev=" + store.revision);
            if (root.phase === "save") {
                if (root.announced || store.storageState !== "empty")
                    return;
                if (!star.available || !pin.available || store.favoriteKeys.length)
                    return;
                const point=star.mapToItem(win.contentItem,
                    star.width/2,star.height/2);
                root.announced=true;
                console.log("U1_READY // x=" + Math.round(point.x)
                    + " y=" + Math.round(point.y));
            } else if (root.phase === "read") {
                if (store.storageState !== "ready") return;
                if (store.revision !== 6 || !store.isFavorite(root.resourceKey)
                        || !store.isPinned(root.resourceKey)
                        || !star.selected || !pin.selected)
                    root.fail("RESTART_READBACK_WRONG");
                else {
                    root.done=true;
                    console.log("U1_PASS // READBACK_WITHOUT_WRITE");
                }
            } else if (root.phase === "corrupt" || root.phase === "unsupported") {
                const expected=root.phase === "corrupt" ? "error" : "unsupported";
                if (store.storageState !== expected) return;
                if (store.canEdit || star.available || pin.available
                        || store.toggleFavorite(root.resourceKey)
                        || store.setPinned(root.resourceKey,false)) {
                    root.fail("BAD_FILE_WRITABLE");
                } else {
                    root.done=true;
                    console.log("U1_PASS // "+root.phase.toUpperCase()+"_PRESERVED");
                }
            } else root.fail("UNKNOWN_PHASE");
        }
    }
    Timer {
        interval: 15000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 260
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
    Component.onCompleted: console.log("U1_BOOT // "+phase)
}
