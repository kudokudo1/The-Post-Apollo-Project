import QtQuick
import "../../components"
import qs.services.time
import qs.services.location
import qs.services.favorites

// CPU++ Favorites++ manager. Three instances share one selection/snapshot.
// No new FileView, owner process, or action authority is created here.
Item {
    id: pane
    required property string area // overview | selector | details
    property var catalogSnapshot: null
    property var candidates: null
    property var selectedResource: null
    property string filterMode: "ALL"
    signal selectionRequested(string key)
    readonly property bool editingText:
        area==="details" && collectionManager.visible
        && collectionManager.editingText
    property bool removeArmed: false
    onSelectedResourceChanged: removeArmed=false

    readonly property var choices:
        candidates && Array.isArray(candidates.rows)
        ? candidates.rows.filter(function(row) {
            return filterMode==="ALL" || row.category===filterMode;
        }) : []
    readonly property var groupRecords:
        FavoritesCollectionsStore.collections

    Column {
        id: overview
        visible: pane.area==="overview"
        anchors.fill: parent
        spacing: 9

        GohuText {
            text: "UNIVERSAL // SAVED RESOURCES"
            width: parent.width
            color: Colors.magenta
            font.pixelSize: 12
        }
        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "READ ORIGINAL SOURCES // MANAGE APPROVED REFERENCES"
            font.pixelSize: 10
        }
        FavoritesUnifiedPreview {
            width: parent.width
            height: Math.min(310,Math.max(180,overview.height-170))
            snapshot: pane.catalogSnapshot
        }
        Rectangle {width: parent.width;height: 1;color: Colors.cyan}
        GohuText {
            text: "COLLECTIONS // "+FavoritesCollectionsStore.collections.length
                  +"  |  SAVE "+FavoritesCollectionsStore.storageState.toUpperCase()
            color: Colors.cyan
            font.pixelSize: 11
            width: parent.width
            elide: Text.ElideRight
        }
        GohuText {
            text: "NEW PROVIDERS // "+FavoritesDefaultStore.favoriteKeys.length
                +" FAV  |  "+FavoritesDefaultStore.pinnedKeys.length+" PIN"
            color: Colors.white
            font.pixelSize: 11
            width: parent.width
            elide: Text.ElideRight
        }
        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "APP CONTROL ITEMS ARE DISPLAY-ONLY. SAVED DOES NOT MEAN CURRENTLY AVAILABLE."
            font.pixelSize: 10
        }
    }

    Column {
        id: selector
        visible: pane.area==="selector"
        anchors.fill: parent
        spacing: 7

        Row {
            width: parent.width
            height: 31
            spacing: 4
            Repeater {
                model: ["ALL","CLOCK","PLACES","NEW"]
                ActionButton {
                    required property string modelData
                    width: Math.max(1,(selector.width-12)/4)
                    height: 30
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
            text: "SELECT A SAFE FAVORITE TO MANAGE"
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
            height: Math.max(0,selector.height-108)
            clip: true
            contentWidth: width
            contentHeight: listRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: listRows
                width: listScroll.width
                spacing: 5
                Repeater {
                    model: pane.choices
                    Rectangle {
                        width: listRows.width
                        height: 46
                        border.width: 1
                        border.color: pane.selectedResource
                            && pane.selectedResource.key===modelData.key
                            ? Colors.magenta : Colors.cyan
                        color: "#1B0623"
                        Row {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 4
                            Column {
                                width: Math.max(0,parent.width-65)
                                height: parent.height
                                spacing: 1
                                GohuText {
                                    width: parent.width
                                    text: modelData.label
                                    textFormat: Text.PlainText
                                    color: Colors.white
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: modelData.category
                                        +" // "+(modelData.isPinned?"PINNED":"SAVED")
                                    color: Colors.orange
                                    font.pixelSize: 9
                                }
                            }
                            ActionButton {
                                width: 60
                                height: 29
                                anchors.verticalCenter: parent.verticalCenter
                                label: "VIEW"
                                labelPixelSize: 10
                                selected: pane.selectedResource
                                    && pane.selectedResource.key===modelData.key
                                accentColor: Colors.magenta
                                onLeftClicked: pane.selectionRequested(modelData.key)
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
                ? pane.selectedResource.category+" // SAVED IDENTITY"
                : "CHOOSE AN ITEM IN THE CENTER BAY"
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Row {
            width: parent.width
            height: 32
            spacing: 7

            ActionButton {
                id: remove
                width: 128
                height: 30
                label: pane.removeArmed ? "CONFIRM REMOVE" : "REMOVE FAVORITE"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: pane.removeArmed
                available: {
                    const item=pane.selectedResource;
                    if (!item) return false;
                    if(item.category==="CLOCK")
                        return TimeSettings.worldFavoriteCanEdit
                            && TimeSettings.zoneCatalogLoaded;
                    if(item.category==="PLACES")
                        return PlaceRegistry.canSaveHome;
                    if(item.category==="NEW")
                        return FavoritesDefaultStore.canEdit && item.isFavorite;
                    return false;
                }
                onLeftClicked: {
                    if (!available || !pane.selectedResource) return;
                    if (!pane.removeArmed) {pane.removeArmed=true;return;}
                    const item=pane.selectedResource;
                    if (item.category==="CLOCK")
                        TimeSettings.toggleWorldFavorite(
                            item.resourceId,TimeSettings.zoneCatalog);
                    else if (item.category==="PLACES")
                        PlaceRegistry.removeSavedPlace(Number(item.resourceId));
                    else if (item.category==="NEW")
                        FavoritesDefaultStore.setFavorite(item.key,false);
                    pane.removeArmed=false;
                }
            }

            ActionButton {
                width: Math.max(0,parent.width-remove.width-parent.spacing)
                height: 30
                label: pane.selectedResource
                    && pane.selectedResource.category==="CLOCK"
                    && !TimeSettings.zoneCatalogLoaded
                    ? "CHECK ZONES"
                    : pane.selectedResource
                        && pane.selectedResource.category==="NEW"
                    ? (pane.selectedResource.isPinned?"UNPIN":"PIN")
                    : "NO ACTION"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: pane.selectedResource !== null &&
                    (pane.selectedResource.category==="CLOCK"
                       ? !TimeSettings.zoneCatalogLoaded
                          && !TimeSettings.zoneCatalogLoading
                       : pane.selectedResource.category==="NEW"
                         && FavoritesDefaultStore.canEdit)
                onLeftClicked: {
                    if(!available || !pane.selectedResource) return;
                    if(pane.selectedResource.category==="CLOCK")
                        TimeSettings.loadZoneCatalog();
                    else if(pane.selectedResource.category==="NEW")
                        FavoritesDefaultStore.togglePinned(pane.selectedResource.key);
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
            height: Math.max(0,details.height-143)
            collectionStore: FavoritesCollectionsStore
            resource: pane.selectedResource
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
            text: "GROUPING ≠ AUTHORITY // ORIGINAL OWNERS KEEP CONTROL"
            elide: Text.ElideRight
        }
    }
}
