import QtQuick
import "../../components"
import qs.services.connections
import "../../services/connections/ConnectionsReviewPolicy.js" as ReviewPolicy
import "../../services/connections/ConnectionsRequestDisplayPolicy.js" as RequestDisplayPolicy

// CPU++ actuator bay. All "setup" guidance is in-world, but C1 has no
// credential editor, adapter handoff, permission grant or session mutation.
Item {
    id: details
    property string selectedId: "social"
    property bool guideOpen: false
    property bool permissionReviewOpen: false
    property string reviewFeedback: ""
    property bool requestStatusOpen: false
    // Synthetic preview is test-injected only and always labeled SIMULATED.
    // It cannot set hostConnected, a permission or a credential.
    property var syntheticStatusPreview: null
    readonly property var requestStatusView:
        syntheticStatusPreview !== null
        ? RequestDisplayPolicy.project(syntheticStatusPreview, selectedId)
        : ConnectionsRequestStatus.display(selectedId)
    readonly property var source: ConnectionsRegistry.entry(selectedId)
    readonly property var keyRequirement: ConnectionsBroker.requirement(selectedId)
    readonly property var permissionPreview: ReviewPolicy.preview(keyRequirement)
    onSelectedIdChanged: {
        guideOpen = false;
        permissionReviewOpen = false;
        requestStatusOpen = false;
        reviewFeedback = "";
    }

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
            Column {
                visible: details.keyRequirement.known
                width: parent.width
                spacing: 7

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "CREDENTIAL BROKER // OS STATUS"
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: ConnectionsBroker.label
                    color: ConnectionsBroker.available
                           ? Colors.yellow : Colors.orange
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                }
                ActionButton {
                    width: Math.min(parent.width, 170)
                    height: 30
                    label: ConnectionsBroker.checking
                           ? "CHECKING..." : "CHECK KEYRING"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: !ConnectionsBroker.checking
                    onClicked: ConnectionsBroker.checkAvailability()
                }
                QuietText {
                    width: parent.width
                    text: "SCOPES // "
                          + details.keyRequirement.operations.join(" // ")
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "CONSUMERS // "
                          + details.keyRequirement.consumers.join(" // ")
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "GRANTS CLOSED // PRESENCE DOES NOT PROVE UNLOCK, OWNERSHIP, OR PROVIDER AUTHENTICATION"
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                }
            }

            Column {
                visible: details.permissionPreview.known
                width: parent.width
                spacing: 7

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "ACCESS REVIEW // IN-WORLD"
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    visible: !details.permissionReviewOpen
                    width: Math.min(parent.width, 180)
                    height: 30
                    label: "REVIEW ACCESS"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onClicked: {
                        details.reviewFeedback = "";
                        details.permissionReviewOpen = true;
                    }
                }
                Column {
                    visible: details.permissionReviewOpen
                    width: parent.width
                    spacing: 7
                    GohuText {
                        width: parent.width
                        text: "REVIEW ONLY // NOT A PERMISSION PROMPT"
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: Math.min(parent.width, 160)
                        height: 30
                        label: "DISMISS REVIEW"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        onClicked: {
                            details.permissionReviewOpen = false;
                            details.reviewFeedback = "REVIEW CLOSED // NO ACCESS GRANTED";
                        }
                    }
                    QuietText {
                        width: parent.width
                        text: "PROVIDER // " + details.permissionPreview.provider
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "REQUESTING COMPONENTS // "
                              + details.permissionPreview.consumers.join(" / ")
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "OPERATIONS // "
                              + details.permissionPreview.operations.join(" / ")
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: details.permissionPreview.authentication
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: details.permissionPreview.status
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: Math.min(parent.width, 180)
                        height: 30
                        label: "APPROVE // UNAVAILABLE"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        available: false
                    }

                }
                QuietText {
                    visible: details.reviewFeedback !== ""
                    width: parent.width
                    text: details.reviewFeedback
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: details.permissionPreview.known
                width: parent.width
                spacing: 7
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "HOST REQUEST // STATUS"
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: Math.min(parent.width, 185)
                    height: 30
                    label: details.requestStatusOpen
                           ? "CLOSE REQUEST STATUS" : "VIEW REQUEST STATUS"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onClicked: details.requestStatusOpen = !details.requestStatusOpen
                }
                Column {
                    visible: details.requestStatusOpen
                    width: parent.width
                    spacing: 7
                    GohuText {
                        width: parent.width
                        text: details.requestStatusView.title
                        font.pixelSize: 10
                        color: Colors.orange
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: details.requestStatusView.explanation
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: details.requestStatusView.state === "OFFLINE"
                              ? "NO HOST-VERIFIED REQUESTS ON THIS DESKTOP"
                              : "REQUEST STATE // " + details.requestStatusView.state
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "READ-ONLY STATUS // NO APPROVAL OR REAL GRANT"
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                    }
                    GohuText {
                        width: parent.width
                        text: "LOCAL HOST // UNVERIFIED"
                        color: Colors.magenta
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: Math.min(parent.width, 185)
                        height: 30
                        label: ConnectionsHostObservation.checking
                               ? "CHECKING LOCAL HOST..."
                               : "INSPECT LOCAL HOST"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: !ConnectionsHostObservation.checking
                        onClicked: ConnectionsHostObservation.inspect()
                    }
                    QuietText {
                        width: parent.width
                        text: ConnectionsHostObservation.observation.label
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        visible: ConnectionsHostObservation.observation.state !== ""
                        width: parent.width
                        text: ConnectionsHostObservation.observation.stateLabel
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "LOCAL SOCKET OBSERVATION IS NOT HOST AUTHENTICATION. NO KEYS OR PERMISSIONS SHARED."
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
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
                text: "C2e // ACCESS REVIEW ONLY. HOST APPROVAL, SECRET STORAGE, ACCOUNT LOGIN AND CROSS-APP GRANTS REMAIN DISABLED. C2g // REQUEST STATUS READ-ONLY; NO VERIFIED HOST FEED."
                color: Colors.orange
                font.pixelSize: 9
            }
        }
    }
}
