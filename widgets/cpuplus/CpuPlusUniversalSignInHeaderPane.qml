import QtQuick
import "../../components"
import qs.services.connections
import "../../services/connections/ConnectionsUnifiedSignInPolicy.js" as SignInPolicy
import "../../services/connections/ConnectionsIdentityJourneyPolicy.js" as JourneyPolicy
import "../../services/connections/ConnectionsSignInFlowContract.js" as FlowContract
import "../messanger"

// CPU++ Connections' reserved UPPER-LEFT identity slot: physically above
// SHARED // STATUS and its divider. Existing Thermal/System owner identity
// remains independent. No new auth controller, write access or provider grant.
Item {
    id: upperSignIn
    signal idManagementRequested()
    property bool panelActive: false
    property bool statusExpanded: false
    property bool flowExpanded: false
    // V3 has no trusted command/status adapter. Offline projection only.
    readonly property var signInFlow: FlowContract.offline()

    // Hide or switch away from CPU++ -> Connections: revoke this view.
    // Existing Identity Center reader also cancels stale in-flight display.
    onPanelActiveChanged: {
        if (!panelActive) {
            statusExpanded = false;
            flowExpanded = false;
        }
    }

    onStatusExpandedChanged: {
        if (!statusExpanded)
            flowExpanded = false;
    }

    IdentityCenterOrganizationDisplayReader {
        id: contextReader
        active: upperSignIn.panelActive && upperSignIn.statusExpanded
    }
    readonly property var journey:
        JourneyPolicy.project(contextReader.snapshot,
                              panelActive && statusExpanded)

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
        // This is the EXISTING token-free private context display reader.
        // Its response cannot verify an installed host, initiate OIDC or
        // turn a display of membership data into authentication authority.
        ActionButton {
            width: Math.min(parent.width, 188)
            height: 30
            label: upperSignIn.statusExpanded
                   ? "HIDE SIGN-IN STATUS" : "VIEW SIGN-IN STATUS"
            labelPixelSize: 9
            accentColor: Colors.magenta
            selected: upperSignIn.statusExpanded
            interactive: upperSignIn.panelActive
            onClicked: upperSignIn.statusExpanded = !upperSignIn.statusExpanded
        }
        Flickable {
            id: journeyViewport
            width: parent.width
            visible: upperSignIn.statusExpanded
            height: visible ? Math.min(journeyBody.implicitHeight + 4, 184) : 0
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: journeyBody.implicitHeight + 8

            Column {
                id: journeyBody
                width: journeyViewport.width
                spacing: 6

                GohuText {
                    width: parent.width
                    text: "IDENTITY CENTER // READ-ONLY DISPLAY"
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: upperSignIn.journey.displayStatus
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: upperSignIn.journey.displayGuidance
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: upperSignIn.journey.hostStep
                          + "\n" + upperSignIn.journey.signInStep
                          + "\n" + upperSignIn.journey.identityStep
                          + "\n" + upperSignIn.journey.providerStep
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: upperSignIn.signInFlow.label
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: upperSignIn.signInFlow.requestLabel
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: Math.min(parent.width, 188)
                    height: 30
                    label: upperSignIn.flowExpanded
                           ? "HIDE REQUEST FLOW" : "VIEW REQUEST FLOW"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    selected: upperSignIn.flowExpanded
                    interactive: upperSignIn.panelActive
                    onClicked: upperSignIn.flowExpanded = !upperSignIn.flowExpanded
                }
                Column {
                    width: parent.width
                    visible: upperSignIn.flowExpanded
                    spacing: 5
                    Repeater {
                        model: upperSignIn.signInFlow.stages
                        delegate: QuietText {
                            required property var modelData
                            width: journeyBody.width
                            text: modelData
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                    }
                    QuietText {
                        width: parent.width
                        text: upperSignIn.signInFlow.explanation
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
                ActionButton {
                    width: Math.min(parent.width, 188)
                    height: 30
                    label: upperSignIn.journey.signInButtonLabel
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    available: upperSignIn.journey.canBeginSignIn
                    // No onClicked: the protected host has NO approved
                    // sign-in command/capability contract.
                }
                Row {
                    width: parent.width
                    spacing: 8
                    ActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 30
                        label: "CANCEL // UNAVAILABLE"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        available: upperSignIn.signInFlow.canCancel
                        // No onClicked: host-originated request receipt absent.
                    }
                    ActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 30
                        label: "RETRY // UNAVAILABLE"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        available: upperSignIn.signInFlow.canRetry
                        // No onClicked: host must issue a new request ID.
                    }
                }
                ActionButton {
                    width: Math.min(parent.width, 188)
                    height: 30
                    label: "REFRESH CONTEXT VIEW"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    interactive: upperSignIn.panelActive
                    onClicked: contextReader.refresh()
                }
                QuietText {
                    width: parent.width
                    text: "NO LOGIN, AUTHORIZATION OR PROVIDER ACCESS FROM THIS VIEW."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
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
