import QtQuick
import QtQuick.Controls
import "../../components"

// M2 // Two compact, independently horizontal-scrollable rows. Data is
// projected from StationRadio; this component never reads or writes favorites.
Item {
    id: strips
    objectName: "media-m2-radio-saved-strips"
    property var favoriteItems: []
    property var recentItems: []
    property bool canRecall: false
    property bool compactDocked: false
    signal recallRequested(var station)
    signal removeRequested(var station)

    readonly property int gap: 2
    readonly property real tileWidth: Math.max(24,(width - 9*gap)/10)
    height: compactDocked ? 28 : 88
    readonly property real dockWidth: Math.max(0,(width-6)/2)
    // M6 // Compact square strips leave room for a real directory viewport
    // inside a half-height RADIO, without modifying standalone RADIO tiles.
    readonly property real dockTileWidth:
        Math.max(15,Math.min(17,(dockWidth-9*gap)/10))

    Column {
        anchors.fill: parent
        visible: !strips.compactDocked
        spacing: 4

        Column {
            width: parent.width
            height: 42
            spacing: 2

            GohuText {
                objectName: "media-m2-favorite-label"
                width: parent.width
                height: 10
                text: "FAVORITES // " + strips.favoriteItems.length + " / 10"
                font.pixelSize: 9
                color: Colors.magenta
            }

            Flickable {
                id: favoritesRow
                objectName: "media-m2-favorite-scroll"
                width: parent.width
                height: 30
                clip: true
                contentHeight: height
                contentWidth: Math.max(width,
                    strips.favoriteItems.length * (strips.tileWidth + strips.gap)
                    - strips.gap)
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentWidth > width
                Row {
                    spacing: strips.gap
                    Repeater {
                        model: strips.favoriteItems
                        delegate: Rectangle {
                            id: favoriteTile
                            required property var modelData
                            objectName: "media-m2-favorite-tile"
                            width: strips.tileWidth
                            height: favoritesRow.height
                            radius: 1
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta
                            GohuText {
                                width: parent.width - 4
                                anchors.left: parent.left
                                anchors.leftMargin: 2
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 4
                                text: modelData.title
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                id: recallHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                enabled: strips.canRecall
                                onClicked: strips.recallRequested(modelData)
                            }
                            ToolTip.visible: recallHover.containsMouse
                            ToolTip.text: modelData.title + " // SAFE RECALL // VERIFY UUID // NO STORED STREAM URL // NO AUTOPLAY"
                            ActionButton {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                width: 13
                                height: 13
                                label: "X"
                                labelPixelSize: 8
                                accentColor: Colors.red
                                destructive: true
                                onClicked: strips.removeRequested(modelData)
                            }
                        }
                    }
                }
                QuietText {
                    visible: strips.favoriteItems.length === 0
                    text: "NO FAVORITES // STAR A STATION"
                    font.pixelSize: 9
                    color: Colors.magenta
                }
            }
        }

        Column {
            width: parent.width
            height: 42
            spacing: 2
            GohuText {
                objectName: "media-m2-recent-label"
                width: parent.width
                height: 10
                text: "RECENTS // " + strips.recentItems.length + " / 8"
                font.pixelSize: 9
                color: Colors.orange
            }
            Flickable {
                id: recentRow
                objectName: "media-m2-recent-scroll"
                width: parent.width
                height: 30
                clip: true
                contentHeight: height
                contentWidth: Math.max(width,
                    strips.recentItems.length * (strips.tileWidth + strips.gap)
                    - strips.gap)
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentWidth > width
                Row {
                    spacing: strips.gap
                    Repeater {
                        model: strips.recentItems
                        delegate: Rectangle {
                            id: recentTile
                            required property var modelData
                            objectName: "media-m2-recent-tile"
                            width: strips.tileWidth
                            height: recentRow.height
                            radius: 1
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.orange
                            GohuText {
                                anchors.fill: parent
                                anchors.margins: 2
                                text: modelData.title
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                            MouseArea {
                                id: recentHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                enabled: strips.canRecall
                                onClicked: strips.recallRequested(modelData)
                            }
                            ToolTip.visible: recentHover.containsMouse
                            ToolTip.text: modelData.title + " // RECALL"
                        }
                    }
                }
                QuietText {
                    visible: strips.recentItems.length === 0
                    text: "NO RECENTLY LOADED STATIONS"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }
        }
    }

    // M4 // Both saved lanes remain pinned, but share one short instrument
    // row on a narrow overview. Each half still fits up to ten square
    // station tiles; overflowing items scroll only sideways.
    Row {
        id: dockedSavedRow
        objectName: "media-m4-pinned-saved-pair"
        anchors.fill: parent
        spacing: 6
        visible: strips.compactDocked
        Column {
            width: strips.dockWidth
            height: parent.height
            spacing: 2
            GohuText {
                height: 9
                width: parent.width
                text: "FAVORITES // " + strips.favoriteItems.length
                font.pixelSize: 8
                color: Colors.magenta
            }
            Flickable {
                id: dockedFavorites
                objectName: "media-m4-docked-favorites-scroll"
                width: parent.width
                height: strips.dockTileWidth
                clip: true
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: Math.max(width,
                    strips.favoriteItems.length * (strips.dockTileWidth + strips.gap)
                    - strips.gap)
                contentHeight: height
                interactive: contentWidth > width
                Row {
                    spacing: strips.gap
                    Repeater {
                        model: strips.favoriteItems
                        delegate: Rectangle {
                            required property var modelData
                            objectName: "media-m4-docked-favorite-tile"
                            width: strips.dockTileWidth
                            height: strips.dockTileWidth
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta
                            GohuText {
                                anchors.left: parent.left
                                anchors.bottom: parent.bottom
                                anchors.margins: 1
                                width: parent.width - 2
                                text: modelData.title
                                font.pixelSize: 7
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                id: favoriteMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                enabled: strips.canRecall
                                onClicked: strips.recallRequested(modelData)
                            }
                            ToolTip.visible: favoriteMouse.containsMouse
                            ToolTip.text: modelData.title + " // SAFE RECALL // NO AUTOPLAY"
                            ActionButton {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                width: 10
                                height: 10
                                label: "X"
                                labelPixelSize: 7
                                accentColor: Colors.red
                                destructive: true
                                onClicked: strips.removeRequested(modelData)
                            }
                        }
                    }
                }
                QuietText {
                    visible: strips.favoriteItems.length===0
                    text: "NONE SAVED"
                    font.pixelSize: 8
                    color: Colors.magenta
                }
            }
        }
        Column {
            width: strips.dockWidth
            height: parent.height
            spacing: 2
            GohuText {
                height: 9
                width: parent.width
                text: "RECENTS // " + strips.recentItems.length
                font.pixelSize: 8
                color: Colors.orange
            }
            Flickable {
                id: dockedRecents
                objectName: "media-m4-docked-recents-scroll"
                width: parent.width
                height: strips.dockTileWidth
                clip: true
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: Math.max(width,
                    strips.recentItems.length * (strips.dockTileWidth + strips.gap)
                    - strips.gap)
                contentHeight: height
                interactive: contentWidth > width
                Row {
                    spacing: strips.gap
                    Repeater {
                        model: strips.recentItems
                        delegate: Rectangle {
                            required property var modelData
                            objectName: "media-m4-docked-recent-tile"
                            width: strips.dockTileWidth
                            height: strips.dockTileWidth
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.orange
                            GohuText {
                                anchors.fill: parent
                                anchors.margins: 1
                                text: modelData.title
                                font.pixelSize: 7
                                color: Colors.white
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                            MouseArea {
                                id: recentMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                enabled: strips.canRecall
                                onClicked: strips.recallRequested(modelData)
                            }
                            ToolTip.visible: recentMouse.containsMouse
                            ToolTip.text: modelData.title + " // SAFE RECALL // NO AUTOPLAY"
                        }
                    }
                }
                QuietText {
                    visible: strips.recentItems.length===0
                    text: "NONE LOADED"
                    font.pixelSize: 8
                    color: Colors.orange
                }
            }
        }
    }
}
