import QtQuick
import "../../components"
import "../../services/favorites/FavoritesDossierIndexPolicy.js" as Dossier
import "../../services/favorites/FavoritesSearchPolicy.js" as Search
import "../../services/favorites/FavoritesCollectionsViewPolicy.js" as CollectionView
import "../../services/favorites/FavoritesOwnerNavigationPolicy.js" as OwnerNavigation
import "../../services/favorites/FavoritesExactNavigationPolicy.js" as ExactNavigation
import "../../services/favorites/FavoritesAppSelectionPolicy.js" as AppSelection
import "../../services/favorites/FavoritesSystemSelectionPolicy.js" as SystemSelection
import "../../services/favorites/FavoritesSystemWatchSelectionPolicy.js" as SystemWatchSelection
import "../../services/favorites/FavoritesThermalSelectionPolicy.js" as ThermalSelection

// CPU++ Favorites++ manager. Three instances share one selection/snapshot.
// No new FileView, owner process, or action authority is created here.
Item {
    id: pane
    required property string area // overview | selector | details
    property var catalogSnapshot: null
    property var candidates: null
    property var selectedResource: null
    // Expose rendered rows for native selector/a11y testing, not actuation.
    property alias favoriteRowRepeater: savedItemRows
    property alias dossierGroupItems: dossierGroupRepeater
    property alias dossierScrollArea: dossierScroll
    property alias collapseAllControl: collapseAllButton
    property alias searchQuery: favoritesSearchInput.text
    property alias collectionGroupItems: collectionGroupRepeater
    // Native fixture inspection of the existing group editor (no new action).
    property alias collectionPanel: collectionManager
    // Test seam for the original read-only owner-navigation button.
    property alias ownerNavigationControl: remove
    property alias exactNavigationControl: openItem
    property var timeOwner: null
    property var placesOwner: null
    property var defaultOwner: null
    property var collectionsOwner: null
    property string filterMode: "ALL"
    // Bottom menu row is local filtering, not an owner-side action.
    property string menuFilter: "ALL"
    // Shared between all three CPU++ bays; selection alone never modifies an owner.
    property string selectedCollectionId: ""
    signal selectionRequested(string key)
    // Overview selects an original candidate and directs the middle bay to
    // its existing filter, never a new owner action.
    signal indexSelectionRequested(string key, string category)
    signal collectionRequested(string collectionId)
    signal collectionMemberRequested(string collectionId, string key)
    signal collectionDeleteAccepted(string collectionId)
    // U7a: navigation asks the shell to open one of its existing widget views.
    // Never transmit the selected favorite's key/resource ID or command.
    signal ownerNavigationRequested(string owner, string view)
    // Fixed, non-sensitive exact route only; Weather rechecks its own store.
    signal exactNavigationRequested(string owner, string route)
    // U7b-C: one vetted DesktopEntry id, never AppControl actions.
    signal appSelectionRequested(string desktopId)
    // U7b-D: fixed SYSTEM metric only, not a device ID or control action.
    signal systemSelectionRequested(string metric)
    // Exact SYSTEM row/metric-watch view only; never an action.
    signal systemWatchSelectionRequested(string token)
    // Opaque selection token; AppControl alone resolves the saved hardware ID.
    signal thermalSelectionRequested(string token)
    readonly property var thermalSelection:
        ThermalSelection.plan(pane.selectedResource)
    readonly property var systemSelection:
        SystemSelection.plan(pane.selectedResource)
    readonly property var systemWatchSelection:
        SystemWatchSelection.plan(pane.selectedResource)
    readonly property var appSelection:
        AppSelection.plan(pane.selectedResource)
    readonly property var ownerNavigation:
        OwnerNavigation.plan(pane.selectedResource)
    readonly property var exactNavigation:
        ExactNavigation.plan(pane.selectedResource)
    readonly property var dossier: Dossier.build(pane.candidates)
    readonly property var collectionView: CollectionView.build(
        pane.collectionsOwner ? pane.collectionsOwner.collections : [],
        pane.candidates,
        pane.collectionsOwner ? pane.collectionsOwner.storageState : "disconnected")
    readonly property var selectedCollection:
        CollectionView.section(pane.collectionView,pane.selectedCollectionId)
    property var collapsedIndexGroups: ({})
    function toggleIndexGroup(key) {
        const next=Object.assign({},collapsedIndexGroups);
        next[key]=!next[key];
        collapsedIndexGroups=next;
    }
    function allIndexGroupsCollapsed() {
        return pane.dossier.groups.length>0
            && pane.dossier.groups.every(function(group) {
                return pane.collapsedIndexGroups[group.key]===true;
            });
    }
    function toggleAllIndexGroups() {
        const collapsed=!allIndexGroupsCollapsed();
        const next={};
        for(const group of pane.dossier.groups)
            if(collapsed)next[group.key]=true;
        collapsedIndexGroups=next;
        dossierScroll.contentY=0;
    }
    function revealSelectedInSelector() {
        if (pane.area!=="selector" || !pane.selectedResource) return;
        const pos=pane.choices.findIndex(function(row) {
            return row.key===pane.selectedResource.key;
        });
        if(pos<0) return;
        const row=savedItemRows.itemAt(pos);
        if(!row) return;
        listScroll.contentY=Math.max(0,Math.min(
            Math.max(0,listScroll.contentHeight-listScroll.height),
            row.y-4));
    }
    onFilterModeChanged: {
        menuFilter="ALL";
        if(pane.area==="selector") {
            subfilterScroll.contentX=0;
            Qt.callLater(pane.revealSelectedInSelector);
        }
    }
    onSelectedCollectionIdChanged: {
        if(pane.filterMode==="GROUP") menuFilter="ALL";
    }
    readonly property bool editingText:
        (area==="selector" && favoritesSearchInput.activeFocus)
        || (area==="details" && collectionManager.visible
            && collectionManager.editingText)
    property bool removeArmed: false
    onSelectedResourceChanged: {
        removeArmed=false;
        if(pane.area==="selector")
            Qt.callLater(pane.revealSelectedInSelector);
    }

    readonly property var menuSourceRows:
        pane.filterMode==="GROUP"
        ? CollectionView.rowsFor(pane.collectionView,pane.selectedCollectionId)
        : pane.candidates && Array.isArray(pane.candidates.rows)
          ? pane.candidates.rows : []
    readonly property var menuOptions:
        Dossier.menusFor(pane.candidates,pane.filterMode,pane.menuSourceRows)
    readonly property var choices: pane.menuSourceRows.filter(function(row) {
        return (pane.filterMode==="ALL" || pane.filterMode==="GROUP"
                || row.category===pane.filterMode)
            && (pane.menuFilter==="ALL" || row.menu===pane.menuFilter)
            && Search.matches(row,pane.searchQuery);
    })
    readonly property var groupRecords:
        collectionsOwner ? collectionsOwner.collections : []

    function favoriteRowLabel(item) {
        if (!item) return "";
        if (item.owner!=="appcontrol") return item.label;
        const menu=String(item.menu || "OTHER");
        const prefix=menu+" // ";
        const fallback=String(item.label || "");
        // Fallback labels already include the menu to make details useful.
        // Avoid printing that same menu twice in the middle selector.
        const text=item.resolved ? item.item
            : fallback.indexOf(prefix)===0
              ? fallback.slice(prefix.length) : fallback;
        return "APP CTRL // "+menu+" // "+text;
    }

    Column {
        id: overview
        visible: pane.area==="overview"
        anchors.fill: parent
        spacing: 5

        GohuText {
            width: parent.width
            height: 16
            text: "FAVORITES++ // INDEX"
            color: Colors.magenta
            font.pixelSize: 12
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 14
            text: "SAVED "+pane.dossier.total
                +" // MENUS "+pane.dossier.groupCount
            color: Colors.orange
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Row {
            width: parent.width
            height: 23
            spacing: 5
            QuietText {
                width: Math.max(0,parent.width-collapseAllButton.width-parent.spacing)
                height: parent.height
                text: "SOURCE // MENU // EXACT ITEM"
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            ActionButton {
                id: collapseAllButton
                width: 91
                height: 22
                label: pane.allIndexGroupsCollapsed() ? "EXPAND ALL" : "COLLAPSE ALL"
                labelPixelSize: 8
                accentColor: Colors.cyan
                available: pane.dossier.groupCount>0
                onLeftClicked: pane.toggleAllIndexGroups()
            }
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        // U6b: collections are a second VIEW of original owner resources,
        // placed above the unchanged source/menu dossier. No raw member key
        // is ever rendered if the owner candidate is missing.
        Column {
            id: collectionSection
            width: parent.width
            spacing: 3
            height: pane.collectionView.groups.length
                ? Math.max(92,Math.min(228,overview.height*0.36))
                : 20
            GohuText {
                width: parent.width
                height: 16
                text: "COLLECTIONS // "+pane.collectionView.count
                color: Colors.magenta
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            Flickable {
                id: collectionScroll
                width: parent.width
                height: Math.max(0,collectionSection.height-19)
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: collectionRows.implicitHeight
                Column {
                    id: collectionRows
                    width: collectionScroll.width
                    spacing: 3
                    Repeater {
                        id: collectionGroupRepeater
                        model: pane.collectionView.groups
                        Column {
                            id: collectionGroup
                            required property var modelData
                            readonly property var section: modelData
                            // Native testing uses the real button, not an action.
                            property alias memberItems: collectionMemberRepeater
                            width: collectionRows.width
                            spacing: 2
                            property bool confirmDelete: false
                            Rectangle {
                                id: collectionHeading
                                width: parent.width
                                height: 29
                                color: pane.selectedCollectionId===collectionGroup.section.id
                                    ? "#341147" : "#301139"
                                border.width: 1
                                border.color: pane.selectedCollectionId===collectionGroup.section.id
                                    ? Colors.magenta : Colors.cyan
                                GohuText {
                                    anchors.fill: parent
                                    anchors.leftMargin: 5
                                    anchors.rightMargin: 42
                                    verticalAlignment: Text.AlignVCenter
                                    text: collectionGroup.section.name+" // "
                                        +collectionGroup.section.available
                                        +"/"+collectionGroup.section.count
                                    textFormat: Text.PlainText
                                    font.pixelSize: 10
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                                MouseArea {
                                    id: collectionHit
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    activeFocusOnTab: true
                                    Accessible.role: Accessible.Button
                                    Accessible.name: "Collection "+collectionGroup.section.name
                                    Accessible.onPressAction:
                                        pane.collectionRequested(collectionGroup.section.id)
                                    onClicked: pane.collectionRequested(collectionGroup.section.id)
                                    onWheel: function(wheel) { wheel.accepted=false; }
                                    Keys.onPressed: function(event) {
                                        if(event.key===Qt.Key_Return
                                                || event.key===Qt.Key_Enter
                                                || event.key===Qt.Key_Space) {
                                            pane.collectionRequested(collectionGroup.section.id);
                                            event.accepted=true;
                                        }
                                    }
                                }
                                // Only the original CollectionsStore can delete.
                                // Two clicks prevent accidental loss of grouping.
                                ActionButton {
                                    id: leftCollectionDelete
                                    anchors.right: parent.right
                                    anchors.rightMargin: 3
                                    anchors.verticalCenter: parent.verticalCenter
                                    z: 3
                                    width: collectionGroup.confirmDelete ? 39 : 26
                                    height: 23
                                    label: collectionGroup.confirmDelete ? "SURE?" : "✕"
                                    labelPixelSize: 10
                                    accentColor: Colors.red
                                    destructive: true
                                    available: pane.collectionsOwner !== null
                                        && pane.collectionsOwner.canEdit
                                    onLeftClicked: {
                                        if (!collectionGroup.confirmDelete) {
                                            collectionGroup.confirmDelete=true;
                                            return;
                                        }
                                        const id=collectionGroup.section.id;
                                        if(pane.collectionsOwner.deleteCollection(id))
                                            pane.collectionDeleteAccepted(id);
                                    }
                                }
                            }
                            Column {
                                width: parent.width
                                spacing: 2
                                visible: pane.selectedCollectionId===collectionGroup.section.id
                                height: visible ? implicitHeight : 0
                                Repeater {
                                    id: collectionMemberRepeater
                                    model: collectionGroup.section.items
                                    Rectangle {
                                        id: collectionMember
                                        required property var modelData
                                        width: collectionGroup.width
                                        height: 29
                                        color: !modelData.missing && pane.selectedResource
                                            && pane.selectedResource.key===modelData.key
                                            ? "#341147" : "#1B0623"
                                        border.width: 1
                                        border.color: modelData.missing ? "#3A2447" : Colors.cyan
                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 3
                                            spacing: 1
                                            GohuText {
                                                width: parent.width
                                                text: collectionMember.modelData.name
                                                textFormat: Text.PlainText
                                                color: collectionMember.modelData.missing
                                                    ? Colors.orange : Colors.white
                                                font.pixelSize: 9
                                                elide: Text.ElideRight
                                            }
                                            QuietText {
                                                width: parent.width
                                                text: collectionMember.modelData.type
                                                textFormat: Text.PlainText
                                                font.pixelSize: 8
                                                elide: Text.ElideRight
                                            }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            enabled: !collectionMember.modelData.missing
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            activeFocusOnTab: enabled
                                            Accessible.role: Accessible.Button
                                            Accessible.name: collectionGroup.section.name
                                                +" // "+collectionMember.modelData.name
                                            Accessible.onPressAction:
                                                pane.collectionMemberRequested(
                                                    collectionGroup.section.id,
                                                    collectionMember.modelData.key)
                                            onClicked: pane.collectionMemberRequested(
                                                collectionGroup.section.id,
                                                collectionMember.modelData.key)
                                            onWheel: function(wheel) { wheel.accepted=false; }
                                            Keys.onPressed: function(event) {
                                                if(enabled && (event.key===Qt.Key_Return
                                                        || event.key===Qt.Key_Enter
                                                        || event.key===Qt.Key_Space)) {
                                                    pane.collectionMemberRequested(
                                                        collectionGroup.section.id,
                                                        collectionMember.modelData.key);
                                                    event.accepted=true;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Flickable {
            id: dossierScroll
            width: parent.width
            height: Math.max(0,overview.height-75-collectionSection.height-5)
            clip: true
            contentWidth: width
            contentHeight: dossierRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: dossierRows
                width: dossierScroll.width
                spacing: 5
                Repeater {
                    id: dossierGroupRepeater
                    model: pane.dossier.groups
                    Column {
                        id: dossierGroup
                        property var section: modelData
                        // Test/reveal navigation, never actuation.
                        property alias entryItems: dossierEntryRepeater
                        width: dossierRows.width
                        spacing: 2
                        Rectangle {
                            width: parent.width
                            height: 23
                            color: "#301139"
                            border.width: 1
                            border.color: Colors.cyan
                            GohuText {
                                anchors.fill: parent
                                anchors.leftMargin: 5
                                anchors.rightMargin: 3
                                verticalAlignment: Text.AlignVCenter
                                text: (pane.collapsedIndexGroups[dossierGroup.section.key]
                                       ? "+ " : "− ")
                                    +dossierGroup.section.title
                                    +" // "+dossierGroup.section.count
                                textFormat: Text.PlainText
                                color: Colors.cyan
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: pane.toggleIndexGroup(
                                    dossierGroup.section.key)
                            }
                        }
                        Column {
                            id: dossierEntries
                            width: parent.width
                            spacing: 2
                            visible: !pane.collapsedIndexGroups[dossierGroup.section.key]
                            height: visible ? implicitHeight : 0
                            Repeater {
                                id: dossierEntryRepeater
                                model: dossierGroup.section.items
                                Rectangle {
                                    id: dossierItem
                                    property var entry: modelData
                                    width: dossierEntries.width
                                    height: 37
                                    color: pane.selectedResource
                                        && pane.selectedResource.key===entry.key
                                        ? "#341147" : "#1B0623"
                                    border.width: 1
                                    border.color: pane.selectedResource
                                        && pane.selectedResource.key===entry.key
                                        ? Colors.magenta
                                        : indexHit.containsMouse || indexHit.activeFocus
                                          ? Colors.orange : "#3A2447"
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        spacing: 1
                                        GohuText {
                                            width: parent.width
                                            height: 16
                                            text: dossierItem.entry.name
                                            textFormat: Text.PlainText
                                            color: Colors.white
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }
                                        QuietText {
                                            width: parent.width
                                            height: 11
                                            text: dossierItem.entry.type
                                                +" // "+(dossierItem.entry.readOnly
                                                         ? "READ ONLY" : "SAVED")
                                            textFormat: Text.PlainText
                                            font.pixelSize: 8
                                            color: Colors.orange
                                            elide: Text.ElideRight
                                        }
                                    }
                                    MouseArea {
                                        id: indexHit
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        activeFocusOnTab: true
                                        Accessible.role: Accessible.Button
                                        Accessible.name: dossierGroup.section.title
                                            +" // "+dossierItem.entry.name
                                        Accessible.onPressAction:
                                            pane.indexSelectionRequested(
                                                dossierItem.entry.key,
                                                dossierItem.entry.category)
                                        onClicked: pane.indexSelectionRequested(
                                            dossierItem.entry.key,
                                            dossierItem.entry.category)
                                        onWheel: function(wheel) {
                                            wheel.accepted=false;
                                        }
                                        Keys.onPressed: function(event) {
                                            if(event.key===Qt.Key_Return
                                                    || event.key===Qt.Key_Enter
                                                    || event.key===Qt.Key_Space) {
                                                pane.indexSelectionRequested(
                                                    dossierItem.entry.key,
                                                    dossierItem.entry.category);
                                                event.accepted=true;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                QuietText {
                    width: parent.width
                    visible: pane.dossier.total===0
                    text: "NO SAVED ITEMS IN ORIGINAL SOURCES"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                }
            }
        }
    }

    Column {
        id: selector
        visible: pane.area==="selector"
        anchors.fill: parent
        spacing: 7

        // U8c // Each row fills the available width. Preserve the readable
        // 6+5 split without leaving a phantom empty button at the right.
        // Icon, frame and halo identities are independent per module.
        Column {
            id: categoryFilterFlow
            width: parent.width
            height: 2*30+spacing
            spacing: 4
            readonly property var categoryKeys: [
                "ALL","GROUP","CPU++","APP CTRL","WEATHER","NOTIFS",
                "RADIO","HOSPITAL","CLOCK","PLACES","NEW"
            ]
            readonly property int upperCount: Math.ceil(categoryKeys.length/2)
            readonly property real tileWidth:
                Math.min(40,Math.max(30,(width-(upperCount-1)*4)/upperCount))

            Repeater {
                model: 2
                Row {
                    required property int index
                    readonly property var rowKeys: index===0
                        ? categoryFilterFlow.categoryKeys.slice(
                              0,categoryFilterFlow.upperCount)
                        : categoryFilterFlow.categoryKeys.slice(
                              categoryFilterFlow.upperCount)
                    // Compact 4px gaps; center the shorter second row
                    // rather than spreading five icons across six slots.
                    spacing: 4
                    width: rowKeys.length*categoryFilterFlow.tileWidth
                        +Math.max(0,rowKeys.length-1)*spacing
                    anchors.horizontalCenter: parent.horizontalCenter
                    height: 30

                    Repeater {
                        model: rowKeys
                        ActionButton {
                            required property string modelData
                            // FAVORITES is the ALL/✦ filter.
                            readonly property bool whiteGlyph:
                                ["CPU++","HOSPITAL","NOTIFS","CLOCK"]
                                    .indexOf(modelData)>=0
                            readonly property color iconInk:
                                whiteGlyph ? Colors.white
                                : ["RADIO","ALL"].indexOf(modelData)>=0
                                  ? Colors.magenta
                                : modelData==="WEATHER" ? Colors.orange
                                : modelData==="PLACES" ? Colors.yellow
                                : Colors.cyan
                            readonly property color frameInk:
                                ["CPU++","RADIO"].indexOf(modelData)>=0
                                ? Colors.cyan
                                : ["HOSPITAL","ALL"].indexOf(modelData)>=0
                                  ? Colors.magenta
                                : ["NOTIFS","CLOCK"].indexOf(modelData)>=0
                                  ? Colors.white
                                : modelData==="WEATHER" ? Colors.orange
                                : modelData==="PLACES" ? Colors.yellow
                                : Colors.cyan
                            // White icons inherit their partner's frame
                            // glow. White-on-white retains a white glow.
                            readonly property color iconGlowInk:
                                whiteGlyph ? frameInk : iconInk

                            width: categoryFilterFlow.tileWidth
                            height: 30
                            contentPadding: 2
                            label: Dossier.mainIcon(modelData)
                            // Weather SUN and Location need a larger glyph
                            // than the standard 18px face inside each tile.
                            labelPixelSize:
                                modelData==="WEATHER" || modelData==="PLACES"
                                ? 23 : 18
                            Accessible.role: Accessible.Button
                            Accessible.name: modelData+" favorites filter"
                            readonly property bool filterOpen:
                                pane.filterMode===modelData
                            selected: filterOpen
                            accentColor: frameInk

                            // U8d // Only the currently opened filter gets
                            // yellow fill + magenta icon/glows. Inactive
                            // filters NEVER acquire a special filled state,
                            // including after the menu is closed/reopened.
                            idleFillColor: Colors.black
                            hoverFillColor:
                                filterOpen ? Colors.yellow : Colors.black
                            pressedFillColor:
                                filterOpen ? Colors.yellow : Colors.black
                            selectedFillColor: Colors.yellow
                            keyboardSelectedFillColor:
                                filterOpen ? Colors.yellow : Colors.black

                            idleForegroundColor: iconInk
                            hoverForegroundColor:
                                filterOpen ? Colors.magenta : iconInk
                            pressedForegroundColor:
                                filterOpen ? Colors.magenta : iconInk
                            selectedForegroundColor: Colors.magenta
                            keyboardSelectedForegroundColor:
                                filterOpen ? Colors.magenta : iconInk
                            idleBorderColor: frameInk
                            hoverBorderColor:
                                filterOpen ? Colors.magenta : frameInk
                            pressedBorderColor:
                                filterOpen ? Colors.magenta : frameInk
                            selectedBorderColor: Colors.magenta
                            keyboardSelectedBorderColor:
                                filterOpen ? Colors.magenta : frameInk
                            idleContentGlowColor: iconGlowInk
                            hoverContentGlowColor:
                                filterOpen ? Colors.magenta : iconGlowInk
                            pressedContentGlowColor:
                                filterOpen ? Colors.magenta : iconGlowInk
                            selectedContentGlowColor: Colors.magenta
                            keyboardSelectedContentGlowColor:
                                filterOpen ? Colors.magenta : iconGlowInk
                            idleSoftGlowColor: frameInk
                            hoverSoftGlowColor:
                                filterOpen ? Colors.magenta : frameInk
                            pressedSoftGlowColor:
                                filterOpen ? Colors.magenta : frameInk
                            selectedSoftGlowColor: Colors.magenta
                            keyboardSelectedSoftGlowColor:
                                filterOpen ? Colors.magenta : frameInk

                            selectedBorderWidth: 2
                            keyboardSelectedBorderWidth: 2
                            contentGlowIdleOpacity: 0.52
                            contentGlowHoverOpacity: 0.80
                            contentGlowPressedOpacity: 0.68
                            contentGlowSelectedOpacity: 0.82
                            contentGlowKeyboardSelectedOpacity: 0.82
                            softGlowIdleOpacity: 0.32
                            softGlowHoverOpacity: 0.66
                            softGlowPressedOpacity: 0.66
                            softGlowSelectedOpacity: 0.72
                            softGlowKeyboardSelectedOpacity: 0.72

                            onLeftClicked: pane.filterMode=modelData
                        }
                    }
                }
            }
        }
        // U9c // Search the same visible, owner-approved saved entries.
        // A new query starts globally; clicking a category afterwards
        // intentionally narrows those results. No owner action is invoked.
        Rectangle {
            id: favoritesSearchBar
            width: parent.width
            height: 32
            color: Colors.black
            border.width: 1
            border.color: favoritesSearchInput.activeFocus
                ? Colors.magenta : Colors.cyan

            // Place the hint and typed query on the LEFT. Center both
            // vertically within the 32px search terminal, not horizontally.
            QuietText {
                anchors.left: favoritesSearchInput.left
                anchors.verticalCenter: parent.verticalCenter
                width: favoritesSearchInput.width
                visible: favoritesSearchInput.text.length===0
                text: "⌕  SEARCH // NAME, MENU, PLACE..."
                font.pixelSize: 9
                color: Colors.cyan
                horizontalAlignment: Text.AlignLeft
                elide: Text.ElideRight
            }
            TextInput {
                id: favoritesSearchInput
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.right: favoritesSearchClear.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                height: 22
                font.family: GohuFont.family
                font.pixelSize: 11
                horizontalAlignment: TextInput.AlignLeft
                verticalAlignment: TextInput.AlignVCenter
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                // Use the native TextInput cursor position and blink; only
                // override the artwork. Orange is reserved for the caret.
                cursorDelegate: Rectangle {
                    width: 2
                    height: favoritesSearchInput.font.pixelSize+4
                    color: Colors.orange
                }
                maximumLength: 120
                selectByMouse: true
                clip: true
                property bool searchWasEmpty: true
                Accessible.role: Accessible.EditableText
                Accessible.name: "Search saved favorites by any words in any order"
                onTextChanged: {
                    const entering=searchWasEmpty && text.trim().length>0;
                    searchWasEmpty=text.trim().length===0;
                    if(entering) {
                        pane.filterMode="ALL";
                        pane.menuFilter="ALL";
                    }
                    listScroll.contentY=0;
                }
                Keys.onEscapePressed: function(event) {
                    if(text.length)text="";
                    else focus=false;
                    event.accepted=true;
                }
            }
            ActionButton {
                id: favoritesSearchClear
                anchors.right: parent.right
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                width: 23
                height: 23
                label: "×"
                labelPixelSize: 16
                available: favoritesSearchInput.text.length>0
                accentColor: Colors.red
                destructive: true
                idleFillColor: Colors.black
                hoverFillColor: Colors.black
                pressedFillColor: Colors.black
                selectedFillColor: Colors.black
                keyboardSelectedFillColor: Colors.black
                idleForegroundColor: Colors.red
                hoverForegroundColor: Colors.red
                pressedForegroundColor: Colors.red
                selectedForegroundColor: Colors.red
                keyboardSelectedForegroundColor: Colors.red
                idleBorderColor: Colors.red
                hoverBorderColor: Colors.red
                pressedBorderColor: Colors.red
                selectedBorderColor: Colors.red
                keyboardSelectedBorderColor: Colors.red
                idleContentGlowColor: Colors.red
                hoverContentGlowColor: Colors.red
                pressedContentGlowColor: Colors.red
                selectedContentGlowColor: Colors.red
                keyboardSelectedContentGlowColor: Colors.red
                idleSoftGlowColor: Colors.red
                hoverSoftGlowColor: Colors.red
                pressedSoftGlowColor: Colors.red
                selectedSoftGlowColor: Colors.red
                keyboardSelectedSoftGlowColor: Colors.red
                contentGlowIdleOpacity: 0.52
                contentGlowHoverOpacity: 0.80
                softGlowIdleOpacity: 0.32
                softGlowHoverOpacity: 0.66
                onLeftClicked: favoritesSearchInput.text=""
            }
        }
        QuietText {
            width: parent.width
            text: pane.filterMode==="GROUP"
                ? pane.selectedCollection
                    ? "COLLECTION // "+pane.selectedCollection.name
                    : "COLLECTION // CHOOSE ONE IN LEFT INDEX"
                : "OWNER-SAVED ITEMS // SELECT TO INSPECT"
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "LISTED "+pane.choices.length
                +" / "+(pane.filterMode==="GROUP"
                    ? pane.selectedCollection ? pane.selectedCollection.count : 0
                    : pane.candidates ? pane.candidates.total : 0)
            color: Colors.orange
            font.pixelSize: 11
        }

        Flickable {
            id: listScroll
            width: parent.width
            height: Math.max(0,selector.height-categoryFilterFlow.height-favoritesSearchBar.height-129)
            clip: true
            contentWidth: width
            contentHeight: listRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: listRows
                width: listScroll.width
                spacing: 5
                Repeater {
                    id: savedItemRows
                    model: pane.choices
                    Rectangle {
                        id: favoriteRow
                        width: listRows.width
                        height: modelData.readOnly ? 58 : 46

                        // U9f // OPEN outranks HOVER. Both use the same
                        // whole-row visual grammar as the shared ActionButton:
                        // idle black/cyan, hover yellow/orange, open
                        // yellow/magenta. This is visual state ONLY.
                        readonly property bool isOpen:
                            !!pane.selectedResource
                            && pane.selectedResource.key===modelData.key
                        readonly property bool isHovered:
                            !isOpen && (rowHit.containsMouse || rowHit.activeFocus)
                        readonly property color rowAccent:
                            isOpen ? Colors.magenta
                            : isHovered ? Colors.orange : Colors.cyan

                        color: isOpen || isHovered ? Colors.yellow : Colors.black
                        border.width: 1
                        border.color: rowAccent

                        // Do not run per-row glow shaders for idle entries.
                        // Only the hovered and opened rows render effects.
                        RectangularShadow {
                            anchors.fill: parent
                            z: -1
                            spread: 3
                            visible: favoriteRow.isOpen || favoriteRow.isHovered
                            opacity: favoriteRow.isOpen ? 0.58 : 0.50
                            color: favoriteRow.rowAccent
                        }

                        Column {
                            id: rowContent
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 1
                            GohuText {
                                id: rowTitle
                                width: parent.width
                                height: modelData.readOnly ? 30 : 15
                                text: pane.favoriteRowLabel(modelData)
                                textFormat: Text.PlainText
                                color: favoriteRow.isOpen ? Colors.magenta
                                    : favoriteRow.isHovered ? Colors.orange : Colors.white
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                                maximumLineCount: modelData.readOnly ? 2 : 1
                                elide: Text.ElideRight
                            }
                            GohuText {
                                id: rowStatus
                                width: parent.width
                                text: modelData.readOnly
                                    ? modelData.favoriteType+" // READ ONLY"
                                    : modelData.category
                                      +" // "+(modelData.readOnly?"READ ONLY":modelData.isPinned?"PINNED":"SAVED")
                                textFormat: Text.PlainText
                                color: favoriteRow.isOpen ? Colors.magenta : Colors.orange
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
                        }

                        // Text glow follows the exact rendered glyph positions.
                        // SafeDropShadow disconnects when the row leaves its
                        // window, and stays off for unselected/unhovered rows.
                        SafeDropShadow {
                            x: rowContent.x + rowTitle.x
                            y: rowContent.y + rowTitle.y
                            width: rowTitle.width
                            height: rowTitle.height
                            z: 2
                            safeSource: rowTitle
                            requestedVisible: favoriteRow.isOpen || favoriteRow.isHovered
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 6
                            samples: 9
                            opacity: favoriteRow.isOpen ? 0.72 : 0.60
                            color: favoriteRow.rowAccent
                            transparentBorder: true
                        }
                        SafeDropShadow {
                            x: rowContent.x + rowStatus.x
                            y: rowContent.y + rowStatus.y
                            width: rowStatus.width
                            height: rowStatus.height
                            z: 2
                            safeSource: rowStatus
                            requestedVisible: favoriteRow.isOpen || favoriteRow.isHovered
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 5
                            samples: 7
                            opacity: favoriteRow.isOpen ? 0.66 : 0.48
                            color: favoriteRow.rowAccent
                            transparentBorder: true
                        }
                        // One full-row selection target. No nested VIEW control,
                        // writer, process action or permission elevation.
                        MouseArea {
                            id: rowHit
                            anchors.fill: parent
                            hoverEnabled: true
                            preventStealing: false
                            cursorShape: Qt.PointingHandCursor
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: modelData.owner==="appcontrol"
                                ? "AppControl // "+modelData.menu+" // "+modelData.item
                                : modelData.label
                            Accessible.onPressAction: pane.selectionRequested(modelData.key)
                            onClicked: pane.selectionRequested(modelData.key)
                            // Keep wheel-scrolling owned by the enclosing Flickable.
                            onWheel: function(wheel) { wheel.accepted=false; }
                            Keys.onPressed: function(event) {
                                if (event.key===Qt.Key_Return
                                        || event.key===Qt.Key_Enter
                                        || event.key===Qt.Key_Space) {
                                    pane.selectionRequested(modelData.key);
                                    event.accepted=true;
                                }
                            }
                        }
                    }
                }
                QuietText {
                    width: parent.width
                    visible: pane.choices.length===0
                    text: pane.filterMode==="GROUP"
                        ? pane.selectedCollection
                          ? "NO LOADED MEMBERS // ORIGINAL SOURCES MAY BE UNAVAILABLE"
                          : "SELECT A COLLECTION IN THE LEFT INDEX"
                        : "NO SUPPORTED SAVED ITEMS IN THIS FILTER"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                }
            }
        }
        // Secondary source/menu filters remain pinned below the scrollable
        // list. Only canonical dossier menu names are offered here.
        Row {
            width: parent.width
            height: 35
            spacing: 3
            ActionButton {
                id: menuFilterPrev
                width: 22
                height: 29
                label: "‹"
                labelPixelSize: 15
                accentColor: Colors.cyan
                available: subfilterScroll.contentX>0
                onLeftClicked: subfilterScroll.contentX=Math.max(
                    0,subfilterScroll.contentX-140)
            }
            Flickable {
                id: subfilterScroll
                width: Math.max(0,parent.width-menuFilterPrev.width
                    -menuFilterNext.width-parent.spacing*2)
                height: 35
                clip: true
                interactive: contentWidth>width
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: subfilterButtons.implicitWidth
                contentHeight: height
                Row {
                    id: subfilterButtons
                    height: 31
                    spacing: 4
                    Repeater {
                        model: pane.menuOptions
                        ActionButton {
                            required property string modelData
                            width: Math.max(54,Math.min(110,modelData.length*8+22))
                            height: 29
                            label: modelData
                            labelPixelSize: 9
                            readonly property bool filterOpen:
                                pane.menuFilter===modelData
                            selected: filterOpen
                            accentColor: Colors.cyan
                            idleFillColor: Colors.black
                            hoverFillColor:
                                filterOpen ? Colors.yellow : Colors.black
                            pressedFillColor:
                                filterOpen ? Colors.yellow : Colors.black
                            selectedFillColor: Colors.yellow
                            keyboardSelectedFillColor:
                                filterOpen ? Colors.yellow : Colors.black
                            idleForegroundColor: Colors.cyan
                            hoverForegroundColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            pressedForegroundColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            selectedForegroundColor: Colors.magenta
                            keyboardSelectedForegroundColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            idleBorderColor: Colors.cyan
                            hoverBorderColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            pressedBorderColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            selectedBorderColor: Colors.magenta
                            keyboardSelectedBorderColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            idleContentGlowColor: Colors.cyan
                            hoverContentGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            pressedContentGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            selectedContentGlowColor: Colors.magenta
                            keyboardSelectedContentGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            idleSoftGlowColor: Colors.cyan
                            hoverSoftGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            pressedSoftGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            selectedSoftGlowColor: Colors.magenta
                            keyboardSelectedSoftGlowColor:
                                filterOpen ? Colors.magenta : Colors.cyan
                            contentGlowPressedOpacity: 0.68
                            softGlowSelectedOpacity: 0.72
                            onLeftClicked: pane.menuFilter=modelData
                        }
                    }
                }
            }
            ActionButton {
                id: menuFilterNext
                width: 22
                height: 29
                label: "›"
                labelPixelSize: 15
                accentColor: Colors.cyan
                available: subfilterScroll.contentX <
                    subfilterScroll.contentWidth-subfilterScroll.width-1
                onLeftClicked: subfilterScroll.contentX=Math.min(
                    Math.max(0,subfilterScroll.contentWidth-subfilterScroll.width),
                    subfilterScroll.contentX+140)
            }
        }
    }

    Column {
        id: details
        visible: pane.area==="details"
        anchors.fill: parent
        spacing: 8

        GohuText {
            width: parent.width
            text: "SELECTED RESOURCE"
            font.pixelSize: 12
            color: Colors.magenta
        }
        GohuText {
            width: parent.width
            text: pane.selectedResource ? pane.selectedResource.label
                : "NONE SELECTED"
            textFormat: Text.PlainText
            color: Colors.white
            font.pixelSize: 12
            elide: Text.ElideRight
        }
        QuietText {
            width: parent.width
            text: pane.selectedResource
                ? pane.selectedResource.category+" // "
                    +(pane.selectedResource.readOnly
                      ? (pane.selectedResource.owner==="weather-home"
                         ? "WEATHER HOME-OWNED // READ ONLY"
                         : pane.selectedResource.owner==="notifications"
                         ? "NOTIFICATIONS-OWNED // READ ONLY"
                         : pane.selectedResource.owner==="radio"
                         ? "RADIO-OWNED // READ ONLY"
                         : pane.selectedResource.owner==="hospital"
                         ? "HOSPITAL RECEPTION-OWNED // READ ONLY"
                         : "APP CONTROL-OWNED // READ ONLY")
                      : "SAVED IDENTITY")
                : "CHOOSE AN ITEM IN THE CENTER BAY"
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        // AppControl provides the original menu and actual source item.
        // No raw commands, paths, PIDs or action callbacks are displayed here.
        Column {
            id: appControlOrigin
            visible: pane.selectedResource !== null
                     && (pane.selectedResource.owner==="appcontrol"
                         || pane.selectedResource.owner==="weather-home"
                         || pane.selectedResource.owner==="notifications"
                         || pane.selectedResource.owner==="radio"
                         || pane.selectedResource.owner==="hospital")
            width: parent.width
            spacing: 3
            GohuText {
                width: parent.width
                text: pane.selectedResource
                    && pane.selectedResource.owner==="weather-home"
                    ? "SOURCE // WEATHER STATION"
                    : pane.selectedResource
                      && pane.selectedResource.owner==="notifications"
                    ? "SOURCE // NOTIFICATIONS"
                    : pane.selectedResource
                      && pane.selectedResource.owner==="radio"
                    ? "SOURCE // WEATHER STATION RADIO"
                    : pane.selectedResource
                      && pane.selectedResource.owner==="hospital"
                    ? "SOURCE // HOSPITAL RECEPTION"
                    : "SOURCE // APP CONTROL"
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "MENU // "+(pane.selectedResource
                                   ? pane.selectedResource.menu : "")
                font.pixelSize: 10
                color: Colors.orange
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: "ITEM // "+(pane.selectedResource
                                   ? (pane.selectedResource.resolved
                                      ? pane.selectedResource.item
                                      : "NAME UNAVAILABLE") : "")
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: "TYPE // "+(pane.selectedResource
                                   ? pane.selectedResource.favoriteType : "")
                font.pixelSize: 10
                color: Colors.magenta
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                text: "STATUS // READ ONLY"
                font.pixelSize: 10
                color: Colors.white
            }
        }
        Row {
            width: parent.width
            height: 32
            spacing: 7

            ActionButton {
                id: remove
                width: 128
                height: 30
                label: pane.selectedResource && pane.selectedResource.readOnly
                    ? "OPEN OWNER"
                    : pane.removeArmed ? "CONFIRM REMOVE" : "REMOVE FAVORITE"
                labelPixelSize: 9
                accentColor: pane.selectedResource
                    && pane.selectedResource.readOnly ? Colors.cyan : Colors.red
                destructive: pane.removeArmed
                    && !!pane.selectedResource && !pane.selectedResource.readOnly
                available: {
                    const item=pane.selectedResource;
                    if (!item) return false;
                    if(item.readOnly) return pane.ownerNavigation.ok;
                    if(item.category==="CLOCK")
                        return pane.timeOwner !== null && pane.timeOwner.worldFavoriteCanEdit
                            && pane.timeOwner.zoneCatalogLoaded;
                    if(item.category==="PLACES")
                        return pane.placesOwner !== null && pane.placesOwner.canSaveHome;
                    if(item.category==="NEW")
                        return pane.defaultOwner !== null && pane.defaultOwner.canEdit && item.isFavorite;
                    return false;
                }
                onLeftClicked: {
                    if (!available || !pane.selectedResource) return;
                    const item=pane.selectedResource;
                    if(item.readOnly) {
                        const target=pane.ownerNavigation;
                        if(target.ok)
                            pane.ownerNavigationRequested(target.owner,target.view);
                        return;
                    }
                    if (!pane.removeArmed) {pane.removeArmed=true;return;}
                    if (item.category==="CLOCK")
                        pane.timeOwner.toggleWorldFavorite(
                            item.resourceId,pane.timeOwner.zoneCatalog);
                    else if (item.category==="PLACES")
                        pane.placesOwner.removeSavedPlace(Number(item.resourceId));
                    else if (item.category==="NEW")
                        pane.defaultOwner.setFavorite(item.key,false);
                    pane.removeArmed=false;
                }
            }

            ActionButton {
                id: openItem
                width: Math.max(0,parent.width-remove.width-parent.spacing)
                height: 30
                label: pane.selectedResource && pane.selectedResource.readOnly
                    ? (pane.exactNavigation.ok || pane.appSelection.ok
                       || pane.systemSelection.ok || pane.systemWatchSelection.ok
                         || pane.thermalSelection.ok
                       ? "OPEN ITEM" : "NO ACTION")
                    : pane.selectedResource
                      && pane.selectedResource.category==="CLOCK"
                      && pane.timeOwner !== null && !pane.timeOwner.zoneCatalogLoaded
                    ? "CHECK ZONES"
                    : pane.selectedResource
                      && pane.selectedResource.category==="NEW"
                    ? (pane.selectedResource.isPinned?"UNPIN":"PIN")
                    : "NO ACTION"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: pane.selectedResource !== null &&
                    (pane.selectedResource.readOnly
                      ? (pane.exactNavigation.ok || pane.appSelection.ok
                         || pane.systemSelection.ok || pane.systemWatchSelection.ok
                         || pane.thermalSelection.ok)
                      : pane.selectedResource.category==="CLOCK"
                        ? pane.timeOwner !== null && !pane.timeOwner.zoneCatalogLoaded
                          && !pane.timeOwner.zoneCatalogLoading
                        : pane.selectedResource.category==="NEW"
                          && pane.defaultOwner !== null && pane.defaultOwner.canEdit)
                onLeftClicked: {
                    if(!available || !pane.selectedResource) return;
                    if(pane.selectedResource.readOnly) {
                        const target=pane.exactNavigation;
                        if(target.ok)
                            pane.exactNavigationRequested(target.owner,target.route);
                        else if(pane.appSelection.ok)
                            pane.appSelectionRequested(pane.appSelection.desktopId);
                        else if(pane.systemSelection.ok)
                            pane.systemSelectionRequested(pane.systemSelection.metric);
                        else if(pane.systemWatchSelection.ok)
                            pane.systemWatchSelectionRequested(pane.systemWatchSelection.token);
                        else if(pane.thermalSelection.ok)
                            pane.thermalSelectionRequested(pane.thermalSelection.token);
                        return;
                    }
                    if(pane.selectedResource.category==="CLOCK")
                        pane.timeOwner.loadZoneCatalog();
                    else if(pane.selectedResource.category==="NEW")
                        pane.defaultOwner.togglePinned(pane.selectedResource.key);
                }
            }
        }
        Rectangle {width:parent.width;height:1;color:Colors.cyan}
        GohuText {
            width: parent.width
            text: "COLLECTIONS // GROUP MEMBERSHIP"
            font.pixelSize: 11
            color: Colors.magenta
        }
        FavoritesCollectionPanel {
            id: collectionManager
            width: parent.width
            height: Math.max(0,details.height-(appControlOrigin.visible ? 255 : 143))
            collectionStore: pane.collectionsOwner
            // Titles in the existing editor open the same collection in
            // the left/middle/right browsing flow. No owner action.
            onCollectionRequested: function(collectionId) {
                pane.collectionRequested(collectionId);
            }
            onCreateAccepted: function(collectionId) {
                // The one-writer store's pending/queued document is reactive;
                // allow the collection view to refresh before navigating.
                Qt.callLater(function() {
                    pane.collectionRequested(collectionId);
                });
            }
            // U6a: grouping does not grant commands/recall/mutation rights.
            // Only identifiers approved by the existing CollectionsStore
            // may be persisted; unsafe external keys stay unavailable.
            collectionKey: pane.selectedResource
                ? pane.selectedResource.key : ""
            resource: pane.selectedResource && !pane.selectedResource.readOnly
                ? ({
                    provider:pane.selectedResource.provider,
                    kind:pane.selectedResource.kind,
                    resourceId:pane.selectedResource.resourceId,
                    label:pane.selectedResource.label,
                    capabilities:["collection"]
                }) : null
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            text: pane.selectedResource && pane.selectedResource.readOnly
                ? (pane.selectedResource.owner==="weather-home"
                   ? "WEATHER STATION REMAINS OWNER // NO RECALL"
                   : pane.selectedResource.owner==="notifications"
                     ? "NOTIFICATIONS REMAINS OWNER // NO MESSAGE ACCESS"
                     : pane.selectedResource.owner==="radio"
                       ? "RADIO REMAINS OWNER // NO PLAYBACK"
                       : pane.selectedResource.owner==="hospital"
                         ? "HOSPITAL REMAINS OWNER // NO ARCHIVE ACCESS"
                         : "APP CONTROL REMAINS OWNER // NO EXECUTION")
                : "GROUPING ≠ AUTHORITY // ORIGINAL OWNERS KEEP CONTROL"
            elide: Text.ElideRight
        }
    }
}
