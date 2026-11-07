import QtQuick
import Quickshell
import "components"
import "services/favorites" as FavoriteServices

// U2 synthetic native QML owner injection and live reactive-view fixture.
// Does not import owner singletons or touch real user preferences.
ShellRoot {
    id: root
    property int stage: 0
    property bool finished: false

    QtObject {
        id: app
        property var favoriteKeys: ["app|synthetic-one"]
        property var favoriteDetailActionKeys: []
        property var favoriteMonitorBoxKeys: []
        property var favoriteTaskMetricKeys: []
    }
    QtObject {
        id: clock
        property var worldFavoriteZones: ["UTC"]
        property string worldFavoriteState: "ready"
    }
    QtObject {
        id: places
        property var savedPlaces: [
            {id:1,place:{label:"Synthetic Place"}}
        ]
        property string storageState: "ready"
    }

    FavoriteServices.FavoritesUnifiedCatalog {
        id: combined
        appControlSource: app
        worldSource: clock
        placesSource: places
    }

    FloatingWindow {
        title: "U2-READ-ONLY-FAVORITES"
        visible: true
        implicitWidth: 425
        implicitHeight: 310
        FavoritesUnifiedPreview {
            id: preview
            anchors.fill: parent
            snapshot: combined.snapshot
        }
    }

    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("U2_FAIL // "+reason+" // stage="+stage);
        Qt.quit();
    }

    Timer {
        interval: 150
        repeat: true
        running: !root.finished
        onTriggered: {
            const current=combined.snapshot;
            if (!current || !current.ok || !preview.snapshot
                    || !preview.snapshot.ok)
                return;
            if (root.stage === 0) {
                if (current.total !== 3 || current.groups.length !== 3
                        || current.rows[0].label !== "APP CONTROL FAVORITE"
                        || current.rows[1].label !== "UTC"
                        || current.rows[2].label !== "Synthetic Place"
                        || current.rows[0].availability !== "unresolved"
                        || current.rows[0].label.indexOf("synthetic-one") >= 0) {
                    root.fail("INITIAL_OWNER_SNAPSHOTS");
                    return;
                }
                console.log("U2_PASS // INITIAL_THREE_OWNERS");
                root.stage=1;
                clock.worldFavoriteZones=["UTC","Europe/London"];
                places.savedPlaces=[{id:1,place:{label:"Synthetic Place"}},
                    {id:2,place:{label:"Synthetic Other"}}];
                app.favoriteKeys=["app|synthetic-one","task|private-data"];
                return;
            }
            if (root.stage === 1) {
                if (current.total !== 6 || current.groups[0].count !== 2
                        || current.groups[1].count !== 2
                        || current.groups[2].count !== 2
                        || preview.rows.length !== 6) {
                    root.fail("REACTIVE_OWNER_CHANGE");
                    return;
                }
                if (JSON.stringify(preview.rows).indexOf("private-data") >= 0) {
                    root.fail("APP_CONTROL_IDENTITY_EXPOSED");
                    return;
                }
                console.log("U2_PASS // REACTIVE_THREE_OWNER_UPDATES");
                root.finished=true;
                console.log("U2_PASS // NATIVE_READ_ONLY_CATALOG");
                Qt.quit();
                return;
            }
            root.fail("UNEXPECTED_STAGE");
        }
    }
    Timer {
        interval: 6000
        running: !root.finished
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
}
