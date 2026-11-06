import QtQuick
import "../../components"
import "StationCosmosLightDetailPolicy.js" as Light

// Complete fixed-viewport solar/light guide based on the existing twilight
// calibration. Four mode pages replace a partly omitted eight-card grid.
Rectangle {
    id: lightPane
    objectName: "cosmos-c6-light-detail"
    color: Colors.black
    clip: true
    property var twilight: null
    property var astronomy: null
    property string sourceStatus: ""
    property string selectedMode: "DAWN"
    readonly property var metrics: Light.rows(
        selectedMode,twilight,astronomy)
    readonly property int renderedFieldCount: fieldRepeater.count

    GohuText {
        id: titleText
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 20
        text: "SUN // TWILIGHT & PHOTO LIGHT WINDOWS"
        color: Colors.magenta
        font.pixelSize: 11
        elide: Text.ElideRight
    }
    Row {
        id: lightModes
        anchors.top: titleText.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        height: 25
        spacing: 4
        Repeater {
            model: Light.MODES
            delegate: ActionButton {
                required property var modelData
                width: Math.max(1,(lightModes.width-12)/4)
                height: 25
                contentPadding: 1
                label: modelData
                labelPixelSize: 9
                selected: lightPane.selectedMode === modelData
                accentColor: Colors.orange
                onClicked: lightPane.selectedMode=modelData
            }
        }
    }
    Grid {
        id: lightGrid
        anchors.top: lightModes.bottom
        anchors.topMargin: 6
        anchors.bottom: noteText.top
        anchors.bottomMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        columns: 2
        spacing: 6
        Repeater {
            id: fieldRepeater
            model: 4
            delegate: Rectangle {
                objectName: "cosmos-c6-light-field"
                required property int index
                readonly property var itemData: lightPane.metrics[index]
                width: Math.max(1,(lightGrid.width-6)/2)
                height: Math.max(1,(lightGrid.height-6)/2)
                color: Colors.dark
                border.width: 1
                border.color: Colors.orange
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7
                    SecondaryText {
                        width: parent.width
                        text: itemData ? itemData.name : "--"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: itemData ? itemData.value : "--"
                        font.pixelSize: 15
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
    QuietText {
        id: noteText
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 20
        color: twilight && twilight.available ? Colors.cyan : Colors.orange
        font.pixelSize: 9
        elide: Text.ElideRight
        text: twilight && twilight.available
            ? "CALIBRATED SOLAR WINDOWS // STATION PHOTO-LIGHT CONVENTION"
            : (sourceStatus || "SUNRISE CALIBRATION UNAVAILABLE")
    }
}
