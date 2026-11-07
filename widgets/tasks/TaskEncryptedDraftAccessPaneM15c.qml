import QtQuick
import "../../components"
import "TaskEncryptedDraftAccessPolicyM15c.js" as AccessPolicy
import "TaskDraftTargetPolicyM15d.js" as DraftTargetPolicy

// TASKS M15c // User-facing scopes & requirements, no consent/credential actor.
// This component receives ONLY existing status/boolean metadata from M13q.
// It cannot see TASKS editor text, IDs, source paths, OS key material or
// ciphertext. Three action buttons stay deliberately unavailable.
Column {
    id: access
    width: parent ? parent.width : 400
    spacing: 8

    property string providerStatus: "NOT CHECKED"
    property bool providerChecking: false
    property bool credentialActionsEnabled: false
    property bool brokerKnown: false
    property bool brokerGrantEnabled: false
    property bool recoveryEnabled: false
    property bool storageAuthorized: false
    property bool unlockAuthorized: false
    property bool draftHostEnabled: false
    property bool draftHostWriteAuthorized: false
    property string editorStatus: "EDITOR STATUS // NOT VERIFIED"
    // M15d: same bounded M13s booleans already shared with RECOVERY.
    // No editor text, task ID, key, source path or credential enters here.
    property var editorSignals: null
    property string selectedDraftTarget: "none"
    readonly property var draftSelection:
        DraftTargetPolicy.view(editorSignals, selectedDraftTarget)

    property string selectedOperation: "capture"
    property bool requirementsChecked: false

    readonly property var modes: [
        {id:"capture", label:"CAPTURE"},
        {id:"preview", label:"PREVIEW"},
        {id:"clear", label:"CLEAR"}
    ]
    readonly property var statusReport: AccessPolicy.view({
        providerStatus: providerStatus,
        providerChecking: providerChecking,
        credentialActionsEnabled: credentialActionsEnabled,
        brokerKnown: brokerKnown,
        brokerGrantEnabled: brokerGrantEnabled,
        recoveryEnabled: recoveryEnabled,
        storageAuthorized: storageAuthorized,
        unlockAuthorized: unlockAuthorized,
        draftHostEnabled: draftHostEnabled,
        draftHostWriteAuthorized: draftHostWriteAuthorized,
        editorStatus: editorStatus
    }, selectedOperation, requirementsChecked)

    // Never derive real grant authority from a broker presence probe.
    readonly property bool canCaptureDraft: false
    readonly property bool canUnlockPreview: false
    readonly property bool canDeleteCheckpoint: false
    readonly property bool canWriteTaskSource: false
    readonly property bool canClearUnsavedEditor: false

    GohuText {
        width: parent.width
        text: "ENCRYPTED DRAFT // CAPTURE + RECOVERY"
        color: Colors.magenta
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "ACCESS CONTRACT // DEFAULT OFF"
        color: Colors.orange
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "Choose an operation to inspect its requirements. "
            + "Nothing here captures editor text, unlocks a key, "
            + "opens a saved draft or changes your TASKS file."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    Row {
        id: modesRow
        width: parent.width
        height: 30
        spacing: 3
        Repeater {
            model: access.modes
            delegate: ModeButton {
                required property var modelData
                width: Math.floor((modesRow.width - modesRow.spacing
                                   * (access.modes.length - 1))
                                   / access.modes.length)
                height: modesRow.height
                textOnly: true
                labelText: modelData.label
                labelFontSize: 9
                bordered: false
                selected: access.selectedOperation === modelData.id
                onTriggered: {
                    access.selectedOperation = modelData.id;
                    access.requirementsChecked = false;
                }
            }
        }
    }

    Rectangle {
        width: parent.width
        height: detailBody.implicitHeight + 18
        color: Colors.dark
        border.width: 1
        border.color: Colors.blue
        radius: 3

        Column {
            id: detailBody
            x: 9
            y: 9
            width: parent.width - 18
            spacing: 7
            GohuText {
                width: parent.width
                text: access.statusReport.title
                color: Colors.yellow
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: access.statusReport.description
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "SCOPE // " + access.statusReport.scope
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WrapAnywhere
            }
            GohuText {
                width: parent.width
                text: access.statusReport.status
                color: Colors.orange
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: access.statusReport.explanation
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }

    // M15d: an explicit in-memory target CHOICE, not draft capture.
    // No plaintext or task identity is copied from either editor.
    Column {
        id: targetReview
        visible: access.selectedOperation === "capture"
        width: parent.width
        height: visible ? implicitHeight : 0
        spacing: 6

        GohuText {
            width: parent.width
            text: "CHOOSE UNSAVED EDITOR // NO DATA CAPTURE"
            color: Colors.magenta
            font.pixelSize: 10
            font.bold: true
            wrapMode: Text.WordWrap
        }
        Row {
            id: targetRail
            width: parent.width
            height: 30
            spacing: 3
            Repeater {
                model: [
                    {id:"none", label:"NONE"},
                    {id:"entry", label:"NEW / RENAME"},
                    {id:"details", label:"DETAILS"}
                ]
                delegate: ModeButton {
                    required property var modelData
                    width: Math.floor((targetRail.width - targetRail.spacing * 2) / 3)
                    height: targetRail.height
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 9
                    bordered: false
                    selected: access.selectedDraftTarget === modelData.id
                    interactive: modelData.id === "none"
                        || (modelData.id === "entry" && access.draftSelection.entryAvailable)
                        || (modelData.id === "details" && access.draftSelection.detailsAvailable)
                    onTriggered: {
                        access.selectedDraftTarget = modelData.id;
                        access.requirementsChecked = false;
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            text: access.draftSelection.statusLabel
            color: access.draftSelection.state === "ENTRY_SELECTED"
                   || access.draftSelection.state === "DETAILS_SELECTED"
                ? Colors.cyan : Colors.orange
            font.pixelSize: 10
            font.bold: true
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: access.draftSelection.explanation
            color: Colors.white
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: access.draftSelection.scopeLabel
            color: Colors.yellow
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }

    Row {
        width: parent.width
        height: 30
        spacing: 6
        ActionButton {
            width: Math.floor((parent.width - 6) * 0.42)
            height: 30
            label: "CHECK REQUIREMENTS"
            labelPixelSize: 9
            accentColor: Colors.cyan
            // This changes local display state only. No host action.
            onLeftClicked: access.requirementsChecked = true
        }
        ActionButton {
            width: Math.max(0, parent.width - 6 - Math.floor((parent.width - 6) * 0.42))
            height: 30
            label: access.statusReport.actionLabel
            labelPixelSize: 9
            accentColor: access.selectedOperation === "clear"
                ? Colors.red : Colors.orange
            destructive: access.selectedOperation === "clear"
            available: false
            // No onLeftClicked: real capture/preview/clear is NOT wired.
        }
    }
    GohuText {
        width: parent.width
        text: "CPU++ // SETTINGS // CONNECTIONS owns consent and key access."
        color: Colors.cyan
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "KEEP UNSAVED DRAFT // NO AUTO-REPLAY // NO SOURCE WRITE"
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
