import QtQuick
import "../../components"

Rectangle {
    id: home

    property var weatherService: null
    property var spaceService: null

    color: Colors.black

    Column {
        anchors.centerIn: parent
        spacing: 12

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "⌂  HOME"
            font.pixelSize: 28
            color: Colors.magenta
        }

        SecondaryText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "FAVORITES // RELEVANT // AUTO"
            font.pixelSize: 14
        }

        QuietText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "modular home layout next"
            font.pixelSize: 11
        }
    }
}
