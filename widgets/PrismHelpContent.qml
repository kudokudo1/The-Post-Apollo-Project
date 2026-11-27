import QtQuick
import "../components"
import "../services/prism/PrismAtlas.js" as PrismAtlas

// Shared help body. A future compact Prism or App Control help host may use
// this same component and catalog, without importing a second PanelWindow.
Item {
    id: help
    property string page: "syntagma"
    property color structuralColor: Colors.white
    readonly property var atlasZones: PrismAtlas.mapZones()

    Column {
        visible: help.page === "syntagma"
        anchors.centerIn: parent
        width: Math.max(0, parent.width - 28)
        spacing: 12
        GohuText {
            width: parent.width
            text: "SYNTAGMA // VISUAL LANGUAGE"
            font.pixelSize: 13
            color: help.structuralColor
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "NO DEFINITIONS YET"
            font.pixelSize: 12
            color: Colors.orange
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "POST APOLLO // CONTEXTUAL HELP"
            font.pixelSize: 11
            color: help.structuralColor
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    Flickable {
        id: atlas
        objectName: "prismAtlas"
        anchors.fill: parent
        anchors.margins: 14
        visible: help.page === "atlas"
        clip: true
        contentWidth: width
        contentHeight: atlasColumn.implicitHeight
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: atlasColumn
            width: atlas.width
            spacing: 10

            GohuText {
                width: parent.width
                text: "ATLAS // POST APOLLO"
                font.pixelSize: 15
                font.bold: true
                color: help.structuralColor
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: "WIDGET LOCATIONS // SCHEMATIC"
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            // A miniature desktop: top left/center/right above the workspace,
            // bottom left/center/right below it. No live launcher or status.
            Rectangle {
                id: desktop
                width: parent.width
                height: mapLayout.implicitHeight + 20
                color: Colors.black
                border.width: 1
                border.color: help.structuralColor
                PrismBorderGlow { anchors.fill: parent }

                Column {
                    id: mapLayout
                    x: 10
                    y: 10
                    width: Math.max(0, desktop.width - 20)
                    spacing: 8

                    Row {
                        id: topZones
                        width: mapLayout.width
                        spacing: 5
                        Repeater {
                            model: help.atlasZones.slice(0, 3)
                            delegate: zoneTile
                        }
                    }
                    Item {
                        width: parent.width
                        height: 62
                        GohuText {
                            anchors.centerIn: parent
                            text: "WORKSPACE"
                            color: Colors.cyan
                            opacity: 0.65
                            font.pixelSize: 11
                        }
                    }
                    Row {
                        id: bottomZones
                        width: mapLayout.width
                        spacing: 5
                        Repeater {
                            model: help.atlasZones.slice(3, 6)
                            delegate: zoneTile
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "Shell entry points in dock order. This is a location guide, not a live status display or a launcher."
                color: help.structuralColor
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }

    Component {
        id: zoneTile
        Rectangle {
            id: tile
            required property var modelData
            width: Math.max(0, (mapLayout.width - 10) / 3)
            height: (modelData.id.indexOf("top-") === 0 ? 10 : 2) * 26 + 38
            color: Colors.dark
            border.width: 1
            border.color: help.structuralColor
            PrismBorderGlow { anchors.fill: parent; strength: 0.65 }

            Column {
                x: 5
                y: 6
                width: Math.max(0, tile.width - 10)
                spacing: 3
                GohuText {
                    width: parent.width
                    height: 23
                    text: tile.modelData.label
                    color: help.structuralColor
                    font.pixelSize: 10
                    font.bold: true
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                }
                Repeater {
                    model: tile.modelData.entries
                    delegate: GohuText {
                        required property var modelData
                        width: parent.width
                        height: 23
                        text: modelData.name
                        color: Colors.cyan
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
