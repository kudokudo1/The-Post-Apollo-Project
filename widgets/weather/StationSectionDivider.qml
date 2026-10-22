import QtQuick
import "../../components"

Item {
    id: divider

    property string title: ""
    property color labelColor: Colors.orange
    property color lineColor: Colors.cyan

    implicitHeight: 14

    GohuText {
        id: dividerLabel

        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter

        text: divider.title
        font.pixelSize: 11
        color: divider.labelColor
    }

    Rectangle {
        anchors.left: dividerLabel.right
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 10

        height: 2
        color: divider.lineColor
    }
}
