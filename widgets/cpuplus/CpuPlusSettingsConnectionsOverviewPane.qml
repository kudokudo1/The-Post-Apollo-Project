import QtQuick
import "../../components"
import qs.services.connections

// CPU++ left instrument bay. All signals are read from canonical owners;
// no account/profile switching, secrets, or disk writes originate here.
Item {
    id: overview
    property string feedback: ""
    readonly property var social: ConnectionsRegistry.entry("social")
    readonly property var firms: ConnectionsRegistry.entry("nasa-firms")
    readonly property var summary: ConnectionsRegistry.summary

    Flickable {
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.y + body.implicitHeight + 14)

        Column {
            id: body
            x: 6
            y: 8
            width: Math.max(0, parent.width - 18)
            spacing: 10

            GohuText {
                width: parent.width
                text: "CONNECTIONS // SHARED CONTROL"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "ONE SERVICE OWNER // MANY AUTHORIZED CONSUMERS"
                font.pixelSize: 10
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.72
            }

            GohuText {
                width: parent.width
                text: "SOCIAL // REUSED IDENTITY"
                color: Colors.cyan
                font.pixelSize: 11
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: overview.social ? overview.social.detail : "SOCIAL DATA UNAVAILABLE"
            }
            GohuText {
                width: parent.width
                text: overview.social ? overview.social.context : "NO ACCOUNT LABEL DATA"
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "SOCIAL ACCOUNT NAMES ARE ORGANIZATION METADATA, NOT AUTHENTICATED LOGINS."
                color: Colors.orange
                font.pixelSize: 9
            }
            ActionButton {
                width: Math.min(parent.width, 186)
                height: 30
                label: "RELOAD SOCIAL STATUS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                onClicked: {
                    overview.feedback = ConnectionsRegistry.refreshSocial()
                        ? "RELOAD REQUESTED // CHECK SOCIAL STATUS"
                        : "RELOAD NOT AVAILABLE // BUSY OR STORAGE ERROR";
                }
            }
            QuietText {
                visible: overview.feedback !== ""
                width: parent.width
                text: overview.feedback
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.yellow
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.65
            }
            GohuText {
                width: parent.width
                text: "CONNECTION INVENTORY"
                color: Colors.cyan
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                text: "PUBLIC SOURCES // " + overview.summary.publicSources
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "KEYS NEEDED // " + overview.summary.keyRequired
                font.pixelSize: 10
                color: overview.summary.keyRequired > 0 ? Colors.orange : Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "MAIL ADAPTERS PENDING // " + overview.summary.unverifiedAccounts
                font.pixelSize: 10
                color: overview.summary.unverifiedAccounts > 0
                       ? Colors.orange : Colors.cyan
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "STATUS INDICATES WHAT CAN BE PROVEN TODAY. KEY PRESENT DOES NOT MEAN PROVIDER AUTHENTICATED."
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }
}
