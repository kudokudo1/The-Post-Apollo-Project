import QtQuick
import Quickshell
import "services/favorites" as Favorites

// Disposable native proof that the original AppControl favorites writer and
// shared operations work without either AppControlW or CpuPlusW instantiated.
// Only this ShellRoot and the Favorites module are copied into the fixture.
ShellRoot {
    id: root
    readonly property string phase: Quickshell.env("FB_PHASE")
    readonly property var service: Favorites.FavoritesService
    readonly property var store: Favorites.FavoritesStore

    readonly property string taskKey: "task|firefox"
    readonly property string fileKey: "file:/tmp/favorites-synthetic-only"
    readonly property string taskMetricKey: "taskmetric|firefox|cpu"
    readonly property string monitorKey: "watchbox|system|cpu|load"
    readonly property string context: "app|synthetic.desktop"
    readonly property string preferredOld: "app|synthetic.desktop|launch"
    readonly property string preferredNew: "app|synthetic.desktop|desktop|Open"

    property bool finished: false

    function fail(reason) {
        if (finished)
            return;
        finished = true;
        console.error("FB_FAIL // " + reason + " phase=" + phase);
        Qt.quit();
    }

    function verified() {
        return service.isFavoriteKey(taskKey)
            && service.isFavoriteKey(fileKey)
            && service.isTaskMetricKey(taskMetricKey)
            && service.isMonitorBoxKey(monitorKey)
            && service.isPreferredActionKey(preferredNew)
            && !service.isPreferredActionKey(preferredOld)
            && store.favoriteKeys.length === 2
            && store.favoriteKeys[0] === fileKey
            && store.favoriteKeys[1] === taskKey
            && store.favoriteTaskMetricKeys.length === 1
            && store.favoriteMonitorBoxKeys.length === 1
            && store.favoriteDetailActionKeys.length === 1;
    }

    Timer {
        interval: 950
        running: true
        repeat: false
        onTriggered: {
            if (root.phase === "save") {
                if (store.favoriteKeys.length !== 0
                        || store.favoriteTaskMetricKeys.length !== 0
                        || store.favoriteMonitorBoxKeys.length !== 0
                        || store.favoriteDetailActionKeys.length !== 0) {
                    root.fail("UNEXPECTED_EXISTING_DATA");
                    return;
                }
                const generalTask = service.toggleFavoriteKey(root.taskKey);
                const generalFile = service.toggleFavoriteKey(root.fileKey);
                const processWatch = service.toggleTaskMetricKey(root.taskMetricKey);
                const monitorWatch = service.toggleMonitorBoxKey(root.monitorKey);
                const preferredFirst =
                    service.togglePreferredActionKey(root.context, root.preferredOld);
                const preferredSecond =
                    service.togglePreferredActionKey(root.context, root.preferredNew);
                const matches = root.verified();
                console.log("FB_TRACE // op=" + JSON.stringify([
                    generalTask, generalFile, processWatch, monitorWatch,
                    preferredFirst, preferredSecond, matches
                ]) + " favorites=" + JSON.stringify(store.favoriteKeys)
                    + " task=" + JSON.stringify(store.favoriteTaskMetricKeys)
                    + " monitor=" + JSON.stringify(store.favoriteMonitorBoxKeys)
                    + " preferred=" + JSON.stringify(store.favoriteDetailActionKeys));
                if (!generalTask || !generalFile || !processWatch
                        || !monitorWatch || !preferredFirst || !preferredSecond) {
                    root.fail("SERVICE_REJECTED_MUTATION");
                    return;
                }
                console.log("FB_PENDING // SERVICE_MUTATIONS_QUEUED");
                settleTimer.start();
            } else if (root.phase === "read") {
                // FileView reads asynchronously. Do not treat the first
                // timer callback as proof that the backing JSON has loaded.
                console.log("FB_READ_INITIAL // favorites="
                    + JSON.stringify(store.favoriteKeys));
            } else {
                root.fail("UNKNOWN_PHASE");
            }
        }
    }

    // In a widgetless shell, asynchronous FileView loading may complete
    // after Component.onCompleted and the first timer callback. Observe
    // the actual owner state rather than guessing a fixed read delay.
    Timer {
        interval: 100
        repeat: true
        running: root.phase === "read" && !root.finished
        onTriggered: {
            if (!root.verified())
                return;
            root.finished = true;
            console.log("FB_PASS // STANDALONE_RESTART_READ_ONLY");
            Qt.quit();
        }
    }

    // The legacy JsonAdapter writes through FileView asynchronously.
    Timer {
        id: settleTimer
        interval: 900
        repeat: false
        onTriggered: {
            console.log("FB_SETTLED // favorites="
                + JSON.stringify(store.favoriteKeys)
                + " task=" + JSON.stringify(store.favoriteTaskMetricKeys)
                + " monitor=" + JSON.stringify(store.favoriteMonitorBoxKeys)
                + " preferred=" + JSON.stringify(store.favoriteDetailActionKeys));
            if (!root.verified()) {
                root.fail("POST_WRITE_IN_MEMORY_STATE");
                return;
            }
            root.finished = true;
            console.log("FB_PASS // STANDALONE_SERVICE_WRITE");
            Qt.quit();
        }
    }

    Timer {
        interval: 12000
        repeat: false
        running: !root.finished
        onTriggered: root.fail("TIMEOUT")
    }

    Component.onCompleted: console.log("FB_BOOT // " + phase)
}
