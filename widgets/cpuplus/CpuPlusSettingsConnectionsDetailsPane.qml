import QtQuick
import "../../components"
import qs.services.connections

// CPU++ actuator bay. All "setup" guidance is in-world, but C1 has no
// credential editor, adapter handoff, permission grant or session mutation.
Item {
    id: details
    property string selectedId: "social"
    property bool guideOpen: false
    readonly property var source: ConnectionsRegistry.entry(selectedId)
    onSelectedIdChanged: guideOpen = false

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.y + body.implicitHeight + 12)

        Column {
            id: body
            x: 5
            y: 7
            width: Math.max(0, scroll.width - 13)
            spacing: 11

            GohuText {
                width: parent.width
                text: details.source ? details.source.title : "SELECT A SERVICE"
                font.pixelSize: 12
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: details.source ? details.source.status : "UNAVAILABLE"
                font.pixelSize: 12
                color: !details.source ? Colors.orange
                       : details.source.accent === "orange" ? Colors.orange
                       : details.source.accent === "yellow" ? Colors.yellow
                       : Colors.cyan
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                text: details.source ? details.source.detail : ""
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }

            Rectangle {width:parent.width; height:1; color:Colors.cyan}
            GohuText {
                width: parent.width
                text: "AUTHORIZED USE // PLANNED"
                color: Colors.magenta
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                text: details.source ? details.source.consumers : ""
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "REQUIRED ACCESS"
                color: Colors.cyan
                font.pixelSize: 10
            }
            QuietText {
                width: parent.width
                text: details.source ? details.source.permissions : ""
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            QuietText {
                width: parent.width
                text: details.source ? details.source.context : ""
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }

            Rectangle {width:parent.width; height:1; color:Colors.cyan}
            ActionButton {
                width: Math.min(parent.width, 180)
                height: 32
                label: details.guideOpen ? "CLOSE SETUP GUIDE" : "SETUP / DETAILS"
                labelPixelSize: 10
                accentColor: Colors.orange
                available: details.source !== null
                onClicked: details.guideOpen = !details.guideOpen
            }
            QuietText {
                visible: details.guideOpen
                width: parent.width
                wrapMode: Text.WordWrap
                text: details.source ? details.source.setup : ""
                font.pixelSize: 10
                color: Colors.white
            }
            ActionButton {
                visible: details.selectedId === "social"
                width: Math.min(parent.width, 160)
                height: 30
                label: "RELOAD SOCIAL"
                labelPixelSize: 10
                accentColor: Colors.cyan
                onClicked: ConnectionsRegistry.refreshSocial()
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "C1 // STATUS ONLY. SHARED SECRET VAULT AND LIVE PERMISSION GRANTS REQUIRE SEPARATE VERIFIED IMPLEMENTATION."
                color: Colors.orange
                font.pixelSize: 9
            }
        }
    }
}
