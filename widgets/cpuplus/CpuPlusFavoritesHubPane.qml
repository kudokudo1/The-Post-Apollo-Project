import QtQuick
import "../../components"
import "../../services/favorites/FavoritesDossierIndexPolicy.js" as Dossier

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
    property var timeOwner: null
    property var placesOwner: null
    property var defaultOwner: null
    property var collectionsOwner: null
    property string filterMode: "ALL"
    signal selectionRequested(string key)
    // Overview selects an original candidate and directs the middle bay to
    // its existing filter, never a new owner action.
    signal indexSelectionRequested(string key, string category)
    readonly property var dossier: Dossier.build(pane.candidates)
    property var collapsedIndexGroups: ({})
    function toggleIndexGroup(key) {
        const next=Object.assign({},collapsedIndexGroups);
        next[key]=!next[key];
        collapsedIndexGroups=next;
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
        if(pane.area==="selector") Qt.callLater(pane.revealSelectedInSelector);
    }
    readonly property bool editingText:
        area==="details" && collectionManager.visible
        && collectionManager.editingText
    property bool removeArmed: false
    onSelectedResourceChanged: {
        removeArmed=false;
        if(pane.area==="selector")
            Qt.callLater(pane.revealSelectedInSelector);
    }

    readonly property var choices:
        candidates && Array.isArray(candidates.rows)
        ? candidates.rows.filter(function(row) {
            return filterMode==="ALL" || row.category===filterMode;
        }) : []
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
        QuietText {
            width: parent.width
            height: 13
            text: "SOURCE // MENU // EXACT ITEM"
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        Flickable {
            id: dossierScroll
            width: parent.width
            height: Math.max(0,overview.height-65)
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

        // Seven categories use three compact rows within the middle bay.
        Flow {
            width: parent.width
            height: 90
            spacing: 4
            Repeater {
                model: ["ALL","CPU++","APP CTRL","WEATHER","NOTIFS","CLOCK","PLACES","NEW"]
                ActionButton {
                    required property string modelData
                    width: Math.max(1,(selector.width-8)/3)
                    height: 27
                    label: modelData
                    labelPixelSize: 9
                    selected: pane.filterMode===modelData
                    accentColor: selected ? Colors.magenta : Colors.cyan
                    onLeftClicked: pane.filterMode=modelData
                }
            }
        }
        QuietText {
            width: parent.width
            text: "OWNER-SAVED ITEMS // SELECT TO INSPECT"
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "LISTED "+pane.choices.length
                +" / "+(pane.candidates ? pane.candidates.total : 0)
            color: Colors.orange
            font.pixelSize: 11
        }

        Flickable {
            id: listScroll
            width: parent.width
            height: Math.max(0,selector.height-167)
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
                        border.width: 1
                        border.color: pane.selectedResource
                            && pane.selectedResource.key===modelData.key
                            ? Colors.magenta
                            : rowHit.containsMouse || rowHit.activeFocus
                              ? Colors.orange : Colors.cyan
                        color: "#1B0623"
                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 1
                            GohuText {
                                width: parent.width
                                height: modelData.readOnly ? 30 : 15
                                text: pane.favoriteRowLabel(modelData)
                                textFormat: Text.PlainText
                                color: Colors.white
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                                maximumLineCount: modelData.readOnly ? 2 : 1
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: modelData.readOnly
                                    ? modelData.favoriteType+" // READ ONLY"
                                    : modelData.category
                                      +" // "+(modelData.readOnly?"READ ONLY":modelData.isPinned?"PINNED":"SAVED")
                                textFormat: Text.PlainText
                                color: Colors.orange
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
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
                    text: "NO SUPPORTED SAVED ITEMS IN THIS FILTER"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                }
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
                         || pane.selectedResource.owner==="notifications")
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
                    ? "OWNER CONTROL"
                    : pane.removeArmed ? "CONFIRM REMOVE" : "REMOVE FAVORITE"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: pane.removeArmed
                available: {
                    const item=pane.selectedResource;
                    if (!item) return false;
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
                    if (!pane.removeArmed) {pane.removeArmed=true;return;}
                    const item=pane.selectedResource;
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
                width: Math.max(0,parent.width-remove.width-parent.spacing)
                height: 30
                label: pane.selectedResource
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
                    (pane.selectedResource.category==="CLOCK"
                       ? pane.timeOwner !== null && !pane.timeOwner.zoneCatalogLoaded
                          && !pane.timeOwner.zoneCatalogLoading
                       : pane.selectedResource.category==="NEW"
                         && pane.defaultOwner !== null && pane.defaultOwner.canEdit)
                onLeftClicked: {
                    if(!available || !pane.selectedResource) return;
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
                     : "APP CONTROL REMAINS OWNER // NO EXECUTION")
                : "GROUPING ≠ AUTHORITY // ORIGINAL OWNERS KEEP CONTROL"
            elide: Text.ElideRight
        }
    }
}
