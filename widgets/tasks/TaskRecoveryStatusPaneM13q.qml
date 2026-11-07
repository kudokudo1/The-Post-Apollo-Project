import QtQuick
import qs.services.connections
import qs.services.hub
import "../../components"
import "TaskRecoveryStatusPolicyM13q.js" as RecoveryStatusPolicy
import "TaskDraftPresencePolicyM13s.js" as DraftPresencePolicy

// TASKS M13q // real SHARED C2 keyring presence, read-only recovery readiness.
// No draft data, user key, file, opt-in/grant, Secret Service caller or TASKS
// mutation API is imported. CHECK KEYRING is the existing explicit C2a
// presence-only probe; opening this pane never performs any OS operation.
Item {
    id: recoveryStatus

    // Never contains task text, identifiers, keys or a credential receipt.
    property var editorSignals: null
    readonly property var draftReport: DraftPresencePolicy.view(editorSignals)

    readonly property var report: RecoveryStatusPolicy.view({
        providerStatus: ConnectionsBroker.status,
        providerChecking: ConnectionsBroker.checking,
        brokerCredentialActionsEnabled: ConnectionsBroker.credentialActionsEnabled,
        recoveryEnabled: ApolloHubTodoStore.encryptedRecoveryEnabled,
        recoveryStorageAuthorized: ApolloHubTodoStore.encryptedRecoveryStorageAuthorized,
        recoveryUnlockAuthorized: ApolloHubTodoStore.encryptedRecoveryUnlockAuthorized,
        draftHostEnabled: ApolloHubTodoStore.encryptedDraftHostEnabled,
        draftHostWriteAuthorized: ApolloHubTodoStore.encryptedDraftHostWriteAuthorized
    })

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.y + body.implicitHeight + 12)

        Column {
            id: body
            x: 3
            y: 4
            width: Math.max(0, scroll.width - 10)
            spacing: 10

            GohuText {
                width: parent.width
                text: "DRAFT RECOVERY // STATUS"
                font.pixelSize: 12
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.recoveryStatus
                font.pixelSize: 11
                font.bold: true
                color: Colors.orange
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.providerLabel
                font.pixelSize: 10
                color: recoveryStatus.report.providerPresent
                    ? Colors.cyan : Colors.white
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.explanation
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.WordWrap
            }

            ActionButton {
                width: Math.min(parent.width, 210)
                height: 32
                label: ConnectionsBroker.checking
                       ? "CHECKING KEYRING..." : "CHECK KEYRING STATUS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: !ConnectionsBroker.checking
                // Read-only C2a NameHasOwner probe, explicitly initiated.
                // It does not open the keyring, inspect records or grant keys.
                onLeftClicked: ConnectionsBroker.checkAvailability()
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            GohuText {
                width: parent.width
                text: "LOCAL EDITORS // UNSAVED CONTENT STATUS"
                color: Colors.magenta
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.draftReport.status
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.draftReport.sourceStatus
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.draftReport.explanation
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.draftReport.scope
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.draftReport.otherScope
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            // M15a // Real, point-in-time structural source check invoked
            // ONLY by an operator click; no new FileView or writer.
            TaskLocalSourceInspectPaneM15a {
                width: parent.width
                sourcePath: ApolloHubTodoStore.storagePath
                saveRequestCount: ApolloHubTodoStore.nativeSaveRequestsM14a
                saveInProgress: ApolloHubTodoStore.storageState === "saving"
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            // M13z // Operator-visible, EXAMPLE-ONLY crash-state review.
            // The real M13y inspector is not connected to live TASKS.
            // Reuse M13s above for genuine in-memory unsaved editor status.
            TaskRecoveryReviewPaneM13z {
                width: parent.width
                // M14a // Live, bounded callback state from the already-owned
                // singleton, never raw draft/task/source bytes.
                nativeSaveSignals: ApolloHubTodoStore.nativeSaveObservationM14a
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            GohuText {
                width: parent.width
                text: "RECOVERY PERMISSIONS // NOT ACTIVE"
                color: Colors.magenta
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.captureStatus
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.previewStatus
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.clearStatus
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.hostStatus
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.checkpointStatus
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.sourceStatus
                color: Colors.magenta
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: recoveryStatus.report.nextStep
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: "READ ONLY // NO CAPTURE // NO KEY RELEASE // NO RESTORE"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
}
