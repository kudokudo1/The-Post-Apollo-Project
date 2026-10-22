pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "ApolloHubNotesPolicy.js" as NotesPolicy

// B8 local quick notes. Deliberate user actions only. This is not The Study
// or a Forest ingestion service; nothing runs in the background.
Scope {
    id: notes

    readonly property string storagePath:
        Quickshell.dataDir + "/apollo-hub-notes-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property var document: NotesPolicy.emptyDocument()
    property var pendingDocument: null

    readonly property var snapshot:
        NotesPolicy.displayList(storageState,document,errorCode)

    // The caller reads a detached copy (not the backing document) when
    // opening a note editor and passes its revision back on explicit SAVE.
    function getNote(id) {
        return NotesPolicy.detail(storageState,document,id);
    }

    function acceptLoaded(raw) {
        if (storageState === "saving")
            return;
        const loaded=NotesPolicy.parse(raw);
        if (!loaded.ok) {
            document=NotesPolicy.emptyDocument();
            storageState=loaded.reason === "UNSUPPORTED_VERSION"
                         ? "unsupported" : "error";
            errorCode=loaded.reason;
            return;
        }
        document=loaded.document;
        storageState=document.notes.length ? "ready" : "empty";
        errorCode="";
    }

    function reloadFromDisk() {
        if (storageState === "saving")
            return false;
        storageState="loading";
        errorCode="";
        notesFile.reload();
        return true;
    }

    function stage(result) {
        if (storageState !== "ready" && storageState !== "empty")
            return false;
        if (!result || result.ok !== true)
            return false;
        pendingDocument=result.document;
        storageState="saving";
        errorCode="";
        // Publish only after an actual successful atomic FileView save.
        notesFile.setText(JSON.stringify(pendingDocument,null,2) + "\n");
        return true;
    }

    function createNote(title, body) {
        return stage(NotesPolicy.create(document,title,body,Date.now()));
    }

    function saveNote(id, expectedRevision, title, body) {
        return stage(NotesPolicy.update(
            document,id,expectedRevision,title,body,Date.now()));
    }

    function deleteNote(id, expectedRevision, confirmed) {
        return stage(NotesPolicy.remove(
            document,id,expectedRevision,confirmed));
    }

    FileView {
        id: notesFile
        path: notes.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: notes.acceptLoaded(notesFile.text())

        onLoadFailed: function(error) {
            if (notes.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                // Missing storage means a new empty notebook. Do not write
                // the file until the operator explicitly creates a note.
                notes.document=NotesPolicy.emptyDocument();
                notes.storageState="empty";
                notes.errorCode="";
            } else {
                notes.storageState="error";
                notes.errorCode="FILE_LOAD_FAILED";
            }
        }

        onSaved: {
            if (notes.storageState !== "saving" || !notes.pendingDocument)
                return;
            notes.document=notes.pendingDocument;
            notes.pendingDocument=null;
            notes.storageState=notes.document.notes.length ? "ready" : "empty";
            notes.errorCode="";
        }

        onSaveFailed: function(error) {
            // No optimistic save: keep last verified document and require
            // explicit recovery/reload before another edit.
            notes.pendingDocument=null;
            notes.storageState="error";
            notes.errorCode="FILE_SAVE_FAILED";
        }
    }
}
