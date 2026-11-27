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
    readonly property var guideEntries: PrismAtlas.guideEntries()
    property bool showLocations: false
    property string guideKey: ""
    property var guideHistory: []
    readonly property var selectedGuide: PrismAtlas.guideFor(guideKey)

    function openGuide(key) {
        if (!PrismAtlas.guideFor(key) || key === guideKey) return;
        guideHistory = guideHistory.concat([guideKey]);
        guideKey = key;
        showLocations = false;
        atlas.contentY = 0;
    }
    function backGuide() {
        if (!guideHistory.length) {
            guideKey = "";
        } else {
            guideKey = guideHistory[guideHistory.length - 1];
            guideHistory = guideHistory.slice(0,-1);
        }
        atlas.contentY = 0;
    }
    function openIndex(locations) {
        guideKey = "";
        guideHistory = [];
        showLocations = locations;
        atlas.contentY = 0;
    }

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

            Row {
                id: atlasNavigation
                width: parent.width
                height: 32
                spacing: 6
                ModeButton {
                    width: (atlasNavigation.width - 6) / 2
                    height: atlasNavigation.height
                    textOnly: true
                    labelText: "GUIDE"
                    selected: !help.showLocations
                    onTriggered: help.openIndex(false)
                }
                ModeButton {
                    width: (atlasNavigation.width - 6) / 2
                    height: atlasNavigation.height
                    textOnly: true
                    labelText: "LOCATIONS"
                    selected: help.showLocations
                    onTriggered: help.openIndex(true)
                }
            }

            Column {
                id: guideIndex
                width: parent.width
                visible: !help.showLocations && !help.selectedGuide
                spacing: 10
                GohuText {
                    width: parent.width
                    text: "WHAT DO YOU WANT TO UNDERSTAND?"
                    font.pixelSize: 11
                    color: help.structuralColor
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: help.guideEntries
                    delegate: Column {
                        id: guideRow
                        required property var modelData
                        width: guideIndex.width
                        spacing: 4
                        ActionButton {
                            width: parent.width
                            height: 30
                            label: guideRow.modelData.title
                            acceptedButtons: Qt.LeftButton
                            Accessible.name: "Read about " + guideRow.modelData.title
                            onLeftClicked: help.openGuide(guideRow.modelData.key)
                        }
                        GohuText {
                            width: parent.width
                            text: guideRow.modelData.purpose
                            color: help.structuralColor
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Column {
                id: guideDetail
                width: parent.width
                visible: !help.showLocations && !!help.selectedGuide
                spacing: 12

                ActionButton {
                    width: parent.width
                    height: 30
                    label: "BACK // ATLAS"
                    acceptedButtons: Qt.LeftButton
                    onLeftClicked: help.backGuide()
                }
                GohuText {
                    width: parent.width
                    text: help.selectedGuide ? help.selectedGuide.title : ""
                    color: help.structuralColor
                    font.bold: true
                    font.pixelSize: 15
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: help.selectedGuide ? help.selectedGuide.purpose : ""
                    color: Colors.cyan
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: help.structuralColor
                    PrismBorderGlow { anchors.fill: parent; divider: true }
                }
                GohuText {
                    width: parent.width
                    text: "HOW TO GET THERE"
                    color: Colors.orange
                    font.pixelSize: 11
                }
                GohuText {
                    width: parent.width
                    text: help.selectedGuide ? help.selectedGuide.path : ""
                    color: help.structuralColor
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: help.selectedGuide ? help.selectedGuide.detail : ""
                    color: help.structuralColor
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    visible: !!help.selectedGuide && help.selectedGuide.related.length > 0
                    text: "CONNECTED FEATURES"
                    color: Colors.orange
                    font.pixelSize: 11
                }
                Repeater {
                    model: help.selectedGuide ? help.selectedGuide.related : []
                    delegate: ActionButton {
                        required property string modelData
                        width: guideDetail.width
                        height: 32
                        label: PrismAtlas.guideFor(modelData).title
                        acceptedButtons: Qt.LeftButton
                        onLeftClicked: help.openGuide(modelData)
                    }
                }
            }

            // A miniature desktop: top left/center/right above the workspace,
            // bottom left/center/right below it. No live launcher or status.
            Rectangle {
                id: desktop
                visible: help.showLocations
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
                visible: help.showLocations
                text: "Select a location to read its feature guide. Atlas never opens or controls the live module."
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
                    delegate: ActionButton {
                        required property var modelData
                        width: parent.width
                        height: 23
                        label: modelData.name
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        labelFontSizeMode: Text.HorizontalFit
                        contentPadding: 2
                        acceptedButtons: Qt.LeftButton
                        Accessible.name: "Read about " + modelData.name
                        onLeftClicked: help.openGuide(modelData.mount)
                    }
                }
            }
        }
    }
}
