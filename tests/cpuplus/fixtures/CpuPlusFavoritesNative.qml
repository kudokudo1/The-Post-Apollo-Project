import QtQuick
import Quickshell
import "components"
import "widgets/cpuplus"
import "widgets/appcontrol"
import "services/favorites/FavoritesManagementPolicy.js" as Management
import "services/favorites/FavoritesCollectionsPolicy.js" as CollectionRules

// Disposable native UI test. Original owners are mocked, no real user stores.
ShellRoot {
    id: root
    property string selectedKey: ""
    property string selectedCollectionId: ""
    property bool collectionClicked: false
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
            "mode:2:↗  Active Contract.pdf",
            "org.example.Demo.desktop"
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
    // Synthetic read-only copy of the single Weather owner snapshot.
    QtObject {
        id: weatherBookmarks
        property string storageState: "ready"
        property var panelRoutes: ["home/auto","home/health"]
        property var cardKeys: ["sky|next-hours"]
    }
    // Saved notification source metadata; no notification message data.
    QtObject {
        id: notificationFavorites
        property bool ready: true
        property string status: "ready"
        property var sources: [
            {appKey:"org.mozilla.firefox",source:"Firefox"},
            {appKey:"github",source:"GitHub"}
        ]
    }
    // Mock the existing Weather Station RADIO memory after owner decode.
    // These are public UUIDs + station titles, not stream URLs or actions.
    QtObject {
        id: radioSaved
        property string state: "ready"
        property var favorites: [
            {ref:{source:"radio-browser",kind:"station",
                   id:"123e4567-e89b-42d3-a456-000000000001"},
             title:"Public News One"},
            {ref:{source:"radio-browser",kind:"station",
                   id:"123e4567-e89b-42d3-a456-000000000002"},
             title:"Jazz Station"}
        ]
        property var recents: [
            {ref:{source:"radio-browser",kind:"station",
                   id:"123e4567-e89b-42d3-a456-000000000002"},
             title:"Jazz Station"},
            {ref:{source:"radio-browser",kind:"station",
                   id:"123e4567-e89b-42d3-a456-000000000003"},
             title:"World Radio"}
        ]
    }
    // Synthetic Reception owner projection. No original activity key, report
    // body, room context, transcript or Reception action passes to CPU++.
    QtObject {
        id: hospitalPins
        property string state: "hydrated"
        property var pins: [
            {ref:"pinned|reports|report|2026-11-08T18:12:05.000Z|1",
             source:"reports",kind:"report",recordedAt:"2026-11-08T18:12:05.000Z"},
            {ref:"pinned|rounds|room|2026-11-08T18:13:08.000Z|1",
             source:"rounds",kind:"room",recordedAt:"2026-11-08T18:13:08.000Z"}
        ]
    }
    readonly property var options:
        Management.list(["UTC"],[{id:12,place:{label:"Example City"}}],
            ["fav1:local:finance:instrument:TEST.01"],[],
            ({
                favoriteKeys:appFavorites.favoriteKeys,
                favoriteDetailActionKeys:appFavorites.favoriteDetailActionKeys,
                favoriteMonitorBoxKeys:appFavorites.favoriteMonitorBoxKeys,
                favoriteTaskMetricKeys:appFavorites.favoriteTaskMetricKeys
            }),({}),ownerNames.records,({
                storageState:weatherBookmarks.storageState,
                panelRoutes:weatherBookmarks.panelRoutes,
                cardKeys:weatherBookmarks.cardKeys
            }),({
                ready:notificationFavorites.ready,
                status:notificationFavorites.status,
                sources:notificationFavorites.sources
            }),({
                state:radioSaved.state,
                favorites:radioSaved.favorites,
                recents:radioSaved.recents
            }),({
                state:hospitalPins.state,
                pins:hospitalPins.pins
            }))
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
        property int renameCalls: 0
        property string lastResultCode: ""
        property var collections: [
            {id:"c1",name:"Daily Operations",members:[
                "fav1:local:weather-home:panel:home%2Fauto",
                "fav1:local:radio:station:123e4567-e89b-42d3-a456-000000000002",
                "fav1:local:weather-home:panel:home%2Fhistory"
            ]}
        ]
        function acceptsKey(key) {
            return CollectionRules.checkMemberKey(key).ok;
        }
        function hasMember(id,key) {return false;}
        function createCollection(name) { return ""; }
        function renameCollection(id,name) {
            if(id!=="c1" || name!=="Daily Workspace") {
                lastResultCode="INVALID_NAME";
                return false;
            }
            const existing=collections.collections[0];
            collections.collections=[{
                id:existing.id,name:name,members:existing.members.slice()
            }];
            renameCalls++;
            lastResultCode="SAVING";
            return true;
        }
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
                selectedCollectionId: root.selectedCollectionId
                onIndexSelectionRequested: function(key, category) {
                    selector.filterMode=category;
                    root.selectedKey=key;
                    root.indexClicked=true;
                    console.log("U4_INDEX // NAVIGATED "+category);
                }
                onCollectionRequested: function(collectionId) {
                    const section=dossier.collectionView.groups.find(function(g) {
                        return g.id===collectionId;
                    });
                    if(!section) {root.fail("U6B_UNKNOWN_COLLECTION");return;}
                    root.selectedCollectionId=collectionId;
                    selector.filterMode="GROUP";
                    root.selectedKey=section.rows.length?section.rows[0].key:"";
                    root.collectionClicked=true;
                    console.log("U6B_INDEX // NAVIGATED "+collectionId);
                }
                onCollectionMemberRequested: function(collectionId,key) {
                    const section=dossier.collectionView.groups.find(function(g) {
                        return g.id===collectionId;
                    });
                    if(!section || !section.rows.some(function(row) {
                        return row.key===key;
                    })) {root.fail("U6B_MEMBER_NOT_FOUND");return;}
                    root.selectedCollectionId=collectionId;
                    selector.filterMode="GROUP";
                    root.selectedKey=key;
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
                selectedCollectionId: root.selectedCollectionId
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
                selectedCollectionId: root.selectedCollectionId
                onCollectionRequested: function(collectionId) {
                    const group=dossier.collectionView.groups.find(function(g) {
                        return g.id===collectionId;
                    });
                    if(!group) {root.fail("U6C_NO_COLLECTION");return;}
                    root.selectedCollectionId=collectionId;
                    selector.filterMode="GROUP";
                    root.selectedKey=group.rows.length?group.rows[0].key:"";
                }
                onOwnerNavigationRequested: function(owner,view) {
                    if(root.testStage!==7 || owner!=="weather" || view!=="home"
                            || time.removals || places.removals
                            || defaults.mutations || collections.renameCalls!==1) {
                        root.fail("U7A_UNSAFE_OWNER_ROUTE");return;
                    }
                    // No selected key or owner object is part of the signal.
                    console.log("U7A_PASS // OWNER_VIEW_ONLY_NO_PROVIDER_ACTIONS");
                    root.testStage=8;
                }
                onExactNavigationRequested: function(owner,route) {
                    if(root.testStage!==9 || owner!=="weather"
                            || route!=="home/auto"
                            || time.removals || places.removals
                            || defaults.mutations || collections.renameCalls!==1) {
                        root.fail("U7B_UNSAFE_EXACT_ROUTE");return;
                    }
                    console.log("U7B_PASS // EXACT_HOME_PANEL_ONLY_NO_PROVIDER_ACTIONS");
                    const app=root.options.rows.find(function(row) {
                        return row.owner==="appcontrol" && row.kind==="item"
                            && row.key==="fav1:local:appcontrol:item:org.example.Demo.desktop";
                    });
                    if(!app) {root.fail("U7C_SAVED_APP_MISSING");return;}
                    root.selectedKey=app.key;
                    root.testStage=10;
                }
                onAppSelectionRequested: function(desktopId) {
                    if(root.testStage!==11 || desktopId!=="org.example.Demo.desktop"
                            || time.removals || places.removals
                            || defaults.mutations || collections.renameCalls!==1) {
                        root.fail("U7C_UNSAFE_APP_SELECTION");return;
                    }
                    console.log("U7C_PASS // EXACT_DESKTOP_ENTRY_SELECTION_NO_EXECUTION");
                    // U7b-D sensor appears only AFTER the old U4/U6 tests,
                    // preserving their original counts and row positions.
                    fakeAppControl.systemRows=[{
                        id:"system:cpu",name:"CPU",label:"CPU",
                        _systemRecord:true
                    }];
                    appFavorites.favoriteKeys=appFavorites.favoriteKeys.concat(
                        ["system|system%3Acpu"]);
                    root.testStage=12;
                }
                onSystemSelectionRequested: function(metric) {
                    if(root.testStage!==14 || metric!=="cpu"
                            || time.removals || places.removals
                            || defaults.mutations || collections.renameCalls!==1) {
                        root.fail("U7D_UNSAFE_SYSTEM_SELECTION");return;
                    }
                    root.done=true;
                    console.log("U7D_PASS // EXACT_SYSTEM_CORE_SELECTION_NO_ACTIONS");
                    Qt.quit();
                }
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
            const weatherPanel=root.options.rows.find(function(item) {
                return item.owner==="weather-home"
                    && item.menu==="HOME" && item.item==="AUTO";
            });
            const weatherCard=root.options.rows.find(function(item) {
                return item.owner==="weather-home"
                    && item.menu==="CARD"
                    && item.item==="SKY // NEXT HOURS";
            });
            const weatherGroups=dossier.dossier.groups.filter(function(group) {
                return group.category==="WEATHER";
            });
            const notificationGroups=dossier.dossier.groups.filter(function(group) {
                return group.category==="NOTIFS";
            });
            const notificationRow=root.options.rows.find(function(item) {
                return item.owner==="notifications"
                    && item.menu==="SOURCES"
                    && item.item==="GitHub";
            });
            const radioFavoritesGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="RADIO|FAVORITES";
            });
            const radioRecentsGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="RADIO|RECENTS";
            });
            const jazz=root.options.rows.find(function(row) {
                return row.owner==="radio" && row.item==="Jazz Station";
            });
            const world=root.options.rows.find(function(row) {
                return row.owner==="radio" && row.item==="World Radio";
            });
            const hospitalReportGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="HOSPITAL|REPORTS";
            });
            const hospitalRoundsGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="HOSPITAL|ROUNDS";
            });
            const hospitalReport=root.options.rows.find(function(row) {
                return row.owner==="hospital" && row.menu==="REPORTS";
            });
            const fileGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="APP CTRL|FILES";
            });
            const processGroup=dossier.dossier.groups.find(function(group) {
                return group.key==="CPU++|KILL";
            });
            if(!root.options || root.options.total!==22
               || dossier.dossier.total!==root.options.rows.length
               || dossier.collectionView.count!==1
               || dossier.collectionView.groups[0].count!==3
               || dossier.collectionView.groups[0].available!==2
               || dossier.collectionView.groups[0].missing!==1
               || dossier.collectionView.groups[0].items[2].key!==""
               || dossier.collectionView.groups[0].items[2].name!=="SAVED MEMBER UNAVAILABLE"
               || !hospitalReportGroup || hospitalReportGroup.count!==1
               || !hospitalRoundsGroup || hospitalRoundsGroup.count!==1
               || !hospitalReport || !hospitalReport.readOnly
               || !hospitalReport.isPinned
               || hospitalReport.available!=="unresolved"
               || hospitalReport.item!=="REPORT // 2026-11-08 18:12:05 UTC"
               || !weatherPanel || !weatherCard
               || weatherGroups.length!==2
               || !radioFavoritesGroup || radioFavoritesGroup.count!==2
               || !radioRecentsGroup || radioRecentsGroup.count!==1
               || !jazz || !jazz.isFavorite || !jazz.isRecent
               || jazz.favoriteType!=="FAVORITE + RECENT STATION"
               || !world || world.isFavorite || !world.isRecent
               || !jazz.readOnly || !world.readOnly
               || jazz.available!=="unresolved"
               || notificationGroups.length!==1
               || notificationGroups[0].title!=="NOTIFICATIONS // SOURCES"
               || notificationGroups[0].count!==2
               || !notificationRow || !notificationRow.readOnly
               || notificationRow.available!=="unresolved"
               || !weatherPanel.readOnly || !weatherCard.readOnly
               || weatherPanel.available!=="unresolved"
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
                const scroll=dossier.dossierScrollArea;
                const pos=fileRow.mapToItem(scroll.contentItem,0,0);
                scroll.contentY=Math.max(0,Math.min(
                    Math.max(0,scroll.contentHeight-scroll.height),pos.y-10));
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
                console.log("U4_PASS // DOSSIER_FILE_NAVIGATION_READ_ONLY");
                const weather=root.options.rows.find(function(item) {
                    return item.owner==="weather-home" && item.menu==="HOME";
                });
                if(!weather) { root.fail("U6_NO_WEATHER_KEY");return; }
                root.testStage=2;
                root.selectedKey=weather.key;
            } else if(root.testStage===2) {
                if(!root.selection || root.selection.owner!=="weather-home"
                        || detail.collectionPanel.resourceKey!==root.selection.key
                        || !detail.collectionPanel.canUseResource) {
                    root.fail("U6_SAFE_WEATHER_COLLECTION_REJECTED");return;
                }
                const unsafe=root.options.rows.find(function(item) {
                    return item.owner==="appcontrol" && item.menu==="RUN";
                });
                if(!unsafe) { root.fail("U6_NO_UNSAFE_APP");return; }
                root.testStage=3;
                root.selectedKey=unsafe.key;
            } else if(root.testStage===3) {
                if(!root.selection || root.selection.owner!=="appcontrol"
                        || root.selection.menu!=="RUN"
                        || detail.collectionPanel.canUseResource) {
                    root.fail("U6_UNSAFE_APP_COLLECTION_ACCEPTED");return;
                }
                if(time.removals || places.removals || defaults.mutations) {
                    root.fail("U6_PROVIDER_MUTATION");return;
                }
                console.log("U6_PASS // SAFE_MEMBER_ONLY_NO_PROVIDER_WRITES");
                const group=dossier.collectionGroupItems.itemAt(0);
                if(!group) {root.fail("U6B_GROUP_NOT_RENDERED");return;}
                const pt=group.mapToItem(win.contentItem,16,14);
                root.testStage=4;
                console.log("U6B_GROUP_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===4 && root.collectionClicked) {
                if(root.selectedCollectionId!=="c1"
                        || selector.filterMode!=="GROUP"
                        || selector.choices.length!==2
                        || selector.choices[0].owner!=="weather-home"
                        || selector.choices[1].owner!=="radio"
                        || !root.selection || root.selection.key!==selector.choices[0].key
                        || dossier.collectionView.missingCount!==1
                        || dossier.collectionView.groups[0].items[2].key!==""
                        || time.removals || places.removals || defaults.mutations) {
                    root.fail("U6B_GROUP_NAVIGATION");return;
                }
                console.log("U6B_PASS // COLLECTION_TO_SELECTOR_AND_DETAILS_NO_WRITES");
                const row=detail.collectionPanel.groupRowItems.itemAt(0);
                const button=row ? row.editControl : null;
                if(!button || !button.available) {
                    root.fail("U6C_RENAME_CONTROL_MISSING");return;
                }
                const pt=button.mapToItem(win.contentItem,
                    button.width/2,button.height/2);
                root.testStage=5;
                console.log("U6C_RENAME_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===5) {
                const row=detail.collectionPanel.groupRowItems.itemAt(0);
                if(row && row.renaming && row.editField.activeFocus) {
                    root.testStage=6;
                    console.log("U6C_EDIT_READY");
                }
            } else if(root.testStage===6 && collections.renameCalls===1) {
                const group=dossier.collectionView.groups[0];
                const row=detail.collectionPanel.groupRowItems.itemAt(0);
                if(!group || group.id!=="c1" || group.name!=="Daily Workspace"
                        || group.count!==3 || group.available!==2
                        || !row || row.renaming
                        || root.selectedCollectionId!=="c1"
                        || selector.filterMode!=="GROUP"
                        || selector.choices.length!==2
                        || !root.selection
                        || root.selection.owner!=="weather-home"
                        || time.removals || places.removals || defaults.mutations) {
                    root.fail("U6C_RENAME_OR_OWNER_BOUNDARY");return;
                }
                console.log("U6C_PASS // INLINE_RENAME_UPDATES_INDEX_NO_OWNER_WRITES");
                const ownerButton=detail.ownerNavigationControl;
                if(!ownerButton || !ownerButton.available
                        || ownerButton.label!=="OPEN OWNER"
                        || !detail.ownerNavigation.ok
                        || detail.ownerNavigation.owner!=="weather"
                        || detail.ownerNavigation.view!=="home") {
                    root.fail("U7A_OWNER_BUTTON_NOT_READY");return;
                }
                const pt=ownerButton.mapToItem(win.contentItem,
                    ownerButton.width/2,ownerButton.height/2);
                root.testStage=7;
                console.log("U7A_OWNER_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===8) {
                const itemButton=detail.exactNavigationControl;
                if(!itemButton || !itemButton.available
                        || itemButton.label!=="OPEN ITEM"
                        || !detail.exactNavigation.ok
                        || detail.exactNavigation.owner!=="weather"
                        || detail.exactNavigation.route!=="home/auto") {
                    root.fail("U7B_ITEM_BUTTON_NOT_READY");return;
                }
                const pt=itemButton.mapToItem(win.contentItem,
                    itemButton.width/2,itemButton.height/2);
                root.testStage=9;
                console.log("U7B_ITEM_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===10) {
                const appButton=detail.exactNavigationControl;
                if(!root.selection || root.selection.owner!=="appcontrol"
                        || root.selection.menu!=="APPS"
                        || !root.selection.readOnly
                        || !detail.appSelection.ok
                        || detail.appSelection.desktopId!=="org.example.Demo.desktop"
                        || !appButton || !appButton.available
                        || appButton.label!=="OPEN ITEM") {
                    root.fail("U7C_APP_BUTTON_NOT_READY");return;
                }
                const pt=appButton.mapToItem(win.contentItem,
                    appButton.width/2,appButton.height/2);
                root.testStage=11;
                console.log("U7C_ITEM_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.testStage===12) {
                const item=root.options.rows.find(function(row) {
                    return row.owner==="appcontrol"
                        && row.menu==="SYSTEM"
                        && row.category==="CPU++"
                        && row.favoriteType==="FAVORITE"
                        && row.item==="CPU";
                });
                if(!item) return;
                root.selectedKey=item.key;
                root.testStage=13;
            } else if(root.testStage===13) {
                const metricButton=detail.exactNavigationControl;
                if(!root.selection || root.selection.menu!=="SYSTEM"
                        || root.selection.category!=="CPU++"
                        || !detail.systemSelection.ok
                        || detail.systemSelection.metric!=="cpu"
                        || !metricButton || !metricButton.available
                        || metricButton.label!=="OPEN ITEM") {
                    root.fail("U7D_SYSTEM_BUTTON_NOT_READY");return;
                }
                const pt=metricButton.mapToItem(win.contentItem,
                    metricButton.width/2,metricButton.height/2);
                root.testStage=14;
                console.log("U7D_ITEM_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
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
