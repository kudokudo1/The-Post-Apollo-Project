import QtQuick
import "../../components"

// B8 quick-notes presentation. The injected singleton owns ALL durable
// storage and revision checks. No autosave, polling, hidden writes or AI.
// Editor text is a local draft until onSaved publishes a confirmed snapshot.
Item {
    id: notesMini

    property var notesStore: null
    property var notesSnapshot: null
    property bool editorOpen: false
    property string openedId: ""
    property int openedRevision: 0
    property string openedTitle: ""
    property string openedBody: ""
    property string pendingAction: ""
    property string feedback: ""
    property bool deleteArmed: false
    property bool discardArmed: false

    signal textFocusChanged(bool focused)

    // Same revision-safe Notes editor. Taller chassis only changes sizing.
    readonly property int densityLevel: height >= 300 ? 3
                                        : height >= 180 ? 2 : 1

    readonly property string storeState:
        notesSnapshot && notesSnapshot.state
        ? String(notesSnapshot.state) : "loading"
    readonly property bool writable:
        notesStore !== null && notesSnapshot !== null
        && notesSnapshot.writable === true
        && (storeState === "ready" || storeState === "empty")
        && pendingAction === ""
    readonly property var entries:
        notesSnapshot && Array.isArray(notesSnapshot.items)
        ? notesSnapshot.items : []
    readonly property bool typing:
        titleInput.activeFocus || bodyInput.activeFocus
    onTypingChanged: textFocusChanged(typing)

    readonly property bool titleValid:
        titleInput.text.trim().length > 0
        && titleInput.text.trim().length <= 120
        && !/[\x00-\x1f\x7f]/.test(titleInput.text)
    readonly property bool bodyValid:
        bodyInput.text.length <= 8192
        && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(bodyInput.text)
    readonly property bool draftDirty:
        titleInput.text !== openedTitle || bodyInput.text !== openedBody
    readonly property bool canSave:
        writable && editorOpen && titleValid && bodyValid
        && (openedId === "" || draftDirty)
    readonly property string statusLine: {
        if (storeState === "saving")
            return "NOTES // SAVING // NOT YET CONFIRMED";
        if (storeState === "unsupported" || storeState === "error")
            return "NOTES // " + storeState.toUpperCase() + " // WRITES LOCKED";
        if (storeState === "loading")
            return "NOTES // LOADING";
        if (feedback.length)
            return "NOTES // " + feedback;
        if (editorOpen)
            return openedId === "" ? "NOTES // UNSAVED NEW DRAFT"
                : "NOTES // REV " + openedRevision
                  + (draftDirty ? " // UNSAVED CHANGES" : " // SAVED");
        return "NOTES // " + entries.length + " CONFIRMED";
    }

    function clearEditor() {
        editorOpen = false;
        openedId = "";
        openedRevision = 0;
        openedTitle = "";
        openedBody = "";
        titleInput.text = "";
        bodyInput.text = "";
        deleteArmed = false;
        discardArmed = false;
        feedback = "";
    }

    function newNote() {
        if (!writable || editorOpen)
            return;
        clearEditor();
        editorOpen = true;
        titleInput.forceActiveFocus();
    }

    function openNote(item) {
        if (!writable || editorOpen || !item || typeof item.id !== "string")
            return;
        // getNote is detached and includes the revision at open time.
        const detail = notesStore.getNote(item.id);
        if (!detail || detail.id !== item.id
                || typeof detail.revision !== "number") {
            feedback = "NOTE NOT AVAILABLE";
            return;
        }
        clearEditor();
        openedId = detail.id;
        openedRevision = detail.revision;
        openedTitle = detail.title;
        openedBody = detail.body;
        titleInput.text = detail.title;
        bodyInput.text = detail.body;
        editorOpen = true;
    }

    function exitEditor() {
        if (!editorOpen || pendingAction !== "")
            return;
        if (draftDirty && !discardArmed) {
            discardArmed = true;
            deleteArmed = false;
            feedback = "PRESS BACK AGAIN TO DISCARD";
            return;
        }
        clearEditor();
    }

    function saveDraft() {
        if (!canSave)
            return;
        const title = titleInput.text.trim();
        const body = bodyInput.text;
        const action = openedId === "" ? "create" : "update";
        pendingAction = action;
        deleteArmed = false;
        discardArmed = false;
        feedback = "";
        // A true result only starts an asynchronous write. No draft is
        // cleared until the singleton transitions out of SAVING on onSaved.
        const started = action === "create"
            ? notesStore.createNote(title, body)
            : notesStore.saveNote(openedId, openedRevision, title, body);
        if (!started) {
            pendingAction = "";
            feedback = "SAVE REJECTED // CHECK REVISION";
        }
    }

    function deleteNote() {
        if (!writable || openedId === "")
            return;
        if (!deleteArmed) {
            deleteArmed = true;
            discardArmed = false;
            feedback = "CONFIRM DELETE";
            return;
        }
        pendingAction = "delete";
        feedback = "";
        // Revision-safe, deliberately confirmed. First DEL never writes.
        if (!notesStore.deleteNote(openedId, openedRevision, true)) {
            pendingAction = "";
            feedback = "DELETE REJECTED // CHECK REVISION";
        }
    }

    function reloadNotes() {
        if (!notesStore || storeState === "saving" || pendingAction !== "")
            return;
        // Reload is explicit recovery; it must NOT clear a draft/revision.
        if (notesStore.reloadFromDisk()) {
            deleteArmed = false;
            discardArmed = false;
            feedback = editorOpen ? "DRAFT HELD // RECHECK REVISION" : "";
        }
    }

    onNotesSnapshotChanged: {
        if (!pendingAction)
            return;
        if (storeState === "ready" || storeState === "empty") {
            const action = pendingAction;
            pendingAction = "";
            if (action === "delete" || action === "create") {
                clearEditor();
            } else if (action === "update") {
                const updated = notesStore.getNote(openedId);
                if (updated && updated.id === openedId) {
                    openedRevision = updated.revision;
                    openedTitle = updated.title;
                    openedBody = updated.body;
                    // Keep any local draft if typed values differ; avoid a
                    // forced text replacement after an asynchronous save.
                }
                feedback = "";
            }
        } else if (storeState === "error" || storeState === "unsupported") {
            // Failed disk writes retain title, body and original revision.
            pendingAction = "";
            feedback = "SAVE FAILED // DRAFT RETAINED";
        }
    }

    onVisibleChanged: {
        if (!visible) {
            titleInput.focus = false;
            bodyInput.focus = false;
            textFocusChanged(false);
        }
    }

    // List mode: max three recent rows fit the half-width 140px tile.
    Item {
        anchors.fill: parent
        visible: !notesMini.editorOpen

        Row {
            id: listHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: notesMini.densityLevel === 3 ? 30
                    : notesMini.densityLevel === 2 ? 25 : 21
            spacing: 5

            GohuText {
                width: Math.max(20, parent.width - newButton.width
                                - listReloadButton.width - 2 * parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 11
                color: Colors.cyan
                elide: Text.ElideRight
                text: notesMini.storeState === "error"
                      || notesMini.storeState === "unsupported"
                      ? "STORAGE // " + String(notesMini.notesSnapshot.error || "ERROR")
                      : notesMini.entries.length + " RECENT NOTES"
            }

            ActionButton {
                id: listReloadButton
                width: 48
                height: parent.height
                softGlowEnabled: false
                trackLabelGlowLocally: true
                labelPixelSize: 9
                label: "RELOAD"
                available: notesMini.notesStore !== null
                           && notesMini.storeState !== "saving"
                           && notesMini.pendingAction === ""
                onLeftClicked: notesMini.reloadNotes()
            }

            ActionButton {
                id: newButton
                width: 43
                height: parent.height
                softGlowEnabled: false
                trackLabelGlowLocally: true
                labelPixelSize: 10
                label: "NEW"
                available: notesMini.writable && notesMini.entries.length < 100
                onLeftClicked: notesMini.newNote()
            }
        }

        ListView {
            id: noteList
            anchors {
                top: listHeader.bottom
                topMargin: 3
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            spacing: 2
            model: notesMini.entries
            delegate: ActionButton {
                id: noteRow
                required property var modelData
                width: noteList.width
                height: notesMini.densityLevel === 3 ? 45
                        : notesMini.densityLevel === 2 ? 35 : 26
                softGlowEnabled: false
                contentGlowEnabled: false
                idleFillColor: Colors.black
                idleBorderWidth: 0
                hoverBorderWidth: 1
                onLeftClicked: notesMini.openNote(modelData)

                Column {
                    anchors {
                        fill: parent
                        leftMargin: 5
                        rightMargin: 5
                    }
                    spacing: 0
                    GohuText {
                        width: parent.width
                        height: notesMini.densityLevel === 3 ? 24
                                : notesMini.densityLevel === 2 ? 19 : 14
                        font.pixelSize: notesMini.densityLevel === 3 ? 15
                                        : notesMini.densityLevel === 2 ? 13 : 11
                        color: Colors.white
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                        text: String(noteRow.modelData.title || "")
                    }
                    GohuText {
                        width: parent.width
                        height: notesMini.densityLevel === 3 ? 18
                                : notesMini.densityLevel === 2 ? 15 : 12
                        font.pixelSize: notesMini.densityLevel === 3 ? 12
                                        : notesMini.densityLevel === 2 ? 10 : 9
                        color: Colors.cyan
                        opacity: 0.7
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                        text: String(noteRow.modelData.preview || "")
                    }
                }
            }
        }

        GohuText {
            anchors.centerIn: noteList
            width: parent.width
            height: 22
            visible: notesMini.entries.length === 0
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: Colors.orange
            text: notesMini.storeState === "empty" ? "NO NOTES // CLICK NEW"
                  : notesMini.storeState === "loading" ? "LOADING NOTES..."
                  : notesMini.storeState === "unsupported" ? "UNSUPPORTED FILE"
                  : notesMini.storeState === "error" ? "STORAGE LOCKED"
                  : "NO NOTES AVAILABLE"
        }
    }

    // Editor: title and body are detached local drafts, not bindings to
    // snapshot items. Save/Delete are user-only, revision-guarded actions.
    Item {
        id: editorPane
        anchors.fill: parent
        visible: notesMini.editorOpen

        Row {
            id: editorHeader
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: notesMini.densityLevel === 3 ? 30
                    : notesMini.densityLevel === 2 ? 25 : 21
            spacing: 5

            Rectangle {
                width: Math.max(20, editorHeader.width
                                - saveButton.width - backButton.width
                                - 2 * editorHeader.spacing)
                height: parent.height
                color: Colors.black
                border.color: titleInput.activeFocus ? Colors.magenta : Colors.cyan
                border.width: 1

                TextInput {
                    id: titleInput
                    anchors.fill: parent
                    anchors.leftMargin: 5
                    anchors.rightMargin: 5
                    verticalAlignment: TextInput.AlignVCenter
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: notesMini.densityLevel === 3 ? 15
                                    : notesMini.densityLevel === 2 ? 13 : 11
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    maximumLength: 120
                    selectByMouse: true
                    clip: true
                    enabled: notesMini.writable
                    onAccepted: notesMini.saveDraft()
                    Keys.onEscapePressed: function(event) {
                        notesMini.exitEditor();
                        event.accepted = true;
                    }
                }
            }

            ActionButton {
                id: saveButton
                width: 43
                height: parent.height
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 10
                label: "SAVE"
                available: notesMini.canSave
                onLeftClicked: notesMini.saveDraft()
            }
            ActionButton {
                id: backButton
                width: 43
                height: parent.height
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 10
                label: notesMini.discardArmed ? "DISCARD" : "BACK"
                available: notesMini.pendingAction === ""
                onLeftClicked: notesMini.exitEditor()
            }
        }

        Rectangle {
            id: bodyFrame
            anchors {
                top: editorHeader.bottom
                topMargin: 3
                left: parent.left
                right: parent.right
                bottom: bottomRow.top
                bottomMargin: 3
            }
            color: Colors.black
            border.color: bodyInput.activeFocus ? Colors.magenta : Colors.cyan
            border.width: 1
            clip: true

            Flickable {
                id: bodyFlick
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: Math.max(height, bodyInput.contentHeight + 4)

                TextEdit {
                    id: bodyInput
                    width: bodyFlick.width
                    height: Math.max(bodyFlick.height, contentHeight + 4)
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: notesMini.densityLevel === 3 ? 15
                                    : notesMini.densityLevel === 2 ? 13 : 11
                    color: Colors.white
                    wrapMode: TextEdit.Wrap
                    textFormat: TextEdit.PlainText
                    selectByMouse: true
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    enabled: notesMini.writable
                    Keys.onEscapePressed: function(event) {
                        notesMini.exitEditor();
                        event.accepted = true;
                    }
                }
            }
        }

        Row {
            id: bottomRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: notesMini.densityLevel === 3 ? 28
                    : notesMini.densityLevel === 2 ? 24 : 20
            spacing: 5

            GohuText {
                width: Math.max(20, parent.width - reloadButton.width
                                - deleteButton.width - cancelDeleteButton.width
                                  * (cancelDeleteButton.visible ? 1 : 0)
                                - (cancelDeleteButton.visible ? 3 : 2) * parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
                color: notesMini.draftDirty ? Colors.orange : Colors.cyan
                elide: Text.ElideRight
                text: notesMini.openedId === "" ? "NEW NOTE"
                      : "REV " + notesMini.openedRevision
                      + (notesMini.draftDirty ? " // DRAFT" : "")
            }
            ActionButton {
                id: reloadButton
                width: 48
                height: parent.height
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 9
                label: "RELOAD"
                available: notesMini.notesStore !== null
                           && notesMini.storeState !== "saving"
                           && notesMini.pendingAction === ""
                onLeftClicked: notesMini.reloadNotes()
            }
            ActionButton {
                id: cancelDeleteButton
                width: 38
                height: parent.height
                visible: notesMini.deleteArmed
                trackLabelGlowLocally: true
                softGlowEnabled: false
                labelPixelSize: 9
                label: "NO"
                available: notesMini.writable
                onLeftClicked: {
                    notesMini.deleteArmed = false;
                    notesMini.feedback = "";
                }
            }
            ActionButton {
                id: deleteButton
                width: 38
                height: parent.height
                trackLabelGlowLocally: true
                softGlowEnabled: false
                destructive: true
                accentColor: Colors.red
                labelPixelSize: 9
                label: notesMini.deleteArmed ? "YES" : "DEL"
                available: notesMini.writable && notesMini.openedId !== ""
                onLeftClicked: notesMini.deleteNote()
            }
        }
    }
}
