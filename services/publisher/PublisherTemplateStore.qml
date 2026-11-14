pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "PublisherTemplatePolicy.js" as Policy

// P1.3 separate, local-only template writer. Facts are locked during preview
// substitution; this neither authenticates claims nor grants posting authority.
Scope {
    id: templates
    readonly property string storagePath:
        Quickshell.dataDir + "/publisher-templates-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string actionError: ""
    property var document: Policy.emptyDocument()
    property var pendingDocument: null
    property string pendingTemplateId: ""
    readonly property var snapshot: Policy.view(storageState, document, errorCode)
    signal savedSuccessfully(string templateId)

    function acceptLoaded(raw) {
        if (storageState === "saving") return;
        var result = Policy.parse(raw);
        if (!result.ok) {
            storageState = result.reason === "UNSUPPORTED_VERSION"
                           ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }
        document = result.document;
        storageState = "ready";
        errorCode = "";
    }
    function reloadFromDisk() {
        if (storageState === "saving" || pendingDocument !== null)
            return false;
        storageState = "loading";
        errorCode = "";
        actionError = "";
        templateFile.reload();
        return true;
    }
    function saveTemplate(id, name, category, language, pattern, factLines) {
        if ((storageState !== "ready" && storageState !== "empty")
                || pendingDocument !== null) {
            actionError = "STORAGE_NOT_WRITABLE";
            return false;
        }
        var facts = Policy.parseFactLines(factLines);
        if (!facts.ok) {
            actionError = facts.reason;
            return false;
        }
        var result = Policy.save(document, id, name, category, language,
                                 pattern, facts.facts, Date.now());
        if (!result.ok) {
            actionError = result.reason;
            return false;
        }
        pendingDocument = result.document;
        pendingTemplateId = result.templateId;
        storageState = "saving";
        actionError = "";
        templateFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true; // Admission only. FileView onSaved signals local completion.
    }

    FileView {
        id: templateFile
        path: templates.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: templates.acceptLoaded(templateFile.text())
        onLoadFailed: function(error) {
            if (templates.storageState === "saving") return;
            if (error === FileViewError.FileNotFound) {
                templates.document = Policy.emptyDocument();
                templates.storageState = "empty";
                templates.errorCode = "";
            } else {
                templates.storageState = "error";
                templates.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (templates.storageState !== "saving" || !templates.pendingDocument)
                return;
            templates.document = templates.pendingDocument;
            templates.pendingDocument = null;
            templates.storageState = "ready";
            templates.errorCode = "";
            var completedId = templates.pendingTemplateId;
            templates.pendingTemplateId = "";
            templates.savedSuccessfully(completedId);
        }
        onSaveFailed: function(error) {
            templates.pendingDocument = null;
            templates.pendingTemplateId = "";
            templates.storageState = "error";
            templates.errorCode = "FILE_SAVE_FAILED";
            templates.actionError = "FILE_SAVE_FAILED";
        }
    }
}
