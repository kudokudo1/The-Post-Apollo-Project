import QtQuick
import "../../components"
import "PhonePersonalDraftState.js" as DraftState

// P42 isolated PHONE Personal editor shell. NOT connected to live PhonePane.
// A future trusted native host may wire this only after independent C5
// consent + installed-host trust. Draft state is memory-only and discarded
// on selection / visibility changes. It cannot save, even in preview mode.
Rectangle {
    id: editor

    property var contact: null
    property bool previewEnabled: false
    readonly property bool secureSaveAuthorized: false
    readonly property bool canStage: previewEnabled && contact !== null
    property var pending: DraftState.empty()
    property bool resettingDraft: false

    signal cancelRequested()

    function currentContactId() {
        return contact && typeof contact.id === "string" ? contact.id : "";
    }

    function discardDraft() {
        resettingDraft = true;
        pending = DraftState.empty();
        noteDraft.text = "";
        resettingDraft = false;
    }

    function resetForSelection() {
        discardDraft();
        if (canStage)
            pending = DraftState.start(currentContactId());
    }

    onContactChanged: resetForSelection()
    onPreviewEnabledChanged: resetForSelection()
    Component.onDestruction: discardDraft()

    visible: canStage
    enabled: visible
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true
    implicitHeight: 350
    implicitWidth: 320

    Column {
        id: editorContent
        anchors.fill: parent
        anchors.margins: 12
        spacing: 9

        Text {
            width: parent.width
            text: "PERSONAL // EDIT REVIEW (LOCAL DRAFT)"
            color: Colors.orange
            font.bold: true
            font.pixelSize: 12
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            text: "PREVIEW ONLY // NOTHING IS SAVED OR SENT TO IPHONE"
            color: Colors.magenta
            font.bold: true
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }

        Row {
            id: draftFavoriteActions
            width: parent.width
            spacing: 7

            ActionButton {
                width: Math.max(0, (draftFavoriteActions.width - 7) / 2)
                height: 32
                label: "☆ FAVORITE ON"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: editor.canStage
                interactive: editor.canStage
                selected: editor.pending.favorite === true
                onTriggered: {
                    editor.pending = DraftState.withFavorite(
                        editor.pending, editor.currentContactId(), true);
                }
            }

            ActionButton {
                width: Math.max(0, (draftFavoriteActions.width - 7) / 2)
                height: 32
                label: "FAVORITE OFF"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: editor.canStage
                interactive: editor.canStage
                selected: editor.pending.favorite === false
                onTriggered: {
                    editor.pending = DraftState.withFavorite(
                        editor.pending, editor.currentContactId(), false);
                }
            }
        }

        Text {
            width: parent.width
            text: "NOTE // PRIVATE DRAFT (MAX 4096 CHARACTERS)"
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
        }

        Rectangle {
            width: parent.width
            height: 98
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta
            clip: true

            TextEdit {
                id: noteDraft
                anchors.fill: parent
                anchors.margins: 7
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.pixelSize: 12
                textFormat: TextEdit.PlainText
                wrapMode: TextEdit.Wrap
                readOnly: !editor.canStage
                selectByMouse: true
                clip: true
                cursorDelegate: Rectangle {
                    width: 2
                    color: Colors.orange
                }
                onTextChanged: {
                    if (editor.resettingDraft || !editor.canStage)
                        return;
                    // Bound the preview buffer. No contact data is loaded
                    // from a vault and this text never leaves this component.
                    if (text.length > 4096) {
                        text = text.substring(0, 4096);
                        return;
                    }
                    editor.pending = DraftState.withNote(
                        editor.pending, editor.currentContactId(), text);
                }
            }
        }

        Text {
            width: parent.width
            text: DraftState.summary(editor.pending, editor.currentContactId())
            color: Colors.orange
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }

        Row {
            id: draftReviewActions
            width: parent.width
            spacing: 7

            ActionButton {
                width: Math.max(0, (draftReviewActions.width - 14) / 3)
                height: 31
                label: "SAVE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: editor.secureSaveAuthorized
                interactive: false // No native, verified one-use save host.
            }
            ActionButton {
                width: Math.max(0, (draftReviewActions.width - 14) / 3)
                height: 31
                label: "CLEAR DRAFT"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: true
                interactive: editor.canStage
                onTriggered: editor.discardDraft()
            }
            ActionButton {
                width: Math.max(0, (draftReviewActions.width - 14) / 3)
                height: 31
                label: "CANCEL"
                labelPixelSize: 10
                accentColor: Colors.orange
                interactive: editor.canStage
                onTriggered: {
                    editor.discardDraft();
                    editor.cancelRequested();
                }
            }
        }

        Text {
            width: parent.width
            text: "SAVE REQUIRES VERIFIED PHONE HOST + C5 HUMAN CONSENT"
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
