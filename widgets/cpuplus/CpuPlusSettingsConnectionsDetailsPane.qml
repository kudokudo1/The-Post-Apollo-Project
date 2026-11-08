import QtQuick
import "../../components"
import qs.services.connections
import qs.services.social
import "../../services/connections/ConnectionsReviewPolicy.js" as ReviewPolicy
import "../../services/connections/ConnectionsRequestDisplayPolicy.js" as RequestDisplayPolicy
import "../../services/connections/ConnectionsTelegramStatusPolicy.js" as TelegramStatus

// CPU++ actuator bay. All "setup" guidance is in-world, but C1 has no
// credential editor, adapter handoff, permission grant or session mutation.
Item {
    id: details
    // Route fixed provider intent to shell-owned Social. No credential data.
    signal telegramOpenRequested()
    signal telegramRecheckRequested()
    property var telegramObservation: null
    readonly property var telegramStatus: TelegramStatus.project(telegramObservation)
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
    // The original local account-name editor owns its own input focus.
    readonly property bool editingText: details.selectedId === "social"
        && connectedAccountNamesEditor.editingText
    readonly property var keyRequirement: ConnectionsBroker.requirement(selectedId)
    readonly property var permissionPreview: ReviewPolicy.preview(keyRequirement)
    onSelectedIdChanged: {
        guideOpen = false;
        permissionReviewOpen = false;
        requestStatusOpen = false;
        reviewFeedback = "";
        // Switching services must never leave an armed local-label removal.
        connectedAccountNamesEditor.resetEditor();
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
            // TASKS M13r-UI // same right-hand details bay and native
            // controls as other Connections sources. The C2 presence
            // check is explicitly requested; no unlock or grant action.
            Column {
                visible: details.selectedId === "tasks-recovery"
                width: parent.width
                spacing: 7

                GohuText {
                    width: parent.width
                    text: "TASKS RECOVERY // SECURITY STATUS"
                    color: Colors.magenta
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: details.source ? details.source.detail : "KEYRING // NOT CHECKED"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "CREDENTIAL OWNER // SHARED CONNECTIONS BROKER"
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "DRAFT CAPTURE // DISABLED"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "UNLOCK / PREVIEW // DISABLED"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "CHECKPOINT DELETE // DISABLED"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
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
                    text: "READ ONLY // KEYRING PRESENCE DOES NOT PROVE UNLOCK OR APPROVAL"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

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
            // Telegram uses its already-running native Social provider
            // workflow. CPU++ merely requests opening that pane. This does
            // not pair, disconnect, inspect a session or start a new adapter.
            Column {
                visible: details.selectedId === "telegram"
                width: parent.width
                spacing: 7
                GohuText {
                    width: parent.width
                    text: "TELEGRAM // NATIVE SIGN-IN"
                    color: Colors.magenta
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "OPEN SOCIAL TO CHECK THE ACTUAL SESSION AND, IF NEEDED, CHOOSE QR OR PHONE SIGN-IN. NO AUTOMATIC PAIRING."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "NATIVE SESSION // " + details.telegramStatus.scope
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: details.telegramStatus.status
                    color: details.telegramStatus.authorizedAtLastCheck
                           ? Colors.green : Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: details.telegramStatus.detail
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: Math.min(parent.width, 186)
                    height: 32
                    label: "OPEN TELEGRAM"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onClicked: details.telegramOpenRequested()
                }
                ActionButton {
                    visible: details.telegramStatus.canRecheck
                    width: Math.min(parent.width, 186)
                    height: 32
                    label: "RECHECK SESSION"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    interactive: details.telegramStatus.canRecheck
                    onClicked: details.telegramRecheckRequested()
                }
            }
            // CPU++ Connected Accounts // REAL local label management.
            // Reuse the original Social writer; this never signs into a
            // provider or converts a saved nickname into verified access.
            Column {
                id: localAccountManagement
                visible: details.selectedId === "social"
                width: parent.width
                spacing: 8
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "CONNECTED ACCOUNTS // SAVED NAMES"
                    color: Colors.magenta
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "EDIT LOCAL ACCOUNT LABELS FOR THE ACTIVE SOCIAL ID. PROVIDER AUTHENTICATION IS SEPARATE."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                CpuPlusIdAccountEditor {
                    id: connectedAccountNamesEditor
                    width: parent.width
                    height: implicitHeight
                    identityId: SocialIdentityStore.snapshot
                        ? String(SocialIdentityStore.snapshot.activeId || "") : ""
                }
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
