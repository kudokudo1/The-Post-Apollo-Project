import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services.publisher
import "../../services/publisher/PublisherTemplatePolicy.js" as TemplatePolicy
import "../../components"

// P1.3 local template editor. No AI rewriter, translation or auto-posting.
// Rendering substitutes verified-by-user text VERBATIM into required slots.
// The resulting COMPOSE draft is editable and must be reviewed before any
// future publishing authorization. Template facts are not legal evidence.
Rectangle {
    id: templatePane
    color: Colors.black
    clip: true

    signal generated(string title, string body)
    property string editingTemplateId: ""
    property string previewBody: ""
    property bool previewValid: false
    property string feedback: "TEMPLATES // LOCAL / MANUAL / NO AI OR POSTING"
    readonly property var snapshot: PublisherTemplateStore.snapshot
    readonly property var categories: ["recruitment","resource","announcement","creator"]

    function invalidatePreview() {
        previewValid = false;
        previewBody = "";
    }
    function loadStarter() {
        editingTemplateId = "";
        var category = categoryChoice.currentText;
        var starter = TemplatePolicy.preset(category);
        templateName.text = category.toUpperCase() + " TEMPLATE";
        languageCode.text = "en";
        patternInput.text = starter.pattern;
        factsInput.text = starter.facts;
        invalidatePreview();
        feedback = "STARTER LOADED // FILL FACTS BEFORE PREVIEW";
    }
    function newTemplate() {
        editingTemplateId = "";
        templateName.text = "";
        categoryChoice.currentIndex = 3;
        languageCode.text = "en";
        patternInput.text = "";
        factsInput.text = "";
        invalidatePreview();
        feedback = "NEW TEMPLATE // NOTHING HAS BEEN SAVED";
    }
    function loadTemplate(row) {
        if (!row || typeof row.id !== "string") return;
        editingTemplateId = row.id;
        templateName.text = row.name;
        categoryChoice.currentIndex = categories.indexOf(row.category);
        languageCode.text = row.language;
        patternInput.text = row.pattern;
        factsInput.text = TemplatePolicy.factLines(row.facts);
        invalidatePreview();
        feedback = "EDITING SAVED " + row.id + " // PREVIEW REQUIRED";
    }
    function runPreview() {
        var result = TemplatePolicy.preview(
            templateName.text.trim(), categoryChoice.currentText,
            languageCode.text.trim(), patternInput.text, factsInput.text);
        if (!result.ok) {
            invalidatePreview();
            feedback = "PREVIEW REFUSED // " + result.reason;
            return;
        }
        previewBody = result.body;
        previewValid = true;
        feedback = "LOCKED FACTS INCLUDED // " + result.facts
                   + " // MANUAL FACT REVIEW REQUIRED";
    }
    function saveTemplate() {
        if (!previewValid) {
            feedback = "PREVIEW FIRST // FACTS MAY HAVE CHANGED";
            return;
        }
        if (PublisherTemplateStore.saveTemplate(
                editingTemplateId, templateName.text.trim(),
                categoryChoice.currentText, languageCode.text.trim(),
                patternInput.text, factsInput.text)) {
            feedback = "SAVE REQUESTED // WAIT FOR LOCAL CONFIRMATION";
        } else {
            feedback = "SAVE REFUSED // " + PublisherTemplateStore.actionError;
        }
    }
    Connections {
        target: PublisherTemplateStore
        function onSavedSuccessfully(templateId) {
            if (!templatePane.visible) return;
            templatePane.editingTemplateId = templateId;
            templatePane.feedback = "LOCAL TEMPLATE SAVED // " + templateId;
        }
        function onStorageStateChanged() {
            if (!templatePane.visible) return;
            if (PublisherTemplateStore.storageState === "error"
                    || PublisherTemplateStore.storageState === "unsupported") {
                templatePane.invalidatePreview();
                templatePane.feedback = "TEMPLATE STORE BLOCKED // "
                    + PublisherTemplateStore.errorCode;
            }
        }
    }

    Flickable {
        id: templateScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 14
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: templateScroll.width
            spacing: 8

            Text {
                width: parent.width
                height: 23
                text: "TEMPLATES // " + templatePane.snapshot.templates.length
                      + " SAVED // " + templatePane.snapshot.state.toUpperCase()
                color: Colors.cyan
                font.pixelSize: 13
            }
            Row {
                width: parent.width
                height: 33
                spacing: 6
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 32
                    label: "NEW TEMPLATE"
                    accentColor: Colors.cyan
                    onTriggered: templatePane.newTemplate()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 32
                    label: "RELOAD SAVED"
                    accentColor: Colors.cyan
                    available: PublisherTemplateStore.storageState !== "saving"
                    onTriggered: {
                        templatePane.invalidatePreview();
                        if (PublisherTemplateStore.reloadFromDisk())
                            templatePane.feedback = "RELOADING TEMPLATE FILE";
                        else
                            templatePane.feedback = "RELOAD REFUSED";
                    }
                }
            }
            Text {
                width: parent.width
                height: 19
                color: Colors.white
                font.pixelSize: 11
                text: "SAVED TEMPLATES // CLICK TO EDIT"
            }
            Flickable {
                id: savedScroll
                width: parent.width
                height: 100
                clip: true
                contentWidth: width
                contentHeight: savedColumn.height
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: savedColumn
                    width: savedScroll.width
                    spacing: 4
                    Repeater {
                        model: templatePane.snapshot.templates
                        ActionButton {
                            required property var modelData
                            width: savedColumn.width
                            height: 32
                            label: modelData.id + " // " + modelData.category.toUpperCase()
                                   + " // " + modelData.name
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            selected: templatePane.editingTemplateId === modelData.id
                            onTriggered: templatePane.loadTemplate(modelData)
                        }
                    }
                }
            }
            TextField {
                id: templateName
                width: parent.width
                height: 35
                placeholderText: "TEMPLATE NAME"
                placeholderTextColor: Colors.cyan
                color: Colors.white
                selectByMouse: true
                onTextChanged: templatePane.invalidatePreview()
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: templateName.activeFocus ? Colors.magenta : Colors.cyan
                }
            }
            Row {
                width: parent.width
                height: 35
                spacing: 6
                ComboBox {
                    id: categoryChoice
                    width: (parent.width - 6) * 0.62
                    height: 34
                    model: templatePane.categories
                    currentIndex: 3
                    onCurrentIndexChanged: templatePane.invalidatePreview()
                }
                TextField {
                    id: languageCode
                    width: (parent.width - 6) * 0.38
                    height: 34
                    text: "en"
                    placeholderText: "LANGUAGE CODE (en)"
                    placeholderTextColor: Colors.cyan
                    color: Colors.white
                    onTextChanged: templatePane.invalidatePreview()
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: languageCode.activeFocus ? Colors.magenta : Colors.cyan
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: 33
                label: "LOAD " + categoryChoice.currentText.toUpperCase() + " STARTER"
                accentColor: Colors.orange
                onTriggered: templatePane.loadStarter()
            }
            Text {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                text: "WORDING // {{key}} INSERTS THE MATCHING LOCKED FACT"
            }
            ScrollView {
                width: parent.width
                height: 142
                clip: true
                TextArea {
                    id: patternInput
                    placeholderText: "Write your message using {{role}}, {{location}}, etc."
                    placeholderTextColor: Colors.cyan
                    wrapMode: TextEdit.Wrap
                    color: Colors.white
                    selectByMouse: true
                    onTextChanged: templatePane.invalidatePreview()
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: patternInput.activeFocus ? Colors.magenta : Colors.cyan
                    }
                }
            }
            Text {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                text: "LOCKED FACTS // ONE key = value PER LINE"
            }
            ScrollView {
                width: parent.width
                height: 120
                clip: true
                TextArea {
                    id: factsInput
                    placeholderText: "role = Field Representative\nlocation = Kentucky\napply_url = https://example.org/apply"
                    placeholderTextColor: Colors.cyan
                    wrapMode: TextEdit.Wrap
                    color: Colors.white
                    selectByMouse: true
                    onTextChanged: templatePane.invalidatePreview()
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: factsInput.activeFocus ? Colors.magenta : Colors.cyan
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: 35
                label: "VALIDATE & PREVIEW"
                accentColor: Colors.cyan
                onTriggered: templatePane.runPreview()
            }
            Rectangle {
                width: parent.width
                height: 145
                color: Colors.black
                border.width: 1
                border.color: templatePane.previewValid ? Colors.magenta : Colors.orange
                clip: true
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 6
                    TextArea {
                        readOnly: true
                        text: templatePane.previewValid ? templatePane.previewBody
                             : "PREVIEW NOT VERIFIED.\nMissing, malformed, duplicated or omitted facts block rendering."
                        color: Colors.white
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                    }
                }
            }
            Row {
                width: parent.width
                height: 36
                spacing: 6
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 35
                    label: "SAVE TEMPLATE"
                    accentColor: Colors.magenta
                    available: templatePane.previewValid && templatePane.snapshot.writable
                    onTriggered: templatePane.saveTemplate()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 35
                    label: "USE IN COMPOSE"
                    accentColor: Colors.cyan
                    available: templatePane.previewValid
                    onTriggered: templatePane.generated(
                        templateName.text.trim(), templatePane.previewBody)
                }
            }
            Text {
                width: parent.width
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
                text: templatePane.feedback
            }
            Text {
                width: parent.width
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
                text: "Only substitution is locked. Compose remains editable. "
                      + "No claims are externally verified, translated, AI rewritten or published."
            }
        }
    }
}
