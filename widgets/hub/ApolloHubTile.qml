import QtQuick
import "../../components"
import "../../services/hub/ApolloHubLayout.js" as Layout

// A presentation adapter, not a second copy of CPU++, Weather, or Media.
// Those domains remain previews until shared provider adapters are connected.
SectionFrame {
    id: tile

    property string moduleId: "time"
    property bool editing: false
    property bool keyboardSelected: false
    property int tileIndex: 0
    property int tileCount: 0
    property date now: new Date()

    signal moveLeft(int index)
    signal moveRight(int index)
    signal changeModule(int index)
    signal pointerEntered(int index)

    HoverHandler {
        onHoveredChanged: {
            if (hovered)
                tile.pointerEntered(tile.tileIndex);
        }
    }

    fillColor: Colors.black
    fillOpacity: 0.92
    borderColor: keyboardSelected ? Colors.orange : Colors.cyan
    borderOpacity: 0.7
    borderWidth: 1
    radius: 5
    inset: 10

    Timer {
        interval: 1000
        repeat: true
        running: tile.visible && (tile.moduleId === "time" || tile.moduleId === "calendar")
        onTriggered: tile.now = new Date()
    }

    GohuText {
        id: titleLabel
        anchors.left: parent.left
        anchors.top: parent.top
        text: Layout.tileTitle(tile.moduleId)
        color: Colors.cyan
        font.pixelSize: 13
    }

    Row {
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4
        visible: tile.editing

        ActionButton {
            trackLabelGlowLocally: true
            width: 28
            height: 25
            label: "←"
            available: tile.tileIndex > 0
            onLeftClicked: tile.moveLeft(tile.tileIndex)
        }
        ActionButton {
            trackLabelGlowLocally: true
            width: 28
            height: 25
            label: "→"
            available: tile.tileIndex < tile.tileCount - 1
            onLeftClicked: tile.moveRight(tile.tileIndex)
        }
        ActionButton {
            trackLabelGlowLocally: true
            width: 57
            height: 25
            label: "SWAP"
            onLeftClicked: tile.changeModule(tile.tileIndex)
        }
    }

    GohuText {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 3
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        color: tile.moduleId === "time" ? Colors.white : Colors.orange
        font.pixelSize: tile.moduleId === "time" ? 23 : 14
        text: tile.moduleId === "time"
              ? Qt.formatTime(tile.now, "HH:mm:ss")
              : tile.moduleId === "calendar"
              ? Qt.formatDate(tile.now, "ddd, d MMM yyyy")
              : "MODULE PREVIEW"
    }

    GohuText {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        color: Colors.cyan
        opacity: 0.7
        font.pixelSize: 10
        text: tile.moduleId === "time" || tile.moduleId === "calendar"
              ? "LOCAL TIME"
              : "DATA ADAPTER NOT CONNECTED"
    }
}
