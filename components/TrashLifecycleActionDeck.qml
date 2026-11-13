import QtQuick
import Quickshell

// Trash++ U1 // Reusable request-only actions for future owner integrations.
// A click emits a REVIEW request; it never writes, moves or deletes data.
// Boolean flags are presentation gates, NOT authentication or permission proof.
// The receiving source owner must reverify identity, revision, authorization,
// retention policy and user confirmation before executing any operation.
Row {
    id: lifecycleDeck

    property string ownerId: ""
    property string resourceId: ""
    property string resourceRevision: ""
    // The default remains the 64-hex source witness. Local managed-copy
    // revisions use a strict decimal store counter. Camera's independently
    // owned one-use preview issues a 32-hex plan ID. Both are request tokens,
    // NEVER independent authentication or permission to delete.
    property string resourceRevisionKind: "sha256"

    // Every new consumer starts with all actions hidden and unavailable.
    property bool showTrash: false
    property bool showRestore: false
    property bool showBurn: false
    property bool trashCapable: false
    property bool restoreCapable: false
    property bool burnCapable: false

    // These must be set only by the owning controller's reviewed integration.
    // They still do NOT confer authority to the callback recipient.
    property bool ownerApproved: false
    property bool policyReviewed: false
    property bool protectedResource: true
    property bool retentionHold: true
    property bool requestInFlight: false

    property int actionWidth: 96
    property int actionHeight: 30
    spacing: 6

    readonly property bool revisionReady:
        (resourceRevisionKind === "sha256"
         && /^[0-9a-f]{64}$/.test(resourceRevision))
        || (resourceRevisionKind === "store-counter"
            && /^(0|[1-9][0-9]{0,9})$/.test(resourceRevision))
        || (resourceRevisionKind === "camera-plan"
            && /^[0-9a-f]{32}$/.test(resourceRevision))

    readonly property bool identityReady:
        /^[A-Za-z0-9._:-]{1,96}$/.test(ownerId)
        && resourceId.length > 0 && resourceId.length <= 260
        && /^[A-Za-z0-9._:|/-]+$/.test(resourceId)
        && revisionReady

    readonly property bool canReviewTrash:
        showTrash && trashCapable && identityReady
        && ownerApproved && policyReviewed
        && !protectedResource && !retentionHold && !requestInFlight

    readonly property bool canReviewRestore:
        showRestore && restoreCapable && identityReady
        && ownerApproved && policyReviewed && !requestInFlight

    readonly property bool canReviewBurn:
        showBurn && burnCapable && identityReady
        && ownerApproved && policyReviewed
        && !protectedResource && !retentionHold && !requestInFlight

    signal trashReviewRequested(string ownerId, string resourceId, string expectedRevision)
    signal restoreReviewRequested(string ownerId, string resourceId, string expectedRevision)
    signal burnReviewRequested(string ownerId, string resourceId, string expectedRevision)

    ActionButton {
        visible: lifecycleDeck.showTrash
        width: lifecycleDeck.actionWidth
        height: lifecycleDeck.actionHeight
        label: "TRASH"
        accentColor: Colors.magenta
        acceptedButtons: Qt.LeftButton
        available: lifecycleDeck.canReviewTrash
        interactive: available
        onLeftClicked: function(mouseEvent) {
            if (lifecycleDeck.canReviewTrash)
                lifecycleDeck.trashReviewRequested(
                    lifecycleDeck.ownerId, lifecycleDeck.resourceId,
                    lifecycleDeck.resourceRevision);
        }
    }

    ActionButton {
        visible: lifecycleDeck.showRestore
        width: lifecycleDeck.actionWidth
        height: lifecycleDeck.actionHeight
        label: "RESTORE"
        accentColor: Colors.cyan
        acceptedButtons: Qt.LeftButton
        available: lifecycleDeck.canReviewRestore
        interactive: available
        onLeftClicked: function(mouseEvent) {
            if (lifecycleDeck.canReviewRestore)
                lifecycleDeck.restoreReviewRequested(
                    lifecycleDeck.ownerId, lifecycleDeck.resourceId,
                    lifecycleDeck.resourceRevision);
        }
    }

    ActionButton {
        visible: lifecycleDeck.showBurn
        width: lifecycleDeck.actionWidth
        height: lifecycleDeck.actionHeight
        label: "BURN"
        destructive: true
        accentColor: Colors.red
        acceptedButtons: Qt.LeftButton
        available: lifecycleDeck.canReviewBurn
        interactive: available
        onLeftClicked: function(mouseEvent) {
            // Deliberately emits a review request, NEVER a delete/commit.
            if (lifecycleDeck.canReviewBurn)
                lifecycleDeck.burnReviewRequested(
                    lifecycleDeck.ownerId, lifecycleDeck.resourceId,
                    lifecycleDeck.resourceRevision);
        }
    }
}
