import QtQuick
import "../../components"

Rectangle {
    id: card

    property string title: ""
    property string valueText: "--"
    property string detailText: ""
    property string footerText: ""
    // W3 // All existing readings; compact presentation is HISTORY-only.
    property bool compact: false
    // Only canonical HOME SERVICES uses this fit-safe two-row instrument.
    property bool servicesCompact: false

    property color accentColor: Colors.cyan
    property color valueColor: Colors.white
    property color meterFillColor: accentColor

    property bool meterVisible: false
    property real meterValue: 0

    // W2b optional per-card inspector and explicit pin control. Disabled
    // by default for all existing HOME snapshots/health/quick cards.
    property string provenanceText: ""
    property bool pinEnabled: false
    property bool pinned: false
    property bool pinAvailable: false
    signal pinRequested()

    color: Colors.black
    clip: true
    border.width: 1
    border.color: Colors.cyan

    Column {
        visible: !card.servicesCompact
        anchors.fill: parent
        anchors.margins: card.compact ? 4 : 10
        spacing: card.compact ? 1 : 5

        GohuText {
            text: card.title
            font.pixelSize: card.compact ? 9 : 10
            color: card.accentColor
            width: parent.width - (card.pinEnabled ? 32 : 0)
            elide: Text.ElideRight
        }

        GohuText {
            text: card.valueText
            font.pixelSize: card.compact ? 15 : 20
            color: card.valueColor
            elide: Text.ElideRight
            width: parent.width
        }

        QuietText {
            text: card.detailText
            font.pixelSize: card.compact ? 8 : 10
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
            font.pixelSize: card.compact ? 8 : 9
            elide: Text.ElideRight
            width: parent.width
            visible: text.length > 0
        }

        QuietText {
            text: card.provenanceText
            font.pixelSize: 8
            elide: Text.ElideRight
            width: parent.width
            visible: text.length > 0
        }
    }

    // At 48px, four vertically stacked Gohu/Quiet text items can extend
    // outside the painted card. Keep the service label and status side by
    // side, with the detail and LAST SUCCESS on dedicated bounded rows.
    Column {
        id: servicesCompactText
        objectName: "home-services-compact-text"
        visible: card.servicesCompact
        anchors.fill: parent
        anchors.margins: 3
        spacing: 1
        Row {
            width: parent.width
            height: 15
            spacing: 3
            GohuText {
                width: Math.max(1,parent.width * 0.54)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: card.title
                font.pixelSize: 9
                color: card.accentColor
                elide: Text.ElideRight
            }
            GohuText {
                width: Math.max(1,parent.width * 0.44)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                text: card.valueText
                font.pixelSize: 10
                color: card.valueColor
                elide: Text.ElideRight
            }
        }
        QuietText {
            width: parent.width
            height: 11
            verticalAlignment: Text.AlignVCenter
            text: card.detailText
            font.pixelSize: 8
            elide: Text.ElideRight
        }
        QuietText {
            objectName: "home-services-last-success-footer"
            width: parent.width
            height: 11
            verticalAlignment: Text.AlignVCenter
            text: card.footerText
            font.pixelSize: 8
            color: Colors.cyan
            elide: Text.ElideRight
        }
    }

    ActionButton {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 5
        width: 26
        height: 23
        visible: card.pinEnabled
        available: card.pinAvailable
        selected: card.pinned
        accentColor: Colors.yellow
        label: card.pinned ? "★" : "☆"
        labelPixelSize: 13
        onClicked: card.pinRequested()
    }
}
