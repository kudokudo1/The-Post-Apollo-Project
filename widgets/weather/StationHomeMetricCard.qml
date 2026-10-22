import QtQuick
import "../../components"

Rectangle {
    id: card

    property string title: ""
    property string valueText: "--"
    property string detailText: ""
    property string footerText: ""

    property color accentColor: Colors.cyan
    property color valueColor: Colors.white
    property color meterFillColor: accentColor

    property bool meterVisible: false
    property real meterValue: 0

    color: Colors.black
    border.width: 1
    border.color: Colors.cyan

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        GohuText {
            text: card.title
            font.pixelSize: 10
            color: card.accentColor
        }

        GohuText {
            text: card.valueText
            font.pixelSize: 20
            color: card.valueColor
            elide: Text.ElideRight
            width: parent.width
        }

        QuietText {
            text: card.detailText
            font.pixelSize: 10
            elide: Text.ElideRight
            width: parent.width
            visible: text.length > 0
        }

        Rectangle {
            width: parent.width
            height: 7
            visible: card.meterVisible

            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Rectangle {
                x: 2
                anchors.verticalCenter: parent.verticalCenter
                width: (parent.width - 4)
                       * Math.max(0, Math.min(1, card.meterValue))
                height: parent.height - 4
                color: card.meterFillColor
            }
        }

        QuietText {
            text: card.footerText
            font.pixelSize: 9
            elide: Text.ElideRight
            width: parent.width
            visible: text.length > 0
        }
    }
}
