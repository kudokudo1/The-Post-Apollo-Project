import QtQuick
import QtQuick.Controls
import "../services/favorites/FavoritesResourcePolicy.js" as Resource

// U3a reusable local group manager. Must receive the original CollectionsStore.
// No favorite storage, provider action or resource-resolution authority here.
Rectangle {
    id: panel
    property var collectionStore: null
    property var resource: null
    // Optional normalized candidate key for an external read-only owner.
    // No raw provider object, FileView or callback enters this panel.
    property string collectionKey: ""
    property alias draftName: nameInput.text
    property alias createControl: createButton
    property alias groupRowItems: collectionGroupRepeater
    property string activeRenameId: ""
    readonly property bool editingText: nameInput.activeFocus
        || activeRenameId!==""
    readonly property var normalized: Resource.normalize(resource)
    readonly property string resourceKey:
        collectionKey !== "" ? collectionKey
        : normalized.ok ? normalized.record.key : ""
    readonly property bool canUseResource:
        collectionStore !== null && resourceKey !== ""
        && (collectionKey !== ""
            || (normalized.ok
                && normalized.record.capabilities.indexOf("collection") >= 0))
        && collectionStore.acceptsKey(resourceKey)
    readonly property var groups:
        collectionStore ? collectionStore.collections : []
    signal createAccepted(string collectionId)
    // UI-only navigation. The source CollectionsStore stays the sole writer.
    signal collectionRequested(string collectionId)

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
                ? "MEMBERSHIP ONLY // ORIGINAL FAVORITES UNCHANGED"
                : "NO SUPPORTED ITEM // EDIT GROUP NAMES BELOW"
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
                    id: collectionGroupRepeater
                    model: panel.groups
                    Rectangle {
                        id: groupRow
                        property bool confirmDelete: false
                        property string renameError: ""
                        readonly property bool renaming:
                            panel.activeRenameId===modelData.id
                        // Native test seam, not an authority-bearing control.
                        property alias editControl: editButton
                        property alias editField: renameInput
                        width: groupRows.width
                        height: renaming ? 82 : 60
                        color: "#1B0623"
                        border.color: renaming ? Colors.magenta : Colors.cyan
                        border.width: 1

                        function beginRename() {
                            if(panel.collectionStore===null
                                    || !panel.collectionStore.canEdit) return;
                            panel.activeRenameId=modelData.id;
                        }
                        function cancelRename() {
                            if(panel.activeRenameId===modelData.id)
                                panel.activeRenameId="";
                            renameError="";
                        }
                        function saveRename() {
                            if(!renaming || panel.collectionStore===null
                                    || !panel.collectionStore.canEdit) return;
                            const accepted=panel.collectionStore.renameCollection(
                                modelData.id,renameInput.text);
                            if(accepted) cancelRename();
                            else renameError=String(
                                panel.collectionStore.lastResultCode || "RENAME REJECTED");
                        }
                        onRenamingChanged: {
                            if(!renaming) return;
                            renameError="";
                            renameInput.text=modelData.name;
                            Qt.callLater(function() {
                                if(groupRow.renaming) {
                                    renameInput.forceActiveFocus();
                                    renameInput.selectAll();
                                }
                            });
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 3

                            Row {
                                width: parent.width
                                height: 25
                                spacing: 4
                                Item {
                                    width: Math.max(0,parent.width-editButton.width
                                        - cancelButton.width-parent.spacing*2)
                                    height: parent.height
                                    GohuText {
                                        anchors.fill: parent
                                        visible: !groupRow.renaming
                                        verticalAlignment: Text.AlignVCenter
                                        text: modelData.name
                                        textFormat: Text.PlainText
                                        font.pixelSize: 10
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                    // Click the collection name to browse its
                                    // existing members. No extra VIEW button.
                                    MouseArea {
                                        anchors.fill: parent
                                        visible: !groupRow.renaming
                                        enabled: !groupRow.renaming
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        activeFocusOnTab: true
                                        Accessible.role: Accessible.Button
                                        Accessible.name: "Open collection "+modelData.name
                                        Accessible.onPressAction:
                                            panel.collectionRequested(modelData.id)
                                        onClicked: panel.collectionRequested(modelData.id)
                                        Keys.onPressed: function(event) {
                                            if(event.key===Qt.Key_Return
                                                    || event.key===Qt.Key_Enter
                                                    || event.key===Qt.Key_Space) {
                                                panel.collectionRequested(modelData.id);
                                                event.accepted=true;
                                            }
                                        }
                                    }
                                    TextField {
                                        id: renameInput
                                        anchors.fill: parent
                                        visible: groupRow.renaming
                                        color: Colors.white
                                        selectionColor: Colors.magenta
                                        placeholderText: "COLLECTION NAME"
                                        placeholderTextColor: Colors.cyan
                                        font.family: "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 10
                                        leftPadding: 5
                                        rightPadding: 5
                                        selectByMouse: true
                                        background: Rectangle {
                                            color: Colors.black
                                            border.width: 1
                                            border.color: Colors.magenta
                                        }
                                        onAccepted: groupRow.saveRename()
                                        Keys.onEscapePressed: groupRow.cancelRename()
                                    }
                                }
                                ActionButton {
                                    id: editButton
                                    width: 55
                                    height: parent.height
                                    label: groupRow.renaming ? "SAVE" : "RENAME"
                                    labelPixelSize: 9
                                    accentColor: Colors.magenta
                                    available: panel.collectionStore!==null
                                        && panel.collectionStore.canEdit
                                    onLeftClicked: {
                                        if(groupRow.renaming) groupRow.saveRename();
                                        else groupRow.beginRename();
                                    }
                                }
                                ActionButton {
                                    id: cancelButton
                                    visible: groupRow.renaming
                                    width: visible ? 49 : 0
                                    height: parent.height
                                    label: "CANCEL"
                                    labelPixelSize: 8
                                    accentColor: Colors.cyan
                                    onLeftClicked: groupRow.cancelRename()
                                }
                            }

                            Row {
                                width: parent.width
                                height: 26
                                spacing: 3
                                GohuText {
                                    id: memberCount
                                    width: 62
                                    height: parent.height
                                    verticalAlignment: Text.AlignVCenter
                                    text: modelData.members.length+" ITEMS"
                                    font.pixelSize: 9
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                                Item {
                                    width: Math.max(0,parent.width
                                        - memberCount.width - groupToggle.width
                                        - upButton.width - downButton.width
                                        - deleteButton.width - parent.spacing*5)
                                    height: parent.height
                                }
                                FavoritesCollectionToggleButton {
                                    id: groupToggle
                                    width: 61
                                    height: parent.height
                                    collectionStore: panel.collectionStore
                                    collectionId: modelData.id
                                    resource: panel.resource
                                    collectionKey: panel.collectionKey
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
                                    width: 46
                                    height: parent.height
                                    label: groupRow.confirmDelete ? "SURE?" : "DELETE"
                                    labelPixelSize: 8
                                    accentColor: Colors.red
                                    destructive: groupRow.confirmDelete
                                    available: panel.collectionStore!==null
                                        && panel.collectionStore.canEdit
                                    onLeftClicked: {
                                        if(!groupRow.confirmDelete) {
                                            groupRow.confirmDelete=true;
                                            return;
                                        }
                                        if(panel.collectionStore.deleteCollection(modelData.id)) {
                                            groupRow.confirmDelete=false;
                                            groupRow.cancelRename();
                                        }
                                    }
                                }
                            }
                            QuietText {
                                width: parent.width
                                height: visible ? 13 : 0
                                visible: groupRow.renaming
                                text: groupRow.renameError!=="" ?
                                    "RENAME REJECTED // "+groupRow.renameError
                                    : "ENTER TO SAVE // ESC TO CANCEL"
                                font.pixelSize: 9
                                elide: Text.ElideRight
                                color: Colors.orange
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
