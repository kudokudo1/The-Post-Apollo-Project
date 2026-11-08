import QtQuick
import QtQuick.Controls
import "../services/favorites/FavoritesResourcePolicy.js" as Resource

// U3a reusable local group manager. Must receive the original CollectionsStore.
// No favorite storage, provider action or resource-resolution authority here.
Rectangle {
    id: panel
    property var collectionStore: null
    property var resource: null
    property alias draftName: nameInput.text
    property alias createControl: createButton
    readonly property bool editingText: nameInput.activeFocus
    readonly property var normalized: Resource.normalize(resource)
    readonly property string resourceKey:
        normalized.ok ? normalized.record.key : ""
    readonly property bool canUseResource:
        collectionStore !== null && normalized.ok
        && normalized.record.capabilities.indexOf("collection") >= 0
        && collectionStore.acceptsKey(resourceKey)
    readonly property var groups:
        collectionStore ? collectionStore.collections : []
    signal createAccepted(string collectionId)

    function createFromInput() {
        if (collectionStore === null || !collectionStore.canEdit)
            return;
        const id=collectionStore.createCollection(nameInput.text);
        if (id !== "") {
            nameInput.text="";
            createAccepted(id);
        }
    }

    color: Colors.black
    clip: true

    Column {
        anchors.fill: parent
        spacing: 5

        Row {
            width: parent.width
            height: 30
            spacing: 5

            TextField {
                id: nameInput
                width: Math.max(0,parent.width - createButton.width - 5)
                height: parent.height
                placeholderText: "NEW COLLECTION NAME"
                color: Colors.white
                placeholderTextColor: Colors.cyan
                selectionColor: Colors.magenta
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 11
                selectByMouse: true
                leftPadding: 8
                rightPadding: 8
                background: Rectangle {
                    color: Colors.black
                    border.color: nameInput.activeFocus
                        ? Colors.magenta : Colors.cyan
                    border.width: 1
                }
                onAccepted: panel.createFromInput()
            }

            ActionButton {
                id: createButton
                width: 67
                height: parent.height
                label: "CREATE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: panel.collectionStore !== null
                    && panel.collectionStore.canEdit
                    && nameInput.text.trim().length > 0
                onLeftClicked: panel.createFromInput()
            }
        }

        GohuText {
            width: parent.width
            height: 15
            text: panel.canUseResource
                ? "SELECTED ITEM // ADD TO ANY COLLECTION"
                : "NO SUPPORTED ITEM SELECTED // CREATE GROUPS"
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }

        Flickable {
            id: groupScroll
            width: parent.width
            height: Math.max(0,panel.height - 81)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: groupRows.implicitHeight

            Column {
                id: groupRows
                width: groupScroll.width
                spacing: 4

                Repeater {
                    model: panel.groups
                    Rectangle {
                        id: groupRow
                        property bool confirmDelete: false
                        width: groupRows.width
                        height: 32
                        color: "#1B0623"
                        border.color: Colors.cyan
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 4

                            GohuText {
                                width: Math.max(0,parent.width
                                    - groupToggle.width - upButton.width
                                    - downButton.width - deleteButton.width
                                    - memberCount.width - parent.spacing*5)
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: modelData.name
                                textFormat: Text.PlainText
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                id: memberCount
                                width: 20
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: String(modelData.members.length)
                                font.pixelSize: 9
                                color: Colors.orange
                            }

                            FavoritesCollectionToggleButton {
                                id: groupToggle
                                width: 57
                                height: parent.height
                                collectionStore: panel.collectionStore
                                collectionId: modelData.id
                                resource: panel.resource
                            }

                            ActionButton {
                                id: upButton
                                width: 24
                                height: parent.height
                                label: "↑"
                                labelPixelSize: 12
                                accentColor: Colors.cyan
                                available: groupToggle.inCollection
                                    && panel.collectionStore.canEdit
                                onLeftClicked: panel.collectionStore.moveMember(
                                    modelData.id,panel.resourceKey,-1)
                            }

                            ActionButton {
                                id: downButton
                                width: 24
                                height: parent.height
                                label: "↓"
                                labelPixelSize: 12
                                accentColor: Colors.cyan
                                available: groupToggle.inCollection
                                    && panel.collectionStore.canEdit
                                onLeftClicked: panel.collectionStore.moveMember(
                                    modelData.id,panel.resourceKey,1)
                            }

                            ActionButton {
                                id: deleteButton
                                width: 50
                                height: parent.height
                                label: groupRow.confirmDelete ? "SURE?" : "DELETE"
                                labelPixelSize: 9
                                accentColor: Colors.red
                                destructive: groupRow.confirmDelete
                                available: panel.collectionStore !== null
                                    && panel.collectionStore.canEdit
                                onLeftClicked: {
                                    if (!groupRow.confirmDelete) {
                                        groupRow.confirmDelete=true;
                                        return;
                                    }
                                    panel.collectionStore.deleteCollection(modelData.id);
                                    groupRow.confirmDelete=false;
                                }
                            }
                        }
                    }
                }

                GohuText {
                    visible: panel.groups.length===0
                    width: parent.width
                    text: "NO COLLECTIONS // CREATE THE FIRST"
                    font.pixelSize: 10
                    color: Colors.cyan
                }
            }
        }

        GohuText {
            width: parent.width
            height: 18
            text: collectionStore === null ? "STORE NOT CONNECTED"
                : collectionStore.storageState === "error"
                    || collectionStore.storageState === "unsupported"
                ? "COLLECTIONS NOT WRITABLE // "
                    + collectionStore.errorCode
                : collectionStore.busy
                ? "SAVE PENDING // NOT YET DURABLE"
                : "GROUPS " + groups.length + "/24 // LOCAL ONLY"
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
        }
    }
}
