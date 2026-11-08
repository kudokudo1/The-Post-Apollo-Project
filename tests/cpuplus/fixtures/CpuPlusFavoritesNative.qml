import QtQuick
import Quickshell
import "components"
import "widgets/cpuplus"
import "widgets/appcontrol"
import "services/favorites/FavoritesManagementPolicy.js" as Management

// Disposable native UI test. Original owners are mocked, no real user stores.
ShellRoot {
    id: root
    property string selectedKey: ""
    property bool ready: false
    property bool selectedByClick: false
    property bool done: false
    QtObject {
        id: fakeAppControl
        property var thermalRows: []
        property var fanRows: []
        property var systemRows: []
        property var taskRows: [{comm:"hidden-process",name:"Hidden Process"}]
    }
    QtObject {
        id: appFavorites
        property var favoriteKeys: ["task|hidden-process","run|private-command"]
        property var favoriteDetailActionKeys: []
        property var favoriteMonitorBoxKeys: []
        property var favoriteTaskMetricKeys: []
    }
    AppControlFavoriteDisplaySource {
        id: ownerNames
        appControlOwner: fakeAppControl
        favoritesStore: appFavorites
    }
    readonly property var options:
        Management.list(["UTC"],[{id:12,place:{label:"Example City"}}],
            ["fav1:local:finance:instrument:TEST.01"],[],
            ({
                favoriteKeys:appFavorites.favoriteKeys,
                favoriteDetailActionKeys:appFavorites.favoriteDetailActionKeys,
                favoriteMonitorBoxKeys:appFavorites.favoriteMonitorBoxKeys,
                favoriteTaskMetricKeys:appFavorites.favoriteTaskMetricKeys
            }),({}),ownerNames.records)
    readonly property var selection: Management.recordFor(options,selectedKey)

    QtObject {
        id: time
        property bool worldFavoriteCanEdit: true
        property bool zoneCatalogLoaded: true
        property bool zoneCatalogLoading: false
        property var zoneCatalog: ["UTC"]
        property int removals: 0
        function toggleWorldFavorite(zoneId,zones) { removals++; return false; }
        function loadZoneCatalog() {}
    }
    QtObject {
        id: places
        property bool canSaveHome: true
        property int removals: 0
        function removeSavedPlace(id) { removals++; return false; }
    }
    QtObject {
        id: defaults
        property bool canEdit: true
        property var favoriteKeys: ["fav1:local:finance:instrument:TEST.01"]
        property var pinnedKeys: []
        property int mutations: 0
        function setFavorite(key,yes) { mutations++; return false; }
        function togglePinned(key) { mutations++; return false; }
    }
    QtObject {
        id: collections
        property bool canEdit: true
        property string storageState: "empty"
        property string errorCode: ""
        property bool busy: false
        property var collections: []
        function acceptsKey(key) { return !!key; }
        function hasMember(id,key) {return false;}
        function createCollection(name) { return ""; }
        function toggleMember(id,key) { return false; }
        function moveMember(id,key,direction) {return false;}
        function deleteCollection(id) {return false;}
    }

    FloatingWindow {
        id: win
        title: "CPU-FAVORITES-NATIVE"
        visible: true
        implicitWidth: 700
        implicitHeight: 480
        Row {
            anchors.fill: parent
            spacing: 12
            CpuPlusFavoritesHubPane {
                id: selector
                area: "selector"
                filterMode: "CPU++"
                width: 263
                height: parent.height
                catalogSnapshot: ({ok:true,groups:[],rows:[],total:0})
                candidates: root.options
                selectedResource: root.selection
                timeOwner: time
                placesOwner: places
                defaultOwner: defaults
                collectionsOwner: collections
                onSelectionRequested: function(key) {
                    root.selectedKey=key;
                    root.selectedByClick=true;
                    console.log("U4_SELECT // "+root.selection.category);
                }
            }
            CpuPlusFavoritesHubPane {
                id: detail
                area: "details"
                width: 385
                height: parent.height
                candidates: root.options
                selectedResource: root.selection
                timeOwner: time
                placesOwner: places
                defaultOwner: defaults
                collectionsOwner: collections
            }
        }
    }
    Timer {
        interval: 180
        running: !root.ready && !root.done
        repeat: true
        onTriggered: {
            if(!root.options || root.options.total!==5
               || selector.choices.length!==1
               || selector.choices[0].category!=="CPU++"
               || !selector.choices[0].readOnly
               || !root.selection || root.selection.category!=="CPU++"
               || root.selection.menu!=="KILL"
               || root.selection.item!=="hidden-process"
               || root.selection.favoriteType!=="PROCESS FAVORITE"
               || root.selection.label!=="KILL // hidden-process") {
                root.fail("INITIAL");
                return;
            }
            const row=selector.favoriteRowRepeater.itemAt(0);
            if(!row) return;
            root.ready=true;
            // Click the LEFT TEXT AREA, far from the former VIEW button.
            // This verifies the complete row now owns selection.
            const pt=row.mapToItem(win.contentItem,
                16,row.height/2);
            console.log("U4_READY // x="+Math.round(pt.x)
                +" y="+Math.round(pt.y));
        }
    }
    Timer {
        interval: 200
        running: root.ready && !root.done
        repeat: true
        onTriggered: {
            if(root.selectedByClick && root.selection
                    && root.selection.category==="CPU++"
                    && root.selection.owner==="appcontrol"
                    && root.selection.readOnly) {
                if(time.removals || places.removals || defaults.mutations) {
                    root.fail("UNEXPECTED_PROVIDER_ACTION");return;
                }
                root.done=true;
                console.log("U4_PASS // SELECTED_PROCESS_READ_ONLY");
                Qt.quit();
            }
        }
    }
    Timer {
        interval: 10000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    function fail(reason) {
        if (done) return;
        done=true;
        console.error("U4_FAIL // "+reason);
        Qt.quit();
    }
}
