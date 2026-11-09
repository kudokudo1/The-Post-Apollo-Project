import QtQuick
import "../../components"
import qs.services.connections
import "../../services/connections/ConnectionsUnifiedSignInPolicy.js" as SignInPolicy

// CPU++ Connections' reserved UPPER-LEFT identity slot: physically above
// SHARED // STATUS and its divider. Existing Thermal/System owner identity
// remains independent. No new auth controller, write access or provider grant.
Item {
    id: upperSignIn
    signal idManagementRequested()

    // No approved desktop Identity Center sign-in channel yet. Keep this
    // explicitly unknown rather than promoting Social labels or test OIDC.
    readonly property var signIn: SignInPolicy.project({
        identityHostConnected: false,
        identityAuthenticated: false,
        credentialHostAuthenticated: ConnectionsRequestStatus.hostAuthenticated,
        credentialActionsEnabled: ConnectionsBroker.credentialActionsEnabled,
        operatorConsentAuthenticated: ConnectionsRequestStatus.canApprove,
        localObservationSeen: ConnectionsHostObservation.observing
    })

    implicitHeight: controlContent.implicitHeight + 20

    Column {
        id: controlContent
        x: 16
        y: 9
        width: Math.max(0, upperSignIn.width - 32)
        spacing: 6

        GohuText {
            width: parent.width
            text: "UNIVERSAL SIGN-IN // CONTROL"
            color: Colors.magenta
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: upperSignIn.signIn.identityStatus
            color: upperSignIn.signIn.identityVerified ? Colors.green : Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: upperSignIn.signIn.identityNote
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            spacing: 8

            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 30
                label: "OPEN ID MANAGEMENT"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onClicked: upperSignIn.idManagementRequested()
            }
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 30
                label: ConnectionsHostObservation.checking
                       ? "CHECKING HOST..." : "INSPECT LOCAL HOST"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: !ConnectionsHostObservation.checking
                onClicked: ConnectionsHostObservation.inspect()
            }
        }
        GohuText {
            width: parent.width
            text: upperSignIn.signIn.connectionStatus
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: upperSignIn.signIn.providerStatus
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: upperSignIn.signIn.batchStatus
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
