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
    property bool indexClicked: false
    property int testStage: 0
    property bool done: false
    QtObject {
        id: fakeAppControl
        property var thermalRows: []
        property var fanRows: []
        property var systemRows: []
        property var taskRows: [{comm:"hidden-process",name:"Hidden Process"}]
        property var swayWindows: [{name:"Favorite Window"}]
        property var appTabs: []
    }
    QtObject {
        id: appFavorites
        property var favoriteKeys: [
            "task|hidden-process","run|private-command",
            "run:kitty:zellij","mode:4:Favorite Window","hidden:btop",
            "mode:2:◇  budget-2026.xlsx",
            "mode:2:⌯🗁๋࣭⭑  Properties/",
            "mode:2:↗  Active Contract.pdf"
        ]
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
        implicitWidth: 930
        implicitHeight: 480
        Row {
            anchors.fill: parent
            spacing: 12
            CpuPlusFavoritesHubPane {
                id: dossier
                area: "overview"
                width: 208
                height: parent.height
                candidates: root.options
                selectedResource: root.selection
                timeOwner: time
                placesOwner: places
                defaultOwner: defaults
                collectionsOwner: collections
                onIndexSelectionRequested: function(key, category) {
                    selector.filterMode=category;
                    root.selectedKey=key;
                    root.indexClicked=true;
                    console.log("U4_INDEX // NAVIGATED "+category);
                }
            }
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
            const named=root.options && root.options.rows
                ? root.options.rows.filter(function(item) {
                    return item.owner==="appcontrol" && item.resolved;
                  }) : [];
            const run=named.find(function(item) {
                return item.menu==="RUN" && item.item==="zellij [KITTY]";
            });
            const winItem=named.find(function(item) {
                return item.menu==="WINDOWS" && item.item==="Favorite Window";
            });
            const cli=named.find(function(item) {
                return item.menu==="APPS" && item.item==="btop [CLI]";
            });
            const unavailable=root.options.rows.find(function(item) {
                return item.menu==="RUN" && item.owner==="appcontrol"
                       && !item.resolved;
            });
            const file=named.find(function(item) {
                return item.menu==="FILES"
                       && item.item==="budget-2026.xlsx"
                       && item.favoriteType==="FILE FAVORITE";
            });
            const folder=named.find(function(item) {
                return item.menu==="FILES"
                       && item.item==="Properties"
                       && item.favoriteType==="DIRECTORY FAVORITE";
            });
            const link=named.find(function(item) {
                return item.menu==="FILES"
                       && item.item==="Active Contract.pdf"
                       && item.favoriteType==="SYMLINK FAVORITE";
            });
            const fileGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="APP CTRL|FILES";
            });
            const processGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="CPU++|KILL";
            });
            if(!root.options || root.options.total!==11
               || dossier.dossier.total!==root.options.rows.length
               || !fileGroup || fileGroup.count!==3
               || !processGroup || processGroup.count!==1
               || fileGroup.items[0].name!=="budget-2026.xlsx"
               || fileGroup.items[1].name!=="Properties"
               || fileGroup.items[2].name!=="Active Contract.pdf"
               || !run || !winItem || !cli || !unavailable
               || !file || !folder || !link
               || selector.favoriteRowLabel(file)
                   !=="APP CTRL // FILES // budget-2026.xlsx"
               || file.available!=="unresolved"
               || !folder.readOnly || !link.readOnly
               || selector.favoriteRowLabel(unavailable)
                   !=="APP CTRL // RUN // SAVED COMMAND #1"
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
            if(root.testStage===0 && root.selectedByClick && root.selection
                    && root.selection.category==="CPU++"
                    && root.selection.owner==="appcontrol"
                    && root.selection.readOnly) {
                if(time.removals || places.removals || defaults.mutations) {
                    root.fail("UNEXPECTED_PROVIDER_ACTION");return;
                }
                console.log("U4_PASS // SELECTED_PROCESS_READ_ONLY");
                const fileGroupIndex=dossier.dossier.groups.findIndex(function(g) {
                    return g.key==="APP CTRL|FILES";
                });
                const group=dossier.dossierGroupItems.itemAt(fileGroupIndex);
                const fileRow=group ? group.entryItems.itemAt(0) : null;
                if(!fileRow) {
                    root.fail("DOSSIER_ROW_MISSING");return;
                }
                const pt=fileRow.mapToItem(win.contentItem,
                    16,fileRow.height/2);
                root.testStage=1;
                console.log("U4_SECOND_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===1 && root.indexClicked) {
                if(!root.selection || root.selection.menu!=="FILES"
                        || root.selection.item!=="budget-2026.xlsx"
                        || root.selection.category!=="APP CTRL"
                        || selector.filterMode!=="APP CTRL"
                        || !root.selection.readOnly) {
                    root.fail("DOSSIER_NAVIGATION");return;
                }
                if(time.removals || places.removals || defaults.mutations) {
                    root.fail("DOSSIER_OWNER_ACTION");return;
                }
                root.done=true;
                console.log("U4_PASS // DOSSIER_FILE_NAVIGATION_READ_ONLY");
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
